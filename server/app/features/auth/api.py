from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.features.auth.deps import require_user
from app.features.auth.service import google_user, create_user, password_login

router = APIRouter(prefix="/api/auth")


class Credentials(BaseModel):
	email: EmailStr
	password: str


class RegisterBody(Credentials):
	name: str = ""


class GoogleBody(BaseModel):
	credential: str


@router.post("/register")
async def register(body: RegisterBody, request: Request, db: AsyncSession = Depends(get_db)):
	if len(body.password) < 8:
		raise HTTPException(400, "Password must be at least 8 characters")
	user = await create_user(db, str(body.email), body.password, body.name)
	if not user:
		raise HTTPException(409, "Account already exists")
	request.session["user_id"] = user.id
	await db.commit()
	return {"ok": True}


@router.post("/login")
async def login(body: Credentials, request: Request, db: AsyncSession = Depends(get_db)):
	user = await password_login(db, str(body.email), body.password)
	if not user:
		raise HTTPException(401, "Invalid email or password")
	request.session["user_id"] = user.id
	return {"ok": True}


@router.post("/google")
async def google(body: GoogleBody, request: Request, db: AsyncSession = Depends(get_db)):
	try:
		user = await google_user(db, body.credential)
	except PermissionError as exc:
		raise HTTPException(403, str(exc)) from exc
	request.session["user_id"] = user.id
	await db.commit()
	return {"ok": True}


@router.post("/logout")
async def logout(request: Request):
	request.session.clear()
	return {"ok": True}


@router.get("/me")
async def me(user=Depends(require_user)):
	return {"id": user.id, "email": user.email, "name": user.name, "is_admin": user.is_admin}
