"""Remove collection volume tracking.

Revision ID: 0004_remove_collection_volumes
Revises: 0003_add_oidc_login_attempts
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_remove_collection_volumes"
down_revision: str | None = "0003_add_oidc_login_attempts"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Keep only bottle/decant ownership and discard milliliter amounts."""

    # SQLite cannot drop constrained columns directly. Batch mode rebuilds the
    # table while preserving its rows, foreign keys, and unrelated indexes.
    with op.batch_alter_table("user_collection_items") as batch_op:
        batch_op.drop_constraint(
            "remaining_volume_nonnegative",
            type_="check",
        )
        batch_op.drop_constraint(
            "remaining_volume_not_above_total",
            type_="check",
        )
        batch_op.drop_constraint(
            "total_volume_positive",
            type_="check",
        )
        batch_op.drop_column("volume_ml_remaining")
        batch_op.drop_column("volume_ml_total")


def downgrade() -> None:
    """Restore volume columns with neutral values when rolling back."""

    # Removed measurements cannot be recovered. Existing rows receive 1 ml so
    # the restored historical constraints remain valid after a downgrade.
    with op.batch_alter_table("user_collection_items") as batch_op:
        batch_op.add_column(
            sa.Column("volume_ml_total", sa.Numeric(8, 2), server_default="1.00", nullable=False)
        )
        batch_op.add_column(
            sa.Column(
                "volume_ml_remaining",
                sa.Numeric(8, 2),
                server_default="1.00",
                nullable=False,
            )
        )
        batch_op.create_check_constraint(
            "total_volume_positive",
            "volume_ml_total > 0",
        )
        batch_op.create_check_constraint(
            "remaining_volume_nonnegative",
            "volume_ml_remaining >= 0",
        )
        batch_op.create_check_constraint(
            "remaining_volume_not_above_total",
            "volume_ml_remaining <= volume_ml_total",
        )
