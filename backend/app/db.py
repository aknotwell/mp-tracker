"""Async SQLAlchemy engine and session factory.

Milestone 2 defines the database metadata but does not create tables at application
startup. Alembic migrations in Milestone 3 will own schema creation and upgrades.
"""

from collections.abc import AsyncIterator
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.debug,
)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine.sync_engine, "connect")
    def enable_sqlite_foreign_keys(dbapi_connection: Any, _connection_record: Any) -> None:
        """SQLite does not enforce foreign keys unless each connection enables them."""

        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


async def get_db_session() -> AsyncIterator[AsyncSession]:
    """Yield one transaction-capable session for a request or background task."""

    async with SessionFactory() as session:
        yield session
