"""Velang application module.

Provide the implementation for this part of the storefront or service layer.
"""
from decimal import Decimal

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.markdown import render
from app.core.template_fields import prepare_template_field_values
from app.core.site import get_site
from app.db.models import Order, Product
from app.db.session import get_db
from app.features.addresses.service import list_all
from app.features.auth.deps import current_user
from app.features.cart.service import cart_items
from app.features.catalog.service import categories, category, product, products
from app.features.content.service import page, page_content_fields, pages as database_pages, static_pages

router = APIRouter()
templates = Jinja2Templates(directory="server/app/templates")

GET_DB = Depends(get_db)


def ctx(request: Request, site_data: dict, title: str, **extra):
	data = {"request": request, "site": site_data, "title": title}
	data.update(extra)
	return data


async def page_ctx(request: Request, db: AsyncSession, title: str, **extra):
	"""Build shared storefront context, including the category-only navigation tree."""
	site_data = await get_site(db)
	user = await current_user(request, db)
	cart_count = 0
	if user:
		items, _ = await cart_items(db, user.id)
		cart_count = sum(item.quantity for item in items)
	all_categories = await categories(db, True)
	by_id = {item.id: item for item in all_categories}
	nav_children = {}
	nav_categories = []
	for item in all_categories:
		parent = by_id.get(item.parent_id) if item.parent_id else None
		# The template consumes slugs for its child lookup, while the database stores
		# stable integer parent IDs so renaming a category never breaks the tree.
		item.parent_slug = parent.slug if parent else ""
		if parent:
			nav_children.setdefault(parent.slug, []).append(item)
		nav_categories.append(item)
	# Merge file-backed built-ins with custom database pages. Previously only the
	# Markdown files appeared in the footer, so admin-created pages were invisible.
	public_pages = {item["slug"]: {"slug": item["slug"], "title": item["title"]}
		for item in static_pages() if item.get("active", True)}
	for item in await database_pages(db):
		if item.active and item.slug not in public_pages:
			public_pages[item.slug] = {"slug": item.slug, "title": item.title}
	page_links = [
		{"href": f"/pages/{item['slug']}", "label": item["title"], "external": False}
		for item in sorted(public_pages.values(), key=lambda value: value["slug"])
	]
	footer_links = []
	seen_hrefs = set()
	for item in site_data.get("footer", []) or []:
		if not isinstance(item, dict):
			continue
		href = str(item.get("href") or "").strip()
		label = str(item.get("label") or "").strip()
		if not href or not label or href in seen_hrefs:
			continue
		if not ((href.startswith("/") and not href.startswith("//")) or href.startswith("https://") or href.startswith("http://") or href.startswith("mailto:")):
			continue
		seen_hrefs.add(href)
		footer_links.append({"href": href, "label": label, "external": href.startswith(("https://", "http://", "mailto:"))})
	for item in page_links:
		if item["href"] not in seen_hrefs:
			seen_hrefs.add(item["href"])
			footer_links.append(item)
	return ctx(
		request, site_data, title, user=user, cart_count=cart_count,
		static_pages=list(public_pages.values()), footer_links=footer_links,
		now_year=__import__("datetime").datetime.now().year,
		nav_categories=nav_categories, nav_category_children=nav_children, **extra
	)


async def rendered_description(row: Product, site_data: dict | None = None):
	"""Render a product description with template-defined, type-aware values."""
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
	context = {"product": product_data, "site": site_data or {}}
	if row.description_template:
		values = (row.meta or {}).get("template_values", {})
		product_data["fields"] = prepare_template_field_values(
			row.description_template.fields_schema or [], values
		)
		return render(row.description_template.body_markdown, context)
	return render(row.description, context)


@router.get("/", response_class=HTMLResponse)
async def home(request: Request, db: AsyncSession = GET_DB):
	"""Render the complete product catalogue as the storefront landing page."""
	rows = await products(db, limit=500)
	return templates.TemplateResponse(
		request,
		"pages/store/home.html",
		await page_ctx(request, db, "Store", products=rows),
	)


@router.get("/shop", response_class=HTMLResponse)
async def shop(
	request: Request,
	q: str = "",
	db: AsyncSession = GET_DB,
):
	"""Render the shop storefront page."""
	rows = await products(db, limit=96, search=q)
	return templates.TemplateResponse(
		request,
		"pages/store/shop.html",
		await page_ctx(request, db, "Shop", products=rows, query=q),
	)


@router.get("/search", response_class=HTMLResponse)
async def search(request: Request, q: str = "", db: AsyncSession = GET_DB):
	"""Render the search storefront page."""
	return await shop(request, q, db)


@router.get("/category/{slug}", response_class=HTMLResponse)
async def category_page(request: Request, slug: str, db: AsyncSession = GET_DB):
	"""Render the category page storefront page."""
	group = await category(db, slug)
	if not group or not group.is_visible:
		return templates.TemplateResponse(
			request,
			"pages/store/404.html",
			await page_ctx(request, db, "Not found"),
			status_code=404,
		)
	return templates.TemplateResponse(
		request,
		"pages/store/category.html",
		await page_ctx(
			request,
			db,
			group.name,
			category=group,
			products=await products(db, 96, category_id=group.id),
		),
	)


@router.get("/product/{slug}", response_class=HTMLResponse)
async def product_page(request: Request, slug: str, db: AsyncSession = GET_DB):
	"""Render the product page storefront page."""
	row = await product(db, slug)
	if not row or row.status != "active" or row.visibility != "public":
		return templates.TemplateResponse(
			request,
			"pages/store/404.html",
			await page_ctx(request, db, "Not found"),
			status_code=404,
		)
	return templates.TemplateResponse(
		request,
		"pages/store/product.html",
		await page_ctx(
			request,
			db,
			row.name,
			product=row,
			rendered_description=await rendered_description(row, await get_site(db)),
		),
	)


