from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.markdown import render
from app.core.site import get_site
from app.db.models import Address, Order, Product
from app.db.session import get_db
from app.features.addresses.service import list_all
from app.features.auth.deps import current_user
from app.features.cart.service import cart_items
from app.features.catalog.service import category, categories, product, products
from app.features.content.service import page
from app.features.wishlist.service import products as wishlist_products

router = APIRouter()
templates = Jinja2Templates(directory="server/app/templates")


def ctx(request: Request, site_data: dict, title: str, **extra):
	data = {"request": request, "site": site_data, "title": title}
	data.update(extra)
	return data


async def page_ctx(request: Request, db: AsyncSession, title: str, **extra):
	site_data = await get_site(db)
	user = await current_user(request, db)
	cart_count = 0
	if user:
		items, _ = await cart_items(db, user.id)
		cart_count = sum(item.quantity for item in items)
	return ctx(request, site_data, title, user=user, cart_count=cart_count, **extra)


async def rendered_description(row: Product):
	product_data = {
		"name": row.name,
		"slug": row.slug,
		"sku": row.sku,
		"subtitle": row.subtitle,
		"description": row.description,
		"price": str(row.price),
		"currency": row.currency,
		"product_type": row.product_type,
		"material": row.material,
		"care": row.care,
		"dimensions": row.dimensions,
		"shipping_note": row.shipping_note,
		"tags": row.tags or [],
		"meta": row.meta or {},
	}
	if row.description_template:
		return render(row.description_template.body_markdown, {"product": product_data})
	return render(row.description, {"product": product_data})


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = Depends(get_db)):
	site_data = await get_site(db)
	user = await current_user(request, db)
	cart_count = 0
	if user:
		items, _ = await cart_items(db, user.id)
		cart_count = sum(item.quantity for item in items)
	sections = []
	for block in site_data.get("homepage", []):
		item = dict(block)
		if item.get("type") == "featured_products":
			item["products"] = await products(db, int(item.get("limit", 6)), featured=True)
		elif item.get("type") == "category_strip":
			groups = (await categories(db, True))[:int(item.get("limit", 4))]
			item["categories"] = []
			for group in groups:
				item["categories"].append({"category": group, "preview": await products(db, 2, category_id=group.id)})
		elif item.get("type") == "latest_products":
			item["products"] = await products(db, int(item.get("limit", 8)))
		sections.append(item)
	return templates.TemplateResponse(request, "home.html", ctx(request, site_data, site_data.get("site", {}).get("name", "VELANG"), sections=sections, user=user, cart_count=cart_count))


@router.get("/shop", response_class=HTMLResponse)
async def shop(request: Request, q: str = "", sort: str = "newest", db: AsyncSession = Depends(get_db)):
	rows = await products(db, limit=96, search=q)
	if sort == "price-low":
		rows.sort(key=lambda item: item.price)
	elif sort == "price-high":
		rows.sort(key=lambda item: item.price, reverse=True)
	return templates.TemplateResponse(request, "shop.html", await page_ctx(request, db, "Shop", products=rows, query=q, sort=sort))


@router.get("/search", response_class=HTMLResponse)
async def search(request: Request, q: str = "", db: AsyncSession = Depends(get_db)):
	return await shop(request, q, "newest", db)


@router.get("/collections", response_class=HTMLResponse)
async def collections_page(request: Request, db: AsyncSession = Depends(get_db)):
	groups = await categories(db, True)
	collection_data = []
	for item in groups:
		collection_data.append({"category": item, "preview": await products(db, 4, category_id=item.id)})
	return templates.TemplateResponse(request, "collections.html", await page_ctx(request, db, "Collections", collections=collection_data))


@router.get("/category/{slug}", response_class=HTMLResponse)
async def category_page(request: Request, slug: str, db: AsyncSession = Depends(get_db)):
	group = await category(db, slug)
	if not group or not group.is_visible:
		return templates.TemplateResponse(request, "404.html", await page_ctx(request, db, "Not found"), status_code=404)
	return templates.TemplateResponse(
		request,
		"category.html",
		await page_ctx(request, db, group.name, category=group, products=await products(db, 96, category_id=group.id)),
	)


