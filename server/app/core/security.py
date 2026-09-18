import hashlib
import secrets
from datetime import datetime
from fastapi import HTTPException, status
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from app.core.config import settings


def utcnow() -> datetime:
	return datetime.utcnow()


def new_token() -> str:
	return secrets.token_urlsafe(48)


def token_hash(token: str) -> str:
	return hashlib.sha256(token.encode("utf-8")).hexdigest()


def normalize_email(value: str) -> str:
	return value.strip().lower()


def verify_google_token(credential: str) -> dict:
	if not settings.google_web_client_id:
		raise HTTPException(503, "Google Sign-In is not configured")
	try:
		payload = id_token.verify_oauth2_token(credential, google_requests.Request(), settings.google_web_client_id)
	except Exception as exc:
		raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid Google credential") from exc
	if not payload.get("email_verified") or not payload.get("email"):
		raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Verified Google email required")
	return payload
