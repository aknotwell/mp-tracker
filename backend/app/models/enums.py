"""String enums persisted by the database and exposed by the API."""

from enum import StrEnum

from sqlalchemy import Enum


def database_enum(enum_class: type[StrEnum], *, name: str) -> Enum:
    """Build a portable constrained string enum that stores public enum values.

    SQLAlchemy stores enum member names unless told otherwise. The API contract uses
    values such as ``0-2h``, so the database must persist those values verbatim.
    """

    return Enum(
        enum_class,
        name=name,
        native_enum=False,
        create_constraint=True,
        validate_strings=True,
        values_callable=lambda members: [member.value for member in members],
    )


class OwnershipStatus(StrEnum):
    FULL_BOTTLE = "full_bottle"
    DECANT = "decant"


class LongevityBucket(StrEnum):
    ZERO_TO_TWO_HOURS = "0-2h"
    TWO_TO_FOUR_HOURS = "2-4h"
    FOUR_TO_SIX_HOURS = "4-6h"
    SIX_TO_EIGHT_HOURS = "6-8h"
    EIGHT_PLUS_HOURS = "8h+"


class DataSource(StrEnum):
    OFFICIAL_SITE = "official_site"
    MANUAL = "manual"


class NotePyramidLevel(StrEnum):
    TOP = "top"
    MIDDLE = "middle"
    BASE = "base"
