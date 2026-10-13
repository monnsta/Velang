from app.db.models import Address
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

FIELDS = (
	"label",
	"full_name",
	"phone",
	"line1",
	"line2",
	"city",
	"state",
	"postal_code",
	"country",
	"is_default",
)


async def list_all(db: AsyncSession, user_id: int):
	return list(
		(
			await db.execute(
				select(Address)
				.where(Address.user_id == user_id)
				.order_by(Address.is_default.desc(), Address.id)
			)
		)
		.scalars()
		.all()
	)


async def save(db: AsyncSession, user_id: int, data: dict, address_id=None):
	row = (
		(
			await db.execute(
				select(Address).where(
					Address.id == address_id, Address.user_id == user_id
				)
			)
		).scalar_one_or_none()
		if address_id
		else None
	)
	if not row:
		row = Address(user_id=user_id)
		db.add(row)
	for key in FIELDS:
		if key in data:
			setattr(row, key, data[key])
	await db.flush()
	if row.is_default:
		others = list(
			(
				await db.execute(
					select(Address).where(
						Address.user_id == user_id, Address.id != row.id
					)
				)
			)
			.scalars()
			.all()
		)
		for other in others:
			other.is_default = False
	await db.flush()
	return row


async def delete(db: AsyncSession, user_id: int, address_id: int):
	row = (
		await db.execute(
			select(Address).where(Address.id == address_id, Address.user_id == user_id)
		)
	).scalar_one_or_none()
	if not row:
		return False
	was_default = row.is_default
	await db.delete(row)
	await db.flush()
	if was_default:
		next_row = (
			(
				await db.execute(
					select(Address)
					.where(Address.user_id == user_id)
					.order_by(Address.id)
				)
			)
			.scalars()
			.first()
		)
		if next_row:
			next_row.is_default = True
	return True
