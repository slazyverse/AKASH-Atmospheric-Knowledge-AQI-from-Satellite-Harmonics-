"""
backend/app/services/xai_service.py — model explanation data service.

Serves the metadata of the trained-model artefact loaded from ML_MODEL_PATH
(see app.data.model_artifact): test-set metrics and global feature
importances. Nothing is computed or estimated here; without a loaded artefact
the service returns None and the endpoint answers 404.

Per-prediction SHAP values are not served: no SHAP output exists for the
team's LightGBM model yet.
"""

from __future__ import annotations

from app.data.sources import sources
from app.schemas.forecast import FeatureImportance, ModelMetrics
from app.schemas.xai import GlobalImportanceResponse

IMPORTANCE_METHOD = (
    "LightGBM built-in feature_importances_ (split counts) from the model artefact, "
    "normalised to shares summing to 1 — not SHAP values."
)


class XAIService:
    def get_global_importance(self) -> GlobalImportanceResponse | None:
        """Return the loaded model's metrics and importances, or None if no model is loaded."""
        model = sources.model
        if model is None:
            return None
        test_n = model.test_samples
        return GlobalImportanceResponse(
            model_metrics=ModelMetrics(
                model_name=model.model_name,
                model_version=model.model_version,
                rmse=model.metrics["RMSE"],
                mae=model.metrics["MAE"],
                r_squared=model.metrics["R2"],
                training_date=None,  # not recorded in the artefact
                validation_period=f"Held-out test split ({test_n} rows)" if test_n else None,
            ),
            mean_bias_error=model.metrics.get("MBE"),
            target_column=model.target_column,
            importance_method=IMPORTANCE_METHOD,
            feature_importances=[
                FeatureImportance(feature=name, importance=round(share, 6))
                for name, share in model.feature_importances
            ],
        )


xai_service = XAIService()
