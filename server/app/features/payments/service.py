from decimal import Decimal
from urllib.parse import quote
from uuid import uuid4
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.db.models import Order, PaymentTransaction


class PaymentProvider:
	name = "base"

	async def create(self, order: Order):
		raise NotImplementedError


class DevPaymentProvider(PaymentProvider):
	name = "dev"

	async def create(self, order: Order):
		return {
			"reference": f"DEV-{uuid4().hex[:16].upper()}",
			"status": "created",
			"mode": "manual",
		}


class GooglePayIndiaProvider(PaymentProvider):
	name = "google_pay_india"

	async def create(self, order: Order):
		if not settings.google_pay_merchant_vpa:
			raise ValueError("GOOGLE_PAY_MERCHANT_VPA is not configured")
		reference = f"VLGP-{uuid4().hex[:20].upper()}"
		description = f"Velang order {order.number}"
		intent_uri = (
			"upi://pay?"
			+ f"pa={quote(settings.google_pay_merchant_vpa)}"
			+ f"&pn={quote(settings.google_pay_merchant_name)}"
			+ f"&am={quote(str(order.total))}"
			+ f"&cu={quote(order.currency)}"
			+ f"&tn={quote(description)}"
		)
		return {
			"reference": reference,
			"status": "created",
			"merchant_vpa": settings.google_pay_merchant_vpa,
			"merchant_name": settings.google_pay_merchant_name,
			"amount": str(order.total),
			"currency": order.currency,
			"description": description,
			"intent_uri": intent_uri,
		}


def provider() -> PaymentProvider:
	if settings.payment_provider == "google_pay_india":
		return GooglePayIndiaProvider()
	return DevPaymentProvider()


async def create(db: AsyncSession, order: Order):
	active_provider = provider()
	data = await active_provider.create(order)
	db.add(PaymentTransaction(
		order_id=order.id,
		provider=active_provider.name,
		provider_reference=data["reference"],
		status=data["status"],
		amount=Decimal(order.total),
		currency=order.currency,
		request_payload=data,
	))
	await db.flush()
	return data
