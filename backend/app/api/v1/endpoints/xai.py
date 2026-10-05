"""
GET /api/v1/xai/global-importance — trained-model metrics and feature importances.

Serves the metadata of the model artefact configured via ML_MODEL_PATH with
ENABLE_ML_ENDPOINTS=true. Returns 404 when no artefact is loaded — the API
never substitutes illustrative values here.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.core.exceptions import NotFoundError
from app.data.sources import sources
from app.schemas.xai import GlobalImportanceResponse
from app.services.xai_service import XAIService, xai_service

router = APIRouter()


@router.get(
    "/xai/global-importance",
    response_model=GlobalImportanceResponse,
    summary="Trained-Model Global Feature Importance",
    description=(
        "Returns the test-set metrics and global feature importances recorded in the team's "
        "trained-model artefact (LightGBM same-day AQI estimator). Importances are LightGBM "
        "split counts normalised to shares, not SHAP values. Returns 404 until an artefact "
        "is configured (`ML_MODEL_PATH` + `ENABLE_ML_ENDPOINTS=true`)."
    ),
    tags=["xai"],
    responses={
        status.HTTP_200_OK: {"description": "Model metadata retrieved."},
        status.HTTP_404_NOT_FOUND: {"description": "No trained-model artefact is loaded."},
    },
)
async def get_global_importance(
    service: XAIService = Depends(lambda: xai_service),
) -> GlobalImportanceResponse:
    """Return the loaded model's metrics and feature importances."""
    result = service.get_global_importance()
    if result is None:
        model = sources.status("model")
        raise NotFoundError(
            message="No trained-model artefact is loaded.",
            detail={
                "reason": model.detail,
                "hint": "Set ML_MODEL_PATH to a validated artefact directory and "
                "ENABLE_ML_ENDPOINTS=true (see GET /api/v1/sources).",
            },
        )
    return result
