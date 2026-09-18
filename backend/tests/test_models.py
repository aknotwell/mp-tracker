"""Database metadata and constraint tests for the Milestone 2 domain."""

from collections.abc import AsyncIterator
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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
        volume_ml_total=Decimal("100.00"),
        volume_ml_remaining=Decimal("75.50"),
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


async def test_volume_remaining_cannot_exceed_total(session: AsyncSession) -> None:
    """The database enforces volume invariants even if API validation is bypassed."""

    user = User(google_subject="google-volume-456", email="volume@example.com")
    fragrance = Fragrance(
        name="Volume Test",
        house=House(name="Volume House"),
        data_source=DataSource.OFFICIAL_SITE,
    )
    session.add(
        UserCollectionItem(
            user=user,
            fragrance=fragrance,
            ownership_status=OwnershipStatus.DECANT,
            volume_ml_total=Decimal("5.00"),
            volume_ml_remaining=Decimal("6.00"),
        )
    )

    with pytest.raises(IntegrityError):
        await session.commit()


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
