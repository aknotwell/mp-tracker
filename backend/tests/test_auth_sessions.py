"""Tests for refresh-token rotation, CSRF validation, and reuse response."""

from datetime import UTC, datetime

import pytest
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.models import AuthSession, Base, User
from app.services.auth_sessions import (
    InvalidCSRFTokenError,
    RefreshTokenReuseError,
    create_browser_session,
    rotate_browser_session,
)


@pytest.fixture
def auth_settings() -> Settings:
    return Settings(
        _env_file=None,
        jwt_secret=SecretStr("session-test-jwt-secret-at-least-32-bytes"),
        refresh_session_days=30,
    )


@pytest.fixture
async def database() -> AsyncSession:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


async def test_refresh_rotates_tokens_in_one_family(
    database: AsyncSession,
    auth_settings: Settings,
) -> None:
    user = User(google_subject="rotation-user", email="rotation@example.com")
    original = create_browser_session(user, auth_settings)
    database.add(original.model)
    await database.commit()

    replacement = await rotate_browser_session(
        database,
        original.refresh_token.raw,
        original.csrf_token.raw,
        auth_settings,
        now=datetime.now(UTC),
    )
    await database.commit()

    assert original.model.revoked_at is not None
    assert original.model.replaced_by_session_id == replacement.model.id
    assert replacement.model.family_id == original.model.family_id
    assert replacement.refresh_token.raw != original.refresh_token.raw


async def test_refresh_rejects_wrong_csrf_token(
    database: AsyncSession,
    auth_settings: Settings,
) -> None:
    original = create_browser_session(
        User(google_subject="csrf-user", email="csrf@example.com"),
        auth_settings,
    )
    database.add(original.model)
    await database.commit()

    with pytest.raises(InvalidCSRFTokenError):
        await rotate_browser_session(
            database,
            original.refresh_token.raw,
            "wrong-csrf-token",
            auth_settings,
        )


async def test_reused_refresh_token_revokes_replacement_family(
    database: AsyncSession,
    auth_settings: Settings,
) -> None:
    original = create_browser_session(
        User(google_subject="reuse-user", email="reuse@example.com"),
        auth_settings,
    )
    database.add(original.model)
    await database.commit()
    replacement = await rotate_browser_session(
        database,
        original.refresh_token.raw,
        original.csrf_token.raw,
        auth_settings,
    )
    await database.commit()

    with pytest.raises(RefreshTokenReuseError):
        await rotate_browser_session(
            database,
            original.refresh_token.raw,
            original.csrf_token.raw,
            auth_settings,
        )
    await database.commit()
    await database.refresh(replacement.model)

    assert replacement.model.revoked_at is not None
    assert await database.get(AuthSession, replacement.model.id) is not None
