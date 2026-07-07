"""
API v1 master router.

This module is the single registration point for all v1 endpoint routers.
Adding a new domain to the API requires only:
  1. Create app/api/v1/endpoints/<domain>.py with a module-level APIRouter.
  2. Import it here and call router.include_router().

Router tags and prefixes can be overridden at include time to keep
individual endpoint modules free of URL path concerns.

Current v1 endpoints:
  GET /api/v1/health   — Service health check (observability)
  GET /api/v1/version  — Application version metadata (observability)
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health, version

router = APIRouter()

router.include_router(health.router)
router.include_router(version.router)
