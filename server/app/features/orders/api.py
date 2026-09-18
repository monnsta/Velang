from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Order
from app.db.session import get_db
from app.features.auth.deps import require_user
from app.features.orders.service import create

router = APIRouter(prefix="/api/orders")


class OrderBody(BaseModel):
	address_id: int
	coupon_code: str = ""
	notes: str = ""


@router.get("")
async def list_orders(user=Depends(require_user), db: AsyncSession = Depends(get_db)):
	rows = list((await db.execute(select(Order).where(Order.user_id == user.id).order_by(Order.id.desc()))).scalars().all())
	return [{"number": x.number, "status": x.status, "payment_status": x.payment_status, "total": str(x.total), "currency": x.currency} for x in rows]


@router.post("")
async def create_order(body: OrderBody, user=Depends(require_user), db: AsyncSession = Depends(get_db)):
	order, result = await create(db, user.id, body.address_id, body.coupon_code, body.notes)
	if not order:
		return {"ok": False, "error": result}
	await db.commit()
	return {"ok": True, "order": {"id": order.id, "number": order.number, "total": str(order.total)}, "payment": result}
