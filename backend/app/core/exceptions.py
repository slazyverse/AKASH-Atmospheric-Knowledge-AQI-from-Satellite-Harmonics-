"""
Domain exception hierarchy and global FastAPI exception handlers.

Design decisions:
  - Single root exception (VayuDrishtiError) with HTTP status and error code
    as class attributes. Route handlers raise domain exceptions — never
    HTTPException — keeping HTTP concerns out of the business logic layer.
  - RFC 7807-style responses: every error response follows the structure
    {"error": {"code": "...", "message": "...", "detail": ...}} for
    consistent parsing by API consumers and dashboards.
  - register_exception_handlers() is called once in the app factory (main.py)
    and attaches handlers at the application level, not the router level,
    so every route benefits from structured error responses.
  - unhandled_exception_handler catches anything not explicitly raised as a
    domain exception, logs it with exc_info=True for traceability, and
    returns a generic 500 without leaking internal details to the client.
"""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import get_logger

logger = get_logger(__name__)


# ── Base Exception ─────────────────────────────────────────────────────────────

class VayuDrishtiError(Exception):
    """
    Root exception for all domain errors in VAYU-DRISHTI.

    Subclasses override http_status and error_code to customise the
    HTTP response without writing new handler functions.
    """

    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR
    error_code: str = "INTERNAL_ERROR"

    def __init__(self, message: str, detail: Any | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail  # Optional structured detail for the client


# ── Client Errors (4xx) ────────────────────────────────────────────────────────

class NotFoundError(VayuDrishtiError):
    """Raised when a requested resource (sensor, reading, station) does not exist."""

    http_status = status.HTTP_404_NOT_FOUND
    error_code = "NOT_FOUND"


class DomainValidationError(VayuDrishtiError):
    """
    Raised when incoming data passes Pydantic schema validation but fails
    domain-level business rules (e.g., AQI value outside sensor range).
    """

    http_status = status.HTTP_422_UNPROCESSABLE_ENTITY
    error_code = "VALIDATION_ERROR"


class ConflictError(VayuDrishtiError):
    """Raised when an operation would create a duplicate resource (e.g., duplicate sensor ID)."""

    http_status = status.HTTP_409_CONFLICT
    error_code = "CONFLICT"


class UnauthorizedError(VayuDrishtiError):
    """Raised when a request lacks valid authentication credentials."""

    http_status = status.HTTP_401_UNAUTHORIZED
    error_code = "UNAUTHORIZED"


class ForbiddenError(VayuDrishtiError):
    """Raised when an authenticated request lacks the required permissions."""

    http_status = status.HTTP_403_FORBIDDEN
    error_code = "FORBIDDEN"


class RateLimitError(VayuDrishtiError):
    """Raised when a client exceeds the configured request rate limit."""

    http_status = status.HTTP_429_TOO_MANY_REQUESTS
    error_code = "RATE_LIMIT_EXCEEDED"


# ── Server Errors (5xx) ────────────────────────────────────────────────────────

class DatabaseError(VayuDrishtiError):
    """
    Raised when a database operation fails unexpectedly.
    Returns 503 (Service Unavailable) so clients and load balancers
    can retry against a different instance.
    """

    http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "DATABASE_ERROR"


class ExternalServiceError(VayuDrishtiError):
    """
    Raised when a call to an external dependency (weather API, geocoding
    service, etc.) fails. Returns 502 Bad Gateway.
    """

    http_status = status.HTTP_502_BAD_GATEWAY
    error_code = "EXTERNAL_SERVICE_ERROR"


class MLInferenceError(VayuDrishtiError):
    """
    Raised when an ML model fails to produce a valid prediction.
    Prepared for Day 4+ when the forecasting service is introduced.
    """

    http_status = status.HTTP_503_SERVICE_UNAVAILABLE
    error_code = "ML_INFERENCE_ERROR"


# ── Response Builder ──────────────────────────────────────────────────────────

def _build_error_response(
    status_code: int,
    error_code: str,
    message: str,
    detail: Any | None = None,
) -> JSONResponse:
    """
    Build an RFC 7807-style error response.

    The 'error' envelope is intentional: it reserves the top-level
    namespace for future additions (request_id, trace_id, timestamp)
    without breaking existing consumers.
    """
    body: dict[str, Any] = {
        "error": {
            "code": error_code,
            "message": message,
        }
    }
    if detail is not None:
        body["error"]["detail"] = detail
    return JSONResponse(status_code=status_code, content=body)


# ── Exception Handlers ─────────────────────────────────────────────────────────

async def vayu_drishti_exception_handler(
    request: Request,
    exc: VayuDrishtiError,
) -> JSONResponse:
    """Handle all known domain exceptions with a structured JSON response."""
    logger.warning(
        "Domain exception",
        error_code=exc.error_code,
        message=exc.message,
        path=str(request.url),
        method=request.method,
        http_status=exc.http_status,
    )
    return _build_error_response(
        status_code=exc.http_status,
        error_code=exc.error_code,
        message=exc.message,
        detail=exc.detail,
    )


async def unhandled_exception_handler(
    request: Request,
    exc: Exception,
) -> JSONResponse:
    """
    Catch-all handler for any exception not caught by a more specific handler.

    Logs the full traceback with exc_info=True (critical for debugging), but
    returns only a generic message to the client to avoid leaking internals.
    """
    logger.error(
        "Unhandled exception",
        exc_info=exc,
        path=str(request.url),
        method=request.method,
    )
    return _build_error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        error_code="INTERNAL_ERROR",
        message="An unexpected error occurred. Our team has been notified.",
    )


async def request_validation_exception_handler(
    request: Request,
    exc: RequestValidationError,
) -> JSONResponse:
    """
    Handle Pydantic request validation errors (HTTP 422).

    FastAPI raises RequestValidationError automatically when incoming request
    data (body, query params, path params, headers) fails Pydantic schema
    validation. The default FastAPI 422 response uses a flat 'detail' list
    that differs structurally from our RFC 7807-style error envelope.

    This handler normalises the Pydantic error list into our standard format
    so all API consumers parse a single, consistent error schema regardless
    of whether the error is a domain exception or a schema violation.

    The normalised detail list preserves:
      - 'field': the dotted location path (body -> field_name)
      - 'message': the human-readable validation message
      - 'type': the Pydantic error type code (e.g., 'value_error.missing')
    """
    normalised_errors = [
        {
            "field": " -> ".join(str(loc) for loc in err["loc"]),
            "message": err["msg"],
            "type": err["type"],
        }
        for err in exc.errors()
    ]
    logger.warning(
        "Request validation failed",
        path=str(request.url),
        method=request.method,
        errors=normalised_errors,
    )
    return _build_error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        error_code="REQUEST_VALIDATION_ERROR",
        message="Request validation failed. Check the 'detail' field for specifics.",
        detail=normalised_errors,
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Attach all global exception handlers to a FastAPI application instance.

    Registration order matters: FastAPI resolves handlers from most-specific
    to least-specific exception type. RequestValidationError must be registered
    before the generic Exception catch-all to prevent it from being shadowed.
    """
    # Pydantic schema validation errors (most specific — registered first)
    app.add_exception_handler(RequestValidationError, request_validation_exception_handler)  # type: ignore[arg-type]
    # Domain exceptions
    app.add_exception_handler(VayuDrishtiError, vayu_drishti_exception_handler)  # type: ignore[arg-type]
    # Unhandled catch-all (least specific — registered last)
    app.add_exception_handler(Exception, unhandled_exception_handler)  # type: ignore[arg-type]
