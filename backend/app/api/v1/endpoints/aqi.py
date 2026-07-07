"""
GET /api/v1/aqi/daily — Surface AQI daily summary endpoint.

Returns aggregated AQI statistics and individual station readings for a
specified region and date. The response includes both the national-level
summary (avg/max/min AQI, dominant pollutant, station count) and the
per-station readings that compose it.

Design decisions:
  - Separate query params for region and date (not path params) to allow
    convenient default behaviour: calling with no params returns today's
    national summary.
  - Response model AQIDailyListResponse uses an envelope pattern so
    the API can add pagination tokens in a future version without
    breaking existing consumers.
  - Business logic lives entirely in AQIService — this handler is
    a thin translation layer between HTTP and the service contract.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, status

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.schemas.aqi import AQIDailyListResponse
from app.services.aqi_service import AQIService, aqi_service

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/aqi/daily",
    response_model=AQIDailyListResponse,
    summary="Daily AQI Summary",
    description=(
        "Returns the surface AQI summary and individual station readings for a region and date. "
        "When called with no parameters, returns the national India summary for today (UTC). "
        "The `summary` field contains aggregate statistics (avg / max / min AQI, dominant pollutant) "
        "while the `summary.readings` array contains per-station observations. "
        "**Note:** Station readings are capped at `limit` per request. "
        "Use `region` to filter by geographic zone."
    ),
    tags=["aqi"],
    responses={
        status.HTTP_200_OK: {
            "description": "AQI summary and station readings retrieved successfully.",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "No data found for the specified region and date.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Unexpected server error — check logs for details.",
        },
    },
)
async def get_aqi_daily(
    region: str = Query(
        default="India",
        description="Geographic region to query. Examples: 'India', 'North India', 'Delhi'.",
        min_length=1,
        max_length=100,
    ),
    date_str: str | None = Query(
        default=None,
        alias="date",
        description=(
            "Target date in ISO 8601 format (YYYY-MM-DD). "
            "Defaults to today (UTC) if not provided."
        ),
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=500,
        description="Maximum number of station readings to include in the response.",
    ),
    service: AQIService = Depends(lambda: aqi_service),
) -> AQIDailyListResponse:
    """Fetch AQI daily summary from the AQI service and return as a typed response."""

    query_date: date | None = None
    if date_str:
        try:
            query_date = date.fromisoformat(date_str)
        except ValueError:
            # FastAPI's pattern validator catches malformed strings first,
            # but this is a secondary guard for edge cases.
            raise NotFoundError(
                message=f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD.",
                detail={"received": date_str},
            )

    logger.info(
        "AQI daily summary request",
        region=region,
        date=str(query_date or "today"),
        limit=limit,
    )

    result = service.get_daily_summary(
        region=region,
        query_date=query_date,
        limit=limit,
    )

    if result.count == 0:
        raise NotFoundError(
            message=f"No AQI data found for region '{region}' on {query_date or 'today'}.",
            detail={"region": region, "date": str(query_date)},
        )

    return result
