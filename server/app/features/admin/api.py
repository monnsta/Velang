"""Velang application module.

Provide the implementation for this part of the storefront or service layer.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
import re
import secrets
import tempfile
from decimal import Decimal
from types import SimpleNamespace
from typing import Literal

from app.core.config import settings
from app.core.site import get_site as load_site_data
from app.db.models import (
	AuditLog,
	Category,
	ContentPage,
	DescriptionTemplate,
	Order,
	Product,
	ProductCategory,
	OrderItem,
	AdminSession,
	Address,
	CartItem,
	User,
)
from app.db.session import get_db
from app.features.auth.deps import require_admin
from app.features.auth.service import (
	development_user,
	google_user,
	issue_admin_session,
	revoke,
)
from app.features.catalog.service import categories, product_id, products, save_product
from app.features.content.service import PAGES_DIR, _static_page, pages, set_value, site, static_pages
from app.features.media.service import UPLOADS, all_media
from app.features.media.service import save as save_media
from app.features.orders.service import commit_stock
from app.web import page_ctx, rendered_description, templates as storefront_templates
from fastapi import APIRouter, Depends, File, Header, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import delete, func, select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/admin")

REQUIRE_ADMIN = Depends(require_admin)
GET_DB = Depends(get_db)
FILE = File(...)


class GoogleBody(BaseModel):
	"""Represent a Google credential exchange request."""
	credential: str


class DevicePairBody(BaseModel):
	key: str
	device_id: str = Field(min_length=16, max_length=128)


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
	price: Decimal = Decimal(0)
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
	special_care: bool = False
	production_notes: str = ""
	seo_title: str = ""
	seo_description: str = ""
	meta: dict = Field(default_factory=dict)
	category_ids: list[int] = Field(default_factory=list)
	images: list[dict] = Field(default_factory=list)
	variants: list[dict] = Field(default_factory=list)

	@field_validator("currency")
	@classmethod
	def validate_currency(cls, value: str) -> str:
		"""Normalize currency codes to the three-letter ISO 4217 shape."""
		code = value.strip().upper()
		if len(code) != 3 or not code.isalpha() or not code.isascii():
			raise ValueError("Currency must be a three-letter ISO 4217 code, such as INR or USD")
		return code


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
	parent_id: int | None = None


class TemplateBody(BaseModel):
	"""Define the description body and the structured values it expects."""
	name: str
	product_type: str = "general"
	body_markdown: str
	fields_schema: list[dict] = Field(default_factory=list)
	is_active: bool = True

	@field_validator("fields_schema")
	@classmethod
	def validate_fields_schema(cls, fields: list[dict]) -> list[dict]:
		if len(fields) > 40:
			raise ValueError("A template can define at most 40 fields")
		cleaned = []
		seen = set()
		for field in fields:
			if not isinstance(field, dict):
				raise ValueError("Each template field must be an object")
			key = str(field.get("key", "")).strip()
			label = str(field.get("label", "")).strip()
			kind = str(field.get("type", "text")).strip().lower()
			if not re.fullmatch(r"[a-zA-Z][a-zA-Z0-9_]{0,63}", key):
				raise ValueError(f"Invalid template field key: {key or '(empty)'}")
			if key in seen:
				raise ValueError(f"Duplicate template field key: {key}")
			if not label or len(label) > 120:
				raise ValueError(f"Field {key} needs a label of 1–120 characters")
			if kind not in {"text", "textarea", "select"}:
				raise ValueError(f"Field {key} type must be text, textarea, or select")
			choices_raw = field.get("choices", [])
			if not isinstance(choices_raw, list):
				raise ValueError(f"Choices for {key} must be a list")
			choices = []
			for choice in choices_raw:
				value = str(choice).strip()
				if value and value not in choices:
					if len(value) > 120:
						raise ValueError(f"Choices for {key} must be 120 characters or fewer")
					choices.append(value)
			if len(choices) > 50:
				raise ValueError(f"Field {key} can have at most 50 choices")
			if kind == "select" and not choices:
				raise ValueError(f"Select field {key} needs at least one choice")
			if kind != "select":
				choices = []
			default_raw = field.get("default", "")
			default = "" if default_raw is None else str(default_raw)[:1000]
			if kind == "select" and default and default not in choices:
				raise ValueError(f"Default for {key} must match one of its choices")
			if kind == "select" and field.get("markdown") is True:
				raise ValueError(f"Select field {key} cannot render Markdown")
			seen.add(key)
			cleaned.append({
				"key": key,
				"label": label,
				"type": kind,
				"markdown": field.get("markdown") is True and kind != "select",
				"required": field.get("required") is True,
				"placeholder": str(field.get("placeholder", ""))[:160],
				"default": default,
				"choices": choices,
			})
		return cleaned


class PageBody(BaseModel):
	slug: str
	title: str
	body_markdown: str
	active: bool = True
	meta: dict = Field(default_factory=dict)


class MarkdownPreviewBody(BaseModel):
	"""Markdown source and optional template context for an admin preview."""
	body_markdown: str = Field(default="", max_length=200000)
	context: dict = Field(default_factory=dict)


class ProductPreviewBody(BaseModel):
	mode: Literal["card", "product"] = "product"
	product: dict = Field(default_factory=dict)
	template: dict = Field(default_factory=dict)


class MediaUpdateBody(BaseModel):
	"""Editable media-library metadata."""
	alt_text: str = Field(default="", max_length=255)


class StatusBody(BaseModel):
	status: str


class MoveBody(BaseModel):
	"""Move a product one slot in the storefront ordering."""
	direction: str

	@field_validator("direction")
	@classmethod
	def validate_direction(cls, value: str) -> str:
		if value not in {"up", "down"}:
			raise ValueError("Direction must be up or down")
		return value


class UserBody(BaseModel):
	is_active: bool | None = None
	is_admin: bool | None = None


class ProductOrderBody(BaseModel):
	"""Complete ordered list of product IDs from the drag-and-drop editor."""
	ids: list[int] = Field(min_length=1, max_length=5000)

	@field_validator("ids")
	@classmethod
	def unique_ids(cls, value: list[int]) -> list[int]:
		if len(value) != len(set(value)):
			raise ValueError("Product order cannot contain duplicate IDs")
		return value


async def audit(
	db: AsyncSession,
	user: User,
	action: str,
	entity_type="",
	entity_id="",
	details=None,
):
	db.add(
		AuditLog(
			user_id=user.id,
			action=action,
			entity_type=entity_type,
			entity_id=entity_id,
			details=details or {},
		)
	)
	await db.flush()


@router.get("/config")
async def admin_config():
	return {
		"google_web_client_id": settings.google_web_client_id,
		"device_pairing_enabled": bool(settings.admin_pairing_key),
		"dev_auth": settings.app_env != "production" and settings.dev_auth,
	}


@router.post("/pair")
async def pair_admin_device(body: DevicePairBody, db: AsyncSession = GET_DB):
	"""Pair an app installation using a server-side bootstrap secret.

	The pairing key is never returned by the server. After pairing, the app stores
	a revocable, expiring bearer token and no longer needs a user account or Google
	sign-in. Keep the bootstrap key private and rotate it after trusted devices pair.
	"""
	if not settings.admin_pairing_key or not secrets.compare_digest(
		body.key.encode("utf-8"), settings.admin_pairing_key.encode("utf-8")
	):
		raise HTTPException(403, "Device pairing key is invalid or pairing is disabled")
	device_hash = hashlib.sha256(body.device_id.encode("utf-8")).hexdigest()[:24]
	email = f"admin-device-{device_hash}@device.invalid"
	user = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
	if user is None:
		user = User(email=email, name="Paired admin device", is_admin=True)
		db.add(user)
		await db.flush()
	else:
		user.is_active = True
		user.is_admin = True
	token, session = await issue_admin_session(db, user)
	# A paired installation behaves like a device credential, not an interactive
	# web login. Use a long lifetime while retaining explicit revocation on logout.
	session.expires_at = datetime.now(timezone.utc) + timedelta(days=3650)
	await db.commit()
	return {"ok": True, "token": token, "expires_at": session.expires_at.isoformat()}


@router.post("/login/google")
async def admin_login(body: GoogleBody, db: AsyncSession = GET_DB):
	try:
		user = await google_user(db, body.credential)
	except PermissionError as exc:
		raise HTTPException(403, str(exc)) from exc
	if user.email not in settings.admin_email_set:
		raise HTTPException(
			403, "This Google account is not allowed to administer Velang"
		)
	user.is_admin = True
	token, session = await issue_admin_session(db, user)
	await db.commit()
	return {
		"ok": True,
		"token": token,
		"expires_at": session.expires_at.isoformat(),
		"user": {"email": user.email, "name": user.name},
	}


@router.post("/login/dev")
async def admin_login_dev(db: AsyncSession = GET_DB):
	if settings.app_env == "production" or not settings.dev_auth:
		raise HTTPException(404, "Development authentication is disabled")
	user = await development_user(db, admin=True)
	token, session = await issue_admin_session(db, user)
	await db.commit()
	return {
		"ok": True,
		"token": token,
		"expires_at": session.expires_at.isoformat(),
		"user": {"email": user.email, "name": user.name},
	}


@router.post("/logout")
async def admin_logout(
	authorization: str | None = Header(default=None), db: AsyncSession = GET_DB
):
	if authorization and authorization.startswith("Bearer "):
		await revoke(db, authorization[7:].strip())
		await db.commit()
	return {"ok": True}


@router.get("/dashboard")
async def dashboard(user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	return {
		"admin": {"email": user.email, "name": user.name},
		"counts": {
			"products": int(
				(await db.execute(select(func.count(Product.id)))).scalar_one()
			),
			"categories": int(
				(await db.execute(select(func.count(Category.id)))).scalar_one()
			),
			"orders": int(
				(await db.execute(select(func.count(Order.id)))).scalar_one()
			),
			"users": int((await db.execute(select(func.count(User.id)))).scalar_one()),
		},
	}


@router.get("/product-options")
async def product_editor_options(user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	"""Return named choices needed by the product editor so staff do not copy IDs."""
	category_rows = await categories(db)
	template_rows = list((await db.execute(
		select(DescriptionTemplate).order_by(DescriptionTemplate.name)
	)).scalars().all())
	return {
		"categories": [{"id": row.id, "name": row.name, "parent_id": row.parent_id,
			"visible": row.is_visible} for row in category_rows],
		"templates": [{"id": row.id, "name": row.name, "product_type": row.product_type,
			"is_active": row.is_active, "body_markdown": row.body_markdown,
			"fields_schema": row.fields_schema or []}
			for row in template_rows],
	}


@router.get("/products")
async def list_products(user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	rows = [
		{
			"id": p.id,
			"name": p.name,
			"slug": p.slug,
			"sku": p.sku,
			"price": str(p.price),
			"currency": p.currency,
			"status": p.status,
			"featured": p.featured,
			"position": p.position,
			"images": [{"path": image.path, "alt_text": image.alt_text} for image in p.images],
			"stock_count": p.stock_count,
			"special_care": p.special_care,
		}
		for p in await products(db, None, active_only=False)
	]
	return {"products": rows}


@router.get("/products/{product_value}")
async def get_product(product_value: int, user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	p = await product_id(db, product_value)
	if not p:
		raise HTTPException(404, "Product not found")
	return {
		"id": p.id,
		"name": p.name,
		"slug": p.slug,
		"sku": p.sku,
		"subtitle": p.subtitle,
		"description": p.description,
		"description_template_id": p.description_template_id,
		"product_type": p.product_type,
		"price": str(p.price),
		"compare_at_price": str(p.compare_at_price)
		if p.compare_at_price is not None
		else None,
		"currency": p.currency,
		"status": p.status,
		"visibility": p.visibility,
		"featured": p.featured,
		"position": p.position,
		"stock_count": p.stock_count,
		"track_inventory": p.track_inventory,
		"low_stock_threshold": p.low_stock_threshold,
		"badge": p.badge,
		"tags": p.tags or [],
		"material": p.material,
		"care": p.care,
		"dimensions": p.dimensions,
		"shipping_note": p.shipping_note,
		"special_care": p.special_care,
		"production_notes": p.production_notes,
		"seo_title": p.seo_title,
		"seo_description": p.seo_description,
		"meta": p.meta or {},
		"category_ids": [x.category_id for x in p.categories],
		"images": [{"path": x.path, "alt_text": x.alt_text} for x in p.images],
		"variants": [
			{
				"name": x.name,
				"sku": x.sku,
				"price": str(x.price) if x.price is not None else None,
				"stock_count": x.stock_count,
				"meta": x.meta or {},
			}
			for x in p.variants
		],
	}


async def _validate_product_template(db: AsyncSession, payload: dict):
	template_id = payload.get("description_template_id")
	if template_id is None:
		return
	template = await db.get(DescriptionTemplate, template_id)
	if template is None:
		raise HTTPException(422, "The selected description template no longer exists")
	meta = payload.get("meta") if isinstance(payload.get("meta"), dict) else {}
	values = meta.get("template_values") if isinstance(meta.get("template_values"), dict) else {}
	for field in template.fields_schema or []:
		if not isinstance(field, dict):
			continue
		key = field.get("key", "")
		label = field.get("label", key)
		value = values.get(key, field.get("default", ""))
		if field.get("required") is True and not str(value or "").strip():
			raise HTTPException(422, f"Template field '{label}' is required")
		if field.get("type") == "select" and str(value or ""):
			choices = field.get("choices", [])
			if not isinstance(choices, list) or value not in choices:
				raise HTTPException(422, f"Choose a valid option for template field '{label}'")


@router.post("/products")
async def create_product(
	body: ProductBody, user=REQUIRE_ADMIN, db: AsyncSession = GET_DB
):
	payload = body.model_dump()
	await _validate_product_template(db, payload)
	p = await save_product(db, payload)
	if p:
		await audit(db, user, "product.create", "product", str(p.id), {"name": p.name})
		await db.commit()
		return {"ok": True, "id": p.id}


@router.put("/products/reorder")
async def reorder_products(
	body: ProductOrderBody, user=REQUIRE_ADMIN, db: AsyncSession = GET_DB
):
	"""Apply a complete drag-and-drop product order atomically."""
	rows = list((await db.execute(select(Product).order_by(Product.position, Product.id.desc()))).scalars().all())
	existing = {row.id for row in rows}
	if set(body.ids) != existing:
		raise HTTPException(409, "The product list changed. Refresh it and try again.")
	by_id = {row.id: row for row in rows}
	for position, product_id in enumerate(body.ids):
		by_id[product_id].position = position
	await audit(db, user, "product.reorder", "product", "", {"count": len(body.ids), "method": "drag_drop"})
	await db.commit()
	return {"ok": True, "count": len(body.ids)}


@router.put("/products/{product_value}")
async def update_product(
	product_value: int,
	body: ProductBody,
	user=REQUIRE_ADMIN,
	db: AsyncSession = GET_DB,
):
	payload = body.model_dump()
	await _validate_product_template(db, payload)
	p = await save_product(db, payload, product_value)
	if not p:
		raise HTTPException(404, "Product not found")
	await audit(db, user, "product.update", "product", str(p.id), {"name": p.name})
	await db.commit()
	return {"ok": True}


@router.put("/products/{product_value}/move")
async def move_product(
	product_value: int,
	body: MoveBody,
	user=REQUIRE_ADMIN,
	db: AsyncSession = GET_DB,
):
	"""Swap a product with its adjacent neighbour in display order."""
	rows = list((await db.execute(select(Product).order_by(Product.position, Product.id.desc()))).scalars().all())
	index = next((i for i, row in enumerate(rows) if row.id == product_value), None)
	if index is None:
		raise HTTPException(404, "Product not found")
	other_index = index - 1 if body.direction == "up" else index + 1
	if other_index < 0 or other_index >= len(rows):
		return {"ok": True, "moved": False}
	rows[index], rows[other_index] = rows[other_index], rows[index]
	# Position values are often equal for old/imported products. Reindex the ordered
	# sequence rather than swapping equal numbers, which would appear to do nothing.
	for position, row in enumerate(rows):
		row.position = position
	current = rows[other_index]
	await audit(db, user, "product.reorder", "product", str(current.id), {"direction": body.direction})
	await db.commit()
	return {"ok": True, "moved": True}


@router.delete("/products/{product_value}")
async def delete_product(
	product_value: int, user=REQUIRE_ADMIN, db: AsyncSession = GET_DB
):
	p = await db.get(Product, product_value)
	if not p:
		raise HTTPException(404, "Product not found")
	has_order_history = (await db.execute(
		select(OrderItem.id).where(OrderItem.product_id == p.id).limit(1)
	)).first()
	if has_order_history:
		raise HTTPException(409, "This product appears in order history. Archive it instead to preserve manufacturing and accounting records.")
	await audit(db, user, "product.delete", "product", str(p.id), {"name": p.name})
	await db.delete(p)
	await db.commit()
	return {"ok": True}


@router.get("/categories")
async def list_categories(user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	rows = [
		{
			"id": x.id,
			"name": x.name,
			"slug": x.slug,
			"parent_id": x.parent_id,
			"visible": x.is_visible,
			"position": x.position,
			"description": x.description,
			"image_path": x.image_path,
			"seo_title": x.seo_title,
			"seo_description": x.seo_description,
			"meta": x.meta or {},
		}
		for x in await categories(db)
	]
	return {"categories": rows}


@router.post("/categories")
async def create_category(
	body: CategoryBody, user=REQUIRE_ADMIN, db: AsyncSession = GET_DB
):
	data = body.model_dump()
	if data["parent_id"] is not None and not await db.get(Category, data["parent_id"]):
		raise HTTPException(422, "Parent category not found")
	row = Category(**data)
	db.add(row)
	await db.flush()
	await audit(
		db, user, "category.create", "category", str(row.id), {"name": row.name}
	)
	await db.commit()
	return {"ok": True, "id": row.id}


@router.put("/categories/{value}")
async def update_category(
	value: int,
	body: CategoryBody,
	user=REQUIRE_ADMIN,
	db: AsyncSession = GET_DB,
):
	row = await db.get(Category, value)
	if not row:
		raise HTTPException(404, "Category not found")
	data = body.model_dump()
	parent_id = data["parent_id"]
	if parent_id == row.id:
		raise HTTPException(422, "A category cannot be its own parent")
	if parent_id is not None:
		parent = await db.get(Category, parent_id)
		if not parent:
			raise HTTPException(422, "Parent category not found")
		seen = {row.id}
		while parent is not None:
			if parent.id in seen:
				raise HTTPException(422, "Category nesting cannot contain a cycle")
			seen.add(parent.id)
			parent = await db.get(Category, parent.parent_id) if parent.parent_id else None
	for key, val in data.items():
		setattr(row, key, val)
	await audit(
		db, user, "category.update", "category", str(row.id), {"name": row.name}
	)
	await db.commit()
	return {"ok": True}


@router.delete("/categories/{value}")
async def delete_category(value: int, user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	row = await db.get(Category, value)
	if not row:
		raise HTTPException(404, "Category not found")
	await audit(
		db, user, "category.delete", "category", str(row.id), {"name": row.name}
	)
	await db.delete(row)
	await db.commit()
	return {"ok": True}


@router.get("/templates")
async def get_templates(user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	rows = list(
		(
			await db.execute(
				select(DescriptionTemplate).order_by(DescriptionTemplate.name)
			)
		)
		.scalars()
		.all()
	)
	assignments = {
		int(template_id): int(count)
		for template_id, count in (await db.execute(
			select(Product.description_template_id, func.count(Product.id))
			.where(Product.description_template_id.is_not(None))
			.group_by(Product.description_template_id)
		)).all()
	}
	return {
		"templates": [
			{
				"id": x.id,
				"name": x.name,
				"product_type": x.product_type,
				"body_markdown": x.body_markdown,
				"fields_schema": x.fields_schema or [],
				"is_active": x.is_active,
				"assigned_products": assignments.get(x.id, 0),
			}
			for x in rows
		]
	}


@router.post("/templates")
async def create_template(
	body: TemplateBody, user=REQUIRE_ADMIN, db: AsyncSession = GET_DB
):
	row = DescriptionTemplate(**body.model_dump())
	db.add(row)
	await db.flush()
	await audit(
		db,
		user,
		"template.create",
		"description_template",
		str(row.id),
		{"name": row.name},
	)
	await db.commit()
	return {"ok": True, "id": row.id}


@router.put("/templates/{value}")
async def update_template(
	value: int,
	body: TemplateBody,
	user=REQUIRE_ADMIN,
	db: AsyncSession = GET_DB,
):
	row = await db.get(DescriptionTemplate, value)
	if not row:
		raise HTTPException(404, "Template not found")
	for key, val in body.model_dump().items():
		setattr(row, key, val)
	await audit(
		db,
		user,
		"template.update",
		"description_template",
		str(row.id),
		{"name": row.name},
	)
	await db.commit()
	return {"ok": True}


@router.delete("/templates/{value}")
async def delete_template(value: int, user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	row = await db.get(DescriptionTemplate, value)
	if not row:
		raise HTTPException(404, "Template not found")
	assigned_product = (await db.execute(
		select(Product.id).where(Product.description_template_id == row.id).limit(1)
	)).first()
	if assigned_product:
		raise HTTPException(409, "This template is assigned to products. Reassign those products before deleting it so their descriptions do not disappear.")
	await audit(
		db,
		user,
		"template.delete",
		"description_template",
		str(row.id),
		{"name": row.name},
	)
	await db.delete(row)
	await db.commit()
	return {"ok": True}


@router.get("/pages")
async def get_pages(user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	"""Return built-in Markdown pages and database-backed custom pages."""
	static_rows = []
	static_slugs = set()
	for item in static_pages(include_inactive=True):
		static_slugs.add(item["slug"])
		static_rows.append({
			"id": -1,
			"source": "static",
			"slug": item["slug"],
			"title": item["title"],
			"body_markdown": item["body_markdown"],
			"active": item.get("active", True),
			"meta": item.get("meta") or {},
		})
	database_rows = []
	for row in await pages(db):
		# Static Markdown takes precedence on the storefront. Avoid showing an
		# unreachable shadow database record as if it were editable content.
		if row.slug in static_slugs:
			continue
		database_rows.append({
			"id": row.id,
			"source": "database",
			"slug": row.slug,
			"title": row.title,
			"body_markdown": row.body_markdown,
			"active": row.active,
			"meta": row.meta or {},
		})
	return {"pages": sorted(static_rows + database_rows, key=lambda row: row["slug"])}


def _validated_page_slug(value: str) -> str:
	"""Accept URL-safe slugs and refuse path traversal or filesystem separators."""
	slug = (value or "").strip().lower()
	if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
		raise HTTPException(422, "Slug must use lowercase letters, numbers, and hyphens only")
	return slug


def _frontmatter_scalar(value: object) -> str:
	"""Encode front matter as a JSON-quoted string for predictable round trips."""
	import json
	text = str(value if value is not None else "").replace("\r", " ").replace("\n", " ")
	return json.dumps(text, ensure_ascii=False)


def _write_static_page(slug: str, body: PageBody) -> str:
	"""Atomically save a built-in Markdown page under its validated slug."""
	os.makedirs(PAGES_DIR, exist_ok=True)
	new_slug = _validated_page_slug(body.slug)
	destination = os.path.realpath(os.path.join(PAGES_DIR, new_slug + ".md"))
	root = os.path.realpath(PAGES_DIR) + os.sep
	if not destination.startswith(root):
		raise HTTPException(422, "Invalid page path")
	old_path = os.path.join(PAGES_DIR, slug + ".md")
	if new_slug != slug and os.path.exists(destination):
		raise HTTPException(409, "A page with that slug already exists")
	metadata = body.meta or {}
	lines = ["---", "title: " + _frontmatter_scalar(body.title), "active: " + ("true" if body.active else "false")]
	for key, value in metadata.items():
		if key in {"title", "active"} or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]{0,60}", str(key)):
			continue
		if isinstance(value, (str, int, float, bool)) or value is None:
			lines.append(f"{key}: " + _frontmatter_scalar(value if value is not None else ""))
	content = "\n".join(lines) + "\n---\n\n" + (body.body_markdown or "").rstrip() + "\n"
	fd, temporary = tempfile.mkstemp(prefix=".velang-page-", suffix=".tmp", dir=PAGES_DIR)
	try:
		with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
			handle.write(content)
		os.replace(temporary, destination)
	finally:
		if os.path.exists(temporary):
			os.remove(temporary)
	if new_slug != slug and os.path.isfile(old_path):
		os.remove(old_path)
	return new_slug


@router.post("/pages")
async def create_page(body: PageBody, user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	"""Create a database-backed custom page."""
	slug = _validated_page_slug(body.slug)
	if _static_page(slug) or (await db.execute(select(ContentPage).where(ContentPage.slug == slug))).scalar_one_or_none():
		raise HTTPException(409, "A page with that slug already exists")
	row = ContentPage(**{**body.model_dump(), "slug": slug})
	db.add(row)
	await db.flush()
	await audit(db, user, "page.create", "content_page", str(row.id), {"slug": row.slug})
	await db.commit()
	return {"ok": True, "id": row.id}


@router.put("/pages/static/{slug}")
async def update_static_page(slug: str, body: PageBody, user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	"""Edit a built-in Markdown page without needing a database migration."""
	slug = _validated_page_slug(slug)
	if not _static_page(slug):
		raise HTTPException(404, "Built-in page not found")
	new_slug = _validated_page_slug(body.slug)
	if new_slug != slug:
		db_conflict = (await db.execute(select(ContentPage).where(ContentPage.slug == new_slug))).scalar_one_or_none()
		if db_conflict:
			raise HTTPException(409, "A page with that slug already exists")
	new_slug = _write_static_page(slug, body)
	await audit(db, user, "page.static.update", "static_page", new_slug, {"previous_slug": slug, "title": body.title, "active": body.active})
	await db.commit()
	return {"ok": True, "slug": new_slug, "source": "static"}


@router.put("/pages/{value}")
async def update_page(value: int, body: PageBody, user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	"""Update a database-backed custom page."""
	row = await db.get(ContentPage, value)
	if not row:
		raise HTTPException(404, "Page not found")
	new_slug = _validated_page_slug(body.slug)
	existing_static = _static_page(new_slug)
	existing_db = (await db.execute(select(ContentPage).where(ContentPage.slug == new_slug, ContentPage.id != row.id))).scalar_one_or_none()
	if (existing_static and new_slug != row.slug) or existing_db:
		raise HTTPException(409, "A page with that slug already exists")
	for key, val in body.model_dump().items():
		setattr(row, key, new_slug if key == "slug" else val)
	await audit(db, user, "page.update", "content_page", str(row.id), {"slug": row.slug})
	await db.commit()
	return {"ok": True}


@router.delete("/pages/{value}")
async def delete_page(value: int, user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	"""Delete a database-backed custom page."""
	row = await db.get(ContentPage, value)
	if not row:
		raise HTTPException(404, "Page not found")
	await audit(db, user, "page.delete", "content_page", str(row.id), {"slug": row.slug})
	await db.delete(row)
	await db.commit()
	return {"ok": True}


@router.post("/markdown-preview")
async def preview_markdown(body: MarkdownPreviewBody, user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	"""Render Markdown with the real storefront variables and production sanitizer."""
	from app.core.markdown import render
	context = {"site": await site(db)}
	context.update(body.context or {})
	return {"html": render(body.body_markdown, context)}


@router.post("/product-preview")
async def preview_product(
	request: Request,
	body: ProductPreviewBody,
	user=REQUIRE_ADMIN,
	db: AsyncSession = GET_DB,
):
	"""Render a draft product through the same templates as the public storefront."""
	data = body.product if isinstance(body.product, dict) else {}
	meta = data.get("meta") if isinstance(data.get("meta"), dict) else {}
	template_data = body.template if isinstance(body.template, dict) else {}

	images = []
	for image in data.get("images", [])[:30] if isinstance(data.get("images"), list) else []:
		if not isinstance(image, dict):
			continue
		path = str(image.get("path", "")).strip()
		if not path:
			continue
		images.append(SimpleNamespace(path=path, alt_text=str(image.get("alt_text", "")).strip()))

	variants = []
	for index, variant in enumerate(data.get("variants", [])[:50] if isinstance(data.get("variants"), list) else []):
		if not isinstance(variant, dict):
			continue
		price = variant.get("price")
		try:
			price = Decimal(str(price)) if price not in (None, "", "null") else None
		except Exception:
			price = None
		try:
			stock_count = max(0, int(variant.get("stock_count", 0)))
		except (TypeError, ValueError):
			stock_count = 0
		variants.append(SimpleNamespace(
			id=index + 1,
			name=str(variant.get("name", f"Option {index + 1}")),
			price=price,
			stock_count=stock_count,
		))

	try:
		price = Decimal(str(data.get("price", "0") or "0"))
	except Exception:
		price = Decimal(0)
	currency = str(data.get("currency", "INR") or "INR").upper()[:3]
	if not re.fullmatch(r"[A-Z]{3}", currency):
		currency = "INR"

	fields_schema = template_data.get("fields_schema", [])
	if not isinstance(fields_schema, list):
		fields_schema = []
	template = None
	if template_data.get("body_markdown"):
		template = SimpleNamespace(
			body_markdown=str(template_data.get("body_markdown", ""))[:200000],
			fields_schema=fields_schema[:40],
		)

	product = SimpleNamespace(
		id=0,
		name=str(data.get("name", "Product preview") or "Product preview")[:200],
		slug=str(data.get("slug", "product-preview") or "product-preview")[:200],
		sku=str(data.get("sku", "PREVIEW") or "PREVIEW")[:120],
		subtitle=str(data.get("subtitle", "") or "")[:255],
		description=str(data.get("description", "") or "")[:200000],
		description_template=template,
		product_type=str(data.get("product_type", "general") or "general")[:100],
		price=price,
		currency=currency,
		status="active",
		visibility="public",
		stock_count=max(0, int(data.get("stock_count", 10) or 0)) if str(data.get("stock_count", 10) or 0).isdigit() else 10,
		track_inventory=bool(data.get("track_inventory", True)),
		images=images,
		variants=variants,
		meta=meta,
		tags=data.get("tags", []) if isinstance(data.get("tags", []), list) else [],
		material=str(data.get("material", "") or ""),
		care=str(data.get("care", "") or ""),
		dimensions=str(data.get("dimensions", "") or ""),
		shipping_note=str(data.get("shipping_note", "") or ""),
	)
	site_data = await load_site_data(db)
	if body.mode == "card":
		context = await page_ctx(
			request, db, "Product preview", query="", products=[product],
			preview_mode=True, preview_page="card",
		)
		response = storefront_templates.TemplateResponse(request, "pages/store/shop.html", context)
	else:
		context = await page_ctx(
			request,
			db,
			product.name,
			product=product,
			rendered_description=await rendered_description(product, site_data),
			preview_mode=True,
			preview_page="product",
		)
		response = storefront_templates.TemplateResponse(request, "pages/store/product.html", context)
	return JSONResponse({"html": response.body.decode("utf-8")})


@router.get("/site")
async def get_site(user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	return await site(db)


@router.put("/site")
async def update_site(body: SiteBody, user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	await set_value(db, body.key.strip(), body.value)
	await audit(db, user, "site.update", "site_setting", body.key.strip())
	await db.commit()
	return {"ok": True}


@router.get("/orders")
async def get_orders(user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	"""Return actionable order detail plus a grouped production queue summary."""
	rows = list((await db.execute(
		select(Order).options(selectinload(Order.items)).order_by(Order.id.desc())
	)).scalars().unique().all())
	user_ids = {row.user_id for row in rows}
	users = {}
	if user_ids:
		users = {row.id: row for row in (await db.execute(
			select(User).where(User.id.in_(user_ids))
		)).scalars().all()}
	orders_payload = []
	production = {}
	for order in rows:
		customer = users.get(order.user_id)
		items = []
		for item in order.items:
			options = item.options if isinstance(item.options, dict) else {}
			items.append({
				"name": item.name_snapshot,
				"variant": item.variant_snapshot,
				"sku": item.sku_snapshot,
				"quantity": item.quantity,
				"unit_price": str(item.unit_price),
				"line_total": str(item.line_total),
				"options": options,
				"special_care": item.special_care_snapshot,
				"production_notes": item.production_notes_snapshot,
				"product_details": item.product_details_snapshot or {},
			})
			# Only paid orders still in the production workflow belong in this queue.
			# Shipped, delivered, cancelled and on-hold items must not be picked again.
			if order.payment_status == "paid" and order.status in {"pending", "processing"}:
				details = item.product_details_snapshot if isinstance(item.product_details_snapshot, dict) else {}
				key = (item.name_snapshot, item.sku_snapshot, item.variant_snapshot,
					json.dumps(options, sort_keys=True, ensure_ascii=False),
					json.dumps(details, sort_keys=True, ensure_ascii=False))
				entry = production.setdefault(key, {
					"name": item.name_snapshot, "sku": item.sku_snapshot,
					"variant": item.variant_snapshot, "options": options,
					"product_details": details,
					"quantity": 0, "special_care": False, "production_notes": [],
					"orders": [],
				})
				entry["quantity"] += item.quantity
				entry["special_care"] = entry["special_care"] or item.special_care_snapshot
				if item.production_notes_snapshot and item.production_notes_snapshot not in entry["production_notes"]:
					entry["production_notes"].append(item.production_notes_snapshot)
				if order.number not in entry["orders"]:
					entry["orders"].append(order.number)
		orders_payload.append({
			"id": order.id, "number": order.number, "user_id": order.user_id,
			"customer_name": customer.name if customer else "Unknown customer",
			"customer_email": customer.email if customer else "",
			"status": order.status, "payment_status": order.payment_status,
			"total": str(order.total), "currency": order.currency,
			"created_at": order.created_at.isoformat(),
			"address": order.address_snapshot or {}, "notes": order.notes or "",
			"items": items,
		})
	production_rows = sorted(production.values(), key=lambda item: (not item["special_care"], item["name"].casefold(), item["variant"].casefold()))
	return {"orders": orders_payload, "production": production_rows}


@router.delete("/orders/{value}")
async def delete_order(value: int, user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	"""Delete an order and dependent payment/item records after explicit app confirmation."""
	row = await db.get(Order, value)
	if not row:
		raise HTTPException(404, "Order not found")
	await audit(db, user, "order.delete", "order", str(row.id), {"number": row.number, "total": str(row.total)})
	await db.delete(row)
	await db.commit()
	return {"ok": True}


@router.put("/orders/{value}/status")
async def update_order_status(
	value: int,
	body: StatusBody,
	user=REQUIRE_ADMIN,
	db: AsyncSession = GET_DB,
):
	row = await db.get(Order, value)
	if not row:
		raise HTTPException(404, "Order not found")
	if body.status not in {"pending", "processing", "shipped", "delivered", "cancelled", "on_hold"}:
		raise HTTPException(422, "Unknown order status")
	row.status = body.status
	await audit(db, user, "order.status", "order", str(row.id), {"status": row.status})
	await db.commit()
	return {"ok": True}


@router.put("/orders/{value}/payment")
async def update_payment(
	value: int,
	body: StatusBody,
	user=REQUIRE_ADMIN,
	db: AsyncSession = GET_DB,
):
	row = await db.get(Order, value)
	if not row:
		raise HTTPException(404, "Order not found")
	if body.status not in {"unpaid", "pending", "paid", "failed", "refunded"}:
		raise HTTPException(422, "Unknown payment status")
	if body.status == "paid" and row.status == "cancelled":
		raise HTTPException(409, "A cancelled order cannot be marked paid. Restore the order status first so stock and production handling remain consistent.")
	was_paid = row.payment_status == "paid"
	row.payment_status = body.status
	if body.status == "paid" and not was_paid:
		await commit_stock(db, value)
	await audit(
		db,
		user,
		"order.payment",
		"order",
		str(row.id),
		{"payment_status": row.payment_status},
	)
	await db.commit()
	return {"ok": True}


@router.get("/users")
async def get_users(user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	rows = list(
		(await db.execute(select(User).order_by(User.id.desc()))).scalars().all()
	)
	return {
		"users": [
			{
				"id": x.id,
				"email": x.email,
				"name": x.name,
				"is_admin": x.is_admin,
				"is_active": x.is_active,
			}
			for x in rows
		]
	}


@router.put("/users/{value}")
async def update_user(
	value: int,
	body: UserBody,
	user=REQUIRE_ADMIN,
	db: AsyncSession = GET_DB,
):
	row = await db.get(User, value)
	if not row:
		raise HTTPException(404, "User not found")
	if body.is_active is not None:
		row.is_active = body.is_active
	if body.is_admin is not None:
		row.is_admin = body.is_admin
	await audit(
		db,
		user,
		"user.update",
		"user",
		str(row.id),
		{"is_active": row.is_active, "is_admin": row.is_admin},
	)
	await db.commit()
	return {"ok": True}


@router.delete("/users/{value}")
async def delete_user(value: int, user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	"""Delete an unused account; retain accounts with orders for audit/history."""
	row = await db.get(User, value)
	if not row:
		raise HTTPException(404, "User not found")
	if row.id == user.id:
		raise HTTPException(409, "You cannot delete the account used by this admin session")
	has_orders = (await db.execute(select(Order.id).where(Order.user_id == row.id).limit(1))).first()
	if has_orders:
		raise HTTPException(409, "This account has order history. Deactivate it instead to preserve records.")
	await db.execute(delete(AdminSession).where(AdminSession.user_id == row.id))
	await db.execute(delete(Address).where(Address.user_id == row.id))
	await db.execute(delete(CartItem).where(CartItem.user_id == row.id))
	await audit(db, user, "user.delete", "user", str(row.id), {"email": row.email})
	await db.delete(row)
	await db.commit()
	return {"ok": True}


@router.get("/media")
async def get_media(user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	return {
		"media": [
			{
				"id": x.id,
				"filename": x.filename,
				"path": x.path,
				"mime_type": x.mime_type,
				"size_bytes": x.size_bytes,
				"alt_text": x.alt_text,
			}
			for x in await all_media(db)
		]
	}


@router.post("/media")
async def upload_media(
	file: UploadFile = FILE,
	alt_text: str = "",
	user=REQUIRE_ADMIN,
	db: AsyncSession = GET_DB,
):
	content = await file.read()
	if len(content) > 20 * 1024 * 1024:
		raise HTTPException(413, "File too large")
	row = await save_media(db, file.filename or "upload.bin", content, alt_text)
	await audit(
		db, user, "media.upload", "media", str(row.id), {"filename": row.filename}
	)
	await db.commit()
	return {
		"ok": True,
		"id": row.id,
		"filename": row.filename,
		"path": row.path,
		"mime_type": row.mime_type,
		"size_bytes": row.size_bytes,
		"alt_text": row.alt_text,
	}


@router.put("/media/{value}")
async def update_media(value: int, body: MediaUpdateBody, user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	"""Update accessible text for a library asset."""
	from app.db.models import MediaAsset
	row = await db.get(MediaAsset, value)
	if not row:
		raise HTTPException(404, "Asset not found")
	row.alt_text = body.alt_text.strip()
	await audit(db, user, "media.update", "media", str(row.id), {"filename": row.filename})
	await db.commit()
	return {"ok": True}


@router.delete("/media/{value}")
async def delete_media(value: int, user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	"""Delete a media-library record and its stored upload, if present."""
	from app.db.models import MediaAsset
	row = await db.get(MediaAsset, value)
	if not row:
		raise HTTPException(404, "Asset not found")
	asset_path = os.path.realpath(os.path.join(UPLOADS, os.path.basename(row.path)))
	root = os.path.realpath(UPLOADS) + os.sep
	if asset_path.startswith(root) and os.path.isfile(asset_path):
		os.remove(asset_path)
	await audit(db, user, "media.delete", "media", str(row.id), {"filename": row.filename, "path": row.path})
	await db.delete(row)
	await db.commit()
	return {"ok": True}


@router.get("/audit")
async def get_audit(user=REQUIRE_ADMIN, db: AsyncSession = GET_DB):
	rows = list(
		(await db.execute(select(AuditLog).order_by(AuditLog.id.desc()).limit(100)))
		.scalars()
		.all()
	)
	return {
		"audit": [
			{
				"id": x.id,
				"action": x.action,
				"entity_type": x.entity_type,
				"entity_id": x.entity_id,
				"details": x.details or {},
				"created_at": x.created_at.isoformat(),
			}
			for x in rows
		]
	}
