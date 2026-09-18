"""Integration tests for the authenticated, read-only catalog API."""

import uuid
from collections.abc import AsyncIterator

import httpx
import pytest
from pydantic import SecretStr
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import Settings, get_settings
from app.core.security import create_access_token
from app.db import get_db_session
from app.main import app
from app.models import Base, Fragrance, FragranceNote, House, Note, User
from app.models.enums import DataSource, NotePyramidLevel


@pytest.fixture
def catalog_settings() -> Settings:
    return Settings(
        _env_file=None,
        jwt_secret=SecretStr("catalog-test-jwt-secret-at-least-32-bytes"),
    )


@pytest.fixture
async def catalog_api(catalog_settings: Settings):  # type: ignore[no-untyped-def]
    """Create an isolated API, database, user, and catalog for each test."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as database:
        user = User(google_subject="catalog-user", email="reader@example.com")
        montagne = House(name="Montagne Parfums")
        creed = House(name="Creed")
        database.add_all([user, montagne, creed])
        await database.flush()

        pineapple = Note(name="Pineapple")
        birch = Note(name="Birch")
        aventus_clone = Fragrance(
            house_id=montagne.id,
            name="Pineapple Royale",
            concentration="Extrait de Parfum",
            gender="Unisex",
            data_source=DataSource.OFFICIAL_SITE,
        )
        original = Fragrance(
            house_id=creed.id,
            name="Aventus",
            data_source=DataSource.MANUAL,
        )
        database.add_all([pineapple, birch, aventus_clone, original])
        await database.flush()
        database.add_all(
            [
                FragranceNote(
                    fragrance_id=aventus_clone.id,
                    note_id=pineapple.id,
                    pyramid_level=NotePyramidLevel.TOP,
                    sort_order=0,
                ),
                FragranceNote(
                    fragrance_id=aventus_clone.id,
                    note_id=birch.id,
                    pyramid_level=NotePyramidLevel.BASE,
                    sort_order=1,
                ),
            ]
        )
        await database.commit()
        access_token = create_access_token(user.id, catalog_settings)
        seeded_ids = {"montagne": montagne.id, "fragrance": aventus_clone.id}

    async def override_database() -> AsyncIterator[AsyncSession]:
        async with session_factory() as database:
            yield database

    app.dependency_overrides[get_db_session] = override_database
    app.dependency_overrides[get_settings] = lambda: catalog_settings
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client, access_token, seeded_ids

    app.dependency_overrides.clear()
    await engine.dispose()


def authorization(token: str) -> dict[str, str]:
    """Build the bearer header used by authenticated requests."""

    return {"Authorization": f"Bearer {token}"}


async def test_catalog_requires_authentication(catalog_api) -> None:  # type: ignore[no-untyped-def]
    client, _, _ = catalog_api

    response = await client.get("/api/v1/houses")

    assert response.status_code == 401


async def test_houses_support_search_and_pagination(catalog_api) -> None:  # type: ignore[no-untyped-def]
    client, token, seeded_ids = catalog_api

    response = await client.get(
        "/api/v1/houses",
        params={"search": "mont", "limit": 1, "offset": 0},
        headers=authorization(token),
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["limit"] == 1
    assert response.json()["items"][0]["id"] == str(seeded_ids["montagne"])


async def test_fragrance_filter_and_detail_include_ordered_notes(catalog_api) -> None:  # type: ignore[no-untyped-def]
    client, token, seeded_ids = catalog_api
    headers = authorization(token)

    listing = await client.get(
        "/api/v1/fragrances",
        params={"house_id": str(seeded_ids["montagne"])},
        headers=headers,
    )
    detail = await client.get(
        f"/api/v1/fragrances/{seeded_ids['fragrance']}",
        headers=headers,
    )

    assert listing.status_code == 200
    assert listing.json()["total"] == 1
    assert listing.json()["items"][0]["name"] == "Pineapple Royale"
    assert detail.status_code == 200
    assert [item["note"]["name"] for item in detail.json()["fragrance_notes"]] == [
        "Pineapple",
        "Birch",
    ]
    assert [item["pyramid_level"] for item in detail.json()["fragrance_notes"]] == [
        "top",
        "base",
    ]


async def test_notes_search_and_missing_resources(catalog_api) -> None:  # type: ignore[no-untyped-def]
    client, token, _ = catalog_api
    headers = authorization(token)

    notes = await client.get("/api/v1/notes", params={"search": "apple"}, headers=headers)
    missing = await client.get(f"/api/v1/houses/{uuid.uuid4()}", headers=headers)

    assert notes.status_code == 200
    assert notes.json()["total"] == 1
    assert notes.json()["items"][0]["name"] == "Pineapple"
    assert missing.status_code == 404
    assert missing.json() == {"detail": "House not found"}
