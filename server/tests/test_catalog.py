from decimal import Decimal

import pytest
from app.db.models import Category, Product, ProductImage
from app.features.catalog.service import products, save_product
from sqlalchemy import select


@pytest.mark.asyncio
async def test_product_create_and_update(db):
	product = await save_product(
		db,
		{
			"name": "Test Piece",
			"slug": "test-piece",
			"sku": "TEST-1",
			"price": Decimal("20.00"),
			"status": "active",
			"visibility": "public",
			"images": [{"path": "/media/test.jpg", "alt_text": "Test"}],
			"meta": {"size_mode": "predefined", "predefined_sizes": ["M"]},
		},
	)
	await db.commit()
	assert product.id is not None
	image = (
		await db.execute(
			select(ProductImage).where(ProductImage.product_id == product.id)
		)
	).scalar_one()
	assert image.path == "/media/test.jpg"

	await save_product(
		db, {"name": "Updated Piece", "price": Decimal("21.00")}, product.id
	)
	await db.commit()
	row = await db.get(Product, product.id)
	assert row.name == "Updated Piece"
	assert row.price == Decimal("21.00")


@pytest.mark.asyncio
async def test_product_search_and_category_filter(db):
	category = Category(name="Graphic", slug="graphic", position=0)
	db.add(category)
	await db.flush()
	await save_product(
		db,
		{
			"name": "Vision Test",
			"slug": "vision-test",
			"sku": "VISION-1",
			"description": "A visual piece",
			"price": Decimal(10),
			"status": "active",
			"visibility": "public",
			"category_ids": [category.id],
		},
	)
	await db.commit()
	rows = await products(db, search="vision", category_id=category.id)
	assert [row.name for row in rows] == ["Vision Test"]


@pytest.mark.asyncio
async def test_categories_support_arbitrary_parent_depth(db):
	"""Category parent relationships are stored as IDs and may be nested repeatedly."""
	root = Category(name="Root", slug="root")
	db.add(root)
	await db.flush()
	child = Category(name="Child", slug="child", parent_id=root.id)
	db.add(child)
	await db.flush()
	leaf = Category(name="Leaf", slug="leaf", parent_id=child.id)
	db.add(leaf)
	await db.commit()
	assert child.parent_id == root.id
	assert leaf.parent_id == child.id
