"""Shared Pydantic response and pagination schemas."""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class APIModel(BaseModel):
    """Base API schema that can serialize SQLAlchemy model attributes."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")


class ResourceSchema(APIModel):
    """Fields shared by persisted API resources."""

    id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class Page[ItemT](APIModel):
    """Offset-paginated API response."""

    items: list[ItemT]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
