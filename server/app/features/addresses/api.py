from app.db.session import get_db
from app.features.addresses.service import delete, list_all, save
from app.features.auth.deps import require_user
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/addresses")

REQUIRE_USER = Depends(require_user)
GET_DB = Depends(get_db)


class AddressBody(BaseModel):

	label: str = "Home"
	full_name: str
	phone: str
	line1: str
	line2: str = ""
	city: str
	state: str
	postal_code: str
	country: str = "India"
	is_default: bool = False


@router.get("")
async def get_addresses(user=REQUIRE_USER, db: AsyncSession = GET_DB):
	return [
		{
			"id": x.id,
			"label": x.label,
			"full_name": x.full_name,
			"phone": x.phone,
			"line1": x.line1,
			"line2": x.line2,
			"city": x.city,
			"state": x.state,
			"postal_code": x.postal_code,
			"country": x.country,
			"is_default": x.is_default,
		}
		for x in await list_all(db, user.id)
	]


@router.post("")
async def create_address(
	body: AddressBody,
	user=REQUIRE_USER,
	db: AsyncSession = GET_DB,
):
	row = await save(db, user.id, body.model_dump())
	await db.commit()
	return {"ok": True, "id": row.id}


@router.put("/{address_id}")
async def update_address(
	address_id: int,
	body: AddressBody,
	user=REQUIRE_USER,
	db: AsyncSession = GET_DB,
):
	row = await save(db, user.id, body.model_dump(), address_id)
	if not row:
		raise HTTPException(404, "Address not found")
	await db.commit()
	return {"ok": True, "id": row.id}


@router.delete("/{address_id}")
async def delete_address(
	address_id: int,
	user=REQUIRE_USER,
	db: AsyncSession = GET_DB,
):
	if not await delete(db, user.id, address_id):
		raise HTTPException(404, "Address not found")
	await db.commit()
	return {"ok": True}
