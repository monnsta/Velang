from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import CartItem, Product, ProductVariant


async def cart_items(db: AsyncSession, user_id: int):
	items = list((await db.execute(
		select(CartItem).where(CartItem.user_id == user_id).order_by(CartItem.id)
	)).scalars().all())
	products = {}
	for item in items:
		products[item.id] = (await db.execute(
			select(Product).where(Product.id == item.product_id)
		)).scalar_one_or_none()
	return items, products


async def add(db: AsyncSession, user_id: int, product_id: int, quantity=1, variant_id=None):
	product = (await db.execute(
		select(Product).where(
			Product.id == product_id,
			Product.status == "active",
			Product.visibility == "public",
		)
	)).scalar_one_or_none()
	if not product or quantity < 1:
		return None
	if variant_id is not None:
		variant = (await db.execute(
			select(ProductVariant).where(
			ProductVariant.id == variant_id,
			ProductVariant.product_id == product_id,
			)
		)).scalar_one_or_none()
		if not variant:
			return None
	row = (await db.execute(
		select(CartItem).where(
			CartItem.user_id == user_id,
			CartItem.product_id == product_id,
			CartItem.variant_id == variant_id,
		)
	)).scalar_one_or_none()
	new_quantity = int(quantity)
	if row:
		new_quantity += row.quantity
	if product.track_inventory:
		available = variant.stock_count if variant_id is not None and variant else product.stock_count
		if available < new_quantity:
			return None
	if row:
		row.quantity = new_quantity
	else:
		row = CartItem(user_id=user_id, product_id=product_id, variant_id=variant_id, quantity=new_quantity)
		db.add(row)
	await db.flush()
	return row


async def set_quantity(db: AsyncSession, user_id: int, item_id: int, quantity: int):
	row = (await db.execute(
		select(CartItem).where(CartItem.id == item_id, CartItem.user_id == user_id)
	)).scalar_one_or_none()
	if not row:
		return False
	if quantity <= 0:
		await db.delete(row)
	else:
		row.quantity = quantity
	await db.flush()
	return True


async def remove(db: AsyncSession, user_id: int, item_id: int):
	row = (await db.execute(
		select(CartItem).where(CartItem.id == item_id, CartItem.user_id == user_id)
	)).scalar_one_or_none()
	if row:
		await db.delete(row)
	await db.flush()


async def clear(db: AsyncSession, user_id: int):
	await db.execute(delete(CartItem).where(CartItem.user_id == user_id))
	await db.flush()
