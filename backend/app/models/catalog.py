"""Shared fragrance catalog models populated by automated imports."""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, CheckConstraint, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.enums import DataSource, NotePyramidLevel, database_enum

if TYPE_CHECKING:
    from app.models.collection import UserCollectionItem


class House(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A fragrance house, optionally inspired by another house."""

    __tablename__ = "houses"

    name: Mapped[str] = mapped_column(String(200), unique=True, index=True, nullable=False)
    inspired_by_house_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("houses.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    inspired_by_house: Mapped[House | None] = relationship(
        remote_side="House.id",
        back_populates="inspired_houses",
    )
    inspired_houses: Mapped[list[House]] = relationship(back_populates="inspired_by_house")
    fragrances: Mapped[list[Fragrance]] = relationship(back_populates="house")


class Fragrance(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A scraper-created fragrance catalog entry."""

    __tablename__ = "fragrances"
    __table_args__ = (
        Index("ix_fragrances_house_name", "house_id", "name"),
        Index("ix_fragrances_review_created", "needs_review", "created_at"),
        Index(
            "uq_fragrances_source_external_id",
            "data_source",
            "source_external_id",
            unique=True,
        ),
    )

    house_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("houses.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    # These remain free text until the product's exact allowed vocabularies are approved.
    concentration: Mapped[str | None] = mapped_column(String(80), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(80), nullable=True)
    clone_of_fragrance_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("fragrances.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    data_source: Mapped[DataSource] = mapped_column(
        database_enum(DataSource, name="data_source"),
        nullable=False,
    )
    source_external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    needs_review: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="0",
        index=True,
    )

    house: Mapped[House] = relationship(back_populates="fragrances")
    clone_of_fragrance: Mapped[Fragrance | None] = relationship(
        remote_side="Fragrance.id",
        foreign_keys=[clone_of_fragrance_id],
        back_populates="clones",
    )
    clones: Mapped[list[Fragrance]] = relationship(
        foreign_keys=[clone_of_fragrance_id],
        back_populates="clone_of_fragrance",
    )
    fragrance_notes: Mapped[list[FragranceNote]] = relationship(
        back_populates="fragrance",
        cascade="all, delete-orphan",
        order_by="FragranceNote.sort_order",
    )
    collection_items: Mapped[list[UserCollectionItem]] = relationship(back_populates="fragrance")


class Note(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A normalized fragrance note such as bergamot or sandalwood."""

    __tablename__ = "notes"

    name: Mapped[str] = mapped_column(String(150), unique=True, index=True, nullable=False)
    fragrance_notes: Mapped[list[FragranceNote]] = relationship(
        back_populates="note",
        cascade="all, delete-orphan",
    )


class FragranceNote(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Place a note at a particular level and order in a fragrance pyramid."""

    __tablename__ = "fragrance_notes"
    __table_args__ = (
        CheckConstraint("sort_order >= 0", name="sort_order_nonnegative"),
        Index(
            "uq_fragrance_notes_fragrance_note_level",
            "fragrance_id",
            "note_id",
            "pyramid_level",
            unique=True,
        ),
        Index("ix_fragrance_notes_pyramid", "fragrance_id", "pyramid_level", "sort_order"),
    )

    fragrance_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fragrances.id", ondelete="CASCADE"),
        nullable=False,
    )
    note_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("notes.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    pyramid_level: Mapped[NotePyramidLevel] = mapped_column(
        database_enum(NotePyramidLevel, name="note_pyramid_level"),
        nullable=False,
    )
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0, server_default="0")

    fragrance: Mapped[Fragrance] = relationship(back_populates="fragrance_notes")
    note: Mapped[Note] = relationship(back_populates="fragrance_notes")
