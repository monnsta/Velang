from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.site import get_site, set_site
from app.db.models import ContentPage


async def site(db: AsyncSession):
	return await get_site(db)


async def set_value(db: AsyncSession, key: str, value):
	await set_site(db, key, value)


async def page(db: AsyncSession, slug: str):
	return (await db.execute(
		select(ContentPage).where(ContentPage.slug == slug, ContentPage.active.is_(True))
	)).scalar_one_or_none()


async def pages(db: AsyncSession):
	return list((await db.execute(select(ContentPage).order_by(ContentPage.slug))).scalars().all())
