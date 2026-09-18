"""Environment-backed application configuration.

Settings use the ``APP_`` prefix so application values are easy to distinguish
from operating-system variables. Local secrets belong in an untracked ``.env`` file.
"""

from functools import lru_cache
from typing import Literal

from pydantic import AnyHttpUrl, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Validated configuration shared by the API process."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="APP_",
        extra="ignore",
    )

    app_name: str = "MP Collection Tracker API"
    env: str = "development"
    debug: bool = False
    api_prefix: str = "/api/v1"
    database_url: str = "sqlite+aiosqlite:///./mp_tracker.sqlite3"
    frontend_origin: AnyHttpUrl = AnyHttpUrl("http://localhost:3000")
    google_client_id: str | None = None
    google_client_secret: SecretStr | None = None
    google_redirect_uri: AnyHttpUrl = AnyHttpUrl(
        "http://localhost:8000/api/v1/auth/google/callback"
    )
    jwt_secret: SecretStr = Field(
        default=SecretStr("development-only-change-me-use-32-bytes"),
        min_length=32,
    )
    jwt_issuer: str = "mp-tracker-api"
    jwt_audience: str = "mp-tracker-web"
    access_token_minutes: int = Field(default=15, ge=1, le=60)
    refresh_session_days: int = Field(default=30, ge=1, le=90)
    refresh_cookie_name: str = "mp_tracker_refresh"
    csrf_cookie_name: str = "mp_tracker_csrf"
    cookie_secure: bool = False
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    admin_emails: str = ""

    @property
    def normalized_admin_emails(self) -> frozenset[str]:
        """Return configured administrator emails in a comparison-safe form."""

        return frozenset(
            email.strip().casefold() for email in self.admin_emails.split(",") if email.strip()
        )


@lru_cache
def get_settings() -> Settings:
    """Build settings once so every request sees one consistent configuration."""

    return Settings()
