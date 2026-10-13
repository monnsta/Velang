from copy import deepcopy

from app.core.config import settings
from app.core.site_defaults import DEFAULT_SITE
from app.db.models import SiteSetting
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


def _merge(base: dict, override: dict) -> dict:
	"""Provide the internal  merge operation."""
	result = deepcopy(base)
	for key, value in override.items():
		if isinstance(value, dict) and isinstance(result.get(key), dict):
			result[key] = _merge(result[key], value)
		else:
			result[key] = value
	return result


async def get_site(db: AsyncSession) -> dict:
	data = deepcopy(DEFAULT_SITE)
	rows = list((await db.execute(select(SiteSetting))).scalars().all())
	for row in rows:
		value = row.value
		data[row.key] = (
			_merge(data.get(row.key, {}), value) if isinstance(value, dict) else value
		)
	# Normalize legacy saved settings: the storefront has one light palette only.
	theme = data.get("theme") or {}
	theme["mode"] = "light"
	theme.pop("dark", None)
	data["theme"] = theme
	# These legacy settings no longer drive any storefront UI.
	data["navigation"] = []
	data["homepage"] = []
	data["payment_provider"] = settings.payment_provider
	return data


async def set_site(db: AsyncSession, key: str, value):
	row = await db.get(SiteSetting, key)
	if row:
		row.value = value
	else:
		db.add(SiteSetting(key=key, value=value))
	await db.flush()
