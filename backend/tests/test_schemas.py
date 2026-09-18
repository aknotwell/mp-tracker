"""Pydantic request validation tests for protected and constrained fields."""

import uuid
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.models.enums import LongevityBucket, OwnershipStatus
from app.schemas.collection import CollectionItemCreate
from app.schemas.rating import ItemAttributeRatingUpsert


def test_collection_create_needs_only_fragrance_and_ownership_type() -> None:
    request = CollectionItemCreate(
        fragrance_id=uuid.uuid4(),
        ownership_status=OwnershipStatus.DECANT,
    )

    assert request.ownership_status is OwnershipStatus.DECANT


def test_collection_create_rejects_server_owned_elo() -> None:
    with pytest.raises(ValidationError):
        CollectionItemCreate(
            fragrance_id=uuid.uuid4(),
            ownership_status=OwnershipStatus.FULL_BOTTLE,
            elo_score=Decimal("9000"),
        )


def test_rating_requires_exactly_the_three_approved_attributes() -> None:
    rating = ItemAttributeRatingUpsert(
        dna_accuracy=9,
        longevity=LongevityBucket.EIGHT_PLUS_HOURS,
        projection=8,
    )

    assert rating.model_dump() == {
        "dna_accuracy": 9,
        "longevity": LongevityBucket.EIGHT_PLUS_HOURS,
        "projection": 8,
    }

    with pytest.raises(ValidationError):
        ItemAttributeRatingUpsert(
            dna_accuracy=9,
            longevity=LongevityBucket.EIGHT_PLUS_HOURS,
            projection=8,
            value_rating=10,
        )
