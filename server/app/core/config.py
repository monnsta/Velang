import os
from functools import lru_cache

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
DEFAULT_DATABASE = os.path.join(ROOT, "server", "database", "velang.db")


class Settings(BaseSettings):
	app_env: str = Field("development", alias="APP_ENV")
	host: str = Field("127.0.0.1", alias="HOST")
	port: int = Field(8000, alias="PORT")
	database_url: str = Field(f"sqlite+aiosqlite:///{DEFAULT_DATABASE}", alias="DATABASE_URL")
	session_secret: str = Field("change-me-before-production", alias="SESSION_SECRET")
	cookie_secure: bool = Field(False, alias="COOKIE_SECURE")
	google_web_client_id: str = Field("", alias="GOOGLE_WEB_CLIENT_ID")
	admin_emails: str = Field("", alias="ADMIN_EMAILS")
	admin_session_days: int = Field(14, alias="ADMIN_SESSION_DAYS")
	payment_provider: str = Field("dev", alias="PAYMENT_PROVIDER")
	google_pay_merchant_vpa: str = Field("", alias="GOOGLE_PAY_MERCHANT_VPA")
	google_pay_merchant_name: str = Field("Velang", alias="GOOGLE_PAY_MERCHANT_NAME")
	gcs_bucket: str = Field("", alias="GCS_BUCKET")
	gcs_project_id: str = Field("", alias="GCS_PROJECT_ID")
	model_config = SettingsConfigDict(
		env_file=os.path.join(ROOT, ".env"),
		extra="ignore",
		populate_by_name=True,
	)

	@property
	def admin_email_set(self) -> set[str]:
		return {x.strip().lower() for x in self.admin_emails.split(",") if x.strip()}

	@model_validator(mode="after")
	def validate_environment(self):
		if self.app_env == "production" and self.session_secret == "change-me-before-production":
			raise ValueError("SESSION_SECRET must be changed before production")
		if self.admin_session_days < 1:
			raise ValueError("ADMIN_SESSION_DAYS must be at least 1")
		return self


@lru_cache
def get_settings() -> Settings:
	return Settings()


settings = get_settings()
