"""
Version endpoint — GET /api/v1/version

Returns immutable deployment metadata about the running API instance.

Use cases:
  - Post-deployment verification: confirm the correct version was deployed.
  - Canary analysis: compare two instances to verify gradual rollout.
  - Incident response: know immediately which build is affected.
  - Feature flag awareness: dashboard can conditionally render ML features
    based on ENABLE_ML_ENDPOINTS (future extension).

This endpoint has no side effects, requires no database access, and
should be extremely low-latency (< 1 ms). It is safe to call frequently.
"""

import sys

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.schemas.version import VersionResponse

router = APIRouter()


@router.get(
    "/version",
    response_model=VersionResponse,
    summary="Application Version",
    description=(
        "Returns version and runtime metadata for the currently deployed API instance. "
        "Use this endpoint after deployments to confirm the rollout succeeded, or during "
        "incidents to identify which build is running."
    ),
    tags=["observability"],
)
async def get_version(
    settings: Settings = Depends(get_settings),
) -> VersionResponse:
    """Return the application version and deployment environment metadata."""
    return VersionResponse(
        name=settings.APP_NAME,
        version=settings.APP_VERSION,
        api_version="v1",
        environment=settings.ENVIRONMENT,
        python_version=sys.version.split()[0],
    )
