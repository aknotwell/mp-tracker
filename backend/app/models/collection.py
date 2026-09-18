"""User-owned collection items and their three approved attribute ratings."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import LongevityBucket, OwnershipStatus, database_enum

if TYPE_CHECKING:
    from app.models.catalog import Fragrance
    from app.models.matchup import HeadToHeadMatchup
    from app.models.user import User


class UserCollectionItem(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One independently ranked bottle or decant owned by a user."""

    __tablename__ = "user_collection_items"
    __table_args__ = (
        CheckConstraint("volume_ml_total > 0", name="total_volume_positive"),
        CheckConstraint("volume_ml_remaining >= 0", name="remaining_volume_nonnegative"),
        CheckConstraint(
            "volume_ml_remaining <= volume_ml_total",
            name="remaining_volume_not_above_total",
        ),
        CheckConstraint("comparisons_count >= 0", name="comparisons_count_nonnegative"),
        Index("ix_collection_user_created", "user_id", "created_at"),
        Index("ix_collection_user_elo", "user_id", "elo_score"),
        Index("ix_collection_user_fragrance", "user_id", "fragrance_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    fragrance_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fragrances.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    ownership_status: Mapped[OwnershipStatus] = mapped_column(
        database_enum(OwnershipStatus, name="ownership_status"),
        nullable=False,
    )
    volume_ml_total: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    volume_ml_remaining: Mapped[Decimal] = mapped_column(Numeric(8, 2), nullable=False)
    elo_score: Mapped[Decimal] = mapped_column(
        Numeric(10, 4),
        nullable=False,
        default=Decimal("1000.0000"),
        server_default="1000.0000",
    )
    comparisons_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        server_default="0",
    )

    user: Mapped[User] = relationship(back_populates="collection_items")
    fragrance: Mapped[Fragrance] = relationship(back_populates="collection_items")
    rating: Mapped[ItemAttributeRating | None] = relationship(
        back_populates="collection_item",
        cascade="all, delete-orphan",
        single_parent=True,
        uselist=False,
    )
    matchups_as_left: Mapped[list[HeadToHeadMatchup]] = relationship(
        foreign_keys="HeadToHeadMatchup.left_item_id",
        back_populates="left_item",
        passive_deletes=True,
    )
    matchups_as_right: Mapped[list[HeadToHeadMatchup]] = relationship(
        foreign_keys="HeadToHeadMatchup.right_item_id",
        back_populates="right_item",
        passive_deletes=True,
    )
    matchup_wins: Mapped[list[HeadToHeadMatchup]] = relationship(
        foreign_keys="HeadToHeadMatchup.winner_item_id",
        back_populates="winner_item",
        passive_deletes=True,
    )


class ItemAttributeRating(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """The complete three-attribute rating for one collection item."""

    __tablename__ = "item_attribute_ratings"
    __table_args__ = (
        CheckConstraint("dna_accuracy BETWEEN 1 AND 10", name="dna_accuracy_range"),
        CheckConstraint("projection BETWEEN 1 AND 10", name="projection_range"),
        Index("ix_ratings_dna_accuracy", "dna_accuracy"),
        Index("ix_ratings_longevity", "longevity"),
    )

    collection_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_collection_items.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    dna_accuracy: Mapped[int] = mapped_column(Integer, nullable=False)
    longevity: Mapped[LongevityBucket] = mapped_column(
        database_enum(LongevityBucket, name="longevity_bucket"),
        nullable=False,
    )
    projection: Mapped[int] = mapped_column(Integer, nullable=False)

    collection_item: Mapped[UserCollectionItem] = relationship(back_populates="rating")
