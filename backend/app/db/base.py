"""Database engine, session factory and declarative base."""

from __future__ import annotations

import datetime as dt
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


def utcnow() -> dt.datetime:
    """Timezone-aware UTC timestamp for ORM-side defaults.

    Using a Python callable (instead of the SQL ``now()`` expression) keeps the
    value available on the instance immediately after a flush, which avoids
    async lazy-loads ("MissingGreenlet") when serialising responses.
    """
    return dt.datetime.now(dt.UTC)


class Base(DeclarativeBase):
    """Declarative base shared by every ORM model."""


def _engine_kwargs() -> dict:
    kwargs: dict = {
        "echo": settings.DB_ECHO,
        "pool_pre_ping": True,
    }
    # Serverless (Vercel) works best with a short-lived pool. Neon also
    # recommends pgbouncer-friendly settings; asyncpg does not support the
    # `statement_cache_size` param via the URL, so we disable prepared
    # statement caching to stay compatible with transaction pooling.
    if settings.is_production:
        kwargs.update(
            pool_size=5,
            max_overflow=5,
            pool_recycle=300,
            connect_args={"statement_cache_size": 0, "prepared_statement_cache_size": 0},
        )
    return kwargs


engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs())

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a transactional session."""
    async with SessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
