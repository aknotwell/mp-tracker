"""Collection-item request and response schemas."""

import uuid
from decimal import Decimal

from app.models.enums import OwnershipStatus
from app.schemas.catalog import FragranceResponse
from app.schemas.common import APIModel, ResourceSchema
from app.schemas.rating import ItemAttributeRatingResponse


class CollectionItemCreate(APIModel):
    """User-controlled fields for adding one independently ranked item."""

    fragrance_id: uuid.UUID
    ownership_status: OwnershipStatus


class CollectionItemUpdate(APIModel):
    """Editable ownership fields; server-owned ranking fields are excluded."""

    ownership_status: OwnershipStatus | None = None


class CollectionItemResponse(ResourceSchema):
    user_id: uuid.UUID
    fragrance_id: uuid.UUID
    ownership_status: OwnershipStatus
    elo_score: Decimal
    comparisons_count: int
    fragrance: FragranceResponse | None = None
    rating: ItemAttributeRatingResponse | None = None
