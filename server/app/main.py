import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.core.config import ROOT, settings
from app.core.site import get_site
from app.db.session import SessionLocal, init_db
from app.features.addresses.api import router as addresses_api
from app.features.admin.api import router as admin_api
from app.features.auth.api import router as auth_api
from app.features.auth.web import router as auth_web
from app.features.cart.api import router as cart_api
from app.features.content.api import router as content_api
from app.features.orders.api import router as orders_api
from app.web import page_ctx, router as web

TEMPLATES = Jinja2Templates(directory=os.path.join(ROOT, "server", "app", "templates"))


@asynccontextmanager
async def lifespan(app: FastAPI):
	"""Initialize application resources for the process lifetime."""
	await init_db()
	yield


app = FastAPI(
	title="Velang",
	version="2.0.0",
	docs_url="/api/docs" if settings.app_env != "production" else None,
	lifespan=lifespan,
)
app.add_middleware(
	SessionMiddleware,
	secret_key=settings.session_secret,
	session_cookie="velang_session",
	https_only=settings.cookie_secure,
	same_site="lax",
)
app.mount(
	"/static",
	StaticFiles(directory=os.path.join(ROOT, "server", "app", "static")),
	name="static",
)
app.mount(
	"/media",
	StaticFiles(directory=os.path.join(ROOT, "server", "data", "media")),
	name="media",
)
for route in (
	auth_api,
	cart_api,
	addresses_api,
	orders_api,
	content_api,
	admin_api,
):
	app.include_router(route)
app.include_router(auth_web)
app.include_router(web)


@app.get("/favicon.ico")
async def favicon():
	return FileResponse(
		os.path.join(ROOT, "server", "app", "static", "assets", "favicon.png")
	)


@app.get("/health")
async def health():
	return {"ok": True, "service": "velang", "version": "2.0.0"}


@app.exception_handler(404)
async def fallback_404(request: Request, exc):
	if request.url.path.startswith("/api/"):
		return JSONResponse({"detail": "Not found"}, status_code=404)
	async with SessionLocal() as db:
		return TEMPLATES.TemplateResponse(
			request,
			"pages/store/404.html",
			await page_ctx(request, db, "Not found"),
			status_code=404,
		)
