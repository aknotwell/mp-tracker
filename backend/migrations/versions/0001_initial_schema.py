"""Create the initial fragrance tracker schema.

Revision ID: 0001_initial_schema
Revises: None
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> tuple[sa.Column, sa.Column]:
    """Return the shared creation and modification timestamp columns."""

    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )


def upgrade() -> None:
    """Create all application tables, constraints, and indexes."""

    op.create_table(
        "users",
        sa.Column("google_subject", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("is_admin", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)
    op.create_index(
        op.f("ix_users_google_subject"),
        "users",
        ["google_subject"],
        unique=True,
    )

    op.create_table(
        "houses",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("inspired_by_house_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["inspired_by_house_id"],
            ["houses.id"],
            name=op.f("fk_houses_inspired_by_house_id_houses"),
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_houses")),
    )
    op.create_index(
        op.f("ix_houses_inspired_by_house_id"),
        "houses",
        ["inspired_by_house_id"],
        unique=False,
    )
    op.create_index(op.f("ix_houses_name"), "houses", ["name"], unique=True)

    op.create_table(
        "notes",
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_notes")),
    )
    op.create_index(op.f("ix_notes_name"), "notes", ["name"], unique=True)

    op.create_table(
        "fragrances",
        sa.Column("house_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=250), nullable=False),
        sa.Column("concentration", sa.String(length=80), nullable=True),
        sa.Column("gender", sa.String(length=80), nullable=True),
        sa.Column("clone_of_fragrance_id", sa.Uuid(), nullable=True),
        sa.Column(
            "data_source",
            sa.Enum(
                "official_site",
                "manual",
                name="data_source",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("source_external_id", sa.String(length=255), nullable=True),
        sa.Column("source_url", sa.Text(), nullable=True),
        sa.Column("needs_review", sa.Boolean(), server_default=sa.text("0"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["clone_of_fragrance_id"],
            ["fragrances.id"],
            name=op.f("fk_fragrances_clone_of_fragrance_id_fragrances"),
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["house_id"],
            ["houses.id"],
            name=op.f("fk_fragrances_house_id_houses"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fragrances")),
    )
    op.create_index(
        op.f("ix_fragrances_clone_of_fragrance_id"),
        "fragrances",
        ["clone_of_fragrance_id"],
        unique=False,
    )
    op.create_index(op.f("ix_fragrances_house_id"), "fragrances", ["house_id"], unique=False)
    op.create_index("ix_fragrances_house_name", "fragrances", ["house_id", "name"])
    op.create_index(
        op.f("ix_fragrances_needs_review"),
        "fragrances",
        ["needs_review"],
        unique=False,
    )
    op.create_index(
        "ix_fragrances_review_created",
        "fragrances",
        ["needs_review", "created_at"],
    )
    op.create_index(
        "uq_fragrances_source_external_id",
        "fragrances",
        ["data_source", "source_external_id"],
        unique=True,
    )

    op.create_table(
        "fragrance_notes",
        sa.Column("fragrance_id", sa.Uuid(), nullable=False),
        sa.Column("note_id", sa.Uuid(), nullable=False),
        sa.Column(
            "pyramid_level",
            sa.Enum(
                "top",
                "middle",
                "base",
                name="note_pyramid_level",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "sort_order >= 0",
            name=op.f("ck_fragrance_notes_sort_order_nonnegative"),
        ),
        sa.ForeignKeyConstraint(
            ["fragrance_id"],
            ["fragrances.id"],
            name=op.f("fk_fragrance_notes_fragrance_id_fragrances"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["note_id"],
            ["notes.id"],
            name=op.f("fk_fragrance_notes_note_id_notes"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_fragrance_notes")),
    )
    op.create_index(
        op.f("ix_fragrance_notes_note_id"),
        "fragrance_notes",
        ["note_id"],
        unique=False,
    )
    op.create_index(
        "ix_fragrance_notes_pyramid",
        "fragrance_notes",
        ["fragrance_id", "pyramid_level", "sort_order"],
    )
    op.create_index(
        "uq_fragrance_notes_fragrance_note_level",
        "fragrance_notes",
        ["fragrance_id", "note_id", "pyramid_level"],
        unique=True,
    )

    op.create_table(
        "user_collection_items",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("fragrance_id", sa.Uuid(), nullable=False),
        sa.Column(
            "ownership_status",
            sa.Enum(
                "full_bottle",
                "decant",
                name="ownership_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("volume_ml_total", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column("volume_ml_remaining", sa.Numeric(precision=8, scale=2), nullable=False),
        sa.Column(
            "elo_score",
            sa.Numeric(precision=10, scale=4),
            server_default=sa.text("1000.0000"),
            nullable=False,
        ),
        sa.Column(
            "comparisons_count",
            sa.Integer(),
            server_default=sa.text("0"),
            nullable=False,
        ),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "comparisons_count >= 0",
            name=op.f("ck_user_collection_items_comparisons_count_nonnegative"),
        ),
        sa.CheckConstraint(
            "volume_ml_remaining >= 0",
            name=op.f("ck_user_collection_items_remaining_volume_nonnegative"),
        ),
        sa.CheckConstraint(
            "volume_ml_remaining <= volume_ml_total",
            name=op.f("ck_user_collection_items_remaining_volume_not_above_total"),
        ),
        sa.CheckConstraint(
            "volume_ml_total > 0",
            name=op.f("ck_user_collection_items_total_volume_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["fragrance_id"],
            ["fragrances.id"],
            name=op.f("fk_user_collection_items_fragrance_id_fragrances"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_user_collection_items_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_collection_items")),
    )
    op.create_index(
        op.f("ix_user_collection_items_fragrance_id"),
        "user_collection_items",
        ["fragrance_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_user_collection_items_user_id"),
        "user_collection_items",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_collection_user_created",
        "user_collection_items",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_collection_user_elo",
        "user_collection_items",
        ["user_id", "elo_score"],
    )
    op.create_index(
        "ix_collection_user_fragrance",
        "user_collection_items",
        ["user_id", "fragrance_id"],
    )

    op.create_table(
        "item_attribute_ratings",
        sa.Column("collection_item_id", sa.Uuid(), nullable=False),
        sa.Column("dna_accuracy", sa.Integer(), nullable=False),
        sa.Column(
            "longevity",
            sa.Enum(
                "0-2h",
                "2-4h",
                "4-6h",
                "6-8h",
                "8h+",
                name="longevity_bucket",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("projection", sa.Integer(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "dna_accuracy BETWEEN 1 AND 10",
            name=op.f("ck_item_attribute_ratings_dna_accuracy_range"),
        ),
        sa.CheckConstraint(
            "projection BETWEEN 1 AND 10",
            name=op.f("ck_item_attribute_ratings_projection_range"),
        ),
        sa.ForeignKeyConstraint(
            ["collection_item_id"],
            ["user_collection_items.id"],
            name=op.f("fk_item_attribute_ratings_collection_item_id_user_collection_items"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_item_attribute_ratings")),
    )
    op.create_index(
        op.f("ix_item_attribute_ratings_collection_item_id"),
        "item_attribute_ratings",
        ["collection_item_id"],
        unique=True,
    )
    op.create_index("ix_ratings_dna_accuracy", "item_attribute_ratings", ["dna_accuracy"])
    op.create_index("ix_ratings_longevity", "item_attribute_ratings", ["longevity"])

    op.create_table(
        "head_to_head_matchups",
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("left_item_id", sa.Uuid(), nullable=False),
        sa.Column("right_item_id", sa.Uuid(), nullable=False),
        sa.Column("winner_item_id", sa.Uuid(), nullable=False),
        sa.Column("left_score_before", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("right_score_before", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("left_score_after", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("right_score_after", sa.Numeric(precision=10, scale=4), nullable=False),
        sa.Column("k_factor", sa.Integer(), nullable=False),
        sa.Column("algorithm_version", sa.String(length=40), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "left_item_id <> right_item_id",
            name=op.f("ck_head_to_head_matchups_different_items"),
        ),
        sa.CheckConstraint(
            "k_factor > 0",
            name=op.f("ck_head_to_head_matchups_k_factor_positive"),
        ),
        sa.CheckConstraint(
            "winner_item_id = left_item_id OR winner_item_id = right_item_id",
            name=op.f("ck_head_to_head_matchups_winner_is_participant"),
        ),
        sa.ForeignKeyConstraint(
            ["left_item_id"],
            ["user_collection_items.id"],
            name=op.f("fk_head_to_head_matchups_left_item_id_user_collection_items"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["right_item_id"],
            ["user_collection_items.id"],
            name=op.f("fk_head_to_head_matchups_right_item_id_user_collection_items"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_head_to_head_matchups_user_id_users"),
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["winner_item_id"],
            ["user_collection_items.id"],
            name=op.f("fk_head_to_head_matchups_winner_item_id_user_collection_items"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_head_to_head_matchups")),
    )
    op.create_index(
        op.f("ix_head_to_head_matchups_left_item_id"),
        "head_to_head_matchups",
        ["left_item_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_head_to_head_matchups_right_item_id"),
        "head_to_head_matchups",
        ["right_item_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_head_to_head_matchups_user_id"),
        "head_to_head_matchups",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_head_to_head_matchups_winner_item_id"),
        "head_to_head_matchups",
        ["winner_item_id"],
        unique=False,
    )
    op.create_index(
        "ix_matchups_pair_created",
        "head_to_head_matchups",
        ["left_item_id", "right_item_id", "created_at"],
    )
    op.create_index(
        "ix_matchups_user_created",
        "head_to_head_matchups",
        ["user_id", "created_at"],
    )


def downgrade() -> None:
    """Remove all application tables in reverse dependency order."""

    op.drop_table("head_to_head_matchups")
    op.drop_table("item_attribute_ratings")
    op.drop_table("user_collection_items")
    op.drop_table("fragrance_notes")
    op.drop_table("fragrances")
    op.drop_table("notes")
    op.drop_table("houses")
    op.drop_table("users")
