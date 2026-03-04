"""Database configuration and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings
from app.core.database.models import Base

# Create async engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # Disabled for cleaner logs - enable only when debugging SQL
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    # pgbouncer requires statement_cache_size=0 to avoid prepared statement conflicts
    connect_args={"ssl": "require", "statement_cache_size": 0},
)

# Create session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Dependency to get database session."""
    async with AsyncSessionLocal() as session:
        yield session


async def init_db():
    """Create all tables (for development)."""
    async with engine.begin() as conn:
        # Enable pgvector extension
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # Create tables
        await conn.run_sync(Base.metadata.create_all)
