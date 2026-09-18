from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.site import get_site
from app.db.session import get_db
from app.features.auth.service import create_user, password_login

router = APIRouter()
templates = Jinja2Templates(directory="server/app/templates")


async def auth_context(request: Request, db: AsyncSession, title: str, error: str = ""):
	site = await get_site(db)
	return {
		"request": request,
		"site": site,
		"title": title,
		"error": error,
		"google_client_id": settings.google_web_client_id,
		"user": None,
		"cart_count": 0,
	}


@router.get("/login")
async def login_page(request: Request, db: AsyncSession = Depends(get_db)):
	return templates.TemplateResponse(request, "auth/login.html", await auth_context(request, db, "Log in"))


@router.post("/login")
async def login_form(request: Request, email: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
	user = await password_login(db, email, password)
	if not user:
		return templates.TemplateResponse(request, "auth/login.html", await auth_context(request, db, "Log in", "Invalid email or password"), status_code=400)
	request.session["user_id"] = user.id
	return RedirectResponse("/account", 303)


@router.get("/register")
async def register_page(request: Request, db: AsyncSession = Depends(get_db)):
	return templates.TemplateResponse(request, "auth/register.html", await auth_context(request, db, "Create account"))


@router.post("/register")
async def register_form(request: Request, name: str = Form(""), email: str = Form(...), password: str = Form(...), db: AsyncSession = Depends(get_db)):
	if len(password) < 8:
		return templates.TemplateResponse(request, "auth/register.html", await auth_context(request, db, "Create account", "Password must be at least 8 characters"), status_code=400)
	user = await create_user(db, email, password, name)
	if not user:
		return templates.TemplateResponse(request, "auth/register.html", await auth_context(request, db, "Create account", "An account with that email already exists"), status_code=409)
	request.session["user_id"] = user.id
	await db.commit()
	return RedirectResponse("/account", 303)


@router.get("/logout")
async def logout(request: Request):
	request.session.clear()
	return RedirectResponse("/")
