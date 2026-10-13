from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
	JSON,
	Boolean,
	DateTime,
	ForeignKey,
	Integer,
	Numeric,
	String,
	Text,
	UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def money():
	return Numeric(12, 2)


class User(Base):

	__tablename__ = "users"
	id: Mapped[int] = mapped_column(primary_key=True)
	email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
	name: Mapped[str] = mapped_column(String(160), default="")
	password_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
	google_subject: Mapped[str | None] = mapped_column(
		String(255), unique=True, nullable=True
	)
	is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
	is_active: Mapped[bool] = mapped_column(Boolean, default=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime, default=lambda: datetime.now(timezone.utc)
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime,
		default=lambda: datetime.now(timezone.utc),
		onupdate=lambda: datetime.now(timezone.utc),
	)


class AdminSession(Base):

	__tablename__ = "admin_sessions"
	id: Mapped[int] = mapped_column(primary_key=True)
	user_id: Mapped[int] = mapped_column(
		ForeignKey("users.id", ondelete="CASCADE"), index=True
	)
	token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
	expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
	revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime, default=lambda: datetime.now(timezone.utc)
	)
	user: Mapped[User] = relationship()


class Category(Base):
	"""Represent a category in a recursively nestable category tree."""

	__tablename__ = "categories"
	id: Mapped[int] = mapped_column(primary_key=True)
	parent_id: Mapped[int | None] = mapped_column(
		ForeignKey("categories.id", ondelete="SET NULL"), nullable=True, index=True
	)
	parent: Mapped["Category | None"] = relationship(
		remote_side="Category.id", back_populates="children"
	)
	children: Mapped[list["Category"]] = relationship(
		back_populates="parent", cascade="save-update, merge"
	)
	name: Mapped[str] = mapped_column(String(160), unique=True)
	slug: Mapped[str] = mapped_column(String(160), unique=True, index=True)
	description: Mapped[str] = mapped_column(Text, default="")
	image_path: Mapped[str] = mapped_column(String(500), default="")
	position: Mapped[int] = mapped_column(Integer, default=0)
	is_visible: Mapped[bool] = mapped_column(Boolean, default=True)
	seo_title: Mapped[str] = mapped_column(String(255), default="")
	seo_description: Mapped[str] = mapped_column(Text, default="")
	meta: Mapped[dict] = mapped_column(JSON, default=dict)


class DescriptionTemplate(Base):

	__tablename__ = "description_templates"
	id: Mapped[int] = mapped_column(primary_key=True)
	name: Mapped[str] = mapped_column(String(160), unique=True)
	product_type: Mapped[str] = mapped_column(
		String(100), default="general", index=True
	)
	body_markdown: Mapped[str] = mapped_column(Text, default="")
	fields_schema: Mapped[list] = mapped_column(JSON, default=list)
	is_active: Mapped[bool] = mapped_column(Boolean, default=True)
	created_at: Mapped[datetime] = mapped_column(
		DateTime, default=lambda: datetime.now(timezone.utc)
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime,
		default=datetime.now(timezone.utc),
		onupdate=lambda: datetime.now(timezone.utc),
	)


class Product(Base):

	__tablename__ = "products"
	id: Mapped[int] = mapped_column(primary_key=True)
	name: Mapped[str] = mapped_column(String(200), index=True)
	slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
	sku: Mapped[str] = mapped_column(String(120), unique=True, index=True)
	subtitle: Mapped[str] = mapped_column(String(255), default="")
	description: Mapped[str] = mapped_column(Text, default="")
	description_template_id: Mapped[int | None] = mapped_column(
		ForeignKey("description_templates.id", ondelete="SET NULL"), nullable=True
	)
	product_type: Mapped[str] = mapped_column(
		String(100), default="general", index=True
	)
	price: Mapped[Decimal] = mapped_column(money(), default=Decimal(0))
	compare_at_price: Mapped[Decimal | None] = mapped_column(money(), nullable=True)
	currency: Mapped[str] = mapped_column(String(8), default="INR")
	status: Mapped[str] = mapped_column(String(30), default="draft", index=True)
	visibility: Mapped[str] = mapped_column(String(30), default="public")
	featured: Mapped[bool] = mapped_column(Boolean, default=False)
	position: Mapped[int] = mapped_column(Integer, default=0)
	stock_count: Mapped[int] = mapped_column(Integer, default=0)
	track_inventory: Mapped[bool] = mapped_column(Boolean, default=True)
	low_stock_threshold: Mapped[int] = mapped_column(Integer, default=2)
	badge: Mapped[str] = mapped_column(String(80), default="")
	tags: Mapped[list] = mapped_column(JSON, default=list)
	material: Mapped[str] = mapped_column(String(255), default="")
	care: Mapped[str] = mapped_column(Text, default="")
	dimensions: Mapped[str] = mapped_column(String(500), default="")
	shipping_note: Mapped[str] = mapped_column(Text, default="")
	special_care: Mapped[bool] = mapped_column(Boolean, default=False)
	production_notes: Mapped[str] = mapped_column(Text, default="")
	seo_title: Mapped[str] = mapped_column(String(255), default="")
	seo_description: Mapped[str] = mapped_column(Text, default="")
	meta: Mapped[dict] = mapped_column(JSON, default=dict)
	created_at: Mapped[datetime] = mapped_column(
		DateTime, default=lambda: datetime.now(timezone.utc)
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime,
		default=lambda: datetime.now(timezone.utc),
		onupdate=lambda: datetime.now(timezone.utc),
	)
	images: Mapped[list["ProductImage"]] = relationship(
		back_populates="product", cascade="all, delete-orphan", order_by="ProductImage.position"
	)
	variants: Mapped[list["ProductVariant"]] = relationship(
		back_populates="product", cascade="all, delete-orphan", order_by="ProductVariant.position"
	)
	categories: Mapped[list["ProductCategory"]] = relationship(
		back_populates="product", cascade="all, delete-orphan"
	)
	description_template: Mapped[DescriptionTemplate | None] = relationship()


