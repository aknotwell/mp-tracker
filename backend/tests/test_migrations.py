"""Integration tests for the complete Alembic database lifecycle."""

import sqlite3
from pathlib import Path

from alembic import command
from alembic.config import Config

EXPECTED_APPLICATION_TABLES = {
    "auth_sessions",
    "oidc_login_attempts",
    "users",
    "houses",
    "fragrances",
    "notes",
    "fragrance_notes",
    "user_collection_items",
    "item_attribute_ratings",
    "head_to_head_matchups",
}


def alembic_config(database_path: Path) -> Config:
    """Build an Alembic configuration targeting an isolated test database."""

    backend_directory = Path(__file__).resolve().parents[1]
    config = Config(backend_directory / "alembic.ini")
    config.set_main_option("script_location", str(backend_directory / "migrations"))
    config.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{database_path.as_posix()}")
    return config


def sqlite_tables(database_path: Path) -> set[str]:
    """Return the tables currently present in a SQLite database."""

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row[0] for row in rows}


def test_upgrade_downgrade_and_reupgrade(tmp_path: Path) -> None:
    """A fresh clone can create, remove, and recreate the entire schema."""

    database_path = tmp_path / "migration_test.sqlite3"
    config = alembic_config(database_path)

    command.upgrade(config, "head")
    assert sqlite_tables(database_path) >= EXPECTED_APPLICATION_TABLES

    with sqlite3.connect(database_path) as connection:
        version = connection.execute("SELECT version_num FROM alembic_version").fetchone()
    assert version == ("0004_remove_collection_volumes",)

    # Model metadata and the migration history must describe the same schema.
    command.check(config)

    command.downgrade(config, "base")
    assert not EXPECTED_APPLICATION_TABLES & sqlite_tables(database_path)

    command.upgrade(config, "head")
    assert sqlite_tables(database_path) >= EXPECTED_APPLICATION_TABLES


def test_migrated_database_uses_google_identity_and_ownership_type(tmp_path: Path) -> None:
    """The final schema contains the approved identity and collection fields."""

    database_path = tmp_path / "constraint_test.sqlite3"
    command.upgrade(alembic_config(database_path), "head")

    with sqlite3.connect(database_path) as connection:
        users_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'users'"
        ).fetchone()
        collection_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'user_collection_items'"
        ).fetchone()

    assert users_sql is not None
    assert "google_subject" in users_sql[0]
    assert "password_hash" not in users_sql[0]
    assert collection_sql is not None
    assert "ownership_status" in collection_sql[0]
    assert "volume_ml_total" not in collection_sql[0]
    assert "volume_ml_remaining" not in collection_sql[0]
