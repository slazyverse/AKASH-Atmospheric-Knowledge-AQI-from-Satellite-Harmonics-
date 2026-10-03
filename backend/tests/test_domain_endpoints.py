"""
Tests for the domain endpoints (AQI, HCHO, Fire, Forecast, Stations).

These cover the correctness fixes made before Day-5 integration:
  - CPCB AQI categories derived from values (single source: app.core.aqi)
  - /stations and /forecast share one station registry
  - region / date / hours filters are applied, not ignored
  - malformed dates return 422, valid dates without data return 404
  - the forecast never reports model metrics it did not measure

The endpoints serve static demo data, so assertions check behaviour against
that data rather than specific "real" values. No database is required.
"""

from __future__ import annotations

import pytest
from fastapi import status
from httpx import AsyncClient

from app.core.aqi import aqi_category
from app.core.regions import region_matches

pytestmark = pytest.mark.unit


# ── AQI category logic ─────────────────────────────────────────────────────────

class TestAQICategory:
    @pytest.mark.parametrize(
        ("aqi", "expected"),
        [
            (0, "Good"), (50, "Good"),
            (51, "Satisfactory"), (100, "Satisfactory"),
            (101, "Moderate"), (200, "Moderate"),
            (201, "Poor"), (300, "Poor"),
            (301, "Very Poor"), (400, "Very Poor"),
            (401, "Severe"), (500, "Severe"),
            (50.4, "Satisfactory"),
        ],
    )
    def test_cpcb_band_boundaries(self, aqi: float, expected: str) -> None:
        assert aqi_category(aqi) == expected


class TestRegionMatching:
    @pytest.mark.parametrize(
        ("region", "state", "city", "expected"),
        [
            ("India", "Kerala", "", True),
            ("All India", "Assam", "", True),
            ("North India", "Delhi", "Delhi", True),
            ("North", "Karnataka", "", False),
            ("Northeast", "Arunachal Pradesh", "", True),
            ("North-East India", "Assam", "", True),
            ("Maharashtra", "Maharashtra", "Pune", True),
            ("pune", "Maharashtra", "Pune", True),
            ("Mars", "Delhi", "Delhi", False),
        ],
    )
    def test_region_matches(self, region: str, state: str, city: str, expected: bool) -> None:
        assert region_matches(region, state, city) is expected


# ── GET /api/v1/aqi/daily ──────────────────────────────────────────────────────

