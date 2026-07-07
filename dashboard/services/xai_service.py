"""
dashboard/services/xai_service.py — Explainable AI (XAI) service interface.

Provides SHAP values, LIME explanations, and counterfactual analyses that
make the ML forecast model interpretable to domain scientists and policy makers.

Day 2: All methods return typed stub data.
Day 3: Replace stub bodies with APIClient.get() calls.

API endpoints this service will consume (Day 3+):
  GET /api/v1/xai/shap              — SHAP values for a forecast instance
  GET /api/v1/xai/lime              — LIME local explanation
  GET /api/v1/xai/counterfactual    — What-if scenarios (e.g., "if wind doubles")
  GET /api/v1/xai/global-importance — Global feature importance across the dataset
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dashboard.services.api_client import APIClient


@dataclass
class SHAPExplanation:
    """SHAP value explanation for a single AQI prediction instance."""
    prediction_id: str
    station_id: str
    predicted_aqi: float
    base_value: float                       # Model's average prediction
    shap_values: dict[str, float]           # Feature → SHAP value mapping
    feature_values: dict[str, float]        # Feature → actual input value


@dataclass
class CounterfactualScenario:
    """What-if analysis scenario."""
    scenario_name: str
    description: str
    changed_features: dict[str, float]     # Feature → new value
    original_aqi: float
    counterfactual_aqi: float
    aqi_change: float


class XAIService:
    """Fetches XAI explanations for ML forecast predictions."""

    def __init__(self, client: APIClient | None = None) -> None:
        self._client = client or APIClient()

    def get_shap_values(
        self,
        prediction_id: str,
    ) -> SHAPExplanation | None:
        """
        Return SHAP explanation for a specific forecast instance.

        Day 2: Returns stub SHAP data.
        Day 3: resp = self._client.get(f"/xai/shap/{prediction_id}")
        """
        return SHAPExplanation(
            prediction_id=prediction_id,
            station_id="DL001",
            predicted_aqi=312.0,
            base_value=148.3,
            shap_values={
                "PM2.5 (t-1)":  +84.2,
                "Wind Speed":   -32.4,
                "Temperature":  +18.1,
                "NO2":          +12.7,
                "Humidity":     -10.3,
                "HCHO":         +5.4,
            },
            feature_values={
                "PM2.5 (t-1)":  89.2,
                "Wind Speed":    2.1,
                "Temperature":  31.4,
                "NO2":          62.1,
                "Humidity":     68.0,
                "HCHO":         12.4,
            },
        )

    def get_counterfactuals(self, station_id: str) -> list[CounterfactualScenario]:
        """
        Return what-if scenarios showing how AQI would change under different conditions.

        Day 2: Returns 3 stub scenarios.
        Day 3: resp = self._client.get(f"/xai/counterfactual", params={"station_id": station_id})
        """
        return [
            CounterfactualScenario(
                "Wind Doubles",
                "If wind speed doubles from 2.1 to 4.2 m/s",
                {"Wind Speed": 4.2},
                312.0, 241.0, -71.0,
            ),
            CounterfactualScenario(
                "Rain Event",
                "If 10mm of rainfall occurs (washout effect)",
                {"Humidity": 95.0, "PM2.5 (t-1)": 45.0},
                312.0, 168.0, -144.0,
            ),
            CounterfactualScenario(
                "Industrial Shutdown",
                "If NO2 drops 50% due to industrial closure",
                {"NO2": 31.0, "HCHO": 6.0},
                312.0, 285.0, -27.0,
            ),
        ]

    def get_global_importance(self) -> list[dict[str, Any]]:
        """
        Return global feature importances averaged across all predictions.

        Day 2: Returns stub global importance.
        Day 3: resp = self._client.get("/xai/global-importance")
        """
        return [
            {"feature": "PM2.5 (t-1)", "mean_abs_shap": 42.1, "rank": 1},
            {"feature": "Wind Speed",   "mean_abs_shap": 28.7, "rank": 2},
            {"feature": "Temperature",  "mean_abs_shap": 21.4, "rank": 3},
            {"feature": "NO2",          "mean_abs_shap": 18.2, "rank": 4},
            {"feature": "Humidity",     "mean_abs_shap": 14.9, "rank": 5},
            {"feature": "HCHO",         "mean_abs_shap": 11.3, "rank": 6},
        ]


xai_service = XAIService()
