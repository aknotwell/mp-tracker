"""HTTP integration tests for the Google-backed application session flow."""

from collections.abc import AsyncIterator
from urllib.parse import parse_qs, urlparse

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.v1 import auth as auth_routes
from app.core.config import Settings, get_settings
from app.db import get_db_session
from app.main import app
from app.models import Base, OIDCLoginAttempt, User
from app.services.google_oidc import GoogleIdentity, create_login_authorization


@pytest.fixture
def auth_settings() -> Settings:
    return Settings(
        _env_file=None,
        google_client_id="api-test-client",
        google_client_secret=SecretStr("api-test-secret"),
        jwt_secret=SecretStr("api-test-jwt-secret-at-least-32-bytes"),
        admin_emails="admin@example.com",
    )


@pytest.fixture
async def session_factory():  # type: ignore[no-untyped-def]
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


@pytest.fixture
async def api_client(
    auth_settings: Settings,
    session_factory,  # type: ignore[no-untyped-def]
) -> AsyncIterator[httpx.AsyncClient]:
    async def override_database() -> AsyncIterator[AsyncSession]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_database
    app.dependency_overrides[get_settings] = lambda: auth_settings
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://testserver",
        follow_redirects=False,
    ) as client:
        yield client
    app.dependency_overrides.clear()


async def test_google_login_redirect_stores_private_attempt(
    api_client: httpx.AsyncClient,
    session_factory,  # type: ignore[no-untyped-def]
) -> None:
    response = await api_client.get("/api/v1/auth/google/login")

    assert response.status_code == 307
    query = parse_qs(urlparse(response.headers["location"]).query)
    assert query["response_type"] == ["code"]
    assert query["code_challenge_method"] == ["S256"]

    async with session_factory() as database:
        attempt_count = await database.scalar(select(func.count()).select_from(OIDCLoginAttempt))
    assert attempt_count == 1


async def test_callback_refresh_me_and_logout_flow(
    api_client: httpx.AsyncClient,
    auth_settings: Settings,
    session_factory,  # type: ignore[no-untyped-def]
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    authorization = create_login_authorization(auth_settings)
    state = parse_qs(urlparse(authorization.url).query)["state"][0]
    async with session_factory() as database:
        database.add(authorization.attempt)
        await database.commit()

    async def verified_google_identity(*_args, **_kwargs) -> GoogleIdentity:  # type: ignore[no-untyped-def]
        return GoogleIdentity(subject="api-google-subject", email="admin@example.com")

    monkeypatch.setattr(auth_routes, "exchange_code_for_identity", verified_google_identity)

    callback = await api_client.get(
        "/api/v1/auth/google/callback",
        params={"code": "one-time-google-code", "state": state},
    )
    assert callback.status_code == 307
    assert callback.headers["location"].endswith("/auth/callback")
    assert "httponly" in callback.headers.get_list("set-cookie")[0].casefold()

    csrf_token = api_client.cookies.get(auth_settings.csrf_cookie_name)
    assert csrf_token is not None
    refresh = await api_client.post(
        "/api/v1/auth/refresh",
        headers={"X-CSRF-Token": csrf_token},
    )
    assert refresh.status_code == 200
    access_token = refresh.json()["access_token"]
    assert refresh.json()["expires_in"] == 900

    me = await api_client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert me.status_code == 200
    assert me.json()["email"] == "admin@example.com"
    assert me.json()["is_admin"] is True

    async with session_factory() as database:
        users = (await database.scalars(select(User))).all()
    assert len(users) == 1

    rotated_csrf_token = api_client.cookies.get(auth_settings.csrf_cookie_name)
    logout_without_csrf = await api_client.post("/api/v1/auth/logout")
    assert logout_without_csrf.status_code == 403

    logout = await api_client.post(
        "/api/v1/auth/logout",
        headers={"X-CSRF-Token": rotated_csrf_token},
    )
    assert logout.status_code == 204
    assert auth_settings.refresh_cookie_name not in api_client.cookies


async def test_me_rejects_missing_access_token(api_client: httpx.AsyncClient) -> None:
    response = await api_client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"
