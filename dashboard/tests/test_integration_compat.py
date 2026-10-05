"""
Dashboard data-layer tests against the backend contracts.

Uses a fake API client — no network, no backend, no real data. Payloads mirror
the backend responses: /sources status, nullable pollutants, observed history,
hotspots without radius / confidence / date, the HCHO trend, FRP-rule fire
alerts with a null impact score, and the XAI 404 when no model is loaded.

Run from the repository root:  python -m pytest dashboard/tests
"""

from __future__ import annotations

from datetime import date

import pytest

from dashboard.services import data_sources
from dashboard.services.api_client import APIConnectionError, APINotFoundError, APIResponse
from dashboard.services.aqi_service import SurfaceAQIService
from dashboard.services.fire_service import FireMonitoringService
from dashboard.services.hcho_service import HCHOService
from dashboard.services.xai_service import XAIService


class FakeClient:
    """Returns a canned payload per path, or raises the configured error."""

    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = responses
        self.calls: list[tuple[str, dict | None]] = []

    def get(self, path: str, params: dict | None = None, timeout: float | None = None) -> APIResponse:
        self.calls.append((path, params))
        result = self.responses[path]
        if isinstance(result, Exception):
            raise result
        return APIResponse(status_code=200, data=result)


READING = {
    "station_id": "CH001", "station_name": "Chennai – Alandur", "latitude": 13.0, "longitude": 80.2,
    "aqi_value": 94, "aqi_category": "Satisfactory", "pm25": 24.6, "pm10": 53.1,
    "no2": None, "so2": None, "co": 1.0, "o3": 22.1, "recorded_at": "2026-07-14T00:00:00Z",
}
HOTSPOT = {
    "hotspot_id": "HS-0", "latitude": 28.6, "longitude": 77.3, "radius_km": None,
    "column_density": 15.658, "source_type": "unknown", "confidence": None, "detected_at": None,
}
FIRE_PAYLOAD = {
    "total_events": 1, "total_alerts": 1, "hours_window": 24, "as_of": "2026-07-14T06:00:00Z",
    "events": [{
        "event_id": "PH-FIRE-003", "latitude": 27.9, "longitude": 95.4, "frp": 210.1,
        "brightness": 341.2, "satellite": "VIIRS-NOAA20", "confidence": "high",
        "land_cover": "forest", "state": "Arunachal Pradesh", "district": "Lohit",
        "detected_at": "2026-07-13T23:00:00Z",
    }],
    "alerts": [{
        "alert_id": "ALERT-PH-FIRE-003", "fire_event_id": "PH-FIRE-003", "severity": "critical",
        "aqi_impact_score": None, "message": "VIIRS-NOAA20 detection with FRP 210 MW in Lohit.",
        "issued_at": "2026-07-13T23:00:00Z",
    }],
}
SOURCES = {
    "aqi": {"domain": "aqi", "kind": "placeholder", "name": "placeholder_station_dataset.csv",
            "detail": "Deterministic placeholder fixture — not real data.", "records": 56,
            "as_of": "2026-07-14"},
    "hcho": {"domain": "hcho", "kind": "local", "name": "cluster_summary.json",
             "detail": "Team output.", "records": 4, "as_of": None},
    "forecast": {"domain": "forecast", "kind": "simulated", "name": "simulated-baseline",
                 "detail": "No forecasting model.", "records": None, "as_of": None},
    "model": {"domain": "model", "kind": "unavailable", "name": "none",
              "detail": "No trained-model artefact.", "records": None, "as_of": None},
}


