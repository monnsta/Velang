from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.features.auth.service import admin_user, by_id


async def current_user(request: Request, db: AsyncSession = Depends(get_db)):
	user_id = request.session.get("user_id")
	if not user_id:
		return None
	user = await by_id(db, int(user_id))
	if not user or not user.is_active:
		request.session.clear()
		return None
	return user


async def require_user(request: Request, db: AsyncSession = Depends(get_db)):
	user = await current_user(request, db)
	if not user:
		raise HTTPException(401, "Login required")
	return user


async def require_admin(request: Request, db: AsyncSession = Depends(get_db)):
	header = request.headers.get("authorization", "")
	if not header.startswith("Bearer "):
		raise HTTPException(401, "Admin session required")
	user = await admin_user(db, header[7:].strip())
	if not user:
		raise HTTPException(401, "Invalid admin session")
	return user
