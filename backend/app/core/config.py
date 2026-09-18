"""Environment-backed application configuration.

Settings use the ``APP_`` prefix so application values are easy to distinguish
from operating-system variables. Local secrets belong in an untracked ``.env`` file.
"""

from functools import lru_cache

from pydantic import AnyHttpUrl
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


@lru_cache
def get_settings() -> Settings:
    """Build settings once so every request sees one consistent configuration."""

    return Settings()