class TestSourceStatus:
    @pytest.fixture(autouse=True)
    def _sources(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(data_sources, "get_sources", lambda: SOURCES)

    def test_kinds(self) -> None:
        assert data_sources.source_kind("aqi") == "placeholder"
        assert data_sources.source_kind("hcho") == "local"
        assert data_sources.source_kind("forecast") == "simulated"
        assert data_sources.source_kind("model") == "unavailable"

    def test_team_data_only_for_real_kinds(self) -> None:
        assert data_sources.is_team_data("hcho")
        assert not data_sources.is_team_data("aqi")        # placeholder is not real data
        assert not data_sources.is_team_data("forecast")
        assert not data_sources.is_team_data("unreported-domain")

    def test_labels(self) -> None:
        assert data_sources.source_label("aqi") == "PLACEHOLDER (placeholder_station_dataset.csv)"
        assert data_sources.source_label("hcho") == "LOCAL (cluster_summary.json)"
        assert data_sources.source_label("forecast") == "SIMULATED"
        assert data_sources.source_label("model") == "UNAVAILABLE"

    def test_backend_unreachable_means_unavailable(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setattr(data_sources, "get_sources", lambda: {})
        status_ = data_sources.get_source("aqi")
        assert status_["kind"] == "unavailable"
        assert "unreachable" in status_["detail"].lower()


class TestAQIService:
    def test_nullable_pollutants_preserved(self) -> None:
        service = SurfaceAQIService(FakeClient({"/aqi/daily": {"summary": {"readings": [READING]}}}))
        (reading,) = service.get_latest_readings()
        assert reading.no2 is None and reading.so2 is None
        assert reading.pm25 == 24.6

    def test_history_is_observed_points_in_order(self) -> None:
        points = [dict(READING, recorded_at=f"2026-07-{d}T00:00:00Z", aqi_value=90 + d) for d in (12, 13, 14)]
        client = FakeClient({"/aqi/history": {"station_id": "CH001", "count": 3, "points": points}})
        history = SurfaceAQIService(client).get_time_series("CH001", days=3)
        assert [h.aqi_value for h in history] == [102, 103, 104]
        assert client.calls == [("/aqi/history", {"station_id": "CH001", "days": 3})]

    @pytest.mark.parametrize("error", [APIConnectionError("down"), APINotFoundError("none", 404)])
    def test_no_hardcoded_fallback(self, error: Exception) -> None:
        service = SurfaceAQIService(FakeClient({"/aqi/daily": error, "/aqi/history": error}))
        assert service.get_latest_readings() == []
        assert service.get_time_series("CH001") == []
        summary = service.get_regional_summary()
        assert summary.station_count == 0 and summary.date_to is None

    def test_summary_carries_source_date(self) -> None:
        payload = {"summary": {"region": "India", "summary_date": "2026-07-14", "station_count": 8,
                               "avg_aqi": 137.2, "max_aqi": 312, "min_aqi": 51,
                               "dominant_pollutant": "N/A"}}
        summary = SurfaceAQIService(FakeClient({"/aqi/daily": payload})).get_regional_summary()
        assert summary.date_to == date(2026, 7, 14) and summary.station_count == 8


class TestHCHOService:
    def test_hotspots_without_radius_confidence_or_date(self) -> None:
        (hotspot,) = HCHOService(FakeClient({"/hcho/hotspots": {"items": [HOTSPOT]}})).get_hotspots()
        assert hotspot.radius_km is None and hotspot.confidence is None and hotspot.detected_at is None

    def test_trend_points(self) -> None:
        payload = {"unit": "1e15 molecules/cm2", "count": 1,
                   "points": [{"obs_date": "2026-07-14", "mean_column_density": 9.4, "station_count": 8}]}
        (point,) = HCHOService(FakeClient({"/hcho/trend": payload})).get_trend(days=7)
        assert point.obs_date == date(2026, 7, 14) and point.station_count == 8

    @pytest.mark.parametrize("error", [APIConnectionError("down"), APINotFoundError("none", 404)])
    def test_no_hardcoded_fallback(self, error: Exception) -> None:
        service = HCHOService(FakeClient({"/hcho/hotspots": error, "/hcho/trend": error}))
        assert service.get_hotspots() == [] and service.get_trend() == []


class TestFireService:
    def test_rule_alert_has_no_impact_score(self) -> None:
        service = FireMonitoringService(FakeClient({"/fire": FIRE_PAYLOAD}))
        (alert,) = service.get_active_alerts()
        assert alert.severity == "critical" and alert.aqi_impact_score is None
        (event,) = service.get_active_fires(region="Northeast")
        assert event.event_id == "PH-FIRE-003"

    def test_no_hardcoded_fallback(self) -> None:
        service = FireMonitoringService(FakeClient({"/fire": APIConnectionError("down")}))
        assert service.get_active_fires() == [] and service.get_active_alerts() == []


class TestXAIService:
    @pytest.mark.parametrize("error", [APINotFoundError("no model", 404), APIConnectionError("down")])
    def test_unavailable_returns_none(self, error: Exception) -> None:
        assert XAIService(FakeClient({"/xai/global-importance": error})).get_model_importance() is None

    def test_payload_passed_through_unchanged(self) -> None:
        payload = {"model_metrics": {"r_squared": 0.4}, "feature_importances": []}
        service = XAIService(FakeClient({"/xai/global-importance": payload}))
        assert service.get_model_importance() == payload

    def test_no_illustrative_explanations_offered(self) -> None:
        for name in ("get_shap_values", "get_counterfactuals", "get_global_importance"):
            assert not hasattr(XAIService, name)
