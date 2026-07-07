"""
backend/app/services/forecast_service.py — AQI Forecast data service.

Business logic for ML model AQI forecast retrieval.
The VAYU-DRISHTI XGBoost ensemble produces 72-hour ahead predictions
with calibrated confidence intervals (5th / 95th percentile quantiles).

Day 3: Returns realistic in-memory stub forecasts with plausible sequences.
Day 4: Replace with actual ML model inference pipeline.
Day N: Add real-time retraining triggers and model registry integration.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.core.logging import get_logger
from app.schemas.forecast import (
    FeatureImportance,
    ForecastResponse,
    ForecastStep,
    ModelMetrics,
)

logger = get_logger(__name__)

# ── Model metadata stub ────────────────────────────────────────────────────────

_MODEL_METRICS = ModelMetrics(
    model_name="VAYU-DRISHTI XGBoost v1",
    model_version="1.0.0",
    rmse=18.4,
    mae=12.7,
    r_squared=0.84,
    training_date="2026-06-01",
    validation_period="2026-06-01 to 2026-06-30",
)

_FEATURE_IMPORTANCES = [
    FeatureImportance(feature="PM2.5 (t-1)",  importance=0.34),
    FeatureImportance(feature="Wind Speed",    importance=0.18),
    FeatureImportance(feature="Temperature",   importance=0.15),
    FeatureImportance(feature="NO2",           importance=0.12),
    FeatureImportance(feature="Humidity",      importance=0.11),
    FeatureImportance(feature="HCHO",          importance=0.10),
]

# AQI category lookup for the CPCB scale
def _aqi_category(aqi: float) -> str:
    if aqi <= 50:
        return "Good"
    if aqi <= 100:
        return "Satisfactory"
    if aqi <= 200:
        return "Moderate"
    if aqi <= 300:
        return "Poor"
    if aqi <= 400:
        return "Very Poor"
    return "Severe"


class ForecastService:
    """
    Service class for AQI forecast data retrieval and construction.

    In Day 3, this service generates a realistic pseudo-forecast sequence
    based on the station's baseline AQI. Day 4 will replace with model calls.
    """

    # Station baseline AQI used to seed the pseudo-forecast
    _STATION_BASELINES: dict[str, float] = {
        "DL001": 312.0,
        "MU001": 127.0,
        "BL001": 88.0,
        "HY001": 51.0,
        "CH001": 94.0,
        "KO001": 198.0,
        "PU001": 76.0,
        "AH001": 152.0,
    }

    def get_station_forecast(
        self,
        station_id: str,
        horizon_hours: int = 72,
    ) -> ForecastResponse:
        """
        Return multi-step AQI forecast for a monitoring station.

        Args:
            station_id:    CPCB station identifier.
            horizon_hours: Forecast horizon (1–72 hours).

        Returns:
            ForecastResponse with ordered forecast steps and model metadata.
        """
        logger.info(
            "Generating AQI forecast",
            station_id=station_id,
            horizon_hours=horizon_hours,
        )

        now = datetime.now(tz=timezone.utc)
        # Round to nearest hour for clean timestamps
        base_time = now.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)

        baseline = self._STATION_BASELINES.get(station_id, 150.0)

        steps: list[ForecastStep] = []
        for h in range(1, min(horizon_hours, 72) + 1):
            # Simulate a mild diurnal pattern: peaks in early morning, dips midday
            hour_of_day = (base_time + timedelta(hours=h)).hour
            diurnal_factor = 1.0 + 0.15 * (1 - abs(hour_of_day - 6) / 12)
            predicted = round(baseline * diurnal_factor - h * 0.8, 1)
            predicted = max(0.0, predicted)
            # Confidence interval widens with horizon
            spread = 10.0 + h * 0.4
            steps.append(
                ForecastStep(
                    forecast_at=base_time + timedelta(hours=h),
                    predicted_aqi=predicted,
                    lower_bound=max(0.0, round(predicted - spread, 1)),
                    upper_bound=round(predicted + spread, 1),
                    aqi_category=_aqi_category(predicted),
                )
            )

        return ForecastResponse(
            station_id=station_id,
            horizon_hours=horizon_hours,
            generated_at=now,
            steps=steps,
            model_metrics=_MODEL_METRICS,
            feature_importances=_FEATURE_IMPORTANCES,
        )


# ── Module-level singleton ─────────────────────────────────────────────────────
forecast_service = ForecastService()
