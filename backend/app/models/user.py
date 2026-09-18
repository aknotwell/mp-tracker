"""User account model."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.auth import AuthSession
    from app.models.collection import UserCollectionItem
    from app.models.matchup import HeadToHeadMatchup


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A Google-authenticated owner of a private fragrance collection.

    Google's stable OpenID Connect ``sub`` claim is the account identity. Email is
    retained for display and administration, but authorization must never identify
    an account by email because a user's address can change.
    """

    __tablename__ = "users"

    google_subject: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    email: Mapped[str] = mapped_column(String(320), index=True, nullable=False)
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
    )

    collection_items: Mapped[list[UserCollectionItem]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    matchups: Mapped[list[HeadToHeadMatchup]] = relationship(
        back_populates="user",
        passive_deletes=True,
    )
    auth_sessions: Mapped[list[AuthSession]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
