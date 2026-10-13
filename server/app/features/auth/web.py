from app.core.config import settings
from app.core.site import get_site
from app.db.session import get_db
from app.features.auth.service import development_user
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter()
templates = Jinja2Templates(directory="server/app/templates")

GET_DB = Depends(get_db)


async def auth_context(request: Request, db: AsyncSession, title: str, error: str = ""):
	site = await get_site(db)
	return {
		"request": request,
		"site": site,
		"title": title,
		"error": error,
		"google_client_id": settings.google_web_client_id,
		"dev_auth": settings.app_env != "production" and settings.dev_auth,
		"next": request.query_params.get("next", "/account"),
		"user": None,
		"cart_count": 0,
	}


@router.get("/login")
async def login_page(request: Request, db: AsyncSession = GET_DB):
	"""Render the login page storefront page."""
	return templates.TemplateResponse(
		request, "pages/auth/login.html", await auth_context(request, db, "Log in")
	)


@router.post("/login/dev")
async def development_login(
	request: Request, next: str = Form("/account"), db: AsyncSession = GET_DB
):
	if settings.app_env == "production" or not settings.dev_auth:
		return RedirectResponse("/login", 303)
	user = await development_user(db)
	await db.commit()
	request.session["user_id"] = user.id
	return RedirectResponse(next if next.startswith("/") else "/account", 303)


@router.get("/register")
async def register_page(request: Request, db: AsyncSession = GET_DB):
	"""Render the register page storefront page."""
	return templates.TemplateResponse(
		request,
		"pages/auth/register.html",
		await auth_context(request, db, "Create account"),
	)


@router.get("/logout")
async def logout(request: Request):
	request.session.clear()
	return RedirectResponse("/")
