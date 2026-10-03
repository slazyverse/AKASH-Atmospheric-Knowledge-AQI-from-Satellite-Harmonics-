"""
dashboard/services/forecast_service.py - AQI Forecast service interface.

Fetches forecasts, model metadata and the station list from the backend.

The backend currently returns a SIMULATED baseline (no forecasting model
exists), with null metrics and no feature importances. This module passes
that through faithfully: it never substitutes its own forecast or metrics, so
when the backend is unreachable the page shows an "unavailable" state instead.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

import streamlit as st

from dashboard.services.api_client import APIClient, APIError


@dataclass
class ForecastStep:
    """A single time step in an AQI forecast sequence."""
    forecast_at: datetime
    predicted_aqi: float
    lower_bound: float
    upper_bound: float
    aqi_category: str


@dataclass
class ModelMetrics:
    """Validation metrics for the forecast model (None = not available)."""
    model_name: str
    model_version: str
    rmse: float | None
    mae: float | None
    r_squared: float | None
    training_date: str | None
    validation_period: str | None


@st.cache_data(ttl=60)
def _get_forecast_payload_cached(station_id: str, horizon_hours: int) -> dict[str, Any]:
    """One GET /forecast per (station, horizon), cached for 60 seconds; {} on error."""
    try:
        resp = APIClient().get(
            "/forecast",
            params={"station_id": station_id, "horizon_hours": horizon_hours},
        )
        return resp.data or {}
    except APIError:
        return {}


@st.cache_data(ttl=300)
def _get_stations_cached() -> list[dict[str, str]]:
    """Station registry from GET /stations, cached for 5 minutes; [] on error."""
    try:
        resp = APIClient().get("/stations", params={"limit": 1000})
        return [
            {"station_id": s["station_id"], "station_name": s["station_name"]}
            for s in resp.data.get("items", [])
        ]
    except (APIError, KeyError, TypeError):
        return []


class ForecastService:
    """Fetches AQI forecast data, model metadata and forecastable stations."""

    def __init__(self, client: APIClient | None = None) -> None:
        self._client = client or APIClient()

    def get_stations(self) -> list[dict[str, str]]:
        """Return [{station_id, station_name}] for every forecastable station."""
        return _get_stations_cached()

    def get_station_forecast(
        self,
        station_id: str,
        horizon_hours: int = 72,
    ) -> list[ForecastStep]:
        """Return forecast steps for a station, or [] if unavailable."""
        raw_steps = _get_forecast_payload_cached(station_id, horizon_hours).get("steps", [])
        try:
            return [
                ForecastStep(
                    forecast_at=datetime.fromisoformat(step["forecast_at"].replace("Z", "+00:00")),
                    predicted_aqi=step["predicted_aqi"],
                    lower_bound=step["lower_bound"],
                    upper_bound=step["upper_bound"],
                    aqi_category=step["aqi_category"],
                )
                for step in raw_steps
            ]
        except (KeyError, TypeError, ValueError):
            return []

    def get_model_metrics(self, station_id: str, horizon_hours: int = 72) -> ModelMetrics | None:
        """Return the forecast model's metadata, or None if the backend is unreachable."""
        m = _get_forecast_payload_cached(station_id, horizon_hours).get("model_metrics")
        if not m:
            return None
        return ModelMetrics(
            model_name=m.get("model_name", "Unknown"),
            model_version=m.get("model_version", "Unknown"),
            rmse=m.get("rmse"),
            mae=m.get("mae"),
            r_squared=m.get("r_squared"),
            training_date=m.get("training_date"),
            validation_period=m.get("validation_period"),
        )

    def get_feature_importances(self, station_id: str, horizon_hours: int = 72) -> list[dict[str, Any]]:
        """Return the model's feature importances ([] when none are available)."""
        features = _get_forecast_payload_cached(station_id, horizon_hours).get("feature_importances", [])
        return [
            {"feature": f["feature"], "importance": f["importance"]}
            for f in features
            if "feature" in f and "importance" in f
        ]


forecast_service = ForecastService()
