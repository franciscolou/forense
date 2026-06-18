"""Database engine, session factory and the declarative base.

Uses SQLAlchemy 2.0 async API. A single async engine is created per process and
sessions are handed out through :func:`get_session`, which is wired into the
FastAPI dependency system so every request gets its own session that is closed
automatically when the request ends.
"""
from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields a transactional database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create tables from the ORM metadata.

    Convenient for local development / SQLite. In production this should be
    handled by Alembic migrations instead.
    """
    # Import models so they are registered on ``Base.metadata`` before create.
    from app import models  # noqa: F401

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
