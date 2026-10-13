from app.core.config import settings
from app.db.session import get_db
from app.features.auth.deps import require_user
from app.features.auth.service import development_user, google_user
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/auth")

GET_DB = Depends(get_db)
REQUIRE_USER = Depends(require_user)


class GoogleBody(BaseModel):

	credential: str


@router.post("/google")
async def google(body: GoogleBody, request: Request, db: AsyncSession = GET_DB):
	try:
		user = await google_user(db, body.credential)
	except PermissionError as exc:
		raise HTTPException(403, str(exc)) from exc
	request.session["user_id"] = user.id
	await db.commit()
	return {"ok": True}


@router.post("/dev")
async def development_login(request: Request, db: AsyncSession = GET_DB):
	if settings.app_env == "production" or not settings.dev_auth:
		raise HTTPException(404, "Development authentication is disabled")
	user = await development_user(db)
	request.session["user_id"] = user.id
	await db.commit()
	return {"ok": True, "id": user.id, "email": user.email}


@router.post("/logout")
async def logout(request: Request):
	request.session.clear()
	return {"ok": True}


@router.get("/me")
async def me(user=REQUIRE_USER):
	return {
		"id": user.id,
		"email": user.email,
		"name": user.name,
		"is_admin": user.is_admin,
	}
