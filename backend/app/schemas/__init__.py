"""Pydantic request and response schemas for the approved domain model."""

from app.schemas.auth import AccessTokenResponse
from app.schemas.catalog import (
    FragranceAdminCorrection,
    FragranceNoteResponse,
    FragranceResponse,
    HouseResponse,
    NoteResponse,
)
from app.schemas.collection import (
    CollectionItemCreate,
    CollectionItemResponse,
    CollectionItemUpdate,
)
from app.schemas.common import Page
from app.schemas.matchup import HeadToHeadMatchupResponse
from app.schemas.rating import ItemAttributeRatingResponse, ItemAttributeRatingUpsert
from app.schemas.user import UserResponse

__all__ = [
    "AccessTokenResponse",
    "CollectionItemCreate",
    "CollectionItemResponse",
    "CollectionItemUpdate",
    "FragranceAdminCorrection",
    "FragranceNoteResponse",
    "FragranceResponse",
    "HeadToHeadMatchupResponse",
    "HouseResponse",
    "ItemAttributeRatingResponse",
    "ItemAttributeRatingUpsert",
    "NoteResponse",
    "Page",
    "UserResponse",
]
