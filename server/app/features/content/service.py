"""Load editable storefront information pages from Markdown files."""

import json
import os
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import ROOT
from app.core.site import get_site, set_site
from app.db.models import ContentPage

PAGES_DIR = os.path.join(ROOT, "server", "content", "pages")


def _parse_markdown_page(source: str, slug: str) -> dict:
	"""Parse a static page's small YAML-like front matter and Markdown body."""
	lines = source.splitlines()
	metadata = {}
	body_start = 0
	if lines and lines[0].strip() == "---":
		for index, line in enumerate(lines[1:], start=1):
			if line.strip() == "---":
				body_start = index + 1
				break
			if ":" in line:
				key, value = line.split(":", 1)
				key = key.strip()
				value = value.strip()
				if value.startswith('"') and value.endswith('"'):
					try:
						value = json.loads(value)
					except json.JSONDecodeError:
						value = value[1:-1]
				elif value.startswith("'") and value.endswith("'"):
					value = value[1:-1]
				metadata[key] = value
	active_value = str(metadata.get("active", "true")).strip().lower()
	return {
		"slug": slug,
		"title": metadata.get("title", slug.replace("-", " ").title()),
		"body_markdown": "\n".join(lines[body_start:]).strip(),
		"active": active_value not in {"false", "0", "no", "off"},
		"meta": metadata,
	}


def _static_page(slug: str) -> dict | None:
	"""Read one safe, top-level static Markdown page from the content directory."""
	if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug or ""):
		return None
	path = os.path.join(PAGES_DIR, f"{slug}.md")
	if not os.path.isfile(path):
		return None
	with open(path, "r", encoding="utf-8") as handle:
		return _parse_markdown_page(handle.read(), slug)


def static_pages(include_inactive: bool = False) -> list[dict]:
	"""Return Markdown storefront pages in stable filename order.

	Inactive pages remain available to the admin when requested, but are not
	listed in the public footer.
	"""
	if not os.path.isdir(PAGES_DIR):
		return []
	items = []
	for filename in sorted(os.listdir(PAGES_DIR)):
		if not filename.endswith(".md"):
			continue
		slug = filename[:-3]
		page_data = _static_page(slug)
		if page_data and (include_inactive or page_data.get("active", True)):
			items.append(page_data)
	return items


async def site(db: AsyncSession):
	"""Return the merged storefront site configuration."""
	return await get_site(db)


async def set_value(db: AsyncSession, key: str, value):
	"""Update one storefront configuration value."""
	await set_site(db, key, value)


async def page(db: AsyncSession, slug: str):
	"""Load a Markdown page first, falling back to legacy database content."""
	static = _static_page(slug)
	if static and static.get("active", True):
		return static
	if static and not static.get("active", True):
		return None
	return (
		await db.execute(
			select(ContentPage).where(
				ContentPage.slug == slug,
				ContentPage.active.is_(True),
			)
		)
	).scalar_one_or_none()


def page_content_fields(row, slug: str) -> tuple[str, str]:
	"""Return a page title and Markdown body for static or database-backed pages."""
	if isinstance(row, dict):
		return (
			row.get("title") or slug.replace("-", " ").title(),
			row.get("body_markdown") or "",
		)
	return row.title, row.body_markdown or ""


async def pages(db: AsyncSession):
	"""Return legacy database content pages for administrative compatibility."""
	return list(
		(await db.execute(select(ContentPage).order_by(ContentPage.slug))).scalars().all()
	)