class TestAQIDaily:
    async def test_every_reading_category_matches_its_value(
        self, client_no_db: AsyncClient
    ) -> None:
        readings = (await client_no_db.get("/api/v1/aqi/daily")).json()["summary"]["readings"]
        assert readings
        for r in readings:
            assert r["aqi_category"] == aqi_category(r["aqi_value"]), r["station_id"]

    async def test_station_count_reflects_matched_stations(self, client_no_db: AsyncClient) -> None:
        summary = (await client_no_db.get("/api/v1/aqi/daily")).json()["summary"]
        assert summary["station_count"] == len(summary["readings"])

    async def test_limit_caps_readings_but_not_summary(self, client_no_db: AsyncClient) -> None:
        full = (await client_no_db.get("/api/v1/aqi/daily")).json()
        capped = (await client_no_db.get("/api/v1/aqi/daily", params={"limit": 2})).json()
        assert capped["count"] == 2
        assert len(capped["summary"]["readings"]) == 2
        assert capped["summary"]["station_count"] == full["summary"]["station_count"]
        assert capped["summary"]["avg_aqi"] == full["summary"]["avg_aqi"]

    async def test_region_zone_filters_by_station_state(self, client_no_db: AsyncClient) -> None:
        stations = (await client_no_db.get("/api/v1/stations")).json()["items"]
        state_of = {s["station_id"]: s["state"] for s in stations}
        resp = await client_no_db.get("/api/v1/aqi/daily", params={"region": "South India"})
        assert resp.status_code == status.HTTP_200_OK
        readings = resp.json()["summary"]["readings"]
        assert readings
        for r in readings:
            assert region_matches("South India", state_of[r["station_id"]])

    async def test_region_state_filter(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get("/api/v1/aqi/daily", params={"region": "Delhi"})
        ids = {r["station_id"] for r in resp.json()["summary"]["readings"]}
        assert ids == {"DL001"}

    async def test_unknown_region_returns_404(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get("/api/v1/aqi/daily", params={"region": "Mars"})
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    async def test_date_without_data_returns_404(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get("/api/v1/aqi/daily", params={"date": "2020-01-01"})
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    async def test_today_returns_data(self, client_no_db: AsyncClient) -> None:
        today = (await client_no_db.get("/api/v1/aqi/daily")).json()["summary"]["summary_date"]
        resp = await client_no_db.get("/api/v1/aqi/daily", params={"date": today})
        assert resp.status_code == status.HTTP_200_OK

    @pytest.mark.parametrize("bad_date", ["2026-13-45", "2026-02-30"])
    async def test_impossible_date_returns_422(
        self, client_no_db: AsyncClient, bad_date: str
    ) -> None:
        resp = await client_no_db.get("/api/v1/aqi/daily", params={"date": bad_date})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert resp.json()["error"]["code"] == "VALIDATION_ERROR"

    async def test_non_iso_date_returns_422(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get("/api/v1/aqi/daily", params={"date": "03/10/2026"})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ── /stations ↔ /forecast consistency ─────────────────────────────────────────

class TestStationForecastConsistency:
    async def test_every_listed_station_has_a_forecast(self, client_no_db: AsyncClient) -> None:
        stations = (await client_no_db.get("/api/v1/stations")).json()["items"]
        assert stations
        for s in stations:
            resp = await client_no_db.get(
                "/api/v1/forecast", params={"station_id": s["station_id"], "horizon_hours": 1}
            )
            assert resp.status_code == status.HTTP_200_OK, s["station_id"]

    async def test_dl002_forecast_is_available(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get("/api/v1/forecast", params={"station_id": "DL002"})
        assert resp.status_code == status.HTTP_200_OK

    async def test_unknown_station_returns_404(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get("/api/v1/forecast", params={"station_id": "XX999"})
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    async def test_missing_station_id_returns_422(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get("/api/v1/forecast")
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ── GET /api/v1/forecast ───────────────────────────────────────────────────────

class TestForecast:
    async def test_steps_match_horizon_and_categories(self, client_no_db: AsyncClient) -> None:
        data = (await client_no_db.get(
            "/api/v1/forecast", params={"station_id": "DL001", "horizon_hours": 24}
        )).json()
        assert len(data["steps"]) == 24
        for step in data["steps"]:
            assert step["lower_bound"] <= step["predicted_aqi"] <= step["upper_bound"]
            assert step["aqi_category"] == aqi_category(step["predicted_aqi"])

    async def test_no_fabricated_model_metrics(self, client_no_db: AsyncClient) -> None:
        data = (await client_no_db.get("/api/v1/forecast", params={"station_id": "DL001"})).json()
        metrics = data["model_metrics"]
        assert "Simulated" in metrics["model_name"]
        for field in ("rmse", "mae", "r_squared", "training_date", "validation_period"):
            assert metrics[field] is None, field
        assert data["feature_importances"] == []

    async def test_horizon_above_72_rejected(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get(
            "/api/v1/forecast", params={"station_id": "DL001", "horizon_hours": 73}
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ── GET /api/v1/hcho/hotspots ──────────────────────────────────────────────────

class TestHCHOHotspots:
    URL = "/api/v1/hcho/hotspots"

    async def test_min_confidence_filter(self, client_no_db: AsyncClient) -> None:
        data = (await client_no_db.get(self.URL, params={"min_confidence": 0.9})).json()
        assert data["count"] == len(data["items"]) > 0
        assert all(item["confidence"] >= 0.9 for item in data["items"])

    async def test_lower_threshold_returns_superset(self, client_no_db: AsyncClient) -> None:
        strict = (await client_no_db.get(self.URL, params={"min_confidence": 0.9})).json()
        loose = (await client_no_db.get(self.URL, params={"min_confidence": 0.0})).json()
        strict_ids = {i["hotspot_id"] for i in strict["items"]}
        assert strict_ids <= {i["hotspot_id"] for i in loose["items"]}
        assert loose["count"] >= strict["count"]

    async def test_date_without_data_returns_404(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get("/api/v1/hcho/hotspots", params={"date": "2020-01-01"})
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    async def test_impossible_date_returns_422(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get("/api/v1/hcho/hotspots", params={"date": "2026-02-30"})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_confidence_out_of_range_returns_422(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get("/api/v1/hcho/hotspots", params={"min_confidence": 1.5})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ── GET /api/v1/fire ───────────────────────────────────────────────────────────

class TestFire:
    async def test_default_returns_events_and_alerts(self, client_no_db: AsyncClient) -> None:
        data = (await client_no_db.get("/api/v1/fire")).json()
        assert data["total_events"] == len(data["events"]) > 0
        assert data["total_alerts"] == len(data["alerts"])

    async def test_region_state_filter(self, client_no_db: AsyncClient) -> None:
        data = (await client_no_db.get("/api/v1/fire", params={"region": "Karnataka"})).json()
        assert data["events"]
        assert all(e["state"] == "Karnataka" for e in data["events"])

    async def test_region_zone_filter(self, client_no_db: AsyncClient) -> None:
        data = (await client_no_db.get("/api/v1/fire", params={"region": "Northeast"})).json()
        assert data["events"]
        assert all(region_matches("Northeast", e["state"]) for e in data["events"])

    async def test_region_without_events_is_empty_200(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get("/api/v1/fire", params={"region": "Kerala"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["events"] == []
        assert resp.json()["alerts"] == []

    async def test_hours_window_filters_by_detection_time(self, client_no_db: AsyncClient) -> None:
        week = await client_no_db.get("/api/v1/fire", params={"hours": 168})
        all_events = week.json()["events"]
        recent = (await client_no_db.get("/api/v1/fire", params={"hours": 6})).json()["events"]
        assert 0 < len(recent) < len(all_events)
        assert {e["event_id"] for e in recent} <= {e["event_id"] for e in all_events}

    async def test_min_frp_filter(self, client_no_db: AsyncClient) -> None:
        data = (await client_no_db.get("/api/v1/fire", params={"min_frp": 100})).json()
        assert data["events"]
        assert all(e["frp"] >= 100 for e in data["events"])
        empty = (await client_no_db.get("/api/v1/fire", params={"min_frp": 5000})).json()
        assert empty["events"] == [] and empty["alerts"] == []

    async def test_alerts_only_reference_returned_events(self, client_no_db: AsyncClient) -> None:
        for params in ({}, {"hours": 6}, {"region": "Northeast"}, {"min_frp": 150}):
            data = (await client_no_db.get("/api/v1/fire", params=params)).json()
            event_ids = {e["event_id"] for e in data["events"]}
            assert all(a["fire_event_id"] in event_ids for a in data["alerts"]), params
