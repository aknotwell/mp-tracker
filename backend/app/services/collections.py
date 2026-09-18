import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalog import Fragrance, FragranceNote
from app.models.collection import UserCollectionItem
from app.models.enums import OwnershipStatus


async def list_collection_items(
    database: AsyncSession,
    user_id: uuid.UUID,
    *,
    limit: int,
    offset: int,
) -> tuple[list[UserCollectionItem], int]:
    """Return collection items owned by one user."""

    fragrance_options = (
        selectinload(UserCollectionItem.fragrance)
        .selectinload(Fragrance.fragrance_notes)
        .selectinload(FragranceNote.note)
    )
    rating_options = selectinload(UserCollectionItem.rating)
    page_query = (
        select(UserCollectionItem)
        .options(fragrance_options, rating_options)
        .where(UserCollectionItem.user_id == user_id)
        .order_by(UserCollectionItem.created_at.desc(),
                  UserCollectionItem.id.desc())
        .limit(limit)
        .offset(offset)
    )
    count_query = (
        select(func.count())
        .select_from(UserCollectionItem)
        .where(UserCollectionItem.user_id == user_id)
    )

    collection = list((await database.scalars(page_query)).all())
    total = int((await database.scalar(count_query)) or 0)

    return collection, total


async def get_collection_item(
    database: AsyncSession,
    user_id: uuid.UUID,
    item_id: uuid.UUID,
) -> UserCollectionItem | None:
    """Return one collection item only when it belongs to the given user."""

    fragrance_options = (
        selectinload(UserCollectionItem.fragrance)
        .selectinload(Fragrance.fragrance_notes)
        .selectinload(FragranceNote.note)
    )

    rating_options = selectinload(UserCollectionItem.rating)

    query = (
        select(UserCollectionItem)
        .options(fragrance_options, rating_options)
        .where(
            UserCollectionItem.id == item_id,
            UserCollectionItem.user_id == user_id,
        )
    )

    result = await database.scalars(query)
    return result.first()


async def create_collection_item(
    database: AsyncSession,
    user_id: uuid.UUID,
    fragrance_id: uuid.UUID,
    ownership_status: OwnershipStatus,
) -> UserCollectionItem | None:
    """Add an existing catalog fragrance to one user's collection.

    Returning ``None`` tells the API route that the requested catalog
    fragrance does not exist. The caller owns the transaction and decides when
    to commit or roll it back.
    """

    fragrance = await database.get(Fragrance, fragrance_id)
    if fragrance is None:
        return None

    item = UserCollectionItem(
        user_id=user_id,
        fragrance_id=fragrance.id,
        ownership_status=ownership_status,
    )
    database.add(item)

    # Flush sends the INSERT without committing it. This assigns the generated
    # item ID so we can retrieve the complete response-ready object below.
    await database.flush()
    return await get_collection_item(database, user_id, item.id)
