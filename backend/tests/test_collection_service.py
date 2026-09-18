"""Tests for user-scoped collection database queries."""

import uuid
from collections.abc import AsyncIterator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import (
    Base,
    DataSource,
    Fragrance,
    House,
    ItemAttributeRating,
    LongevityBucket,
    OwnershipStatus,
    User,
    UserCollectionItem,
)
from app.services.collections import (
    create_collection_item,
    get_collection_item,
    list_collection_items,
)


@pytest.fixture
async def session() -> AsyncIterator[AsyncSession]:
    """Give each test a new in-memory SQLite database."""

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    async with session_factory() as database:
        yield database

    await engine.dispose()


async def test_list_collection_items_returns_only_requested_users_items(
    session: AsyncSession,
) -> None:
    """One user must never receive another user's collection data."""

    first_user = User(google_subject="collection-user-one", email="one@example.com")
    second_user = User(google_subject="collection-user-two", email="two@example.com")
    house = House(name="Collection Test House")
    first_fragrance = Fragrance(
        name="First Fragrance",
        house=house,
        data_source=DataSource.OFFICIAL_SITE,
    )
    second_fragrance = Fragrance(
        name="Second Fragrance",
        house=house,
        data_source=DataSource.OFFICIAL_SITE,
    )
    first_item = UserCollectionItem(
        user=first_user,
        fragrance=first_fragrance,
        ownership_status=OwnershipStatus.FULL_BOTTLE,
    )
    first_item.rating = ItemAttributeRating(
        dna_accuracy=8,
        longevity=LongevityBucket.SIX_TO_EIGHT_HOURS,
        projection=7,
    )
    second_item = UserCollectionItem(
        user=second_user,
        fragrance=second_fragrance,
        ownership_status=OwnershipStatus.DECANT,
    )
    session.add_all([first_item, second_item])
    await session.commit()
    first_item_id = first_item.id
    first_user_id = first_user.id

    # Clear SQLAlchemy's in-memory object cache so the service must reload the
    # collection item and its relationships from the database.
    session.expunge_all()

    items, total = await list_collection_items(
        session,
        first_user_id,
        limit=25,
        offset=0,
    )

    assert total == 1
    assert len(items) == 1
    assert items[0].id == first_item_id
    assert items[0].user_id == first_user_id
    assert items[0].fragrance.name == "First Fragrance"
    assert items[0].rating is not None
    assert items[0].rating.dna_accuracy == 8


async def test_get_collection_item_requires_matching_owner(session: AsyncSession) -> None:
    """Return an item to its owner but hide it from every other user."""

    owner = User(google_subject="item-owner", email="owner@example.com")
    other_user = User(google_subject="different-user", email="other@example.com")
    fragrance = Fragrance(
        name="Owner's Fragrance",
        house=House(name="Single Item Test House"),
        data_source=DataSource.OFFICIAL_SITE,
    )
    item = UserCollectionItem(
        user=owner,
        fragrance=fragrance,
        ownership_status=OwnershipStatus.DECANT,
    )
    item.rating = ItemAttributeRating(
        dna_accuracy=9,
        longevity=LongevityBucket.EIGHT_PLUS_HOURS,
        projection=8,
    )
    session.add_all([item, other_user])
    await session.commit()
    item_id = item.id
    owner_id = owner.id
    other_user_id = other_user.id

    # Force the service to retrieve the item and its relationships from SQLite.
    session.expunge_all()

    owners_result = await get_collection_item(session, owner_id, item_id)
    other_users_result = await get_collection_item(session, other_user_id, item_id)

    assert owners_result is not None
    assert owners_result.id == item_id
    assert owners_result.fragrance.name == "Owner's Fragrance"
    assert owners_result.rating is not None
    assert owners_result.rating.dna_accuracy == 9
    assert other_users_result is None


async def test_create_collection_item_uses_existing_fragrance(session: AsyncSession) -> None:
    """A user can add an existing catalog fragrance as a bottle or decant."""

    user = User(google_subject="collection-creator", email="creator@example.com")
    fragrance = Fragrance(
        name="Catalog Fragrance",
        house=House(name="Creation Test House"),
        data_source=DataSource.OFFICIAL_SITE,
    )
    session.add_all([user, fragrance])
    await session.commit()

    item = await create_collection_item(
        session,
        user.id,
        fragrance.id,
        OwnershipStatus.FULL_BOTTLE,
    )

    assert item is not None
    assert item.user_id == user.id
    assert item.fragrance_id == fragrance.id
    assert item.ownership_status is OwnershipStatus.FULL_BOTTLE
    assert item.elo_score == 1000
    assert item.comparisons_count == 0
    assert item.fragrance.name == "Catalog Fragrance"


async def test_create_collection_item_rejects_unknown_fragrance(session: AsyncSession) -> None:
    """An ownership row cannot originate a fragrance outside the catalog."""

    user = User(google_subject="missing-fragrance-user", email="missing@example.com")
    session.add(user)
    await session.commit()

    item = await create_collection_item(
        session,
        user.id,
        uuid.uuid4(),
        OwnershipStatus.DECANT,
    )
    items, total = await list_collection_items(session, user.id, limit=25, offset=0)

    assert item is None
    assert items == []
    assert total == 0
