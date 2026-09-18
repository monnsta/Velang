from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.site_defaults import DEFAULT_SITE
from app.db.models import SiteSetting


async def get_site(db: AsyncSession) -> dict:
	data = {key: value.copy() if isinstance(value, dict) else list(value) if isinstance(value, list) else value for key, value in DEFAULT_SITE.items()}
	rows = list((await db.execute(select(SiteSetting))).scalars().all())
	for row in rows:
		data[row.key] = row.value
	data["payment_provider"] = settings.payment_provider
	return data


async def set_site(db: AsyncSession, key: str, value):
	row = await db.get(SiteSetting, key)
	if row:
		row.value = value
	else:
		db.add(SiteSetting(key=key, value=value))
	await db.flush()
