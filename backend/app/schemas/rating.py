"""Schemas for the product's exact three attribute ratings."""

import uuid

from pydantic import Field

from app.models.enums import LongevityBucket
from app.schemas.common import APIModel, ResourceSchema


class ItemAttributeRatingUpsert(APIModel):
    """Create or replace a complete rating; partial ratings are not supported."""

    dna_accuracy: int = Field(ge=1, le=10)
    longevity: LongevityBucket
    projection: int = Field(ge=1, le=10)


class ItemAttributeRatingResponse(ResourceSchema):
    collection_item_id: uuid.UUID
    dna_accuracy: int
    longevity: LongevityBucket
    projection: int
