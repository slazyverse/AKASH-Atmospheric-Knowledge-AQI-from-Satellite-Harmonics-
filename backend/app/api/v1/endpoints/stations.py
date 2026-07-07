"""
GET /api/v1/stations — CPCB Monitoring Station registry endpoint.

Returns metadata for CPCB (Central Pollution Control Board) air quality
monitoring stations. Station records are quasi-static — they change only
when new stations are commissioned or decommissioned.

This endpoint is used by:
  - Dashboard station selector dropdowns
  - Base map layer rendering
  - Forecast station validation

Design decisions:
  - Returns metadata only (no real-time readings). Readings are fetched
    via GET /api/v1/aqi/daily to avoid bloating the station registry response.
  - active_only=true is the default to avoid displaying decommissioned
    stations in the dashboard by default.
  - state and network query params support partial, case-insensitive
    matching for user-facing geographic filtering.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.logging import get_logger
from app.schemas.stations import StationsResponse
from app.services.station_service import StationService, station_service

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/stations",
    response_model=StationsResponse,
    summary="CPCB Monitoring Station Registry",
    description=(
        "Returns metadata for CPCB air quality monitoring stations. "
        "Includes station identifiers, geographic coordinates, administrative location, "
        "monitoring network affiliation, and operational status. "
        "Use the `state` parameter to filter to a specific Indian state. "
        "Use `network` to filter by monitoring network (CPCB | SPCB | SAFAR). "
        "Set `active_only=false` to include decommissioned stations for historical analysis. "
        "**Note:** This endpoint returns metadata only. "
        "Use **GET /api/v1/aqi/daily** to retrieve live AQI readings."
    ),
    tags=["stations"],
    responses={
        status.HTTP_200_OK: {
            "description": "Station list retrieved successfully.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Unexpected server error.",
        },
    },
)
async def list_stations(
    state: str | None = Query(
        default=None,
        description=(
            "Filter stations by Indian state name (case-insensitive, partial match). "
            "Examples: 'Delhi', 'Maharashtra', 'Karnataka'."
        ),
        max_length=100,
    ),
    network: str | None = Query(
        default=None,
        description=(
            "Filter by monitoring network. "
            "Accepted values: 'CPCB', 'SPCB', 'SAFAR' (case-insensitive)."
        ),
        max_length=20,
    ),
    active_only: bool = Query(
        default=True,
        description=(
            "If true (default), return only stations currently transmitting data. "
            "Set to false to include decommissioned stations."
        ),
    ),
    limit: int = Query(
        default=100,
        ge=1,
        le=1000,
        description="Maximum number of stations to return. Default: 100.",
    ),
    service: StationService = Depends(lambda: station_service),
) -> StationsResponse:
    """Fetch station registry from the Station service and return as a typed response."""

    logger.info(
        "Station list request",
        state=state,
        network=network,
        active_only=active_only,
        limit=limit,
    )

    return service.list_stations(
        state=state,
        network=network,
        active_only=active_only,
        limit=limit,
    )
