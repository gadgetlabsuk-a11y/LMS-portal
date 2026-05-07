"""SQLAlchemy async database setup — supports SQLite (dev) and PostgreSQL (prod)."""

import logging
import os

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .models import Base

logger = logging.getLogger(__name__)

# Read DATABASE_URL from environment; fall back to SQLite for local dev.
DATABASE_URL: str = os.environ.get(
    "DATABASE_URL", "sqlite+aiosqlite:///data/lms.db"
)

_is_sqlite = DATABASE_URL.startswith("sqlite")

# Pool args are not supported by SQLite — only apply for real DBs.
_engine_kwargs: dict = {"echo": False}
if not _is_sqlite:
    _engine_kwargs.update(
        {
            "pool_size": 10,
            "max_overflow": 20,
            "pool_pre_ping": True,
            "pool_recycle": 3600,
        }
    )

engine = create_async_engine(DATABASE_URL, **_engine_kwargs)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def get_db() -> AsyncSession:
    """Return a new async session (caller is responsible for closing it)."""
    return AsyncSessionLocal()


async def init_db() -> None:
    """Create all tables from ORM metadata (no-op if they already exist)."""
    os.makedirs("data", exist_ok=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database initialised", extra={"database_url": DATABASE_URL})
