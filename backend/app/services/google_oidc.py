"""Google OpenID Connect authorization-code and ID-token operations."""

import base64
import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import httpx
import jwt
from jwt import InvalidTokenError, PyJWKSet
from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings
from app.core.security import hash_token
from app.models.oidc import OIDCLoginAttempt

GOOGLE_AUTHORIZATION_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
GOOGLE_JWKS_ENDPOINT = "https://www.googleapis.com/oauth2/v3/certs"
GOOGLE_ISSUERS = frozenset({"https://accounts.google.com", "accounts.google.com"})
OIDC_ATTEMPT_MINUTES = 10


class OIDCConfigurationError(RuntimeError):
    """Raised when Google login is requested before credentials are configured."""


class InvalidOIDCResponseError(ValueError):
    """Raised when a Google response or login attempt cannot be trusted."""


@dataclass(frozen=True)
class GoogleIdentity:
    """The small set of verified Google claims retained by this application."""

    subject: str
    email: str


@dataclass(frozen=True)
class LoginAuthorization:
    """Authorization URL plus the private attempt row awaiting its callback."""

    url: str
    attempt: OIDCLoginAttempt


def _google_credentials(settings: Settings) -> tuple[str, str]:
    if not settings.google_client_id or not settings.google_client_secret:
        raise OIDCConfigurationError("Google OpenID Connect is not configured")
    return settings.google_client_id, settings.google_client_secret.get_secret_value()


def _pkce_challenge(verifier: str) -> str:
    digest = hashlib.sha256(verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def create_login_authorization(settings: Settings) -> LoginAuthorization:
    """Create private OIDC transaction state and Google's redirect URL."""

    client_id, _client_secret = _google_credentials(settings)
    attempt_id = uuid.uuid4()
    state = f"{attempt_id}.{secrets.token_urlsafe(32)}"
    nonce = secrets.token_urlsafe(32)
    pkce_verifier = secrets.token_urlsafe(64)
    attempt = OIDCLoginAttempt(
        id=attempt_id,
        state_hash=hash_token(state),
        nonce=nonce,
        pkce_verifier=pkce_verifier,
        expires_at=datetime.now(UTC) + timedelta(minutes=OIDC_ATTEMPT_MINUTES),
    )
    query = urlencode(
        {
            "client_id": client_id,
            "redirect_uri": str(settings.google_redirect_uri),
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "code_challenge": _pkce_challenge(pkce_verifier),
            "code_challenge_method": "S256",
        }
    )
    return LoginAuthorization(url=f"{GOOGLE_AUTHORIZATION_ENDPOINT}?{query}", attempt=attempt)


def _state_attempt_id(state: str) -> uuid.UUID:
    attempt_id, separator, secret = state.partition(".")
    if not separator or not secret:
        raise InvalidOIDCResponseError("OIDC state is malformed")
    try:
        return uuid.UUID(attempt_id)
    except ValueError as error:
        raise InvalidOIDCResponseError("OIDC state has an invalid identifier") from error


async def consume_login_attempt(
    session: AsyncSession,
    state: str,
    *,
    now: datetime | None = None,
) -> OIDCLoginAttempt:
    """Atomically consume one unexpired attempt so a callback cannot be replayed."""

    consumed_at = now or datetime.now(UTC)
    statement = (
        update(OIDCLoginAttempt)
        .where(
            OIDCLoginAttempt.id == _state_attempt_id(state),
            OIDCLoginAttempt.state_hash == hash_token(state),
            OIDCLoginAttempt.used_at.is_(None),
            OIDCLoginAttempt.expires_at > consumed_at,
        )
        .values(used_at=consumed_at)
        .returning(OIDCLoginAttempt)
    )
    attempt = (await session.execute(statement)).scalar_one_or_none()
    if attempt is None:
        raise InvalidOIDCResponseError("OIDC login attempt is invalid, expired, or already used")
    return attempt


async def exchange_code_for_identity(
    code: str,
    attempt: OIDCLoginAttempt,
    settings: Settings,
    http_client: httpx.AsyncClient,
) -> GoogleIdentity:
    """Exchange Google's one-time code and validate its signed identity token."""

    client_id, client_secret = _google_credentials(settings)
    try:
        token_response = await http_client.post(
            GOOGLE_TOKEN_ENDPOINT,
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": str(settings.google_redirect_uri),
                "grant_type": "authorization_code",
                "code_verifier": attempt.pkce_verifier,
            },
        )
        token_response.raise_for_status()
        id_token = token_response.json()["id_token"]
        jwks_response = await http_client.get(GOOGLE_JWKS_ENDPOINT)
        jwks_response.raise_for_status()
        return _validate_google_id_token(
            id_token=id_token,
            jwks=jwks_response.json(),
            client_id=client_id,
            expected_nonce=attempt.nonce,
        )
    except (httpx.HTTPError, KeyError, TypeError, ValueError) as error:
        if isinstance(error, InvalidOIDCResponseError):
            raise
        raise InvalidOIDCResponseError("Google authentication response is invalid") from error


def _validate_google_id_token(
    *,
    id_token: str,
    jwks: dict[str, object],
    client_id: str,
    expected_nonce: str,
) -> GoogleIdentity:
    """Verify signature and required Google identity claims."""

    try:
        header = jwt.get_unverified_header(id_token)
        if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
            raise InvalidOIDCResponseError("Google ID token has an unsupported header")

        key = next(
            (
                candidate.key
                for candidate in PyJWKSet.from_dict(jwks).keys
                if candidate.key_id == header["kid"]
            ),
            None,
        )
        if key is None:
            raise InvalidOIDCResponseError("Google ID token signing key was not found")

        claims = jwt.decode(
            id_token,
            key,
            algorithms=["RS256"],
            audience=client_id,
            options={
                "verify_iss": False,
                "require": ["sub", "email", "email_verified", "nonce", "iss", "aud", "exp", "iat"],
            },
        )
        if claims["iss"] not in GOOGLE_ISSUERS:
            raise InvalidOIDCResponseError("Google ID token issuer is invalid")
        if not hmac.compare_digest(str(claims["nonce"]), expected_nonce):
            raise InvalidOIDCResponseError("Google ID token nonce is invalid")
        if claims["email_verified"] is not True:
            raise InvalidOIDCResponseError("Google email is not verified")
        if not isinstance(claims["sub"], str) or not isinstance(claims["email"], str):
            raise InvalidOIDCResponseError("Google identity claims are invalid")
        return GoogleIdentity(subject=claims["sub"], email=claims["email"].casefold())
    except (InvalidTokenError, KeyError, StopIteration, TypeError, ValueError) as error:
        if isinstance(error, InvalidOIDCResponseError):
            raise
        raise InvalidOIDCResponseError("Google ID token is invalid") from error
