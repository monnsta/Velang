from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, File, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models import AuditLog, Category, ContentPage, Coupon, DescriptionTemplate, Order, Product, User
from app.db.session import get_db
from app.features.auth.deps import require_admin
from app.features.auth.service import google_user, issue_admin_session, revoke
from app.features.catalog.service import categories, product_id, products, save_product
from app.features.content.service import pages, set_value, site
from app.features.media.service import all_media, save as save_media
from app.features.orders.service import commit_stock

router = APIRouter(prefix="/api/admin")


class GoogleBody(BaseModel):
	credential: str


class SiteBody(BaseModel):
	key: str
	value: object


class ProductBody(BaseModel):
	name: str
	slug: str
	sku: str
	subtitle: str = ""
	description: str = ""
	description_template_id: int | None = None
	product_type: str = "general"
	price: Decimal = Decimal("0")
	compare_at_price: Decimal | None = None
	currency: str = "INR"
	status: str = "draft"
	visibility: str = "public"
	featured: bool = False
	position: int = 0
	stock_count: int = 0
	track_inventory: bool = True
	low_stock_threshold: int = 2
	badge: str = ""
	tags: list[str] = Field(default_factory=list)
	material: str = ""
	care: str = ""
	dimensions: str = ""
	shipping_note: str = ""
	seo_title: str = ""
	seo_description: str = ""
	meta: dict = Field(default_factory=dict)
	category_ids: list[int] = Field(default_factory=list)
	images: list[dict] = Field(default_factory=list)
	variants: list[dict] = Field(default_factory=list)


class CategoryBody(BaseModel):
	name: str
	slug: str
	description: str = ""
	image_path: str = ""
	position: int = 0
	is_visible: bool = True
	seo_title: str = ""
	seo_description: str = ""
	meta: dict = Field(default_factory=dict)


class TemplateBody(BaseModel):
	name: str
	product_type: str = "general"
	body_markdown: str
	is_active: bool = True


class PageBody(BaseModel):
	slug: str
	title: str
	body_markdown: str
	active: bool = True
	meta: dict = Field(default_factory=dict)


class CouponBody(BaseModel):
	code: str
	discount_type: str = "percent"
	value: Decimal
	minimum_order_value: Decimal = Decimal("0")
	max_discount: Decimal | None = None
	starts_at: datetime | None = None
	expires_at: datetime | None = None
	usage_limit: int | None = None
	active: bool = True


class StatusBody(BaseModel):
	status: str


class UserBody(BaseModel):
	is_active: bool | None = None
	is_admin: bool | None = None


async def audit(db: AsyncSession, user: User, action: str, entity_type="", entity_id="", details=None):
	db.add(AuditLog(user_id=user.id, action=action, entity_type=entity_type, entity_id=entity_id, details=details or {}))
	await db.flush()


@router.get("/config")
async def admin_config():
	return {"google_web_client_id": settings.google_web_client_id}


@router.post("/login/google")
async def admin_login(body: GoogleBody, db: AsyncSession = Depends(get_db)):
	try:
		user = await google_user(db, body.credential)
	except PermissionError as exc:
		raise HTTPException(403, str(exc)) from exc
	if user.email not in settings.admin_email_set:
		raise HTTPException(403, "This Google account is not allowed to administer Velang")
	user.is_admin = True
	token, session = await issue_admin_session(db, user)
	await db.commit()
	return {"ok": True, "token": token, "expires_at": session.expires_at.isoformat(), "user": {"email": user.email, "name": user.name}}


@router.post("/logout")
async def admin_logout(authorization: str | None = Header(default=None), db: AsyncSession = Depends(get_db)):
	if authorization and authorization.startswith("Bearer "):
		await revoke(db, authorization[7:].strip())
		await db.commit()
	return {"ok": True}


