"""Authenticated, read-only routes for browsing the fragrance catalog."""

import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import CurrentUser, DatabaseSession
from app.schemas.catalog import FragranceResponse, HouseResponse, NoteResponse
from app.schemas.common import Page
from app.services import catalog as catalog_service

router = APIRouter(tags=["catalog"])

Limit = Annotated[int, Query(ge=1, le=100)]
Offset = Annotated[int, Query(ge=0)]
Search = Annotated[str | None, Query(max_length=200)]


@router.get("/houses", response_model=Page[HouseResponse])
async def houses(
    database: DatabaseSession,
    _current_user: CurrentUser,
    limit: Limit = 25,
    offset: Offset = 0,
    search: Search = None,
) -> Page[HouseResponse]:
    """List houses with optional name search and offset pagination."""

    items, total = await catalog_service.list_houses(
        database, search=search, limit=limit, offset=offset
    )
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/houses/{house_id}", response_model=HouseResponse)
async def house(
    house_id: uuid.UUID,
    database: DatabaseSession,
    _current_user: CurrentUser,
) -> HouseResponse:
    """Return a single house or a clear 404 response."""

    item = await catalog_service.get_house(database, house_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="House not found")
    return HouseResponse.model_validate(item)


@router.get("/fragrances", response_model=Page[FragranceResponse])
async def fragrances(
    database: DatabaseSession,
    _current_user: CurrentUser,
    limit: Limit = 25,
    offset: Offset = 0,
    search: Search = None,
    house_id: uuid.UUID | None = None,
) -> Page[FragranceResponse]:
    """List fragrances, optionally filtering by name and house."""

    items, total = await catalog_service.list_fragrances(
        database,
        search=search,
        house_id=house_id,
        limit=limit,
        offset=offset,
    )
    return Page(items=items, total=total, limit=limit, offset=offset)


@router.get("/fragrances/{fragrance_id}", response_model=FragranceResponse)
async def fragrance(
    fragrance_id: uuid.UUID,
    database: DatabaseSession,
    _current_user: CurrentUser,
) -> FragranceResponse:
    """Return a fragrance together with its ordered note pyramid."""

    item = await catalog_service.get_fragrance(database, fragrance_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Fragrance not found")
    return FragranceResponse.model_validate(item)


@router.get("/notes", response_model=Page[NoteResponse])
async def notes(
    database: DatabaseSession,
    _current_user: CurrentUser,
    limit: Limit = 25,
    offset: Offset = 0,
    search: Search = None,
) -> Page[NoteResponse]:
    """List normalized notes with optional name search and pagination."""

    items, total = await catalog_service.list_notes(
        database, search=search, limit=limit, offset=offset
    )
    return Page(items=items, total=total, limit=limit, offset=offset)
