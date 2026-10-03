"""
Dashboard compatibility tests for the Day-5 integration contract.

Uses a fake API client — no network, no backend, no real data. Payloads mirror
the backend responses when it serves the team's outputs: nullable pollutants,
hotspots without radius / confidence / date, the XAI 404 when no model is
loaded, and /version `data_sources`.

Run from the repository root:  python -m pytest dashboard/tests
"""

from __future__ import annotations

import pytest

from dashboard.services import data_sources
from dashboard.services.api_client import APIConnectionError, APINotFoundError, APIResponse
from dashboard.services.aqi_service import SurfaceAQIService
from dashboard.services.hcho_service import HCHOService
from dashboard.services.xai_service import XAIService


class FakeClient:
    """Returns a canned payload per path, or raises the configured error."""

    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = responses

    def get(self, path: str, params: dict | None = None, timeout: float | None = None) -> APIResponse:
        result = self.responses[path]
        if isinstance(result, Exception):
            raise result
        return APIResponse(status_code=200, data=result)


READING = {
    "station_id": "STN_001", "station_name": "Test Station", "latitude": 16.5, "longitude": 80.6,
    "aqi_value": 137, "aqi_category": "Moderate", "pm25": None, "pm10": 80.0,
    "no2": None, "so2": 4.0, "co": None, "o3": 30.0, "recorded_at": "2026-07-14T00:00:00Z",
}

HOTSPOT = {
    "hotspot_id": "HS-0", "latitude": 25.6, "longitude": 85.1, "radius_km": None,
    "column_density": 18.7, "source_type": "unknown", "confidence": None, "detected_at": None,
}


class TestDataSourceLabels:
    @pytest.fixture(autouse=True)
    def _sources(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(data_sources, "get_data_sources", lambda: {
            "aqi": "dataset:analysis_ready_dataset.csv", "hcho": "hotspot_file",
            "fire": "demo", "forecast": "simulated", "model": "artifact:lightgbm_run",
        })

    def test_team_data_detection(self) -> None:
        assert data_sources.is_team_data("aqi")
        assert data_sources.is_team_data("hcho")
        assert data_sources.is_team_data("model")
        assert not data_sources.is_team_data("fire")
        assert not data_sources.is_team_data("forecast")
        assert not data_sources.is_team_data("unknown-domain")

    def test_labels(self) -> None:
        assert data_sources.source_label("aqi") == "team dataset (analysis_ready_dataset.csv)"
        assert data_sources.source_label("hcho") == "team hotspot clusters"
        assert data_sources.source_label("model") == "trained-model artefact (lightgbm_run)"
        assert data_sources.source_label("forecast") == "simulated"
        assert data_sources.source_label("fire") == "demo data"

    def test_unreachable_backend_means_demo(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(data_sources, "get_data_sources", lambda: {})
        assert data_sources.source_label("aqi") == "demo data"
        assert not data_sources.is_team_data("aqi")


class TestNullableFields:
    def test_readings_keep_missing_pollutants_as_none(self) -> None:
        service = SurfaceAQIService(FakeClient({"/aqi/daily": {"summary": {"readings": [READING]}}}))
        (reading,) = service.get_latest_readings()
        assert reading.pm25 is None and reading.no2 is None and reading.co is None
        assert reading.pm10 == 80.0

    def test_hotspots_without_radius_confidence_or_date(self) -> None:
        service = HCHOService(FakeClient({"/hcho/hotspots": {"items": [HOTSPOT]}}))
        (hotspot,) = service.get_hotspots()
        assert hotspot.radius_km is None
        assert hotspot.confidence is None
        assert hotspot.detected_at is None

    def test_no_match_is_empty_not_demo(self) -> None:
        service = HCHOService(FakeClient({"/hcho/hotspots": APINotFoundError("none", 404)}))
        assert service.get_hotspots() == []

    def test_unreachable_backend_uses_offline_demo(self) -> None:
        service = HCHOService(FakeClient({"/hcho/hotspots": APIConnectionError("down")}))
        assert len(service.get_hotspots()) > 0


class TestTrainedModelSection:
    def test_no_model_loaded_returns_none(self) -> None:
        service = XAIService(FakeClient({"/xai/global-importance": APINotFoundError("no model", 404)}))
        assert service.get_model_importance() is None

    def test_backend_down_returns_none(self) -> None:
        service = XAIService(FakeClient({"/xai/global-importance": APIConnectionError("down")}))
        assert service.get_model_importance() is None

    def test_payload_passed_through_unchanged(self) -> None:
        payload = {"model_metrics": {"r_squared": 0.4}, "feature_importances": []}
        service = XAIService(FakeClient({"/xai/global-importance": payload}))
        assert service.get_model_importance() == payload
