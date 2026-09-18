"""Tests for private Google OpenID Connect transaction handling."""

import json
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from jwt.algorithms import RSAAlgorithm
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings
from app.models import Base
from app.services.google_oidc import (
    InvalidOIDCResponseError,
    _validate_google_id_token,
    consume_login_attempt,
    create_login_authorization,
)


@pytest.fixture
def google_settings() -> Settings:
    return Settings(
        _env_file=None,
        google_client_id="test-client-id",
        google_client_secret=SecretStr("test-client-secret"),
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


def test_authorization_uses_code_pkce_state_and_nonce(google_settings: Settings) -> None:
    authorization = create_login_authorization(google_settings)
    query = parse_qs(urlparse(authorization.url).query)

    assert query["response_type"] == ["code"]
    assert query["scope"] == ["openid email profile"]
    assert query["code_challenge_method"] == ["S256"]
    assert query["state"][0].startswith(str(authorization.attempt.id))
    assert query["nonce"] == [authorization.attempt.nonce]
    assert authorization.attempt.pkce_verifier not in authorization.url


async def test_login_attempt_can_only_be_consumed_once(
    google_settings: Settings,
    database: AsyncSession,
) -> None:
    authorization = create_login_authorization(google_settings)
    state = parse_qs(urlparse(authorization.url).query)["state"][0]
    database.add(authorization.attempt)
    await database.commit()

    attempt = await consume_login_attempt(database, state)
    await database.commit()
    assert attempt.used_at is not None

    with pytest.raises(InvalidOIDCResponseError):
        await consume_login_attempt(database, state)


def _signed_google_token(
    *,
    client_id: str,
    nonce: str,
    email_verified: bool = True,
) -> tuple[str, dict[str, object]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk["kid"] = "test-google-key"
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": "google-subject-123",
            "email": "Student@Example.com",
            "email_verified": email_verified,
            "nonce": nonce,
            "iss": "https://accounts.google.com",
            "aud": client_id,
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "test-google-key"},
    )
    return token, {"keys": [public_jwk]}


def test_google_id_token_signature_and_claims_are_validated() -> None:
    token, jwks = _signed_google_token(client_id="client-id", nonce="expected-nonce")

    identity = _validate_google_id_token(
        id_token=token,
        jwks=jwks,
        client_id="client-id",
        expected_nonce="expected-nonce",
    )

    assert identity.subject == "google-subject-123"
    assert identity.email == "student@example.com"


def test_google_id_token_requires_verified_email() -> None:
    token, jwks = _signed_google_token(
        client_id="client-id",
        nonce="expected-nonce",
        email_verified=False,
    )

    with pytest.raises(InvalidOIDCResponseError):
        _validate_google_id_token(
            id_token=token,
            jwks=jwks,
            client_id="client-id",
            expected_nonce="expected-nonce",
        )
