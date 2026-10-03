"""
backend/app/services/forecast_service.py — AQI Forecast data service.

Current state: NO forecasting model exists. Every forecast is a SIMULATED
baseline — a deterministic diurnal curve seeded from the station's latest AQI
reading (team dataset or demo data), with an illustrative uncertainty band that
widens with horizon. Model metrics are therefore null and feature importances
empty; the service never reports accuracy numbers it did not measure.

The team's LightGBM artefact (ML_MODEL_PATH) is a same-day AQI estimator, not a
forecaster, so its metrics are served by /xai/global-importance and are
deliberately not attached here. Planned: a real forecasting model.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.aqi import aqi_category
from app.core.logging import get_logger
from app.schemas.forecast import (
    ForecastResponse,
    ForecastStep,
    ModelMetrics,
)
from app.services.aqi_service import aqi_service

logger = get_logger(__name__)

# ── Model metadata: honest placeholder until a forecasting model exists ────────

SIMULATED_MODEL_NAME = "Simulated baseline (no forecasting model)"

_MODEL_METRICS = ModelMetrics(
    model_name=SIMULATED_MODEL_NAME,
    model_version="stub",
)

# Seed used for stations that have no AQI reading (e.g. demo station DL002).
_DEFAULT_BASELINE_AQI = 150.0


class ForecastService:
    """
    Service class for AQI forecast construction.

    Station validation happens in the endpoint against the station registry;
    this service only builds the simulated sequence.
    """

    def get_station_forecast(
        self,
        station_id: str,
        horizon_hours: int = 72,
    ) -> ForecastResponse:
        """
        Return a simulated multi-step AQI forecast for a monitoring station.

        Args:
            station_id:    Station identifier from the station registry.
            horizon_hours: Forecast horizon (1–72 hours).

        Returns:
            ForecastResponse with ordered steps and placeholder model metadata.
        """
        logger.info(
            "Generating simulated AQI forecast",
            station_id=station_id,
            horizon_hours=horizon_hours,
        )

        now = datetime.now(tz=timezone.utc)
        # Round to nearest hour for clean timestamps
        base_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        latest = aqi_service.get_latest_aqi(station_id)
        baseline = float(latest) if latest is not None else _DEFAULT_BASELINE_AQI

        steps: list[ForecastStep] = []
        for h in range(1, min(horizon_hours, 72) + 1):
            # Simulate a mild diurnal pattern: peaks in early morning, dips midday
            hour_of_day = (base_time + timedelta(hours=h)).hour
            diurnal_factor = 1.0 + 0.15 * (1 - abs(hour_of_day - 6) / 12)
            predicted = round(baseline * diurnal_factor - h * 0.8, 1)
            predicted = max(0.0, predicted)
            # Illustrative band that widens with horizon (not calibrated)
            spread = 10.0 + h * 0.4
            steps.append(
                ForecastStep(
                    forecast_at=base_time + timedelta(hours=h),
                    predicted_aqi=predicted,
                    lower_bound=max(0.0, round(predicted - spread, 1)),
                    upper_bound=round(predicted + spread, 1),
                    aqi_category=aqi_category(predicted),
                )
            )

        return ForecastResponse(
            station_id=station_id,
            horizon_hours=horizon_hours,
            generated_at=now,
            steps=steps,
            model_metrics=_MODEL_METRICS,
            feature_importances=[],
        )


# ── Module-level singleton ─────────────────────────────────────────────────────
forecast_service = ForecastService()
