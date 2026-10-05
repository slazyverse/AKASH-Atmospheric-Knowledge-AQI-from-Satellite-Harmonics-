"""
GET /api/v1/forecast — AQI Forecast endpoint.

Returns a multi-step ahead AQI forecast for a single monitoring station
along with model performance metrics and feature importances.

Current state: no forecasting model exists — forecasts are a SIMULATED
baseline (see ForecastService), metrics are null and feature importances empty.
Valid station IDs come from the same registry as GET /api/v1/stations.

Design decisions:
  - station_id is a required query param (not a path param) to avoid
    implicit 404 responses when the client forgets to supply it.
    Explicit 422 validation error is clearer than a 404 for the caller.
  - Full ForecastResponse includes model_metrics and feature_importances
    to support single-request rendering of the forecast + model panel.
  - horizon_hours is capped at 72 — beyond this the forecast uncertainty
    is too wide to be scientifically useful for AQI prediction.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from fastapi.concurrency import run_in_threadpool

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.schemas.forecast import ForecastResponse
from app.services.forecast_service import ForecastService, forecast_service
from app.services.station_service import station_service

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/forecast",
    response_model=ForecastResponse,
    summary="AQI Station Forecast",
    description=(
        "Returns a multi-step ahead AQI forecast (1-hour steps, up to 72 hours) for a single "
        "monitoring station, plus model metrics and feature importances so the dashboard can "
        "render the forecast panel in one call. "
        "**No forecasting model is integrated: `forecast_kind` is `simulated` — steps are a "
        "diurnal baseline seeded from the station's latest observation "
        "(`based_on_observation_at`), bounds are illustrative (not calibrated quantiles), "
        "metric fields are null and `feature_importances` is empty.** "
        "Any active station from GET /api/v1/stations is accepted."
    ),
    tags=["forecast"],
    responses={
        status.HTTP_200_OK: {
            "description": "Forecast generated successfully.",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "The specified station_id is not recognised.",
        },
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "description": "Invalid query parameters (e.g., horizon_hours out of range).",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Unexpected server error.",
        },
    },
)
async def get_forecast(
    station_id: str = Query(
        description=(
            "CPCB station identifier to generate a forecast for. "
            "Example: 'DL001' (Delhi – Anand Vihar). "
            "Call GET /api/v1/stations to retrieve the full station list."
        ),
        min_length=3,
        max_length=20,
        examples=["DL001"],
    ),
    horizon_hours: int = Query(
        default=72,
        ge=1,
        le=72,
        description="Forecast horizon in hours. Range: 1–72. Default: 72.",
    ),
    service: ForecastService = Depends(lambda: forecast_service),
) -> ForecastResponse:
    """Generate and return an AQI forecast from the Forecast service."""

    # Validate against the same registry that backs GET /api/v1/stations
    if station_service.get_station(station_id) is None:
        raise NotFoundError(
            message=f"Station '{station_id}' not found. Use GET /api/v1/stations for the full list.",
            detail={"station_id": station_id},
        )

    logger.info(
        "Forecast request",
        station_id=station_id,
        horizon_hours=horizon_hours,
    )

    result = await run_in_threadpool(
        service.get_station_forecast,
        station_id=station_id,
        horizon_hours=horizon_hours,
    )
    if result is None:
        raise NotFoundError(
            message=f"Station '{station_id}' has no observation to seed a forecast from.",
            detail={"station_id": station_id},
        )
    return result