class ProductImage(Base):

	__tablename__ = "product_images"
	id: Mapped[int] = mapped_column(primary_key=True)
	product_id: Mapped[int] = mapped_column(
		ForeignKey("products.id", ondelete="CASCADE"), index=True
	)
	path: Mapped[str] = mapped_column(String(500))
	alt_text: Mapped[str] = mapped_column(String(255), default="")
	position: Mapped[int] = mapped_column(Integer, default=0)
	is_primary: Mapped[bool] = mapped_column(Boolean, default=False)
	product: Mapped[Product] = relationship(back_populates="images")


class ProductVariant(Base):

	__tablename__ = "product_variants"
	id: Mapped[int] = mapped_column(primary_key=True)
	product_id: Mapped[int] = mapped_column(
		ForeignKey("products.id", ondelete="CASCADE"), index=True
	)
	name: Mapped[str] = mapped_column(String(160))
	sku: Mapped[str] = mapped_column(String(120), unique=True, index=True)
	price: Mapped[Decimal | None] = mapped_column(money(), nullable=True)
	stock_count: Mapped[int] = mapped_column(Integer, default=0)
	position: Mapped[int] = mapped_column(Integer, default=0)
	meta: Mapped[dict] = mapped_column(JSON, default=dict)
	product: Mapped[Product] = relationship(back_populates="variants")


class ProductCategory(Base):

	__tablename__ = "product_categories"
	product_id: Mapped[int] = mapped_column(
		ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
	)
	category_id: Mapped[int] = mapped_column(
		ForeignKey("categories.id", ondelete="CASCADE"), primary_key=True
	)
	product: Mapped[Product] = relationship(back_populates="categories")
	category: Mapped[Category] = relationship()


class Address(Base):

	__tablename__ = "addresses"
	id: Mapped[int] = mapped_column(primary_key=True)
	user_id: Mapped[int] = mapped_column(
		ForeignKey("users.id", ondelete="CASCADE"), index=True
	)
	label: Mapped[str] = mapped_column(String(80), default="Home")
	full_name: Mapped[str] = mapped_column(String(160))
	phone: Mapped[str] = mapped_column(String(40))
	line1: Mapped[str] = mapped_column(String(255))
	line2: Mapped[str] = mapped_column(String(255), default="")
	city: Mapped[str] = mapped_column(String(120))
	state: Mapped[str] = mapped_column(String(120))
	postal_code: Mapped[str] = mapped_column(String(30))
	country: Mapped[str] = mapped_column(String(120), default="India")
	is_default: Mapped[bool] = mapped_column(Boolean, default=False)


class CartItem(Base):

	__tablename__ = "cart_items"
	id: Mapped[int] = mapped_column(primary_key=True)
	user_id: Mapped[int] = mapped_column(
		ForeignKey("users.id", ondelete="CASCADE"), index=True
	)
	product_id: Mapped[int] = mapped_column(
		ForeignKey("products.id", ondelete="CASCADE"), index=True
	)
	variant_id: Mapped[int | None] = mapped_column(
		ForeignKey("product_variants.id", ondelete="CASCADE"), nullable=True
	)
	quantity: Mapped[int] = mapped_column(Integer, default=1)
	options: Mapped[dict] = mapped_column(JSON, default=dict)
	__table_args__ = (
		UniqueConstraint("user_id", "product_id", "variant_id", name="uq_cart_item"),
	)


class Order(Base):

	__tablename__ = "orders"
	id: Mapped[int] = mapped_column(primary_key=True)
	number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
	user_id: Mapped[int] = mapped_column(
		ForeignKey("users.id", ondelete="RESTRICT"), index=True
	)
	status: Mapped[str] = mapped_column(String(30), default="pending", index=True)
	payment_status: Mapped[str] = mapped_column(
		String(30), default="unpaid", index=True
	)
	currency: Mapped[str] = mapped_column(String(8), default="INR")
	subtotal: Mapped[Decimal] = mapped_column(money(), default=Decimal(0))
	total: Mapped[Decimal] = mapped_column(money(), default=Decimal(0))
	address_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
	notes: Mapped[str] = mapped_column(Text, default="")
	stock_committed: Mapped[bool] = mapped_column(Boolean, default=False)
	created_at: Mapped[datetime] = mapped_column(
		DateTime, default=lambda: datetime.now(timezone.utc)
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime,
		default=lambda: datetime.now(timezone.utc),
		onupdate=lambda: datetime.now(timezone.utc),
	)
	items: Mapped[list["OrderItem"]] = relationship(
		back_populates="order", cascade="all, delete-orphan"
	)


