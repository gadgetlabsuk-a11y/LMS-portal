"""Alembic migration environment — async engine, reads DATABASE_URL from env."""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Load .env if present (dev convenience)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Alembic Config object — gives access to values in alembic.ini
config = context.config

# Set sqlalchemy.url from environment (overrides alembic.ini placeholder)
database_url = os.environ.get("DATABASE_URL", "sqlite+aiosqlite:///data/lms.db")
config.set_main_option("sqlalchemy.url", database_url)

# Set up logging from alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import Base so Alembic knows about all models for autogenerate support
from app.models import Base  # noqa: E402

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emits SQL without a DB connection)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Create async engine and run migrations."""
    is_sqlite = database_url.startswith("sqlite")
    pool_class = pool.StaticPool if is_sqlite else pool.NullPool

    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool_class,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (with a live DB connection)."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
