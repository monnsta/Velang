import os

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import ROOT, settings

engine = create_async_engine(settings.database_url, echo=False)


@event.listens_for(engine.sync_engine, "connect")
def _enable_sqlite_foreign_keys(dbapi_connection, connection_record):
	if "sqlite" not in settings.database_url:
		return
	cursor = dbapi_connection.cursor()
	cursor.execute("PRAGMA foreign_keys=ON")
	cursor.close()


SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
	async with SessionLocal() as session:
		yield session


async def init_db():
	from app.db.base import Base
	from app.db import models  # noqa: F401
	os.makedirs(os.path.join(ROOT, "server", "database"), exist_ok=True)
	async with engine.begin() as connection:
		await connection.run_sync(Base.metadata.create_all)
