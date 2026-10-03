"""
backend/app/schemas/forecast.py — Pydantic v2 response models for AQI Forecast data.

Forecast output includes:
  - Per-step AQI predictions with lower / upper uncertainty bounds
  - Model performance metrics (RMSE, MAE, R²) from the model's validation run
  - Feature importances (global)

Current state: no forecasting model exists. The service returns a simulated
baseline, so metric fields are null and feature_importances is empty rather
than showing invented numbers.

Models:
  - ForecastStep         — single time step in a forecast sequence
  - ModelMetrics         — accuracy metrics from the active model version
  - FeatureImportance    — (feature_name, importance_score) pair
  - ForecastResponse     — envelope for GET /api/v1/forecast
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ForecastStep(BaseModel):
    """
    A single time step in the AQI forecast sequence.

    While the simulated baseline is active, the bounds are an illustrative
    band that widens with horizon — they are not calibrated quantiles.
    """

    forecast_at: datetime = Field(
        description="UTC timestamp this step is valid for.",
    )
    predicted_aqi: float = Field(
        ge=0,
        description="Point forecast of AQI for this step.",
    )
    lower_bound: float = Field(
        ge=0,
        description="Lower uncertainty bound (illustrative while simulated).",
    )
    upper_bound: float = Field(
        ge=0,
        description="Upper uncertainty bound (illustrative while simulated).",
    )
    aqi_category: str = Field(
        description=(
            "CPCB AQI category for the predicted value. "
            "One of: Good | Satisfactory | Moderate | Poor | Very Poor | Severe."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "forecast_at": "2026-07-08T06:00:00Z",
                "predicted_aqi": 145.0,
                "lower_bound": 118.0,
                "upper_bound": 174.0,
                "aqi_category": "Moderate",
            }
        }
    }


class ModelMetrics(BaseModel):
    """
    Validation metrics for the forecast model.

    Metric fields are null while the forecast is the simulated baseline (it has
    no validation run), so clients must handle None.
    """

    model_name: str = Field(
        description="Model name.",
        examples=["Simulated baseline (no forecasting model)"],
    )
    model_version: str = Field(description="Version of the model artefact.", examples=["stub"])
    rmse: float | None = Field(
        default=None, ge=0, description="Root Mean Squared Error in AQI units."
    )
    mae: float | None = Field(default=None, ge=0, description="Mean Absolute Error in AQI units.")
    r_squared: float | None = Field(
        default=None,
        le=1,
        description="Coefficient of determination (R²) on the validation set.",
    )
    training_date: str | None = Field(
        default=None, description="ISO date when the model was trained."
    )
    validation_period: str | None = Field(
        default=None, description="Description of the validation window."
    )

    model_config = {
        "protected_namespaces": (),
        "json_schema_extra": {
            "example": {
                "model_name": "Simulated baseline (no forecasting model)",
                "model_version": "stub",
                "rmse": None,
                "mae": None,
                "r_squared": None,
                "training_date": None,
                "validation_period": None,
            }
        }
    }


class FeatureImportance(BaseModel):
    """Feature importance score from the trained forecast model."""

    feature: str = Field(description="Feature name.", examples=["PM2.5 (t-1)"])
    importance: float = Field(
        ge=0.0,
        le=1.0,
        description="Normalised importance score (sum across all features = 1.0).",
    )

    model_config = {
        "json_schema_extra": {
            "example": {"feature": "PM2.5 (t-1)", "importance": 0.34}
        }
    }


class ForecastResponse(BaseModel):
    """
    Envelope for GET /api/v1/forecast.

    Returns the full forecast sequence plus model metadata so the dashboard
    can render both the time series chart and the model performance panel
    in a single request.
    """

    station_id: str = Field(description="CPCB station identifier this forecast is for.")
    horizon_hours: int = Field(ge=1, description="Forecast horizon in hours.")
    generated_at: datetime = Field(description="UTC timestamp when this forecast was generated.")
    steps: list[ForecastStep] = Field(description="Ordered forecast steps (oldest → newest).")
    model_metrics: ModelMetrics = Field(description="Active model's validation performance metrics.")
    feature_importances: list[FeatureImportance] = Field(
        description="Top feature importances driving this model's predictions.",
    )

    model_config = {
        "protected_namespaces": (),
        "json_schema_extra": {
            "example": {
                "station_id": "DL001",
                "horizon_hours": 72,
                "generated_at": "2026-07-07T12:00:00Z",
                "steps": [],
                "model_metrics": {
                    "model_name": "Simulated baseline (no forecasting model)",
                    "model_version": "stub",
                    "rmse": None,
                    "mae": None,
                    "r_squared": None,
                    "training_date": None,
                    "validation_period": None,
                },
                "feature_importances": [],
            }
        }
    }
