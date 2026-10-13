from decimal import Decimal

import pytest
from app.db.models import Product
from app.features.cart.service import add


@pytest.mark.asyncio
async def test_predefined_size_is_validated(db, user):
	product = Product(
		name="Sized",
		slug="sized",
		sku="SIZED-1",
		price=Decimal(10),
		status="active",
		visibility="public",
		stock_count=5,
		meta={"size_mode": "predefined", "predefined_sizes": ["M", "L"]},
	)
	db.add(product)
	await db.flush()
	assert await add(db, user.id, product.id, options={"size": "M"})
	assert await add(db, user.id, product.id, options={"size": "XS"}) is None


@pytest.mark.asyncio
async def test_custom_measurements_require_all_fields(db, user):
	product = Product(
		name="Custom",
		slug="custom",
		sku="CUSTOM-1",
		price=Decimal(10),
		status="active",
		visibility="public",
		stock_count=5,
		meta={"size_mode": "custom", "custom_size_fields": ["width", "length"]},
	)
	db.add(product)
	await db.flush()
	assert (
		await add(db, user.id, product.id, options={"custom_size": {"width": "20"}})
		is None
	)
	assert await add(
		db,
		user.id,
		product.id,
		options={"custom_size": {"width": "20", "length": "28"}},
	)


@pytest.mark.asyncio
async def test_predefined_size_is_required_and_both_mode_accepts_either_choice(db, user):
	predefined = Product(
		name="Required size", slug="required-size", sku="REQUIRED-SIZE-1",
		price=Decimal(10), status="active", visibility="public", stock_count=5,
		meta={"size_mode": "predefined", "predefined_sizes": ["M", "L"]},
	)
	both = Product(
		name="Flexible size", slug="flexible-size", sku="FLEXIBLE-SIZE-1",
		price=Decimal(10), status="active", visibility="public", stock_count=5,
		meta={"size_mode": "both", "predefined_sizes": ["M", "L"],
			"custom_size_fields": ["width", "length"]},
	)
	db.add_all([predefined, both])
	await db.flush()
	assert await add(db, user.id, predefined.id) is None
	assert await add(db, user.id, both.id) is None
	assert await add(db, user.id, both.id, options={"size": "M"})
	assert await add(db, user.id, both.id, options={"custom_size": {"width": "20", "length": "28"}})
	assert await add(db, user.id, both.id, options={"custom_size": {"width": "20"}}) is None
