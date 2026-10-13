from decimal import Decimal

import pytest
from sqlalchemy import select

from app.db.models import Address, CartItem, OrderItem, Product, ProductVariant
from app.features.orders.service import create


@pytest.mark.asyncio
async def test_order_item_snapshots_manufacturing_details(db, user):
	address = Address(
		user_id=user.id,
		label="Workshop delivery",
		full_name="Tester",
		phone="1234567890",
		line1="1 Test Street",
		line2="",
		city="Pune",
		state="Maharashtra",
		postal_code="411001",
		country="India",
		is_default=True,
	)
	product = Product(
		name="Hand-finished lamp",
		slug="hand-finished-lamp",
		sku="LAMP-001",
		price=Decimal("12000.00"),
		currency="INR",
		status="active",
		stock_count=5,
		track_inventory=True,
		special_care=True,
		production_notes="Polish by hand; do not machine-buff.",
		material="Brushed brass",
		meta={"template_values": {"finish": "Satin", "shade": "Opal glass"}},
	)
	db.add_all([address, product])
	await db.flush()
	variant = ProductVariant(
		product_id=product.id,
		name="Large shade",
		sku="LAMP-001-L",
		stock_count=3,
		meta={"finish": "Satin brass"},
	)
	db.add(variant)
	await db.flush()
	db.add(CartItem(user_id=user.id, product_id=product.id, variant_id=variant.id, quantity=2, options={"size": "Large"}))
	await db.flush()

	order, payment = await create(db, user.id, address.id, "Gift wrapping requested")
	assert order is not None, payment
	await db.commit()
	item = (await db.execute(select(OrderItem).where(OrderItem.order_id == order.id))).scalar_one()

	assert order.number.startswith("ord-")
	assert item.sku_snapshot == "LAMP-001-L"
	assert item.special_care_snapshot is True
	assert item.production_notes_snapshot == "Polish by hand; do not machine-buff."
	assert item.product_details_snapshot["material"] == "Brushed brass"
	assert item.product_details_snapshot["template_fields"] == {"finish": "Satin", "shade": "Opal glass"}
	assert item.product_details_snapshot["variant_sku"] == "LAMP-001-L"
	assert item.product_details_snapshot["variant_meta"] == {"finish": "Satin brass"}
	assert item.options == {"size": "Large"}
