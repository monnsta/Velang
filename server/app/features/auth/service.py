from datetime import timedelta, timezone

from app.core.config import settings
from app.core.security import (
	new_token,
	normalize_email,
	token_hash,
	utcnow,
	verify_google_token,
)
from app.db.models import AdminSession, User
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


async def by_id(db: AsyncSession, user_id: int):
	return (
		await db.execute(select(User).where(User.id == user_id))
	).scalar_one_or_none()


async def by_email(db: AsyncSession, email: str):
	return (
		await db.execute(select(User).where(User.email == normalize_email(email)))
	).scalar_one_or_none()


async def google_user(db: AsyncSession, credential: str):
	payload = verify_google_token(credential)
	email = normalize_email(payload["email"])
	user = await by_email(db, email)
	if not user:
		user = User(email=email, name=str(payload.get("name") or email.split("@")[0]))
		db.add(user)
		await db.flush()
	elif not user.is_active:
		raise PermissionError("This account is inactive")
	user.google_subject = str(payload.get("sub") or "") or None
	return user


async def development_user(db: AsyncSession, admin: bool = False):
	"""Return a deterministic local-only user for development and tests."""
	email = "dev-admin@localhost" if admin else "dev-user@localhost"
	user = await by_email(db, email)
	if not user:
		user = User(
			email=email,
			name="Development Admin" if admin else "Development User",
			is_admin=admin,
		)
		db.add(user)
		await db.flush()
	else:
		user.is_active = True
		if admin:
			user.is_admin = True
	return user


async def issue_admin_session(db: AsyncSession, user: User):
	token = new_token()
	session = AdminSession(
		user_id=user.id,
		token_hash=token_hash(token),
		expires_at=utcnow() + timedelta(days=settings.admin_session_days),
	)
	db.add(session)
	await db.flush()
	return token, session


async def admin_user(db: AsyncSession, raw_token: str):
	session = (
		await db.execute(
			select(AdminSession).where(
				AdminSession.token_hash == token_hash(raw_token),
				AdminSession.revoked_at.is_(None),
			)
		)
	).scalar_one_or_none()
	if not session:
		return None
	# SQLite returns timezone-naive values for SQLAlchemy DateTime columns even
	# when an aware UTC value was originally inserted. Normalize before comparing.
	expires_at = session.expires_at
	if expires_at.tzinfo is None:
		expires_at = expires_at.replace(tzinfo=timezone.utc)
	if expires_at < utcnow():
		return None
	user = await by_id(db, session.user_id)
	return user if user and user.is_admin and user.is_active else None


async def revoke(db: AsyncSession, raw_token: str):
	session = (
		await db.execute(
			select(AdminSession).where(AdminSession.token_hash == token_hash(raw_token))
		)
	).scalar_one_or_none()
	if session:
		session.revoked_at = utcnow()
	await db.flush()
