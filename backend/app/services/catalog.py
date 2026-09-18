"""Read-only database queries for the shared fragrance catalog."""

import uuid

from sqlalchemy import ColumnElement, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalog import Fragrance, FragranceNote, House, Note


def _name_search(
    model: type[House] | type[Fragrance] | type[Note],
    search: str | None,
) -> ColumnElement[bool] | None:
    """Build a case-insensitive name filter, ignoring an empty search value."""

    cleaned_search = search.strip() if search else ""
    if not cleaned_search:
        return None
    return model.name.ilike(f"%{cleaned_search}%")


async def list_houses(
    database: AsyncSession,
    *,
    search: str | None,
    limit: int,
    offset: int,
) -> tuple[list[House], int]:
    """Return one page of houses and the total matching row count."""

    name_filter = _name_search(House, search)
    page_query = select(House)
    count_query = select(func.count()).select_from(House)
    if name_filter is not None:
        page_query = page_query.where(name_filter)
        count_query = count_query.where(name_filter)

    page_query = page_query.order_by(func.lower(House.name), House.id).limit(limit).offset(offset)
    houses = list((await database.scalars(page_query)).all())
    total = int((await database.scalar(count_query)) or 0)
    return houses, total


async def get_house(database: AsyncSession, house_id: uuid.UUID) -> House | None:
    """Find a house by its public UUID."""

    return await database.get(House, house_id)


async def list_fragrances(
    database: AsyncSession,
    *,
    search: str | None,
    house_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[Fragrance], int]:
    """Return fragrances with their note pyramids already loaded."""

    filters = []
    name_filter = _name_search(Fragrance, search)
    if name_filter is not None:
        filters.append(name_filter)
    if house_id is not None:
        filters.append(Fragrance.house_id == house_id)

    # Eager loading prevents Pydantic from triggering asynchronous database work
    # while it turns each fragrance and its notes into JSON.
    note_options = selectinload(Fragrance.fragrance_notes).selectinload(FragranceNote.note)
    page_query = (
        select(Fragrance)
        .options(note_options)
        .where(*filters)
        .order_by(func.lower(Fragrance.name), Fragrance.id)
        .limit(limit)
        .offset(offset)
    )
    count_query = select(func.count()).select_from(Fragrance).where(*filters)

    fragrances = list((await database.scalars(page_query)).all())
    total = int((await database.scalar(count_query)) or 0)
    return fragrances, total


async def get_fragrance(
    database: AsyncSession,
    fragrance_id: uuid.UUID,
) -> Fragrance | None:
    """Find one fragrance and eagerly load its ordered note pyramid."""

    query = (
        select(Fragrance)
        .options(
            selectinload(Fragrance.fragrance_notes).selectinload(FragranceNote.note),
        )
        .where(Fragrance.id == fragrance_id)
    )
    result = await database.scalars(query)
    return result.first()


async def list_notes(
    database: AsyncSession,
    *,
    search: str | None,
    limit: int,
    offset: int,
) -> tuple[list[Note], int]:
    """Return one page of normalized fragrance notes."""

    name_filter = _name_search(Note, search)
    page_query = select(Note)
    count_query = select(func.count()).select_from(Note)
    if name_filter is not None:
        page_query = page_query.where(name_filter)
        count_query = count_query.where(name_filter)

    page_query = page_query.order_by(func.lower(Note.name), Note.id).limit(limit).offset(offset)
    notes = list((await database.scalars(page_query)).all())
    total = int((await database.scalar(count_query)) or 0)
    return notes, total
