from decimal import Decimal
from uuid import uuid4
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Address, CartItem, Order, OrderItem, Product, ProductVariant
from app.features.cart.service import clear
from app.features.coupons.service import by_code, discount
from app.features.payments.service import create as create_payment


async def create(db: AsyncSession, user_id: int, address_id: int, coupon_code="", notes=""):
	address = (await db.execute(
		select(Address).where(Address.id == address_id, Address.user_id == user_id)
	)).scalar_one_or_none()
	if not address:
		return None, "Address not found"
	cart = list((await db.execute(
		select(CartItem).where(CartItem.user_id == user_id)
	)).scalars().all())
	if not cart:
		return None, "Cart is empty"

	order = Order(
		number=f"VL-{uuid4().hex[:10].upper()}",
		user_id=user_id,
		notes=notes,
		address_snapshot={
			"full_name": address.full_name,
			"phone": address.phone,
			"line1": address.line1,
			"line2": address.line2,
			"city": address.city,
			"state": address.state,
			"postal_code": address.postal_code,
			"country": address.country,
			"label": address.label,
		},
	)
	subtotal = Decimal("0.00")
	for item in cart:
		product = (await db.execute(select(Product).where(Product.id == item.product_id))).scalar_one_or_none()
		if not product or product.status != "active":
			return None, "A product in your cart is unavailable"
		price = product.price
		variant_name = ""
		if item.variant_id:
			variant = (await db.execute(select(ProductVariant).where(
				ProductVariant.id == item.variant_id,
				ProductVariant.product_id == product.id,
			))).scalar_one_or_none()
			if not variant:
				return None, "A selected variant is unavailable"
			price = variant.price if variant.price is not None else price
			variant_name = variant.name
		if product.track_inventory:
			available = variant.stock_count if item.variant_id and variant else product.stock_count
			if available < item.quantity:
				return None, f"Not enough stock for {product.name}"
		line = price * item.quantity
		subtotal += line
		order.items.append(OrderItem(
			product_id=product.id,
			variant_id=item.variant_id,
			name_snapshot=product.name,
			variant_snapshot=variant_name,
			unit_price=price,
			quantity=item.quantity,
			line_total=line,
		))

	coupon = await by_code(db, coupon_code) if coupon_code else None
	order.subtotal = subtotal
	order.discount = discount(subtotal, coupon)
	order.total = subtotal - order.discount
	order.coupon_code = coupon.code if coupon else ""
	db.add(order)
	await db.flush()
	payment = await create_payment(db, order)
	if coupon and order.discount > Decimal("0.00"):
		coupon.used_count += 1
	await clear(db, user_id)
	await db.flush()
	return order, payment


async def commit_stock(db: AsyncSession, order_id: int):
	order = await db.get(Order, order_id)
	if not order or order.stock_committed:
		return
	items = list((await db.execute(
		select(OrderItem).where(OrderItem.order_id == order_id)
	)).scalars().all())
	for item in items:
		product = await db.get(Product, item.product_id)
		if product and product.track_inventory:
			if item.variant_id:
				variant = await db.get(ProductVariant, item.variant_id)
				if variant:
					variant.stock_count = max(0, variant.stock_count - item.quantity)
			else:
				product.stock_count = max(0, product.stock_count - item.quantity)
	order.stock_committed = True
	await db.flush()
