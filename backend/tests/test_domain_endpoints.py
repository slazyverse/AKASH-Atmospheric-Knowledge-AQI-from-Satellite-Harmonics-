"""
Tests for the domain endpoints (AQI, history, stations, forecast, HCHO, fire,
sources) against the bundled deterministic placeholder fixtures, which
conftest.py loads for every test.

Covers the full path: placeholder source → adapter → normalised contract →
service → API. Expected values are derived from the fixture files themselves
where practical, so the tests describe behaviour rather than magic numbers.
"""

from __future__ import annotations

import json

import pytest
from fastapi import status
from httpx import AsyncClient

from app.core.aqi import aqi_category
from app.core.regions import region_matches
from app.core.units import hcho_mol_m2_to_1e15_molec_cm2
from app.data.dataset import load_dataset
from app.data.sources import PLACEHOLDERS

pytestmark = pytest.mark.unit

LATEST = "2026-07-14"  # last date in placeholder_station_dataset.csv


# ── Shared logic ───────────────────────────────────────────────────────────────

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


class TestUnits:
    def test_hcho_conversion(self) -> None:
        # 1 mol/m² = 6.022e23 molecules / 1e4 cm² = 6.022e4 × 10¹⁵ molecules/cm²
        assert hcho_mol_m2_to_1e15_molec_cm2(1e-4) == pytest.approx(6.022, abs=1e-3)


# ── GET /api/v1/aqi/daily ──────────────────────────────────────────────────────

