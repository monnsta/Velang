from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Coupon


def discount(subtotal: Decimal, coupon: Coupon | None):
	if not coupon or not coupon.active or subtotal < coupon.minimum_order_value:
		return Decimal("0.00")
	now = datetime.now(timezone.utc).replace(tzinfo=None)
	if coupon.starts_at and coupon.starts_at > now:
		return Decimal("0.00")
	if coupon.expires_at and coupon.expires_at < now:
		return Decimal("0.00")
	if coupon.usage_limit is not None and coupon.used_count >= coupon.usage_limit:
		return Decimal("0.00")
	amount = coupon.value if coupon.discount_type == "fixed" else subtotal * coupon.value / Decimal("100")
	if coupon.max_discount is not None:
		amount = min(amount, coupon.max_discount)
	return min(subtotal, amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


async def by_code(db: AsyncSession, code: str):
	return (await db.execute(
		select(Coupon).where(Coupon.code == code.strip().upper())
	)).scalar_one_or_none()