class OrderItem(Base):

	__tablename__ = "order_items"
	id: Mapped[int] = mapped_column(primary_key=True)
	order_id: Mapped[int] = mapped_column(
		ForeignKey("orders.id", ondelete="CASCADE"), index=True
	)
	product_id: Mapped[int] = mapped_column(
		ForeignKey("products.id", ondelete="RESTRICT"), index=True
	)
	variant_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
	name_snapshot: Mapped[str] = mapped_column(String(200))
	variant_snapshot: Mapped[str] = mapped_column(String(160), default="")
	sku_snapshot: Mapped[str] = mapped_column(String(120), default="")
	special_care_snapshot: Mapped[bool] = mapped_column(Boolean, default=False)
	production_notes_snapshot: Mapped[str] = mapped_column(Text, default="")
	product_details_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
	unit_price: Mapped[Decimal] = mapped_column(money(), default=Decimal(0))
	quantity: Mapped[int] = mapped_column(Integer, default=1)
	line_total: Mapped[Decimal] = mapped_column(money(), default=Decimal(0))
	options: Mapped[dict] = mapped_column(JSON, default=dict)
	order: Mapped[Order] = relationship(back_populates="items")


class PaymentTransaction(Base):

	__tablename__ = "payment_transactions"
	id: Mapped[int] = mapped_column(primary_key=True)
	order_id: Mapped[int] = mapped_column(
		ForeignKey("orders.id", ondelete="CASCADE"), index=True
	)
	provider: Mapped[str] = mapped_column(String(50))
	provider_reference: Mapped[str] = mapped_column(
		String(255), unique=True, index=True
	)
	status: Mapped[str] = mapped_column(String(30), default="created")
	amount: Mapped[Decimal] = mapped_column(money())
	currency: Mapped[str] = mapped_column(String(8), default="INR")
	request_payload: Mapped[dict] = mapped_column(JSON, default=dict)
	response_payload: Mapped[dict] = mapped_column(JSON, default=dict)
	created_at: Mapped[datetime] = mapped_column(
		DateTime, default=lambda: datetime.now(timezone.utc)
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime,
		default=lambda: datetime.now(timezone.utc),
		onupdate=lambda: datetime.now(timezone.utc),
	)


class ContentPage(Base):

	__tablename__ = "content_pages"
	id: Mapped[int] = mapped_column(primary_key=True)
	slug: Mapped[str] = mapped_column(String(200), unique=True, index=True)
	title: Mapped[str] = mapped_column(String(200))
	body_markdown: Mapped[str] = mapped_column(Text, default="")
	meta: Mapped[dict] = mapped_column(JSON, default=dict)
	active: Mapped[bool] = mapped_column(Boolean, default=True)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime,
		default=lambda: datetime.now(timezone.utc),
		onupdate=lambda: datetime.now(timezone.utc),
	)


class SiteSetting(Base):

	__tablename__ = "site_settings"
	key: Mapped[str] = mapped_column(String(100), primary_key=True)
	value: Mapped[dict] = mapped_column(JSON, default=dict)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime,
		default=lambda: datetime.now(timezone.utc),
		onupdate=lambda: datetime.now(timezone.utc),
	)


class MediaAsset(Base):

	__tablename__ = "media_assets"
	id: Mapped[int] = mapped_column(primary_key=True)
	filename: Mapped[str] = mapped_column(String(255))
	path: Mapped[str] = mapped_column(String(500), unique=True)
	mime_type: Mapped[str] = mapped_column(String(120))
	size_bytes: Mapped[int] = mapped_column(Integer, default=0)
	alt_text: Mapped[str] = mapped_column(String(255), default="")
	created_at: Mapped[datetime] = mapped_column(
		DateTime, default=lambda: datetime.now(timezone.utc)
	)


class AuditLog(Base):

	__tablename__ = "audit_logs"
	id: Mapped[int] = mapped_column(primary_key=True)
	user_id: Mapped[int | None] = mapped_column(
		ForeignKey("users.id", ondelete="SET NULL"), nullable=True
	)
	action: Mapped[str] = mapped_column(String(120))
	entity_type: Mapped[str] = mapped_column(String(80), default="")
	entity_id: Mapped[str] = mapped_column(String(80), default="")
	details: Mapped[dict] = mapped_column(JSON, default=dict)
	created_at: Mapped[datetime] = mapped_column(
		DateTime, default=lambda: datetime.now(timezone.utc)
	)
