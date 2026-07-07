"""
Alembic migration environment — async configuration using asyncpg.

Why async Alembic (no psycopg2):
  The previous version used engine_from_config() with a psycopg2-based
  SYNC_DATABASE_URL, requiring a second PostgreSQL driver (psycopg2-binary)
  solely for Alembic. This created dependency bloat and a maintenance surface.

  SQLAlchemy 2.0+ supports async Alembic via connection.run_sync(): a sync
  function (do_run_migrations) is passed to an async connection and executed
  inside a thread-safe sync context. asyncpg serves as the SINGLE PostgreSQL
  driver for both the application runtime and migrations.

Offline vs. online mode:
  - offline: Alembic generates SQL without a live connection. The asyncpg URL
    is used with '+asyncpg' stripped so SQLAlchemy resolves the PostgreSQL
    dialect without importing the asyncpg DBAPI module (no connection is made).
  - online: asyncio.run() drives the async migration runner. Safe because
    Alembic's CLI always starts in a fresh thread with no running event loop.

Startup sequence (production):
  Migrations must complete before the API server starts accepting traffic.
  Options:
    1. docker compose exec api alembic upgrade head   (manual, recommended)
    2. Set RUN_MIGRATIONS=true in the container environment — the entrypoint
       script will run 'alembic upgrade head' before starting uvicorn.
    3. Run a dedicated init-container / Job in Kubernetes that runs migrations
       before the Deployment rolls out.

PostGIS:
  Extensions are enabled in the first migration
  (alembic/versions/20260706_0000_*_enable_postgis_extensions.py).
  All subsequent schema migrations can rely on PostGIS types being available.
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import get_settings
from app.db.base import Base

# ── Import all ORM models so their tables are visible to Alembic ───────────────
# Add one import per domain model module as they are created (Day 2+).
# Example:
#   from app.db.models import sensor      # noqa: F401
#   from app.db.models import reading     # noqa: F401
#   from app.db.models import alert       # noqa: F401

# ─────────────────────────────────────────────────────────────────────────────

alembic_config = context.config
settings = get_settings()

# Configure stdlib logging from alembic.ini [loggers] section.
# Must be called after settings are loaded (settings may configure log level).
if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name)

target_metadata = Base.metadata


# ── Core migration function (sync, passed via run_sync) ────────────────────────

def do_run_migrations(connection: Connection) -> None:
    """
    Execute pending migrations on the provided synchronous connection.

    This function is called via connection.run_sync() inside the async runner.
    SQLAlchemy bridges the async engine to a synchronous execution context so
    that Alembic's (inherently synchronous) migration runner can use it.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,        # Detect column type changes in autogenerate
        include_schemas=True,     # Required for non-public schemas (future)
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Offline mode (SQL generation, no live connection) ──────────────────────────

def run_migrations_offline() -> None:
    """
    Generate SQL migration scripts without connecting to the database.

    Useful for reviewing migration SQL before applying to production, or for
    DBAs who apply schema changes manually. Run with: alembic upgrade head --sql

    We strip '+asyncpg' from the URL so SQLAlchemy resolves the PostgreSQL
    dialect for SQL compilation without importing or initialising the asyncpg
    DBAPI module — no connection attempt is made in offline mode.
    """
    offline_url = settings.DATABASE_URL.replace("+asyncpg", "", 1)
    context.configure(
        url=offline_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        include_schemas=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# ── Online mode (live database, async) ────────────────────────────────────────

async def run_async_migrations() -> None:
    """
    Run migrations against a live PostgreSQL database using asyncpg.

    A transient async engine is created for the migration run.
    NullPool is used so the engine holds no persistent connections after
    migrations complete — appropriate for the short-lived Alembic CLI process.
    """
    from sqlalchemy.pool import NullPool

    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=NullPool,  # No persistent connection pool for one-shot CLI usage
    )
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_online() -> None:
    """
    Entry point for online migration mode.

    asyncio.run() is safe here because Alembic's CLI always starts in a fresh
    interpreter context with no pre-existing event loop.
    """
    asyncio.run(run_async_migrations())


# ── Dispatch ──────────────────────────────────────────────────────────────────

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
