"""Catalog response and restricted admin-correction schemas."""

import uuid

from pydantic import Field

from app.models.enums import DataSource, NotePyramidLevel
from app.schemas.common import APIModel, ResourceSchema


class HouseResponse(ResourceSchema):
    name: str
    inspired_by_house_id: uuid.UUID | None


class NoteResponse(ResourceSchema):
    name: str


class FragranceNoteResponse(ResourceSchema):
    note: NoteResponse
    pyramid_level: NotePyramidLevel
    sort_order: int


class FragranceResponse(ResourceSchema):
    house_id: uuid.UUID
    name: str
    concentration: str | None
    gender: str | None
    clone_of_fragrance_id: uuid.UUID | None
    data_source: DataSource
    source_url: str | None
    needs_review: bool
    fragrance_notes: list[FragranceNoteResponse] = Field(default_factory=list)


class FragranceAdminCorrection(APIModel):
    """Fields an admin may correct on an existing scraper-created row.

    There is deliberately no public ``FragranceCreate`` schema. Provenance and
    scraper identity fields are also excluded so this cannot become a creation path.
    """

    house_id: uuid.UUID | None = None
    name: str | None = Field(default=None, min_length=1, max_length=250)
    concentration: str | None = Field(default=None, max_length=80)
    gender: str | None = Field(default=None, max_length=80)
    clone_of_fragrance_id: uuid.UUID | None = None
    needs_review: bool | None = None
