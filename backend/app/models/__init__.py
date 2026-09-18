"""Import every model so SQLAlchemy and Alembic can discover full metadata."""

from app.models.auth import AuthSession
from app.models.base import Base
from app.models.catalog import Fragrance, FragranceNote, House, Note
from app.models.collection import ItemAttributeRating, UserCollectionItem
from app.models.enums import DataSource, LongevityBucket, NotePyramidLevel, OwnershipStatus
from app.models.matchup import HeadToHeadMatchup
from app.models.oidc import OIDCLoginAttempt
from app.models.user import User

__all__ = [
    "AuthSession",
    "Base",
    "DataSource",
    "Fragrance",
    "FragranceNote",
    "HeadToHeadMatchup",
    "House",
    "ItemAttributeRating",
    "LongevityBucket",
    "Note",
    "NotePyramidLevel",
    "OIDCLoginAttempt",
    "OwnershipStatus",
    "User",
    "UserCollectionItem",
]