@router.get("/dashboard")
async def dashboard(user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	return {
		"admin": {"email": user.email, "name": user.name},
		"counts": {
			"products": int((await db.execute(select(func.count(Product.id)))).scalar_one()),
			"categories": int((await db.execute(select(func.count(Category.id)))).scalar_one()),
			"orders": int((await db.execute(select(func.count(Order.id)))).scalar_one()),
			"users": int((await db.execute(select(func.count(User.id)))).scalar_one()),
		},
	}


@router.get("/products")
async def list_products(user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	rows = [{"id": p.id, "name": p.name, "slug": p.slug, "sku": p.sku, "price": str(p.price), "status": p.status, "featured": p.featured, "stock_count": p.stock_count} for p in await products(db, 500, active_only=False)]
	return {"products": rows}


@router.get("/products/{product_value}")
async def get_product(product_value: int, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	p = await product_id(db, product_value)
	if not p:
		raise HTTPException(404, "Product not found")
	return {
		"id": p.id, "name": p.name, "slug": p.slug, "sku": p.sku, "subtitle": p.subtitle,
		"description": p.description, "description_template_id": p.description_template_id,
		"product_type": p.product_type, "price": str(p.price),
		"compare_at_price": str(p.compare_at_price) if p.compare_at_price is not None else None,
		"currency": p.currency, "status": p.status, "visibility": p.visibility, "featured": p.featured,
		"position": p.position, "stock_count": p.stock_count, "track_inventory": p.track_inventory,
		"low_stock_threshold": p.low_stock_threshold, "badge": p.badge, "tags": p.tags or [],
		"material": p.material, "care": p.care, "dimensions": p.dimensions,
		"shipping_note": p.shipping_note, "seo_title": p.seo_title, "seo_description": p.seo_description,
		"meta": p.meta or {}, "category_ids": [x.category_id for x in p.categories],
		"images": [{"path": x.path, "alt_text": x.alt_text} for x in p.images],
		"variants": [{"name": x.name, "sku": x.sku, "price": str(x.price) if x.price is not None else None, "stock_count": x.stock_count, "meta": x.meta or {}} for x in p.variants],
	}


@router.post("/products")
async def create_product(body: ProductBody, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	p = await save_product(db, body.model_dump())
	await audit(db, user, "product.create", "product", str(p.id), {"name": p.name})
	await db.commit()
	return {"ok": True, "id": p.id}


@router.put("/products/{product_value}")
async def update_product(product_value: int, body: ProductBody, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	p = await save_product(db, body.model_dump(), product_value)
	if not p:
		raise HTTPException(404, "Product not found")
	await audit(db, user, "product.update", "product", str(p.id), {"name": p.name})
	await db.commit()
	return {"ok": True}


@router.delete("/products/{product_value}")
async def delete_product(product_value: int, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	p = await db.get(Product, product_value)
	if not p:
		raise HTTPException(404, "Product not found")
	await audit(db, user, "product.delete", "product", str(p.id), {"name": p.name})
	await db.delete(p)
	await db.commit()
	return {"ok": True}


@router.get("/categories")
async def list_categories(user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	rows = [{"id": x.id, "name": x.name, "slug": x.slug, "visible": x.is_visible, "position": x.position, "description": x.description, "image_path": x.image_path, "seo_title": x.seo_title, "seo_description": x.seo_description, "meta": x.meta or {}} for x in await categories(db)]
	return {"categories": rows}


@router.post("/categories")
async def create_category(body: CategoryBody, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	row = Category(**body.model_dump())
	db.add(row)
	await db.flush()
	await audit(db, user, "category.create", "category", str(row.id), {"name": row.name})
	await db.commit()
	return {"ok": True, "id": row.id}


@router.put("/categories/{value}")
async def update_category(value: int, body: CategoryBody, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	row = await db.get(Category, value)
	if not row:
		raise HTTPException(404, "Category not found")
	for key, val in body.model_dump().items():
		setattr(row, key, val)
	await audit(db, user, "category.update", "category", str(row.id), {"name": row.name})
	await db.commit()
	return {"ok": True}


@router.delete("/categories/{value}")
async def delete_category(value: int, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	row = await db.get(Category, value)
	if not row:
		raise HTTPException(404, "Category not found")
	await audit(db, user, "category.delete", "category", str(row.id), {"name": row.name})
	await db.delete(row)
	await db.commit()
	return {"ok": True}


@router.get("/templates")
async def get_templates(user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	rows = list((await db.execute(select(DescriptionTemplate).order_by(DescriptionTemplate.name))).scalars().all())
	return {"templates": [{"id": x.id, "name": x.name, "product_type": x.product_type, "body_markdown": x.body_markdown, "is_active": x.is_active} for x in rows]}


@router.post("/templates")
async def create_template(body: TemplateBody, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	row = DescriptionTemplate(**body.model_dump())
	db.add(row)
	await db.flush()
	await audit(db, user, "template.create", "description_template", str(row.id), {"name": row.name})
	await db.commit()
	return {"ok": True, "id": row.id}


@router.put("/templates/{value}")
async def update_template(value: int, body: TemplateBody, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	row = await db.get(DescriptionTemplate, value)
	if not row:
		raise HTTPException(404, "Template not found")
	for key, val in body.model_dump().items():
		setattr(row, key, val)
	await audit(db, user, "template.update", "description_template", str(row.id), {"name": row.name})
	await db.commit()
	return {"ok": True}


@router.delete("/templates/{value}")
async def delete_template(value: int, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	row = await db.get(DescriptionTemplate, value)
	if not row:
		raise HTTPException(404, "Template not found")
	await audit(db, user, "template.delete", "description_template", str(row.id), {"name": row.name})
	await db.delete(row)
	await db.commit()
	return {"ok": True}


@router.get("/pages")
async def get_pages(user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	return {"pages": [{"id": x.id, "slug": x.slug, "title": x.title, "body_markdown": x.body_markdown, "active": x.active, "meta": x.meta or {}} for x in await pages(db)]}


@router.post("/pages")
async def create_page(body: PageBody, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	row = ContentPage(**body.model_dump())
	db.add(row)
	await db.flush()
	await audit(db, user, "page.create", "content_page", str(row.id), {"slug": row.slug})
	await db.commit()
	return {"ok": True, "id": row.id}


@router.put("/pages/{value}")
async def update_page(value: int, body: PageBody, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	row = await db.get(ContentPage, value)
	if not row:
		raise HTTPException(404, "Page not found")
	for key, val in body.model_dump().items():
		setattr(row, key, val)
	await audit(db, user, "page.update", "content_page", str(row.id), {"slug": row.slug})
	await db.commit()
	return {"ok": True}


@router.delete("/pages/{value}")
async def delete_page(value: int, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	row = await db.get(ContentPage, value)
	if not row:
		raise HTTPException(404, "Page not found")
	await audit(db, user, "page.delete", "content_page", str(row.id), {"slug": row.slug})
	await db.delete(row)
	await db.commit()
	return {"ok": True}


@router.get("/site")
async def get_site(user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	return await site(db)


@router.put("/site")
async def update_site(body: SiteBody, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	await set_value(db, body.key.strip(), body.value)
	await audit(db, user, "site.update", "site_setting", body.key.strip())
	await db.commit()
	return {"ok": True}


@router.get("/orders")
async def get_orders(user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	rows = list((await db.execute(select(Order).order_by(Order.id.desc()))).scalars().all())
	return {"orders": [{"id": x.id, "number": x.number, "user_id": x.user_id, "status": x.status, "payment_status": x.payment_status, "total": str(x.total), "currency": x.currency, "created_at": x.created_at.isoformat()} for x in rows]}


@router.put("/orders/{value}/status")
async def update_order_status(value: int, body: StatusBody, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	row = await db.get(Order, value)
	if not row:
		raise HTTPException(404, "Order not found")
	row.status = body.status
	await audit(db, user, "order.status", "order", str(row.id), {"status": row.status})
	await db.commit()
	return {"ok": True}


@router.put("/orders/{value}/payment")
async def update_payment(value: int, body: StatusBody, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	row = await db.get(Order, value)
	if not row:
		raise HTTPException(404, "Order not found")
	was_paid = row.payment_status == "paid"
	row.payment_status = body.status
	if body.status == "paid" and not was_paid:
		await commit_stock(db, value)
	await audit(db, user, "order.payment", "order", str(row.id), {"payment_status": row.payment_status})
	await db.commit()
	return {"ok": True}


@router.get("/users")
async def get_users(user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	rows = list((await db.execute(select(User).order_by(User.id.desc()))).scalars().all())
	return {"users": [{"id": x.id, "email": x.email, "name": x.name, "is_admin": x.is_admin, "is_active": x.is_active} for x in rows]}


@router.put("/users/{value}")
async def update_user(value: int, body: UserBody, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	row = await db.get(User, value)
	if not row:
		raise HTTPException(404, "User not found")
	if body.is_active is not None:
		row.is_active = body.is_active
	if body.is_admin is not None:
		row.is_admin = body.is_admin
	await audit(db, user, "user.update", "user", str(row.id), {"is_active": row.is_active, "is_admin": row.is_admin})
	await db.commit()
	return {"ok": True}


@router.get("/coupons")
async def get_coupons(user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	rows = list((await db.execute(select(Coupon).order_by(Coupon.id.desc()))).scalars().all())
	return {"coupons": [{"id": x.id, "code": x.code, "discount_type": x.discount_type, "value": str(x.value), "minimum_order_value": str(x.minimum_order_value), "max_discount": str(x.max_discount) if x.max_discount is not None else None, "active": x.active, "used": x.used_count, "usage_limit": x.usage_limit} for x in rows]}


@router.post("/coupons")
async def create_coupon(body: CouponBody, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	data = body.model_dump()
	data["code"] = data["code"].strip().upper()
	row = Coupon(**data)
	db.add(row)
	await db.flush()
	await audit(db, user, "coupon.create", "coupon", str(row.id), {"code": row.code})
	await db.commit()
	return {"ok": True, "id": row.id}


@router.put("/coupons/{value}")
async def update_coupon(value: int, body: CouponBody, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	row = await db.get(Coupon, value)
	if not row:
		raise HTTPException(404, "Coupon not found")
	data = body.model_dump()
	data["code"] = data["code"].strip().upper()
	for key, val in data.items():
		setattr(row, key, val)
	await audit(db, user, "coupon.update", "coupon", str(row.id), {"code": row.code})
	await db.commit()
	return {"ok": True}


@router.delete("/coupons/{value}")
async def delete_coupon(value: int, user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	row = await db.get(Coupon, value)
	if not row:
		raise HTTPException(404, "Coupon not found")
	await audit(db, user, "coupon.delete", "coupon", str(row.id), {"code": row.code})
	await db.delete(row)
	await db.commit()
	return {"ok": True}


@router.get("/media")
async def get_media(user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	return {"media": [{"id": x.id, "filename": x.filename, "path": x.path, "mime_type": x.mime_type, "size_bytes": x.size_bytes, "alt_text": x.alt_text} for x in await all_media(db)]}


@router.post("/media")
async def upload_media(file: UploadFile = File(...), alt_text: str = "", user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	content = await file.read()
	if len(content) > 20 * 1024 * 1024:
		raise HTTPException(413, "File too large")
	row = await save_media(db, file.filename or "upload.bin", content, alt_text)
	await audit(db, user, "media.upload", "media", str(row.id), {"filename": row.filename})
	await db.commit()
	return {"ok": True, "id": row.id, "path": row.path}


@router.get("/audit")
async def get_audit(user=Depends(require_admin), db: AsyncSession = Depends(get_db)):
	rows = list((await db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(100))).scalars().all())
	return {"audit": [{"id": x.id, "action": x.action, "entity_type": x.entity_type, "entity_id": x.entity_id, "details": x.details or {}, "created_at": x.created_at.isoformat()} for x in rows]}
