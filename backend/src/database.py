"""
src/database.py
===============
Async SQLAlchemy 2.0 engine, session factory, and Base declarative class.
Supports both SQLite (development) and PostgreSQL (production).
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from src.config import settings

logger = logging.getLogger(__name__)

# ── Engine creation with SQLite / PostgreSQL detection ────────────────────────
_engine_kwargs = {
    "echo": settings.debug and settings.environment == "development",
}

if settings.is_sqlite:
    # SQLite needs special handling for async + in-memory/file
    _engine_kwargs.update({
        "connect_args": {"check_same_thread": False},
        "poolclass": StaticPool,
    })
else:
    _engine_kwargs.update({
        "pool_size": 20,
        "max_overflow": 10,
        "pool_pre_ping": True,
    })

engine = create_async_engine(settings.db_url, **_engine_kwargs)

# ── Session factory ───────────────────────────────────────────────────────────
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


# ── Declarative base ──────────────────────────────────────────────────────────
class Base(DeclarativeBase):
    """Shared metadata base for all ORM models."""
    pass


# ── Dependency injection helper ───────────────────────────────────────────────
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields an async DB session.
    Rolls back automatically on exception; commits are the caller's responsibility.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """Context manager variant for use outside of FastAPI dependency injection."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    """Create all tables. Called once at application startup in development."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized (engine=%s).", "SQLite" if settings.is_sqlite else "PostgreSQL")


async def close_db() -> None:
    """Dispose of the connection pool. Called on application shutdown."""
    await engine.dispose()
    logger.info("Database connection pool closed.")
