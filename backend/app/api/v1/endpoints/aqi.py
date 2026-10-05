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

from app.core.exceptions import DomainValidationError, NotFoundError
from app.core.logging import get_logger
from app.schemas.aqi import AQIDailyListResponse, AQIHistoryResponse
from app.services.aqi_service import AQIService, aqi_service

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/aqi/daily",
    response_model=AQIDailyListResponse,
    summary="Daily AQI Summary",
    description=(
        "Returns the surface AQI summary and individual station readings for a region and date. "
        "When called with no parameters, returns the national India summary for the latest "
        "available date. "
        "The `summary` field aggregates every matched station (avg / max / min AQI) "
        "while the `summary.readings` array contains per-station observations, capped at `limit`. "
        "`region` accepts 'India' (all), a zone ('North India', 'Central India', 'East India', "
        "'Northeast India', 'West India', 'South India'), or a state / city name. "
        "Data source: the resolved station dataset — team output when available, otherwise "
        "the bundled placeholder fixture (not real measurements); `GET /api/v1/sources` "
        "reports which. Each station's latest observation on the date is used; pollutants "
        "are null when not reported. Dates without data return 404."
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
        description=(
            "Region to query: 'India' (all), a zone such as 'North India' or 'South', "
            "or a state / city name such as 'Maharashtra' or 'Delhi'."
        ),
        min_length=1,
        max_length=100,
    ),
    date_str: str | None = Query(
        default=None,
        alias="date",
        description=(
            "Target date in ISO 8601 format (YYYY-MM-DD). "
            "Defaults to the latest date in the data source."
        ),
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    limit: int = Query(
        default=50,
        ge=1,
        le=1000,
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
            # The pattern validator rejects non-YYYY-MM-DD strings; this catches
            # impossible dates that match the pattern (e.g. 2026-13-45).
            raise DomainValidationError(
                message=f"Invalid date: '{date_str}'. Expected a real calendar date in YYYY-MM-DD.",
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
            message=f"No AQI data found for region '{region}' on {result.summary.summary_date}.",
            detail={"region": region, "date": str(query_date)},
        )

    return result


@router.get(
    "/aqi/history",
    response_model=AQIHistoryResponse,
    summary="Station AQI History",
    description=(
        "Returns one station's observations from the data source, oldest first, over the last "
        "`days` days of the source (the window ends at the source's latest date). Values are "
        "observations from the resolved dataset — never simulated. Single-date sources return "
        "a single point. `GET /api/v1/sources` reports whether the dataset is team output or "
        "a placeholder."
    ),
    tags=["aqi"],
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Station not found in the data source."},
    },
)
async def get_aqi_history(
    station_id: str = Query(
        min_length=1,
        max_length=50,
        description="Station identifier from GET /api/v1/stations.",
    ),
    days: int = Query(default=30, ge=1, le=366, description="Window length in days."),
    service: AQIService = Depends(lambda: aqi_service),
) -> AQIHistoryResponse:
    """Return the station's observation history from the AQI service."""
    result = service.get_history(station_id=station_id, days=days)
    if result is None:
        raise NotFoundError(
            message=f"Station '{station_id}' not found in the data source.",
            detail={"station_id": station_id},
        )
    return result
