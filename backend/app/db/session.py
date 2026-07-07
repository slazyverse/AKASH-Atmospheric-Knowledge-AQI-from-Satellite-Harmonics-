"""
Async database engine, session factory, and FastAPI session dependency.

Design decisions:
  - async_engine: a single engine instance per process, managing an internal
    connection pool. Pool parameters are sized for a moderate-traffic API;
    increase pool_size and max_overflow under heavy sensor ingestion load.
  - pool_pre_ping=True: before handing out a connection from the pool,
    SQLAlchemy executes a cheap "SELECT 1" to detect stale connections
    broken by the database server or a firewall timeout. This prevents
    "server closed the connection unexpectedly" errors under idle conditions.
  - pool_recycle=3600: connections are forcibly recycled after 1 hour to
    avoid hitting the PostgreSQL idle session timeout (typically 8 hours but
    configurable per deployment). Must be less than the server-side timeout.
  - expire_on_commit=False: prevents SQLAlchemy from expiring all ORM
    attributes after a commit. Without this, accessing relationship attributes
    after commit raises a lazy-load error in async context (there is no
    implicit IO in async sessions). This is the standard recommendation for
    async SQLAlchemy applications.
  - get_db: a FastAPI dependency that provides exactly one session per request.
    The try/except/finally block guarantees the session is always closed and
    the connection is returned to the pool, even if the route handler raises.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

_settings = get_settings()

# ── Async Engine ───────────────────────────────────────────────────────────────

async_engine: AsyncEngine = create_async_engine(
    url=_settings.DATABASE_URL,
    echo=_settings.DEBUG,         # Logs all SQL when DEBUG=True; off in production
    pool_size=5,                   # Baseline connections kept open
    max_overflow=15,               # Additional connections under burst load (total: 20)
    pool_pre_ping=True,            # Validate connections before checkout
    pool_recycle=3600,             # Recycle connections every hour
    connect_args={
        "server_settings": {
            # Identifies this application in pg_stat_activity for DBA diagnostics
            "application_name": _settings.APP_NAME,
        }
    },
)

# ── Session Factory ────────────────────────────────────────────────────────────

AsyncSessionLocal: async_sessionmaker[AsyncSession] = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # Safe access to ORM attributes after commit in async context
    autocommit=False,
    autoflush=False,
)


# ── FastAPI Request-Scoped Session Dependency ──────────────────────────────────

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency that yields a database session scoped to the request.

    One session is created per HTTP request. If the route handler or any
    downstream call raises an exception, the session is rolled back before
    closing to ensure no partial writes remain.

    Usage:
        from sqlalchemy.ext.asyncio import AsyncSession
        from fastapi import Depends
        from app.db.session import get_db

        @router.get("/sensors")
        async def list_sensors(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(Sensor))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
