from app.db.models import (
	Category,
	Product,
	ProductCategory,
	ProductImage,
	ProductVariant,
)
from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


async def categories(db: AsyncSession, visible_only=False):
	query = select(Category).order_by(Category.position, Category.name)
	if visible_only:
		query = query.where(Category.is_visible.is_(True))
	return list((await db.execute(query)).scalars().all())


async def category(db: AsyncSession, slug: str):
	return (
		await db.execute(select(Category).where(Category.slug == slug))
	).scalar_one_or_none()


async def products(
	db: AsyncSession,
	limit=48,
	search="",
	category_id=None,
	featured=None,
	active_only=True,
):
	query = (
		select(Product)
		.options(
			selectinload(Product.images),
			selectinload(Product.variants),
			selectinload(Product.categories).selectinload(ProductCategory.category),
			selectinload(Product.description_template),
		)
		.order_by(Product.position, Product.id.desc())
	)
	if limit is not None:
		query = query.limit(limit)
	if active_only:
		query = query.where(Product.status == "active", Product.visibility == "public")
	if search:
		term = f"%{search.strip()}%"
		query = query.where(
			or_(
				Product.name.ilike(term),
				Product.subtitle.ilike(term),
				Product.description.ilike(term),
			)
		)
	if category_id is not None:
		query = query.join(ProductCategory).where(
			ProductCategory.category_id == category_id
		)
	if featured is not None:
		query = query.where(Product.featured.is_(featured))
	return list((await db.execute(query)).scalars().unique().all())


async def product(db: AsyncSession, slug: str):
	query = (
		select(Product)
		.options(
			selectinload(Product.images),
			selectinload(Product.variants),
			selectinload(Product.categories).selectinload(ProductCategory.category),
			selectinload(Product.description_template),
		)
		.where(Product.slug == slug)
	)
	return (await db.execute(query)).scalar_one_or_none()


async def product_id(db: AsyncSession, value: int):
	query = (
		select(Product)
		.options(
			selectinload(Product.images),
			selectinload(Product.variants),
			selectinload(Product.categories).selectinload(ProductCategory.category),
			selectinload(Product.description_template),
		)
		.where(Product.id == value)
	)
	return (await db.execute(query)).scalar_one_or_none()


async def save_product(db: AsyncSession, payload: dict, value: int | None = None):
	row = await product_id(db, value) if value else Product()
	if value and not row:
		return None
	fields = (
		"name",
		"slug",
		"sku",
		"subtitle",
		"description",
		"description_template_id",
		"product_type",
		"price",
		"compare_at_price",
		"currency",
		"status",
		"visibility",
		"featured",
		"position",
		"stock_count",
		"track_inventory",
		"low_stock_threshold",
		"badge",
		"tags",
		"material",
		"care",
		"dimensions",
		"shipping_note",
		"special_care",
		"production_notes",
		"seo_title",
		"seo_description",
		"meta",
	)
	for field in fields:
		if field in payload:
			setattr(row, field, payload[field])
	if not value:
		db.add(row)
		await db.flush()
	if "category_ids" in payload:
		await db.execute(
			delete(ProductCategory).where(ProductCategory.product_id == row.id)
		)
		for category_id in payload["category_ids"]:
			db.add(ProductCategory(product_id=row.id, category_id=int(category_id)))
	if "images" in payload:
		await db.execute(delete(ProductImage).where(ProductImage.product_id == row.id))
		for index, image in enumerate(payload["images"]):
			db.add(
				ProductImage(
					product_id=row.id,
					position=index,
					path=str(image.get("path", "")),
					alt_text=str(image.get("alt_text", "")),
					is_primary=index == 0,
				)
			)
	if "variants" in payload:
		await db.execute(
			delete(ProductVariant).where(ProductVariant.product_id == row.id)
		)
		for index, variant in enumerate(payload["variants"]):
			db.add(
				ProductVariant(
					product_id=row.id,
					position=index,
					name=str(variant.get("name", "")),
					sku=str(variant.get("sku", f"{row.sku}-{index + 1}")),
					price=variant.get("price"),
					stock_count=int(variant.get("stock_count", 0)),
					meta=variant.get("meta", {}),
				)
			)
	await db.flush()
	return row
