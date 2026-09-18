"""Creation, rotation, and revocation of browser refresh sessions."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.core.config import Settings
from app.core.security import (
    OpaqueToken,
    create_csrf_token,
    create_refresh_token,
    refresh_token_session_id,
    token_hash_matches,
)
from app.models.auth import AuthSession
from app.models.user import User


class InvalidSessionError(ValueError):
    """Raised when a browser session is missing, expired, or invalid."""


class InvalidCSRFTokenError(ValueError):
    """Raised when cookie-backed authentication lacks valid CSRF proof."""


class RefreshTokenReuseError(InvalidSessionError):
    """Raised when a revoked refresh token is presented again."""


@dataclass(frozen=True)
class BrowserSession:
    """New database session plus raw values to return as cookies."""

    model: AuthSession
    refresh_token: OpaqueToken
    csrf_token: OpaqueToken


def create_browser_session(
    user: User,
    settings: Settings,
    *,
    family_id: uuid.UUID | None = None,
    now: datetime | None = None,
) -> BrowserSession:
    """Create an uncommitted session and its independently random tokens."""

    created_at = now or datetime.now(UTC)
    session_id = uuid.uuid4()
    refresh_token = create_refresh_token(session_id)
    csrf_token = create_csrf_token()
    model = AuthSession(
        id=session_id,
        user=user,
        family_id=family_id or uuid.uuid4(),
        refresh_token_hash=refresh_token.hash,
        csrf_token_hash=csrf_token.hash,
        expires_at=created_at + timedelta(days=settings.refresh_session_days),
    )
    return BrowserSession(model=model, refresh_token=refresh_token, csrf_token=csrf_token)


def _utc(value: datetime) -> datetime:
    """Normalize SQLite's timezone-naive datetime values to UTC."""

    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


async def rotate_browser_session(
    database: AsyncSession,
    raw_refresh_token: str,
    raw_csrf_token: str,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> BrowserSession:
    """Validate and replace a refresh session exactly once."""

    rotated_at = now or datetime.now(UTC)
    session = await database.scalar(
        select(AuthSession)
        .options(joinedload(AuthSession.user))
        .where(AuthSession.id == refresh_token_session_id(raw_refresh_token))
    )
    if session is None or not token_hash_matches(raw_refresh_token, session.refresh_token_hash):
        raise InvalidSessionError("Refresh session is invalid")
    if session.revoked_at is not None:
        await revoke_session_family(database, session.family_id, now=rotated_at)
        raise RefreshTokenReuseError("A revoked refresh token was reused")
    if _utc(session.expires_at) <= rotated_at:
        session.revoked_at = rotated_at
        raise InvalidSessionError("Refresh session has expired")
    if not token_hash_matches(raw_csrf_token, session.csrf_token_hash):
        raise InvalidCSRFTokenError("CSRF token is invalid")

    replacement = create_browser_session(
        session.user,
        settings,
        family_id=session.family_id,
        now=rotated_at,
    )
    session.revoked_at = rotated_at
    session.last_used_at = rotated_at
    session.replaced_by_session_id = replacement.model.id
    database.add(replacement.model)
    return replacement


async def revoke_browser_session(
    database: AsyncSession,
    raw_refresh_token: str,
    raw_csrf_token: str,
    *,
    now: datetime | None = None,
) -> None:
    """Validate both browser tokens and revoke the current session."""

    session = await database.get(AuthSession, refresh_token_session_id(raw_refresh_token))
    if session is None or not token_hash_matches(raw_refresh_token, session.refresh_token_hash):
        raise InvalidSessionError("Refresh session is invalid")
    if not token_hash_matches(raw_csrf_token, session.csrf_token_hash):
        raise InvalidCSRFTokenError("CSRF token is invalid")
    if session.revoked_at is None:
        session.revoked_at = now or datetime.now(UTC)


async def revoke_session_family(
    database: AsyncSession,
    family_id: uuid.UUID,
    *,
    now: datetime | None = None,
) -> None:
    """Revoke every active refresh token descended from the same login."""

    await database.execute(
        update(AuthSession)
        .where(AuthSession.family_id == family_id, AuthSession.revoked_at.is_(None))
        .values(revoked_at=now or datetime.now(UTC))
    )
