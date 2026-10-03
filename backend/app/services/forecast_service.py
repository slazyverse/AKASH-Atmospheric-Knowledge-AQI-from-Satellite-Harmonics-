"""
backend/app/services/forecast_service.py — AQI Forecast data service.

Architecture: ForecastService delegates step generation to a `Forecaster`.
Today the only implementation is SimulatedBaselineForecaster (kind
"simulated"); a genuine forecasting model plugs in as another Forecaster
(kind "model") without changing the service, API contract or dashboard.

Current state: NO forecasting model exists. Every forecast is a SIMULATED
baseline — a deterministic diurnal curve seeded from the station's latest AQI
observation in the resolved dataset (team output or placeholder), with an
illustrative band that widens with horizon. Metrics are null and feature
importances empty; the service never reports accuracy it did not measure.

The team's LightGBM artefact (ML_MODEL_PATH) is a same-day AQI estimator, not
a forecaster, so it is deliberately NOT used here; its metadata is served by
/xai/global-importance.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Literal, Protocol

from app.core.aqi import aqi_category
from app.core.logging import get_logger
from app.schemas.forecast import (
    FeatureImportance,
    ForecastResponse,
    ForecastStep,
    ModelMetrics,
)
from app.services.aqi_service import aqi_service

logger = get_logger(__name__)

SIMULATED_MODEL_NAME = "Simulated baseline (no forecasting model)"


class Forecaster(Protocol):
    """Contract every forecaster (simulated or real model) implements."""

    kind: Literal["simulated", "model"]
    metrics: ModelMetrics
    feature_importances: list[FeatureImportance]

    def steps(
        self, baseline_aqi: float, issued_at: datetime, horizon_hours: int
    ) -> list[ForecastStep]: ...


class SimulatedBaselineForecaster:
    """Deterministic diurnal curve — a stand-in, never a prediction."""

    kind: Literal["simulated", "model"] = "simulated"
    metrics = ModelMetrics(model_name=SIMULATED_MODEL_NAME, model_version="simulated")
    feature_importances: list[FeatureImportance] = []

    def steps(
        self, baseline_aqi: float, issued_at: datetime, horizon_hours: int
    ) -> list[ForecastStep]:
        base_time = issued_at.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
        out: list[ForecastStep] = []
        for h in range(1, min(horizon_hours, 72) + 1):
            # Mild diurnal pattern: peaks in early morning, dips midday
            hour_of_day = (base_time + timedelta(hours=h)).hour
            diurnal_factor = 1.0 + 0.15 * (1 - abs(hour_of_day - 6) / 12)
            predicted = max(0.0, round(baseline_aqi * diurnal_factor - h * 0.8, 1))
            spread = 10.0 + h * 0.4  # illustrative band, not calibrated
            out.append(
                ForecastStep(
                    forecast_at=base_time + timedelta(hours=h),
                    predicted_aqi=predicted,
                    lower_bound=max(0.0, round(predicted - spread, 1)),
                    upper_bound=round(predicted + spread, 1),
                    aqi_category=aqi_category(predicted),
                )
            )
        return out


class ForecastService:
    """
    Builds forecasts for stations in the registry (the endpoint validates IDs).
    """

    def __init__(self, forecaster: Forecaster | None = None) -> None:
        self.forecaster: Forecaster = forecaster or SimulatedBaselineForecaster()

    def get_station_forecast(
        self,
        station_id: str,
        horizon_hours: int = 72,
    ) -> ForecastResponse | None:
        """
        Return a forecast for a station, or None if it has no observation to
        seed from (unknown station / no data source).
        """
        latest = aqi_service.get_latest_observation(station_id)
        if latest is None:
            return None

        now = datetime.now(tz=timezone.utc)
        logger.info(
            "Generating forecast",
            station_id=station_id,
            horizon_hours=horizon_hours,
            forecast_kind=self.forecaster.kind,
        )
        return ForecastResponse(
            station_id=station_id,
            horizon_hours=horizon_hours,
            generated_at=now,
            steps=self.forecaster.steps(float(latest.aqi), now, horizon_hours),
            model_metrics=self.forecaster.metrics,
            feature_importances=self.forecaster.feature_importances,
            forecast_kind=self.forecaster.kind,
            based_on_observation_at=latest.observed_at,
        )


# ── Module-level singleton ─────────────────────────────────────────────────────
forecast_service = ForecastService()
