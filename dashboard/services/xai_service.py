"""
dashboard/services/xai_service.py — model explanation service interface.

Serves only what the backend can genuinely provide: the trained model's
test-set metrics and global feature importances (GET /api/v1/xai/global-importance).
Per-prediction SHAP and counterfactuals do not exist for the team model yet, so
this service offers no such methods — the page reports them as unavailable.
"""

from __future__ import annotations

from typing import Any

from dashboard.services.api_client import APIClient, APIError


class XAIService:
    """Fetches trained-model explanation data from the backend."""

    def __init__(self, client: APIClient | None = None) -> None:
        self._client = client or APIClient()

    def get_model_importance(self) -> dict[str, Any] | None:
        """
        Trained-model metrics + global importances from GET /xai/global-importance.

        Returns None when the backend has no model artefact loaded (404) or is
        unreachable — never substitutes illustrative values.
        """
        try:
            return self._client.get("/xai/global-importance").data
        except APIError:
            return None


xai_service = XAIService()
