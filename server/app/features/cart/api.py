from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.features.auth.deps import require_user
from app.features.cart.service import add, cart_items, remove, set_quantity

router = APIRouter(prefix="/api/cart")


class ItemBody(BaseModel):
	product_id: int
	quantity: int = 1
	variant_id: int | None = None


class QuantityBody(BaseModel):
	quantity: int


@router.get("")
async def get_cart(user=Depends(require_user), db: AsyncSession = Depends(get_db)):
	items, products = await cart_items(db, user.id)
	return {"items": [{"id": x.id, "product_id": x.product_id, "quantity": x.quantity, "name": products[x.id].name if products[x.id] else ""} for x in items]}


@router.post("/items")
async def add_item(body: ItemBody, user=Depends(require_user), db: AsyncSession = Depends(get_db)):
	row = await add(db, user.id, body.product_id, body.quantity, body.variant_id)
	if not row:
		return {"ok": False, "error": "Product or variant unavailable"}
	return {"ok": True, "id": row.id}


@router.patch("/items/{item_id}")
async def change_quantity(item_id: int, body: QuantityBody, user=Depends(require_user), db: AsyncSession = Depends(get_db)):
	ok = await set_quantity(db, user.id, item_id, body.quantity)
	return {"ok": ok}


@router.delete("/items/{item_id}")
async def delete_item(item_id: int, user=Depends(require_user), db: AsyncSession = Depends(get_db)):
	await remove(db, user.id, item_id)
	return {"ok": True}
