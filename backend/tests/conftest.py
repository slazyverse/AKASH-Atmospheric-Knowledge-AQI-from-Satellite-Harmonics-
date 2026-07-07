"""
Shared pytest fixtures for the VAYU-DRISHTI test suite.

Architecture:
  The health endpoint was updated to use async_engine.connect() directly
  instead of Depends(get_db). This makes the health probe resilient to all
  failure modes (pool exhausted, host unreachable, auth failure) by keeping
  every exception inside the endpoint's own try/except block.

  Consequently, the previous dependency_overrides approach (replacing get_db)
  no longer applies to health tests. Fixtures now use unittest.mock.patch to
  replace the module-level 'async_engine' reference in the health endpoint
  module with a mock that either succeeds or raises.

Fixture design:
  - mock_engine_healthy:  Async context manager that yields a mock connection
                          where execute() returns successfully.
  - mock_engine_failure:  Async context manager that raises Exception in
                          __aenter__, simulating an unreachable database.
  - client:               Patches async_engine with mock_engine_healthy.
  - client_db_failure:    Patches async_engine with mock_engine_failure.
  - client_no_db:         No patching — for endpoints with no DB dependency
                          (e.g., /version, /).

Test isolation:
  - patch() is used as a context manager, scoped to the client fixture.
    It is active for the duration of each test and cleaned up automatically.
  - No app.dependency_overrides are used; there is no global state to leak.

Integration tests:
  - Tests tagged @pytest.mark.integration require a live PostgreSQL instance.
  - Exclude from default run: pytest -m 'not integration'

Async configuration:
  - asyncio_mode='auto' in pyproject.toml — all 'async def' test functions
    and fixtures run without explicit @pytest.mark.asyncio decoration.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


# ── Engine mock factories ──────────────────────────────────────────────────────

@pytest.fixture
def mock_engine_healthy() -> MagicMock:
    """
    Mock async engine where connect() succeeds and SELECT 1 returns normally.

    Simulates a healthy PostgreSQL connection pool for unit tests that
    exercise the happy path of GET /api/v1/health.
    """
    engine = MagicMock()

    @asynccontextmanager
    async def healthy_connect():
        conn = AsyncMock()
        conn.execute = AsyncMock(return_value=MagicMock())
        yield conn

    engine.connect = healthy_connect
    return engine


@pytest.fixture
def mock_engine_failure() -> MagicMock:
    """
    Mock async engine where connect() raises an exception in __aenter__.

    Simulates a database that is unreachable (wrong host, network partition,
    authentication failure, etc.). The health endpoint should catch this and
    report the database component as 'unhealthy'.
    """
    engine = MagicMock()

    @asynccontextmanager
    async def failing_connect():
        raise Exception("Connection refused: database is unavailable")
        yield  # pragma: no cover — required by asynccontextmanager, never reached

    engine.connect = failing_connect
    return engine


# ── Test client fixtures ───────────────────────────────────────────────────────

@pytest.fixture
async def client(mock_engine_healthy: MagicMock) -> AsyncClient:
    """
    Async HTTP test client with a healthy mock database engine.

    Patches app.api.v1.endpoints.health.async_engine for the duration of
    each test so all health endpoint database probes use the mock engine.
    """
    with patch("app.api.v1.endpoints.health.async_engine", mock_engine_healthy):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            yield ac


@pytest.fixture
async def client_db_failure(mock_engine_failure: MagicMock) -> AsyncClient:
    """
    Async HTTP test client with a failing mock database engine.

    Used to verify that the health endpoint correctly reports 'unhealthy'
    when the database raises a connection error.
    """
    with patch("app.api.v1.endpoints.health.async_engine", mock_engine_failure):
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://testserver",
        ) as ac:
            yield ac


@pytest.fixture
async def client_no_db() -> AsyncClient:
    """
    Async HTTP test client with no database patching.

    Suitable for endpoints that do not perform any database operations,
    such as GET /api/v1/version and GET /.
    """
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac
