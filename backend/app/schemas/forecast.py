"""
backend/app/schemas/forecast.py — Pydantic v2 response models for AQI Forecast data.

The VAYU-DRISHTI ML pipeline produces multi-step ahead AQI forecasts using
an XGBoost ensemble trained on CPCB sensor readings, meteorological data
(MERRA-2), and satellite HCHO/fire inputs.

Forecast output includes:
  - Per-step AQI predictions with 5th/95th percentile confidence intervals
  - Model performance metrics (RMSE, MAE, R²) from the last validation run
  - Feature importances (global, across all training predictions)

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

    Confidence intervals are calibrated quantiles from the XGBoost
    quantile regression variant, not ± stddev — they are asymmetric
    when the predicted distribution is skewed (e.g., severe episodes).
    """

    forecast_at: datetime = Field(
        description="UTC timestamp this step is valid for.",
    )
    predicted_aqi: float = Field(
        ge=0,
        description="Point forecast — the 50th percentile (median) AQI prediction.",
    )
    lower_bound: float = Field(
        ge=0,
        description="5th percentile (lower) confidence bound.",
    )
    upper_bound: float = Field(
        ge=0,
        description="95th percentile (upper) confidence bound.",
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
    Validation metrics for the currently deployed forecast model.

    Metrics are computed on a held-out validation set (last 30 days)
    using hourly AQI readings across all active stations.
    """

    model_name: str = Field(description="Model architecture name.", examples=["VAYU-DRISHTI XGBoost v1"])
    model_version: str = Field(description="Semantic version of the model artefact.", examples=["1.0.0"])
    rmse: float = Field(ge=0, description="Root Mean Squared Error in AQI units.")
    mae: float  = Field(ge=0, description="Mean Absolute Error in AQI units.")
    r_squared: float = Field(
        ge=-1,
        le=1,
        description="Coefficient of determination (R²). 1.0 = perfect fit.",
    )
    training_date: str = Field(description="ISO date when the model was last retrained.")
    validation_period: str = Field(description="Human-readable description of the validation window.")

    model_config = {
        "protected_namespaces": (),
        "json_schema_extra": {
            "example": {
                "model_name": "VAYU-DRISHTI XGBoost v1",
                "model_version": "1.0.0",
                "rmse": 18.4,
                "mae": 12.7,
                "r_squared": 0.84,
                "training_date": "2026-06-01",
                "validation_period": "2026-06-01 to 2026-06-30",
            }
        }
    }


class FeatureImportance(BaseModel):
    """Feature importance score from the XGBoost model."""

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
                    "model_name": "VAYU-DRISHTI XGBoost v1",
                    "model_version": "1.0.0",
                    "rmse": 18.4,
                    "mae": 12.7,
                    "r_squared": 0.84,
                    "training_date": "2026-06-01",
                    "validation_period": "2026-06-01 to 2026-06-30",
                },
                "feature_importances": [],
            }
        }
    }
