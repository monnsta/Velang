from datetime import datetime, timedelta
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.security import hash_token, new_token, normalize_email, utcnow, verify_google_token
from app.db.models import AdminSession, User

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


async def by_id(db: AsyncSession, user_id: int):
	return (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()


async def by_email(db: AsyncSession, email: str):
	return (await db.execute(select(User).where(User.email == normalize_email(email)))).scalar_one_or_none()


async def create_user(db: AsyncSession, email: str, password: str, name: str):
	if await by_email(db, email):
		return None
	user = User(email=normalize_email(email), name=name.strip(), password_hash=pwd.hash(password))
	db.add(user)
	await db.flush()
	return user


async def password_login(db: AsyncSession, email: str, password: str):
	user = await by_email(db, email)
	if not user or not user.password_hash or not user.is_active or not pwd.verify(password, user.password_hash):
		return None
	return user


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


async def issue_admin_session(db: AsyncSession, user: User):
	token = new_token()
	session = AdminSession(user_id=user.id, token_hash=hash_token(token), expires_at=utcnow() + timedelta(days=settings.admin_session_days))
	db.add(session)
	await db.flush()
	return token, session


async def admin_user(db: AsyncSession, raw_token: str):
	session = (await db.execute(select(AdminSession).where(AdminSession.token_hash == hash_token(raw_token), AdminSession.revoked_at.is_(None)))).scalar_one_or_none()
	if not session or session.expires_at < utcnow():
		return None
	user = await by_id(db, session.user_id)
	return user if user and user.is_admin and user.is_active else None


async def revoke(db: AsyncSession, raw_token: str):
	session = (await db.execute(select(AdminSession).where(AdminSession.token_hash == hash_token(raw_token)))).scalar_one_or_none()
	if session:
		session.revoked_at = utcnow()
	await db.flush()
