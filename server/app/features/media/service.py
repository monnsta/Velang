import asyncio
import mimetypes
import os
from uuid import uuid4

from app.db.models import MediaAsset
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

UPLOADS = os.path.join(
	os.path.dirname(
		os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
	),
	"data",
	"media",
	"uploads",
)
os.makedirs(UPLOADS, exist_ok=True)


def _write_file(path: str, content: bytes):
	"""Provide the internal  write file operation."""
	with open(path, "wb") as handle:
		handle.write(content)


async def save(db: AsyncSession, filename: str, content: bytes, alt_text=""):
	safe = os.path.basename(filename).replace("\x00", "") or "upload.bin"
	stored = f"img-{uuid4().hex[:8]}-{safe}"
	file_path = os.path.join(UPLOADS, stored)

	await asyncio.to_thread(_write_file, file_path, content)

	row = MediaAsset(
		filename=safe,
		path=f"/media/uploads/{stored}",
		mime_type=mimetypes.guess_type(stored)[0] or "application/octet-stream",
		size_bytes=len(content),
		alt_text=alt_text,
	)
	db.add(row)
	await db.flush()
	return row


async def all_media(db: AsyncSession):
	return list(
		(await db.execute(select(MediaAsset).order_by(MediaAsset.id.desc())))
		.scalars()
		.all()
	)
