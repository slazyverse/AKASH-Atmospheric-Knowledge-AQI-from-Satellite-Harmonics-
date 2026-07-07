"""
Health check endpoint — GET /api/v1/health

Performs active liveness and readiness probing:
  - api:      Always healthy if this handler executes (confirms the ASGI
              process is alive and reachable).
  - database: Opens a connection from the async engine pool, executes
              'SELECT 1', and measures round-trip latency.

Why direct engine probe (not get_db dependency):
  The previous implementation used Depends(get_db) — the request-scoped
  session factory — to probe the database. This had two problems:
    1. If AsyncSessionLocal() raises before yielding (e.g., pool exhausted),
       the exception occurs outside the health handler's try/except, and the
       endpoint returns a 500 rather than a structured 'unhealthy' response.
    2. Health checks should bypass the business-logic session lifecycle.
       Using async_engine.connect() directly gives the probe its own dedicated
       connection that is not affected by the normal session middleware.

  The direct engine.connect() approach ensures that ALL failure modes
  (host unreachable, auth failure, pool exhausted, timeout) are caught by
  the health handler's try/except and reported as component 'unhealthy'.

HTTP status note:
  - If any critical backend dependency (like the database) is unhealthy,
    returns HTTP 503 Service Unavailable in RFC 7807 format.
  - If components are healthy or partially degraded, returns HTTP 200 OK.
"""

import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.db.session import async_engine
from app.schemas.health import (
    ComponentHealth,
    ComponentStatus,
    HealthResponse,
    OverallStatus,
)

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health Check",
    description=(
        "Returns the real-time health status of the VAYU-DRISHTI API and its dependencies. "
        "A response with status code 200 and `status: healthy` confirms the service is fully ready to serve traffic. "
        "A response with status code 503 Service Unavailable indicates that critical required "
        "dependencies (like the database) are unhealthy. "
        "Component-level breakdown is provided to diagnose subsystems."
    ),
    tags=["observability"],
    responses={
        200: {
            "description": "Health check completed. Application is healthy or partially degraded.",
            "model": HealthResponse,
        },
        503: {
            "description": "Service Unavailable. Critical dependencies (Database) are unhealthy.",
            "content": {
                "application/json": {
                    "example": {
                        "error": {
                            "code": "DATABASE_ERROR",
                            "message": "Database is unreachable or unhealthy.",
                            "detail": {
                                "status": "unhealthy",
                                "timestamp": "2026-07-06T18:00:00Z",
                                "environment": "development",
                                "components": {
                                    "api": {"status": "healthy", "detail": "Request handler reachable."},
                                    "database": {"status": "unhealthy", "detail": "Database unreachable: ..."}
                                }
                            }
                        }
                    }
                }
            }
        }
    },
)
async def health_check(
    response: Response,
    settings: Settings = Depends(get_settings),
) -> Any:
    """Probe all registered service components and return an aggregate health report."""

    components: dict[str, ComponentHealth] = {}

    # ── API component ──────────────────────────────────────────────────────────
    # If this handler is executing, the ASGI process and event loop are healthy.
    components["api"] = ComponentHealth(
        status=ComponentStatus.HEALTHY,
        detail="Request handler reachable.",
    )

    # ── Database component ─────────────────────────────────────────────────────
    db_status = ComponentStatus.HEALTHY
    db_latency_ms: float | None = None
    db_detail: str | None = None

    try:
        # Open a dedicated connection from the pool — bypasses the request-scoped
        # session lifecycle so pool exhaustion or session errors don't mask the
        # true connectivity status.
        t_start = time.perf_counter()
        async with async_engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        db_latency_ms = round((time.perf_counter() - t_start) * 1000, 2)
        db_detail = "Connection pool healthy."
        logger.debug("Database health check passed", latency_ms=db_latency_ms)
    except Exception as exc:
        db_status = ComponentStatus.UNHEALTHY
        db_detail = f"Database unreachable: {type(exc).__name__}: {exc}"
        logger.error(
            "Database health check failed",
            exc_info=exc,
            environment=settings.ENVIRONMENT,
        )

    components["database"] = ComponentHealth(
        status=db_status,
        latency_ms=db_latency_ms,
        detail=db_detail,
    )

    # ── Aggregate status ───────────────────────────────────────────────────────
    all_statuses = {c.status for c in components.values()}
    if ComponentStatus.UNHEALTHY in all_statuses:
        overall = OverallStatus.UNHEALTHY
    elif ComponentStatus.DEGRADED in all_statuses:
        overall = OverallStatus.DEGRADED
    else:
        overall = OverallStatus.HEALTHY

    if overall == OverallStatus.UNHEALTHY:
        # Return 503 Service Unavailable with RFC 7807 error layout
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": {
                    "code": "DATABASE_ERROR",
                    "message": "Database is unreachable or unhealthy.",
                    "detail": {
                        "status": overall.value,
                        "timestamp": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
                        "environment": settings.ENVIRONMENT,
                        "components": {
                            k: {
                                "status": v.status.value,
                                "latency_ms": v.latency_ms,
                                "detail": v.detail,
                            }
                            for k, v in components.items()
                        },
                    },
                }
            },
        )

    response.status_code = status.HTTP_200_OK
    return HealthResponse(
        status=overall,
        timestamp=datetime.now(UTC),
        environment=settings.ENVIRONMENT,
        components=components,
    )
