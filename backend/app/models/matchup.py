"""Immutable audit records for Overall Favorites Elo comparisons."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Numeric, String, event
from sqlalchemy.orm import Mapped, Mapper, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.collection import UserCollectionItem
    from app.models.user import User


class HeadToHeadMatchup(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A scored comparison and the values needed to audit or replay it."""

    __tablename__ = "head_to_head_matchups"
    __table_args__ = (
        CheckConstraint("left_item_id <> right_item_id", name="different_items"),
        CheckConstraint(
            "winner_item_id = left_item_id OR winner_item_id = right_item_id",
            name="winner_is_participant",
        ),
        CheckConstraint("k_factor > 0", name="k_factor_positive"),
        Index("ix_matchups_user_created", "user_id", "created_at"),
        Index("ix_matchups_pair_created", "left_item_id", "right_item_id", "created_at"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    left_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_collection_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    right_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_collection_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    winner_item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_collection_items.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    left_score_before: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    right_score_before: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    left_score_after: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    right_score_after: Mapped[Decimal] = mapped_column(Numeric(10, 4), nullable=False)
    k_factor: Mapped[int] = mapped_column(Integer, nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(40), nullable=False)

    user: Mapped[User] = relationship(back_populates="matchups")
    left_item: Mapped[UserCollectionItem] = relationship(
        foreign_keys=[left_item_id],
        back_populates="matchups_as_left",
    )
    right_item: Mapped[UserCollectionItem] = relationship(
        foreign_keys=[right_item_id],
        back_populates="matchups_as_right",
    )
    winner_item: Mapped[UserCollectionItem] = relationship(
        foreign_keys=[winner_item_id],
        back_populates="matchup_wins",
    )


def _reject_matchup_mutation(
    _mapper: Mapper[HeadToHeadMatchup],
    _connection: object,
    target: HeadToHeadMatchup,
) -> None:
    """Protect the Elo audit log from ORM updates and deletes."""

    raise ValueError(f"HeadToHeadMatchup {target.id} is immutable")


event.listen(HeadToHeadMatchup, "before_update", _reject_matchup_mutation)
event.listen(HeadToHeadMatchup, "before_delete", _reject_matchup_mutation)
