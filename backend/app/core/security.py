"""Application JWT and random session-token security helpers."""

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from jwt import InvalidTokenError

from app.core.config import Settings

ACCESS_TOKEN_ALGORITHM = "HS256"


class InvalidAccessTokenError(ValueError):
    """Raised when an application access token cannot be trusted."""


class InvalidRefreshTokenError(ValueError):
    """Raised when a refresh token does not use the expected opaque format."""


@dataclass(frozen=True)
class AccessTokenClaims:
    """Validated claims needed to authenticate an API request."""

    user_id: uuid.UUID
    token_id: uuid.UUID
    expires_at: datetime


@dataclass(frozen=True)
class OpaqueToken:
    """A raw browser token plus the one-way hash safe to persist."""

    raw: str
    hash: str


def hash_token(raw_token: str) -> str:
    """Create a fixed-length SHA-256 digest for database storage."""

    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def token_hash_matches(raw_token: str, expected_hash: str) -> bool:
    """Compare token hashes without leaking matching-prefix timing information."""

    return hmac.compare_digest(hash_token(raw_token), expected_hash)


def create_refresh_token(session_id: uuid.UUID) -> OpaqueToken:
    """Create an opaque refresh token tied to a database session identifier."""

    raw_token = f"{session_id}.{secrets.token_urlsafe(32)}"
    return OpaqueToken(raw=raw_token, hash=hash_token(raw_token))


def create_csrf_token() -> OpaqueToken:
    """Create a separate token for double-submit CSRF validation."""

    raw_token = secrets.token_urlsafe(32)
    return OpaqueToken(raw=raw_token, hash=hash_token(raw_token))


def refresh_token_session_id(raw_token: str) -> uuid.UUID:
    """Extract the lookup ID without treating it as proof the token is valid."""

    session_id, separator, secret = raw_token.partition(".")
    if not separator or not secret:
        raise InvalidRefreshTokenError("Refresh token has an invalid format")

    try:
        return uuid.UUID(session_id)
    except ValueError as error:
        raise InvalidRefreshTokenError("Refresh token has an invalid session ID") from error


def create_access_token(
    user_id: uuid.UUID,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> str:
    """Issue a short-lived JWT for this API, audience, and user."""

    issued_at = now or datetime.now(UTC)
    expires_at = issued_at + timedelta(minutes=settings.access_token_minutes)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "jti": str(uuid.uuid4()),
        "type": "access",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": issued_at,
        "exp": expires_at,
    }
    return jwt.encode(
        payload,
        settings.jwt_secret.get_secret_value(),
        algorithm=ACCESS_TOKEN_ALGORITHM,
    )


def decode_access_token(token: str, settings: Settings) -> AccessTokenClaims:
    """Validate a JWT and return only strongly typed claims used by the API."""

    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[ACCESS_TOKEN_ALGORITHM],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": ["sub", "jti", "type", "iss", "aud", "iat", "exp"]},
        )
        if payload["type"] != "access":
            raise InvalidAccessTokenError("Token is not an access token")

        return AccessTokenClaims(
            user_id=uuid.UUID(payload["sub"]),
            token_id=uuid.UUID(payload["jti"]),
            expires_at=datetime.fromtimestamp(payload["exp"], tz=UTC),
        )
    except (InvalidTokenError, KeyError, TypeError, ValueError) as error:
        if isinstance(error, InvalidAccessTokenError):
            raise
        raise InvalidAccessTokenError("Access token is invalid") from error