class TestAQIDaily:
    async def test_defaults_to_latest_source_date(self, client_no_db: AsyncClient) -> None:
        summary = (await client_no_db.get("/api/v1/aqi/daily")).json()["summary"]
        assert summary["summary_date"] == LATEST
        assert summary["station_count"] == 8
        assert summary["dominant_pollutant"] == "N/A"

    async def test_every_reading_category_matches_its_value(
        self, client_no_db: AsyncClient
    ) -> None:
        readings = (await client_no_db.get("/api/v1/aqi/daily")).json()["summary"]["readings"]
        assert readings
        for r in readings:
            assert r["aqi_category"] == aqi_category(r["aqi_value"]), r["station_id"]

    async def test_nullable_pollutants_are_preserved(self, client_no_db: AsyncClient) -> None:
        readings = (await client_no_db.get("/api/v1/aqi/daily")).json()["summary"]["readings"]
        chennai = next(r for r in readings if r["station_id"] == "CH001")
        assert chennai["so2"] is None
        assert chennai["pm25"] is not None

    async def test_limit_caps_readings_but_not_summary(self, client_no_db: AsyncClient) -> None:
        full = (await client_no_db.get("/api/v1/aqi/daily")).json()
        capped = (await client_no_db.get("/api/v1/aqi/daily", params={"limit": 2})).json()
        assert capped["count"] == 2
        assert capped["summary"]["station_count"] == full["summary"]["station_count"]
        assert capped["summary"]["avg_aqi"] == full["summary"]["avg_aqi"]

    async def test_region_zone_filters_by_station_state(self, client_no_db: AsyncClient) -> None:
        stations = (await client_no_db.get("/api/v1/stations")).json()["items"]
        state_of = {s["station_id"]: s["state"] for s in stations}
        resp = await client_no_db.get("/api/v1/aqi/daily", params={"region": "South India"})
        readings = resp.json()["summary"]["readings"]
        assert {r["station_id"] for r in readings} == {"BL001", "HY001", "CH001"}
        assert all(region_matches("South India", state_of[r["station_id"]]) for r in readings)

    async def test_region_state_filter(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get("/api/v1/aqi/daily", params={"region": "Delhi"})
        assert {r["station_id"] for r in resp.json()["summary"]["readings"]} == {"DL001"}

    async def test_unknown_region_returns_404(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get("/api/v1/aqi/daily", params={"region": "Mars"})
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    async def test_earlier_date_returns_that_days_values(self, client_no_db: AsyncClient) -> None:
        ds = load_dataset(PLACEHOLDERS["dataset"])
        day = ds.latest_date.replace(day=10)
        expected = {o.station_id: o.aqi for o in ds.latest_per_station(day)}
        resp = await client_no_db.get("/api/v1/aqi/daily", params={"date": "2026-07-10"})
        got = {r["station_id"]: r["aqi_value"] for r in resp.json()["summary"]["readings"]}
        assert got == expected

    async def test_date_without_data_returns_404(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get("/api/v1/aqi/daily", params={"date": "2020-01-01"})
        assert resp.status_code == status.HTTP_404_NOT_FOUND

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

    async def test_limit_above_max_returns_422(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get("/api/v1/aqi/daily", params={"limit": 1001})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ── GET /api/v1/aqi/history ────────────────────────────────────────────────────

class TestAQIHistory:
    async def test_full_history_is_ordered_observations(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get("/api/v1/aqi/history", params={"station_id": "DL001"})
        data = resp.json()
        assert data["station_name"] == "Delhi – Anand Vihar"
        assert data["count"] == 7
        times = [p["recorded_at"] for p in data["points"]]
        assert times == sorted(times)
        assert data["points"][-1]["recorded_at"].startswith(LATEST)

    async def test_days_window_ends_at_latest_date(self, client_no_db: AsyncClient) -> None:
        params = {"station_id": "DL001", "days": 3}
        resp = await client_no_db.get("/api/v1/aqi/history", params=params)
        dates = [p["recorded_at"][:10] for p in resp.json()["points"]]
        assert dates == ["2026-07-12", "2026-07-13", LATEST]

    async def test_nullable_values_in_history(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get("/api/v1/aqi/history", params={"station_id": "PU001"})
        data = resp.json()
        co = [p["co"] for p in data["points"]]
        assert None in co and any(v is not None for v in co)

    async def test_unknown_station_404(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get("/api/v1/aqi/history", params={"station_id": "XX999"})
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    async def test_days_out_of_range_422(self, client_no_db: AsyncClient) -> None:
        params = {"station_id": "DL001", "days": 0}
        resp = await client_no_db.get("/api/v1/aqi/history", params=params)
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ── /stations ↔ /forecast consistency ─────────────────────────────────────────

class TestStationForecastConsistency:
    async def test_registry_is_sorted_and_complete(self, client_no_db: AsyncClient) -> None:
        items = (await client_no_db.get("/api/v1/stations")).json()["items"]
        ids = [s["station_id"] for s in items]
        assert ids == sorted(ids) and len(ids) == 8

    async def test_every_listed_station_has_a_forecast(self, client_no_db: AsyncClient) -> None:
        stations = (await client_no_db.get("/api/v1/stations")).json()["items"]
        for s in stations:
            resp = await client_no_db.get(
                "/api/v1/forecast", params={"station_id": s["station_id"], "horizon_hours": 1}
            )
            assert resp.status_code == status.HTTP_200_OK, s["station_id"]

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

    async def test_simulated_and_never_fabricates_metrics(self, client_no_db: AsyncClient) -> None:
        data = (await client_no_db.get("/api/v1/forecast", params={"station_id": "DL001"})).json()
        assert data["forecast_kind"] == "simulated"
        metrics = data["model_metrics"]
        assert "Simulated" in metrics["model_name"]
        for field in ("rmse", "mae", "r_squared", "training_date", "validation_period"):
            assert metrics[field] is None, field
        assert data["feature_importances"] == []

    async def test_seeded_from_latest_observation(self, client_no_db: AsyncClient) -> None:
        data = (await client_no_db.get("/api/v1/forecast", params={"station_id": "DL001"})).json()
        assert data["based_on_observation_at"].startswith(LATEST)

    async def test_horizon_above_72_rejected(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get(
            "/api/v1/forecast", params={"station_id": "DL001", "horizon_hours": 73}
        )
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


# ── GET /api/v1/hcho/hotspots and /hcho/trend ──────────────────────────────────

class TestHCHOHotspots:
    URL = "/api/v1/hcho/hotspots"

    async def test_clusters_follow_contract_without_invented_fields(
        self, client_no_db: AsyncClient
    ) -> None:
        data = (await client_no_db.get(self.URL)).json()
        raw = json.loads(PLACEHOLDERS["hcho"].read_text(encoding="utf-8"))
        assert data["count"] == len(raw) == 4
        assert data["query_date"] is None
        for item, cluster in zip(data["items"], raw, strict=True):
            assert item["column_density"] == hcho_mol_m2_to_1e15_molec_cm2(cluster["mean_hcho"])
            assert item["radius_km"] is None
            assert item["confidence"] is None
            assert item["detected_at"] is None
            assert item["source_type"] == "unknown"

    async def test_unscored_clusters_survive_confidence_filter(
        self, client_no_db: AsyncClient
    ) -> None:
        data = (await client_no_db.get(self.URL, params={"min_confidence": 0.99})).json()
        assert data["count"] == 4

    async def test_explicit_date_without_dated_clusters_404(
        self, client_no_db: AsyncClient
    ) -> None:
        resp = await client_no_db.get(self.URL, params={"date": LATEST})
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    async def test_impossible_date_returns_422(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get(self.URL, params={"date": "2026-02-30"})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    async def test_confidence_out_of_range_returns_422(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get(self.URL, params={"min_confidence": 1.5})
        assert resp.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestHCHOTrend:
    async def test_daily_means_from_station_dataset(self, client_no_db: AsyncClient) -> None:
        data = (await client_no_db.get("/api/v1/hcho/trend")).json()
        assert data["unit"] == "1e15 molecules/cm2"
        assert data["count"] == 7
        assert [p["obs_date"] for p in data["points"]][-1] == LATEST
        ds = load_dataset(PLACEHOLDERS["dataset"])
        values = [o.hcho_mol_m2 for o in ds.latest_per_station(ds.latest_date)]
        expected = hcho_mol_m2_to_1e15_molec_cm2(sum(values) / len(values))
        assert data["points"][-1]["mean_column_density"] == expected
        assert data["points"][-1]["station_count"] == 8

    async def test_days_window(self, client_no_db: AsyncClient) -> None:
        data = (await client_no_db.get("/api/v1/hcho/trend", params={"days": 2})).json()
        assert [p["obs_date"] for p in data["points"]] == ["2026-07-13", LATEST]


# ── GET /api/v1/fire ───────────────────────────────────────────────────────────

class TestFire:
    async def test_default_window_and_rule_based_alerts(self, client_no_db: AsyncClient) -> None:
        data = (await client_no_db.get("/api/v1/fire")).json()
        assert data["as_of"].startswith("2026-07-14T06:00:00")
        assert data["total_events"] == len(data["events"]) == 5
        severities = {a["fire_event_id"]: a["severity"] for a in data["alerts"]}
        assert severities == {"PH-FIRE-001": "high", "PH-FIRE-003": "critical"}
        assert all(a["aqi_impact_score"] is None for a in data["alerts"])

    async def test_hours_window_ends_at_source_as_of(self, client_no_db: AsyncClient) -> None:
        data = (await client_no_db.get("/api/v1/fire", params={"hours": 6})).json()
        assert {e["event_id"] for e in data["events"]} == {"PH-FIRE-001", "PH-FIRE-002"}

    async def test_region_state_filter(self, client_no_db: AsyncClient) -> None:
        data = (await client_no_db.get("/api/v1/fire", params={"region": "Karnataka"})).json()
        assert [e["state"] for e in data["events"]] == ["Karnataka"]

    async def test_region_zone_filter(self, client_no_db: AsyncClient) -> None:
        data = (await client_no_db.get("/api/v1/fire", params={"region": "Northeast"})).json()
        assert data["events"]
        assert all(region_matches("Northeast", e["state"]) for e in data["events"])

    async def test_region_without_events_is_empty_200(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get("/api/v1/fire", params={"region": "Kerala"})
        assert resp.status_code == status.HTTP_200_OK
        assert resp.json()["events"] == [] and resp.json()["alerts"] == []

    async def test_min_frp_filter(self, client_no_db: AsyncClient) -> None:
        data = (await client_no_db.get("/api/v1/fire", params={"min_frp": 100})).json()
        assert data["events"] and all(e["frp"] >= 100 for e in data["events"])

    async def test_alerts_only_reference_returned_events(self, client_no_db: AsyncClient) -> None:
        for params in ({}, {"hours": 6}, {"region": "Northeast"}, {"min_frp": 150}):
            data = (await client_no_db.get("/api/v1/fire", params=params)).json()
            event_ids = {e["event_id"] for e in data["events"]}
            assert all(a["fire_event_id"] in event_ids for a in data["alerts"]), params


# ── GET /api/v1/sources and /version ───────────────────────────────────────────

class TestSourceStatus:
    async def test_every_domain_reported(self, client_no_db: AsyncClient) -> None:
        listed = (await client_no_db.get("/api/v1/sources")).json()["sources"]
        by_domain = {s["domain"]: s for s in listed}
        assert set(by_domain) == {
            "aqi", "stations", "hcho_trend", "hcho", "fire", "model", "forecast",
            "xai_global", "xai_local", "spatial_rasters",
        }
        assert by_domain["aqi"]["kind"] == "placeholder"
        assert by_domain["aqi"]["as_of"] == LATEST
        assert by_domain["stations"]["records"] == 8
        assert by_domain["model"]["kind"] == "unavailable"
        assert by_domain["forecast"]["kind"] == "simulated"
        assert by_domain["spatial_rasters"]["kind"] == "unavailable"
        assert all("/" not in s["name"] and "\\" not in s["name"] for s in listed)  # no paths

    async def test_placeholder_limitations_and_quality(self, client_no_db: AsyncClient) -> None:
        listed = (await client_no_db.get("/api/v1/sources")).json()["sources"]
        by_domain = {s["domain"]: s for s in listed}
        # The placeholder stations have distinct coordinates: maps are allowed
        assert by_domain["aqi"]["limitations"] == []
        assert by_domain["aqi"]["quality"]["coordinate_quality"] == "reported"
        assert by_domain["aqi"]["quality"]["rows_accepted"] == 56
        # The cluster contract itself lacks this metadata — reported, never invented
        codes = {lim["code"] for lim in by_domain["hcho"]["limitations"]}
        assert codes == {"no_observation_date", "no_radius_or_confidence", "no_source_attribution"}
        assert by_domain["hcho"]["quality"]["clusters_matched_to_stations"] == 4

    async def test_version_compact_form_matches(self, client_no_db: AsyncClient) -> None:
        version = (await client_no_db.get("/api/v1/version")).json()["data_sources"]
        assert version["aqi"] == "placeholder:placeholder_station_dataset.csv"
        assert version["model"] == "unavailable"
        assert version["forecast"] == "simulated"
