"""
backend/app/schemas/xai.py — response model for GET /api/v1/xai/global-importance.

Reuses ModelMetrics / FeatureImportance from the forecast schemas so the
dashboard renders both with the same components.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.forecast import FeatureImportance, ModelMetrics


class GlobalImportanceResponse(BaseModel):
    """Metrics and global feature importances of the loaded trained model."""

    model_metrics: ModelMetrics = Field(
        description="Test-set metrics reported by the model artefact."
    )
    mean_bias_error: float | None = Field(
        default=None, description="Mean bias error (prediction − observed) on the test set."
    )
    target_column: str | None = Field(default=None, description="Column the model predicts.")
    importance_method: str = Field(description="How the importances were computed.")
    feature_importances: list[FeatureImportance] = Field(
        description="Global feature importances, descending; shares sum to 1.",
    )

    model_config = {"protected_namespaces": ()}
