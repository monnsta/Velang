from decimal import Decimal
from uuid import uuid4

from app.db.models import Address, CartItem, Order, OrderItem, Product, ProductVariant
from app.features.cart.service import clear
from app.features.payments.service import create as create_payment
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def create(db: AsyncSession, user_id: int, address_id: int, notes=""):
	address = (
		await db.execute(
			select(Address).where(Address.id == address_id, Address.user_id == user_id)
		)
	).scalar_one_or_none()
	if not address:
		return None, "Address not found"
	cart = list(
		(await db.execute(select(CartItem).where(CartItem.user_id == user_id)))
		.scalars()
		.all()
	)
	if not cart:
		return None, "Cart is empty"

	order = Order(
		number=f"ord-{uuid4().hex[:8]}",
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
	order_currency = None
	for item in cart:
		product = (
			await db.execute(select(Product).where(Product.id == item.product_id))
		).scalar_one_or_none()
		if not product or product.status != "active":
			return None, "A product in your cart is unavailable"
		if order_currency is None:
			order_currency = product.currency
		elif product.currency != order_currency:
			return (
				None,
				"Your cart contains multiple currencies. Place separate orders for each currency.",
			)
		price = product.price
		variant_name = ""
		variant_sku = ""
		variant_meta = {}
		if item.variant_id:
			variant = (
				await db.execute(
					select(ProductVariant).where(
						ProductVariant.id == item.variant_id,
						ProductVariant.product_id == product.id,
					)
				)
			).scalar_one_or_none()
			if not variant:
				return None, "A selected variant is unavailable"
			price = variant.price if variant.price is not None else price
			variant_name = variant.name
			variant_sku = variant.sku
			variant_meta = variant.meta or {}
		if product.track_inventory:
			available = (
				variant.stock_count
				if item.variant_id and variant
				else product.stock_count
			)
			if available < item.quantity:
				return None, f"Not enough stock for {product.name}"
		line = price * item.quantity
		subtotal += line
		order.items.append(
			OrderItem(
				product_id=product.id,
				variant_id=item.variant_id,
				name_snapshot=product.name,
				variant_snapshot=variant_name,
				sku_snapshot=variant_sku or product.sku,
				special_care_snapshot=product.special_care,
				production_notes_snapshot=product.production_notes,
				product_details_snapshot={
					"product_type": product.product_type,
					"material": product.material,
					"care": product.care,
					"dimensions": product.dimensions,
					"shipping_note": product.shipping_note,
					"template_fields": (product.meta or {}).get("template_values", {}),
					"variant_sku": variant_sku,
					"variant_meta": variant_meta,
				},
				unit_price=price,
				quantity=item.quantity,
				line_total=line,
				options=item.options or {},
			)
		)

	# Orders are charged at catalogue prices; discount codes are not supported.
	order.currency = order_currency or "INR"
	order.subtotal = subtotal
	order.total = subtotal
	db.add(order)
	await db.flush()
	payment = await create_payment(db, order)
	await clear(db, user_id)
	await db.flush()
	return order, payment


async def commit_stock(db: AsyncSession, order_id: int):
	order = await db.get(Order, order_id)
	if not order or order.stock_committed or order.status == "cancelled":
		return
	items = list(
		(await db.execute(select(OrderItem).where(OrderItem.order_id == order_id)))
		.scalars()
		.all()
	)
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
