"""Add private, one-time Google OIDC login attempts.

Revision ID: 0003_add_oidc_login_attempts
Revises: 0002_add_auth_sessions
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_add_oidc_login_attempts"
down_revision: str | None = "0002_add_auth_sessions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create short-lived server-side storage for OIDC transaction secrets."""

    op.create_table(
        "oidc_login_attempts",
        sa.Column("state_hash", sa.String(length=64), nullable=False),
        sa.Column("nonce", sa.String(length=128), nullable=False),
        sa.Column("pkce_verifier", sa.String(length=128), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
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
        sa.PrimaryKeyConstraint("id", name=op.f("pk_oidc_login_attempts")),
    )
    op.create_index(
        op.f("ix_oidc_login_attempts_expires_at"),
        "oidc_login_attempts",
        ["expires_at"],
    )
    op.create_index(
        op.f("ix_oidc_login_attempts_state_hash"),
        "oidc_login_attempts",
        ["state_hash"],
        unique=True,
    )


def downgrade() -> None:
    """Remove stored OIDC login attempts."""

    op.drop_table("oidc_login_attempts")
