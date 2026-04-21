"""Async database session management.

Uses SQLAlchemy 2.0's async API with asyncpg driver. One shared engine per
process; a new session per request (handed out by `get_session` in deps.py
in Phase B).
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import settings
from app.core.logging import get_logger

log = get_logger(__name__)


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


def _build_engine() -> AsyncEngine:
    return create_async_engine(
        settings.database_url,
        echo=settings.database_echo,
        pool_size=settings.database_pool_size,
        max_overflow=settings.database_max_overflow,
        pool_pre_ping=True,  # detect stale connections before use
        pool_recycle=1800,   # recycle every 30 min to avoid Supabase idle drops
    )


engine: AsyncEngine = _build_engine()

SessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Use for scripts and workers; API routes should use the `get_session` dep."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def check_database() -> bool:
    """Cheap liveness probe. Used by /readyz."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        log.error("db_health_check_failed", error=str(e))
        return False


async def dispose_engine() -> None:
    """Close all pool connections on shutdown."""
    await engine.dispose()
