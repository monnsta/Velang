from app.db.models import Order
from app.db.session import get_db
from app.features.auth.deps import require_user
from app.features.orders.service import create
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/orders")

GET_DB = Depends(get_db)
REQUIRE_USER = Depends(require_user)


class OrderBody(BaseModel):

	address_id: int
	notes: str = ""


@router.get("")
async def list_orders(user=REQUIRE_USER, db: AsyncSession = GET_DB):
	rows = list(
		(
			await db.execute(
				select(Order).where(Order.user_id == user.id).order_by(Order.id.desc())
			)
		)
		.scalars()
		.all()
	)
	return [
		{
			"number": x.number,
			"status": x.status,
			"payment_status": x.payment_status,
			"total": str(x.total),
			"currency": x.currency,
		}
		for x in rows
	]


@router.post("")
async def create_order(body: OrderBody, user=REQUIRE_USER, db: AsyncSession = GET_DB):
	order, result = await create(db, user.id, body.address_id, body.notes)
	if not order:
		return {"ok": False, "error": result}
	await db.commit()
	return {
		"ok": True,
		"order": {"id": order.id, "number": order.number, "total": str(order.total)},
		"payment": result,
	}
