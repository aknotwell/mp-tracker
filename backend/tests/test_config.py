"""Tests for environment-backed application configuration."""

from app.core.config import Settings


def test_settings_have_safe_local_defaults() -> None:
    """A developer can start the scaffold without supplying secrets."""

    settings = Settings(_env_file=None)

    assert settings.env == "development"
    assert settings.database_url.startswith("sqlite+aiosqlite:///")
    assert str(settings.frontend_origin) == "http://localhost:3000/"
