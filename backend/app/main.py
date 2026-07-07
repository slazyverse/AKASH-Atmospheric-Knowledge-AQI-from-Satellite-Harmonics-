"""
VAYU-DRISHTI FastAPI application factory.

This module is the entry point for the API server. It is responsible for:
  1. Configuring structured logging before any other initialisation.
  2. Building the FastAPI application instance via the factory function.
  3. Registering CORS middleware and the request-ID injection middleware.
  4. Mounting the versioned API router.
  5. Registering global exception handlers.
  6. Exposing /docs and /redoc only in non-production environments.

Design decisions:
  - Application factory pattern (create_application()): separates application
    construction from the module-level 'app' object, allowing tests to call
    the factory with custom settings without side effects on other tests.
  - Lifespan context manager: replaces the deprecated @app.on_event("startup")
    / @app.on_event("shutdown") decorators. Code before 'yield' runs at
    startup; code after 'yield' runs at shutdown. This hook is where DB pool
    warm-up, ML model loading, and background task initialisation will live.
  - Request-ID middleware: injects a unique UUID into every request/response
    cycle via the X-Request-ID header. structlog.contextvars binds this ID so
    every log line emitted during the request carries it, enabling full
    request tracing across middleware, route handlers, and services.
  - CORS middleware: configured from ALLOWED_ORIGINS setting. In production,
    this must be restricted to the actual frontend domain.
  - Interactive docs (Swagger UI, ReDoc): disabled in production to reduce
    the attack surface. They are available in development and staging.
"""

from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from typing import AsyncGenerator

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router as api_v1_router
from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger

# ── Bootstrap ─────────────────────────────────────────────────────────────────
# Load settings and configure logging as the very first actions.
# No logger should be created before configure_logging() is called.
settings: Settings = get_settings()
configure_logging(
    log_level=settings.LOG_LEVEL,
    log_format=settings.LOG_FORMAT,
)

logger = get_logger(__name__)


# ── Lifespan ───────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Manage the full lifecycle of the FastAPI application.

    Startup (before yield):
      - Emit a structured startup log with key configuration metadata.
      - Future: warm up the DB connection pool.
      - Future: load ML model weights into memory.
      - Future: start background sensor polling tasks.

    Shutdown (after yield):
      - Future: drain active DB connections gracefully.
      - Future: flush async log buffers.
      - Future: cancel background tasks cleanly.
    """
    logger.info(
        "VAYU-DRISHTI API starting",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
        host=settings.HOST,
        port=settings.PORT,
        api_prefix=settings.API_V1_PREFIX,
        debug=settings.DEBUG,
    )

    yield  # Application is live and serving traffic

    logger.info(
        "VAYU-DRISHTI API shutting down gracefully.",
        version=settings.APP_VERSION,
        environment=settings.ENVIRONMENT,
    )


# ── Application Factory ────────────────────────────────────────────────────────

def create_application() -> FastAPI:
    """
    Construct and configure the FastAPI application instance.

    This function is the single point of assembly for all application
    components: middleware, routers, and exception handlers.
    It can be called in tests with different settings to produce isolated
    application instances without polluting global state.

    Returns:
        A fully configured FastAPI instance ready to serve requests.
    """
    is_production = settings.ENVIRONMENT == "production"

    app = FastAPI(
        title=settings.APP_NAME,
        description=settings.APP_DESCRIPTION,
        version=settings.APP_VERSION,
        lifespan=lifespan,
        # Disable interactive API docs in production:
        # They expose the full schema to anyone who can reach the server,
        # which is an unnecessary information disclosure risk.
        docs_url=None if is_production else "/docs",
        redoc_url=None if is_production else "/redoc",
        openapi_url=None if is_production else "/openapi.json",
        # Contact and license metadata for the OpenAPI spec
        contact={
            "name": "VAYU-DRISHTI Engineering Team",
            "email": "engineering@vayu-drishti.io",
        },
        license_info={
            "name": "MIT",
        },
    )

    # ── CORS Middleware ────────────────────────────────────────────────────────
    # Configured before any route-level middleware so it applies to all routes.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # ── Request-ID Middleware ──────────────────────────────────────────────────
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        """
        Assign a unique request ID to every incoming request.

        If the client provides X-Request-ID (e.g., from a frontend or
        API gateway), it is honoured. Otherwise a new UUID is generated.
        The ID is bound to structlog's context variables so every log
        line emitted during this request carries 'request_id' automatically.
        The same ID is echoed in the response header so clients can correlate
        their request with log entries in a support ticket.
        """
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))

        # Clear any context from previous requests (important for reused threads/tasks)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # ── Routers ────────────────────────────────────────────────────────────────
    app.include_router(
        api_v1_router,
        prefix=settings.API_V1_PREFIX,
    )

    # ── Root Discovery Endpoint ────────────────────────────────────────────────
    @app.get("/", include_in_schema=False)
    async def root() -> JSONResponse:
        """
        Returns basic service discovery information.
        Not versioned — consumers should use /api/v1/ endpoints directly.
        """
        return JSONResponse(
            status_code=200,
            content={
                "service": settings.APP_NAME,
                "version": settings.APP_VERSION,
                "environment": settings.ENVIRONMENT,
                "docs_url": "/docs" if not is_production else None,
                "health_url": f"{settings.API_V1_PREFIX}/health",
                "version_url": f"{settings.API_V1_PREFIX}/version",
            },
        )

    # ── Exception Handlers ─────────────────────────────────────────────────────
    register_exception_handlers(app)

    return app


# ── Module-level application instance ─────────────────────────────────────────
# Uvicorn imports this 'app' object directly.
# Usage: uvicorn app.main:app --reload
app: FastAPI = create_application()
