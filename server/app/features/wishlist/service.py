from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Product, WishlistItem


async def products(db: AsyncSession, user_id: int):
	rows = list((await db.execute(
		select(WishlistItem).where(WishlistItem.user_id == user_id).order_by(WishlistItem.id.desc())
	)).scalars().all())
	result = []
	for row in rows:
		product = (await db.execute(select(Product).where(Product.id == row.product_id))).scalar_one_or_none()
		if product:
			result.append(product)
	return result


async def toggle(db: AsyncSession, user_id: int, product_id: int):
	row = (await db.execute(
		select(WishlistItem).where(WishlistItem.user_id == user_id, WishlistItem.product_id == product_id)
	)).scalar_one_or_none()
	if row:
		await db.delete(row)
		await db.flush()
		return False
	db.add(WishlistItem(user_id=user_id, product_id=product_id))
	await db.flush()
	return True
