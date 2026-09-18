"""Collection-item request and response schemas."""

import uuid
from decimal import Decimal
from typing import Annotated

from pydantic import Field, model_validator

from app.models.enums import OwnershipStatus
from app.schemas.catalog import FragranceResponse
from app.schemas.common import APIModel, ResourceSchema
from app.schemas.rating import ItemAttributeRatingResponse

PositiveVolume = Annotated[Decimal, Field(gt=0, max_digits=8, decimal_places=2)]
RemainingVolume = Annotated[Decimal, Field(ge=0, max_digits=8, decimal_places=2)]


class CollectionItemCreate(APIModel):
    """User-controlled fields for adding one independently ranked item."""

    fragrance_id: uuid.UUID
    ownership_status: OwnershipStatus
    volume_ml_total: PositiveVolume
    volume_ml_remaining: RemainingVolume

    @model_validator(mode="after")
    def remaining_does_not_exceed_total(self) -> "CollectionItemCreate":
        if self.volume_ml_remaining > self.volume_ml_total:
            raise ValueError("volume_ml_remaining cannot exceed volume_ml_total")
        return self


class CollectionItemUpdate(APIModel):
    """Editable ownership fields; server-owned ranking fields are excluded."""

    ownership_status: OwnershipStatus | None = None
    volume_ml_total: PositiveVolume | None = None
    volume_ml_remaining: RemainingVolume | None = None

    @model_validator(mode="after")
    def supplied_volumes_are_consistent(self) -> "CollectionItemUpdate":
        if (
            self.volume_ml_total is not None
            and self.volume_ml_remaining is not None
            and self.volume_ml_remaining > self.volume_ml_total
        ):
            raise ValueError("volume_ml_remaining cannot exceed volume_ml_total")
        return self


class CollectionItemResponse(ResourceSchema):
    user_id: uuid.UUID
    fragrance_id: uuid.UUID
    ownership_status: OwnershipStatus
    volume_ml_total: Decimal
    volume_ml_remaining: Decimal
    elo_score: Decimal
    comparisons_count: int
    fragrance: FragranceResponse | None = None
    rating: ItemAttributeRatingResponse | None = None
