from app.db.session import get_db
from app.features.auth.deps import require_user
from app.features.cart.service import add, cart_items, remove, set_quantity
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from app.db.models import CartItem
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/cart")

GET_DB = Depends(get_db)
REQUIRE_USER = Depends(require_user)


class ItemBody(BaseModel):

	product_id: int
	quantity: int = 1
	variant_id: int | None = None
	options: dict = Field(default_factory=dict)


class QuantityBody(BaseModel):

	quantity: int


@router.get("")
async def get_cart(user=REQUIRE_USER, db: AsyncSession = GET_DB):
	items, products = await cart_items(db, user.id)
	return {
		"items": [
			{
				"id": x.id,
				"product_id": x.product_id,
				"quantity": x.quantity,
				"name": products[x.id].name if products[x.id] else "",
			}
			for x in items
		]
	}


@router.post("/items")
async def add_item(body: ItemBody, user=REQUIRE_USER, db: AsyncSession = GET_DB):
	row = await add(
		db, user.id, body.product_id, body.quantity, body.variant_id, body.options
	)
	if not row:
		return {"ok": False, "error": "Product or variant unavailable"}
	# get_db deliberately leaves transaction policy to each endpoint. Commit cart
	# mutations here; otherwise the session closes and silently rolls the item back.
	await db.commit()
	count = int((await db.execute(
		select(func.coalesce(func.sum(CartItem.quantity), 0)).where(CartItem.user_id == user.id)
	)).scalar_one())
	return {"ok": True, "id": row.id, "cart_count": count}


@router.patch("/items/{item_id}")
async def change_quantity(
	item_id: int,
	body: QuantityBody,
	user=REQUIRE_USER,
	db: AsyncSession = GET_DB,
):
	ok = await set_quantity(db, user.id, item_id, body.quantity)
	if ok:
		await db.commit()
	return {"ok": ok}


@router.delete("/items/{item_id}")
async def delete_item(item_id: int, user=REQUIRE_USER, db: AsyncSession = GET_DB):
	await remove(db, user.id, item_id)
	await db.commit()
	return {"ok": True}
