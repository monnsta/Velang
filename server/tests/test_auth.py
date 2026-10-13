import pytest
from app.features.auth.service import (
	admin_user,
	development_user,
	issue_admin_session,
	revoke,
)


@pytest.mark.asyncio
async def test_development_admin_session_round_trip(db):
	user = await development_user(db, admin=True)
	token, _ = await issue_admin_session(db, user)
	await db.commit()
	assert await admin_user(db, token)
	await revoke(db, token)
	await db.commit()
	assert await admin_user(db, token) is None
