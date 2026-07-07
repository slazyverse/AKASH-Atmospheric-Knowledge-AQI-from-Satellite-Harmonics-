"""
GET /api/v1/fire — Active Fire Monitoring endpoint.

Returns active satellite-detected fire events and high-severity alerts
within a configurable time window. Fire detections come from MODIS
(Terra/Aqua) and VIIRS (SNPP / NOAA-20) instruments via NASA FIRMS.

Design decisions:
  - Single endpoint returns BOTH events AND alerts in one payload,
    eliminating a second round-trip from the dashboard. The `FireResponse`
    envelope carries `events` and `alerts` as separate arrays.
  - min_frp filter: FRP (Fire Radiative Power) is the primary scientific
    measure of fire intensity. 10 MW is the typical FIRMS threshold;
    lowering it reveals smaller agricultural fires.
  - hours parameter controls the temporal window. 24h = standard operational
    view; 72h supports trend analysis.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.core.logging import get_logger
from app.schemas.fire import FireResponse
from app.services.fire_service import FireService, fire_service

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/fire",
    response_model=FireResponse,
    summary="Active Fire Detections",
    description=(
        "Returns active fire detection points from MODIS and VIIRS satellites "
        "along with high-severity fire alerts for the specified time window. "
        "Fire events include Fire Radiative Power (FRP in MW), brightness temperature, "
        "satellite source, confidence level, land cover type, and administrative location. "
        "Alerts are generated when FRP exceeds severity thresholds or when predicted "
        "AQI impact at downwind monitoring stations is significant. "
        "The response combines events and alerts in a single payload to minimise "
        "client round-trips. Filter by `min_frp` to focus on intense fires "
        "and by `hours` to narrow the observation window."
    ),
    tags=["fire"],
    responses={
        status.HTTP_200_OK: {
            "description": "Fire events and alerts retrieved successfully.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Unexpected server error.",
        },
    },
)
async def get_fire_data(
    region: str = Query(
        default="All India",
        description="Geographic region filter. Examples: 'All India', 'North', 'Northeast'.",
        min_length=1,
        max_length=100,
    ),
    min_frp: float = Query(
        default=10.0,
        ge=0.0,
        le=10000.0,
        description=(
            "Minimum Fire Radiative Power in megawatts (MW). "
            "10 MW = FIRMS standard operational threshold. "
            "Set to 0 to include all detections including very small fires."
        ),
    ),
    hours: int = Query(
        default=24,
        ge=1,
        le=168,
        description=(
            "Time window in hours over which to return fire detections. "
            "Range: 1–168 hours (1 week). Default: 24 hours."
        ),
    ),
    service: FireService = Depends(lambda: fire_service),
) -> FireResponse:
    """Fetch active fire detections and alerts from the Fire service."""

    logger.info(
        "Fire data request",
        region=region,
        min_frp=min_frp,
        hours=hours,
    )

    result = service.get_fire_data(
        region=region,
        min_frp=min_frp,
        hours=hours,
    )

    # Fire endpoint always returns HTTP 200 even with zero events —
    # "no fires detected" is a valid and informative response.
    return result
