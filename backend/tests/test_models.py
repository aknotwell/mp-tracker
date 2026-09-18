"""Database metadata and constraint tests for the Milestone 2 domain."""

from collections.abc import AsyncIterator
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import (
    AuthSession,
    Base,
    DataSource,
    Fragrance,
    House,
    ItemAttributeRating,
    LongevityBucket,
    OIDCLoginAttempt,
    OwnershipStatus,
    User,
    UserCollectionItem,
)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """Create an isolated SQLite database directly from approved metadata."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as database_session:
        yield database_session

    await engine.dispose()


async def test_full_collection_graph_round_trip(session: AsyncSession) -> None:
    """Core catalog, ownership, and rating rows can be persisted together."""

    user = User(google_subject="google-owner-123", email="owner@example.com")
    house = House(name="Example House")
    fragrance = Fragrance(
        name="Example Fragrance",
        house=house,
        data_source=DataSource.OFFICIAL_SITE,
        source_external_id="example-fragrance",
    )
    item = UserCollectionItem(
        user=user,
        fragrance=fragrance,
        ownership_status=OwnershipStatus.FULL_BOTTLE,
    )
    item.rating = ItemAttributeRating(
        dna_accuracy=8,
        longevity=LongevityBucket.SIX_TO_EIGHT_HOURS,
        projection=7,
    )
    session.add(item)
    await session.commit()

    stored_item = await session.scalar(select(UserCollectionItem))

    assert stored_item is not None
    assert stored_item.elo_score == Decimal("1000.0000")
    assert stored_item.comparisons_count == 0


def test_all_expected_tables_are_registered() -> None:
    """Importing app.models exposes complete metadata to Alembic."""

    assert set(Base.metadata.tables) == {
        "auth_sessions",
        "oidc_login_attempts",
        "users",
        "houses",
        "fragrances",
        "notes",
        "fragrance_notes",
        "user_collection_items",
        "item_attribute_ratings",
        "head_to_head_matchups",
    }


def test_collection_item_tracks_type_without_volume() -> None:
    """Ownership records distinguish bottles and decants without tracking milliliters."""

    columns = Base.metadata.tables[UserCollectionItem.__tablename__].columns

    assert "ownership_status" in columns
    assert "volume_ml_total" not in columns
    assert "volume_ml_remaining" not in columns


def test_user_stores_google_identity_without_password_data() -> None:
    """The user table has only the identity fields needed for Google login."""

    user_columns = Base.metadata.tables["users"].columns

    assert "google_subject" in user_columns
    assert "email" in user_columns
    assert "is_admin" in user_columns
    assert "password_hash" not in user_columns


def test_auth_session_stores_hashes_instead_of_raw_tokens() -> None:
    """The session table must never contain columns for raw browser secrets."""

    session_columns = Base.metadata.tables[AuthSession.__tablename__].columns

    assert "refresh_token_hash" in session_columns
    assert "csrf_token_hash" in session_columns
    assert "refresh_token" not in session_columns
    assert "csrf_token" not in session_columns


def test_oidc_attempt_keeps_pkce_and_nonce_server_side() -> None:
    """Private login transaction values have a dedicated database table."""

    attempt_columns = Base.metadata.tables[OIDCLoginAttempt.__tablename__].columns

    assert "state_hash" in attempt_columns
    assert "nonce" in attempt_columns
    assert "pkce_verifier" in attempt_columns
    assert "used_at" in attempt_columns