@router.get("/cart", response_class=HTMLResponse)
async def cart_page(request: Request, db: AsyncSession = GET_DB):
	"""Render the cart page storefront page."""
	user = await current_user(request, db)
	if not user:
		return RedirectResponse("/login?next=/cart", 303)
	items, lookup = await cart_items(db, user.id)
	total = sum(
		(lookup[x.id].price * x.quantity for x in items if lookup[x.id]), Decimal(0)
	)
	currencies = {lookup[x.id].currency for x in items if lookup[x.id]}
	cart_currency = next(iter(currencies), "INR") if len(currencies) <= 1 else "INR"
	mixed_currency = len(currencies) > 1
	return templates.TemplateResponse(
		request,
		"pages/account/cart.html",
		await page_ctx(
			request,
			db,
			"Cart",
			items=items,
			products=lookup,
			total=total,
			cart_currency=cart_currency,
			mixed_currency=mixed_currency,
		),
	)


@router.get("/checkout", response_class=HTMLResponse)
async def checkout_page(request: Request, db: AsyncSession = GET_DB):
	"""Render the checkout page storefront page."""
	user = await current_user(request, db)
	if not user:
		return RedirectResponse("/login?next=/checkout", 303)
	items, lookup = await cart_items(db, user.id)
	if not items:
		return RedirectResponse("/cart", 303)
	addresses = await list_all(db, user.id)
	total = sum(
		(lookup[x.id].price * x.quantity for x in items if lookup[x.id]), Decimal(0)
	)
	currencies = {lookup[x.id].currency for x in items if lookup[x.id]}
	cart_currency = next(iter(currencies), "INR") if len(currencies) <= 1 else "INR"
	mixed_currency = len(currencies) > 1
	return templates.TemplateResponse(
		request,
		"pages/account/checkout.html",
		await page_ctx(
			request,
			db,
			"Checkout",
			items=items,
			products=lookup,
			addresses=addresses,
			total=total,
			cart_currency=cart_currency,
			mixed_currency=mixed_currency,
		),
	)


@router.get("/account", response_class=HTMLResponse)
async def account_page(request: Request, db: AsyncSession = GET_DB):
	"""Render the account page storefront page."""
	user = await current_user(request, db)
	if not user:
		return RedirectResponse("/login?next=/account", 303)
	orders = list(
		(
			await db.execute(
				select(Order)
				.where(Order.user_id == user.id)
				.order_by(Order.id.desc())
				.limit(10)
			)
		)
		.scalars()
		.all()
	)
	return templates.TemplateResponse(
		request,
		"pages/account/account.html",
		await page_ctx(request, db, "Account", orders=orders),
	)


@router.get("/orders", response_class=HTMLResponse)
async def orders_page(request: Request, db: AsyncSession = GET_DB):
	"""Render the orders page storefront page."""
	user = await current_user(request, db)
	if not user:
		return RedirectResponse("/login?next=/orders", 303)
	orders = list(
		(
			await db.execute(
				select(Order).where(Order.user_id == user.id).order_by(Order.id.desc())
			)
		)
		.scalars()
		.all()
	)
	return templates.TemplateResponse(
		request,
		"pages/account/orders.html",
		await page_ctx(request, db, "Orders", orders=orders),
	)


@router.get("/orders/{number}", response_class=HTMLResponse)
async def order_detail_page(request: Request, number: str, db: AsyncSession = GET_DB):
	"""Render the order detail page storefront page."""
	user = await current_user(request, db)
	if not user:
		return RedirectResponse("/login?next=/orders/" + number, 303)
	row = (
		await db.execute(
			select(Order).where(Order.number == number, Order.user_id == user.id)
		)
	).scalar_one_or_none()
	if not row:
		return templates.TemplateResponse(
			request,
			"pages/store/404.html",
			await page_ctx(request, db, "Not found"),
			status_code=404,
		)
	from app.db.models import OrderItem

	items = list(
		(
			await db.execute(
				select(OrderItem)
				.where(OrderItem.order_id == row.id)
				.order_by(OrderItem.id)
			)
		)
		.scalars()
		.all()
	)
	return templates.TemplateResponse(
		request,
		"pages/account/order.html",
		await page_ctx(request, db, row.number, order=row, items=items),
	)


@router.get("/addresses", response_class=HTMLResponse)
async def addresses_page(request: Request, db: AsyncSession = GET_DB):
	"""Render the addresses page storefront page."""
	user = await current_user(request, db)
	if not user:
		return RedirectResponse("/login?next=/addresses", 303)
	return templates.TemplateResponse(
		request,
		"pages/account/addresses.html",
		await page_ctx(request, db, "Addresses", addresses=await list_all(db, user.id)),
	)


@router.get("/pages/{slug:path}", response_class=HTMLResponse)
async def content_page(request: Request, slug: str, db: AsyncSession = GET_DB):
	"""Render the content page storefront page."""
	row = await page(db, slug)
	if not row:
		return templates.TemplateResponse(
			request,
			"pages/store/404.html",
			await page_ctx(request, db, "Not found"),
			status_code=404,
		)
	# Built-in Markdown pages are dictionaries; legacy admin-created pages are
	# SQLAlchemy model instances. Normalize both to the same template contract.
	content_title, content_body = page_content_fields(row, slug)
	return templates.TemplateResponse(
		request,
		"pages/store/content.html",
		await page_ctx(
			request,
			db,
			content_title,
			content=row,
			content_html=render(content_body, {"site": await get_site(db)}),
		),
	)