@router.get("/product/{slug}", response_class=HTMLResponse)
async def product_page(request: Request, slug: str, db: AsyncSession = Depends(get_db)):
	row = await product(db, slug)
	if not row or row.status != "active" or row.visibility != "public":
		return templates.TemplateResponse(request, "404.html", await page_ctx(request, db, "Not found"), status_code=404)
	related = []
	if row.categories:
		related = await products(db, 5, category_id=row.categories[0].category_id)
	related = [item for item in related if item.id != row.id]
	return templates.TemplateResponse(
		request,
		"product.html",
		await page_ctx(request, db, row.name, product=row, rendered_description=await rendered_description(row), related=related),
	)


@router.get("/cart", response_class=HTMLResponse)
async def cart_page(request: Request, db: AsyncSession = Depends(get_db)):
	user = await current_user(request, db)
	if not user:
		return RedirectResponse("/login?next=/cart", 303)
	items, lookup = await cart_items(db, user.id)
	total = sum((lookup[x.id].price * x.quantity for x in items if lookup[x.id]), Decimal("0"))
	return templates.TemplateResponse(request, "cart.html", await page_ctx(request, db, "Cart", items=items, products=lookup, total=total))


@router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request, db: AsyncSession = Depends(get_db)):
	user = await current_user(request, db)
	if not user:
		return RedirectResponse("/login?next=/checkout", 303)
	items, lookup = await cart_items(db, user.id)
	if not items:
		return RedirectResponse("/cart", 303)
	addresses = await list_all(db, user.id)
	total = sum((lookup[x.id].price * x.quantity for x in items if lookup[x.id]), Decimal("0"))
	return templates.TemplateResponse(request, "checkout.html", await page_ctx(request, db, "Checkout", items=items, products=lookup, addresses=addresses, total=total))


@router.get("/wishlist", response_class=HTMLResponse)
async def wishlist_page(request: Request, db: AsyncSession = Depends(get_db)):
	user = await current_user(request, db)
	if not user:
		return RedirectResponse("/login?next=/wishlist", 303)
	return templates.TemplateResponse(request, "shop.html", await page_ctx(request, db, "Wishlist", products=await wishlist_products(db, user.id), query=""))


@router.get("/account", response_class=HTMLResponse)
async def account_page(request: Request, db: AsyncSession = Depends(get_db)):
	user = await current_user(request, db)
	if not user:
		return RedirectResponse("/login?next=/account", 303)
	orders = list((await db.execute(
		select(Order).where(Order.user_id == user.id).order_by(Order.id.desc()).limit(10)
	)).scalars().all())
	return templates.TemplateResponse(request, "account.html", await page_ctx(request, db, "Account", orders=orders))


@router.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request, db: AsyncSession = Depends(get_db)):
	user = await current_user(request, db)
	if not user:
		return RedirectResponse("/login?next=/orders", 303)
	orders = list((await db.execute(
		select(Order).where(Order.user_id == user.id).order_by(Order.id.desc())
	)).scalars().all())
	return templates.TemplateResponse(request, "orders.html", await page_ctx(request, db, "Orders", orders=orders))


@router.get("/orders/{number}", response_class=HTMLResponse)
async def order_detail_page(request: Request, number: str, db: AsyncSession = Depends(get_db)):
	user = await current_user(request, db)
	if not user:
		return RedirectResponse("/login?next=/orders/" + number, 303)
	row = (await db.execute(
		select(Order).where(Order.number == number, Order.user_id == user.id)
	)).scalar_one_or_none()
	if not row:
		return templates.TemplateResponse(request, "404.html", await page_ctx(request, db, "Not found"), status_code=404)
	from app.db.models import OrderItem
	items = list((await db.execute(select(OrderItem).where(OrderItem.order_id == row.id).order_by(OrderItem.id))).scalars().all())
	return templates.TemplateResponse(request, "order.html", await page_ctx(request, db, row.number, order=row, items=items))


@router.get("/addresses", response_class=HTMLResponse)
async def addresses_page(request: Request, db: AsyncSession = Depends(get_db)):
	user = await current_user(request, db)
	if not user:
		return RedirectResponse("/login?next=/addresses", 303)
	return templates.TemplateResponse(request, "addresses.html", await page_ctx(request, db, "Addresses", addresses=await list_all(db, user.id)))


@router.get("/pages/{slug:path}", response_class=HTMLResponse)
async def content_page(request: Request, slug: str, db: AsyncSession = Depends(get_db)):
	row = await page(db, slug)
	if not row:
		return templates.TemplateResponse(request, "404.html", await page_ctx(request, db, "Not found"), status_code=404)
	return templates.TemplateResponse(request, "content.html", await page_ctx(request, db, row.title, content=row, content_html=render(row.body_markdown)))
