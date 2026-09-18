"""Read model for immutable Overall Favorites comparison records."""

import uuid
from decimal import Decimal

from app.schemas.common import ResourceSchema


class HeadToHeadMatchupResponse(ResourceSchema):
    user_id: uuid.UUID
    left_item_id: uuid.UUID
    right_item_id: uuid.UUID
    winner_item_id: uuid.UUID
    left_score_before: Decimal
    right_score_before: Decimal
    left_score_after: Decimal
    right_score_after: Decimal
    k_factor: int
    algorithm_version: str
