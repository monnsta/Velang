import os
import sys
from collections.abc import AsyncIterator

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SERVER = os.path.join(ROOT, "server")
if SERVER not in sys.path:
	sys.path.insert(0, SERVER)

from app.db import models  # noqa: F401
from app.db.base import Base
from app.db.models import User


@pytest_asyncio.fixture
async def db() -> AsyncIterator[AsyncSession]:
	engine = create_async_engine("sqlite+aiosqlite:///:memory:")
	async with engine.begin() as connection:
		await connection.run_sync(Base.metadata.create_all)
	Session = async_sessionmaker(engine, expire_on_commit=False)
	async with Session() as session:
		yield session
	await engine.dispose()


@pytest_asyncio.fixture
async def user(db: AsyncSession) -> User:
	row = User(email="tester@example.com", name="Tester")
	db.add(row)
	await db.flush()
	return row
