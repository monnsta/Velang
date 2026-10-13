from app.db.models import CartItem, Product, ProductVariant
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


async def cart_items(db: AsyncSession, user_id: int):
	items = list(
		(
			await db.execute(
				select(CartItem)
				.where(CartItem.user_id == user_id)
				.order_by(CartItem.id)
			)
		)
		.scalars()
		.all()
	)
	products = {}
	for item in items:
		products[item.id] = (
			await db.execute(
				select(Product)
				.options(selectinload(Product.images))
				.where(Product.id == item.product_id)
			)
		).scalar_one_or_none()
	return items, products


async def add(
	db: AsyncSession,
	user_id: int,
	product_id: int,
	quantity=1,
	variant_id=None,
	options=None,
):
	product = (
		await db.execute(
			select(Product).where(
				Product.id == product_id,
				Product.status == "active",
				Product.visibility == "public",
			)
		)
	).scalar_one_or_none()
	if not product or quantity < 1:
		return None
	options = options or {}
	meta = product.meta or {}
	size_mode = meta.get("size_mode", "none")
	selected_size = options.get("size")
	custom_size = options.get("custom_size")
	allowed_sizes = meta.get("predefined_sizes", [])
	allowed_fields = meta.get("custom_size_fields", ["width", "length"])
	valid_predefined = bool(selected_size) and selected_size in allowed_sizes
	valid_custom = isinstance(custom_size, dict) and all(
		field in custom_size and str(custom_size[field]).strip()
		for field in allowed_fields
	)
	if size_mode == "none":
		if selected_size or custom_size:
			return None
	elif size_mode == "predefined":
		if not valid_predefined or custom_size:
			return None
	elif size_mode == "custom":
		if not valid_custom or selected_size:
			return None
	elif size_mode == "both":
		# Customers can choose a listed size or enter custom measurements. If both
		# payloads are sent, validate both instead of silently accepting partial data.
		if custom_size and not valid_custom:
			return None
		if selected_size and not valid_predefined:
			return None
		if not valid_predefined and not valid_custom:
			return None
	if variant_id is not None:
		variant = (
			await db.execute(
				select(ProductVariant).where(
					ProductVariant.id == variant_id,
					ProductVariant.product_id == product_id,
				)
			)
		).scalar_one_or_none()
		if not variant:
			return None
	row = (
		await db.execute(
			select(CartItem).where(
				CartItem.user_id == user_id,
				CartItem.product_id == product_id,
				CartItem.variant_id == variant_id,
			)
		)
	).scalar_one_or_none()
	new_quantity = int(quantity)
	if row:
		new_quantity += row.quantity
	if product.track_inventory:
		available = (
			variant.stock_count
			if variant_id is not None and variant
			else product.stock_count
		)
		if available < new_quantity:
			return None
	if row:
		row.quantity = new_quantity
		if options:
			row.options = options
	else:
		row = CartItem(
			user_id=user_id,
			product_id=product_id,
			variant_id=variant_id,
			quantity=new_quantity,
			options=options or {},
		)
		db.add(row)
	await db.flush()
	return row


async def set_quantity(db: AsyncSession, user_id: int, item_id: int, quantity: int):
	row = (
		await db.execute(
			select(CartItem).where(CartItem.id == item_id, CartItem.user_id == user_id)
		)
	).scalar_one_or_none()
	if not row:
		return False
	if quantity <= 0:
		await db.delete(row)
	else:
		row.quantity = quantity
	await db.flush()
	return True


async def remove(db: AsyncSession, user_id: int, item_id: int):
	row = (
		await db.execute(
			select(CartItem).where(CartItem.id == item_id, CartItem.user_id == user_id)
		)
	).scalar_one_or_none()
	if row:
		await db.delete(row)
	await db.flush()


async def clear(db: AsyncSession, user_id: int):
	await db.execute(delete(CartItem).where(CartItem.user_id == user_id))
	await db.flush()
