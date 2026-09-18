"""Tests for JWT and opaque browser-session token helpers."""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
import pytest
from pydantic import SecretStr

from app.core.config import Settings
from app.core.security import (
    InvalidAccessTokenError,
    InvalidRefreshTokenError,
    create_access_token,
    create_csrf_token,
    create_refresh_token,
    decode_access_token,
    refresh_token_session_id,
    token_hash_matches,
)


@pytest.fixture
def auth_settings() -> Settings:
    """Use a test-only signing key and disable loading a developer's .env file."""

    return Settings(
        _env_file=None,
        jwt_secret=SecretStr("test-secret-that-is-not-used-outside-tests"),
        jwt_issuer="test-issuer",
        jwt_audience="test-audience",
        access_token_minutes=15,
    )


def test_access_token_round_trip(auth_settings: Settings) -> None:
    user_id = uuid.uuid4()
    now = datetime.now(UTC)

    token = create_access_token(user_id, auth_settings, now=now)
    claims = decode_access_token(token, auth_settings)

    assert claims.user_id == user_id
    assert claims.expires_at == now.replace(microsecond=0) + timedelta(minutes=15)


def test_access_token_rejects_wrong_audience(auth_settings: Settings) -> None:
    token = create_access_token(uuid.uuid4(), auth_settings)
    wrong_audience = auth_settings.model_copy(update={"jwt_audience": "another-app"})

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token, wrong_audience)


def test_access_token_rejects_expired_token(auth_settings: Settings) -> None:
    token = create_access_token(
        uuid.uuid4(),
        auth_settings,
        now=datetime.now(UTC) - timedelta(hours=1),
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token, auth_settings)


def test_access_token_rejects_non_access_type(auth_settings: Settings) -> None:
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(uuid.uuid4()),
            "jti": str(uuid.uuid4()),
            "type": "refresh",
            "iss": auth_settings.jwt_issuer,
            "aud": auth_settings.jwt_audience,
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        auth_settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )

    with pytest.raises(InvalidAccessTokenError):
        decode_access_token(token, auth_settings)


def test_refresh_token_contains_lookup_id_but_persists_only_hash() -> None:
    session_id = uuid.uuid4()
    token = create_refresh_token(session_id)

    assert refresh_token_session_id(token.raw) == session_id
    assert token_hash_matches(token.raw, token.hash)
    assert token.raw != token.hash
    assert len(token.hash) == 64


def test_malformed_refresh_token_is_rejected() -> None:
    with pytest.raises(InvalidRefreshTokenError):
        refresh_token_session_id("not-a-valid-refresh-token")


def test_csrf_tokens_are_random_and_hash_verifiable() -> None:
    first = create_csrf_token()
    second = create_csrf_token()

    assert first.raw != second.raw
    assert token_hash_matches(first.raw, first.hash)
    assert not token_hash_matches(first.raw, second.hash)
