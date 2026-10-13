import os

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import ROOT, settings

engine = create_async_engine(settings.database_url, echo=False)


@event.listens_for(engine.sync_engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
	"""Provide the internal  enable sqlite foreign keys operation."""
	if "sqlite" not in settings.database_url:
		return
	cursor = dbapi_connection.cursor()
	cursor.execute("PRAGMA foreign_keys=ON")
	cursor.close()


SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
	async with SessionLocal() as session:
		yield session


async def init_db():
	from app.db import models  # noqa: F401
	from app.db.base import Base

	os.makedirs(os.path.join(ROOT, "database"), exist_ok=True)
	async with engine.begin() as connection:
		await connection.run_sync(Base.metadata.create_all)
		if "sqlite" in settings.database_url:
			# Remove tables for features retired from this release. These tables are no
			# longer referenced by application code or order creation.
			await connection.exec_driver_sql("DROP TABLE IF EXISTS wishlist_items")
			await connection.exec_driver_sql("DROP TABLE IF EXISTS coupons")
			# Remove legacy coupon-only columns while preserving stored order totals.
			if await _column_exists(connection, "orders", "coupon_code"):
				await connection.exec_driver_sql(
					"ALTER TABLE orders DROP COLUMN coupon_code"
				)
			if await _column_exists(connection, "orders", "discount"):
				await connection.exec_driver_sql(
					"ALTER TABLE orders DROP COLUMN discount"
				)
			# create_all creates new tables but does not evolve existing SQLite tables.
			# Keep this tiny forward migration safe to run on every startup.
			if await _table_exists(
				connection, "categories"
			) and not await _column_exists(connection, "categories", "parent_id"):
				await connection.exec_driver_sql(
					"ALTER TABLE categories ADD COLUMN parent_id INTEGER REFERENCES categories(id) ON DELETE SET NULL"
				)
			if not await _column_exists(connection, "cart_items", "options"):
				await connection.exec_driver_sql(
					"ALTER TABLE cart_items ADD COLUMN options JSON DEFAULT '{}'"
				)
			if not await _column_exists(connection, "order_items", "options"):
				await connection.exec_driver_sql(
					"ALTER TABLE order_items ADD COLUMN options JSON DEFAULT '{}'"
				)
			# Additive migrations for template-defined product fields and production snapshots.
			for table, column, declaration in (
				("description_templates", "fields_schema", "JSON NOT NULL DEFAULT '[]'"),
				("products", "special_care", "BOOLEAN NOT NULL DEFAULT 0"),
				("products", "production_notes", "TEXT NOT NULL DEFAULT ''"),
				("order_items", "sku_snapshot", "VARCHAR(120) NOT NULL DEFAULT ''"),
				("order_items", "special_care_snapshot", "BOOLEAN NOT NULL DEFAULT 0"),
				("order_items", "production_notes_snapshot", "TEXT NOT NULL DEFAULT ''"),
				("order_items", "product_details_snapshot", "JSON NOT NULL DEFAULT '{}'"),
			):
				if await _table_exists(connection, table) and not await _column_exists(connection, table, column):
					await connection.exec_driver_sql(
					f"ALTER TABLE {table} ADD COLUMN {column} {declaration}"
					)

async def _column_exists(connection, table: str, column: str) -> bool:
	"""Provide the internal  column exists operation."""
	result = await connection.exec_driver_sql(f"PRAGMA table_info({table})")
	return any(row[1] == column for row in result.fetchall())


async def _table_exists(connection, table: str) -> bool:
	"""Return whether a table exists before applying a schema migration."""
	result = await connection.exec_driver_sql(
		"SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (table,)
	)
	return result.first() is not None
