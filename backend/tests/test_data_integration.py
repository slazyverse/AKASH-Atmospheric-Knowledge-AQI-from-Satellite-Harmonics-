"""
Tests for the Day-5 integration layer (app/data) and the services/endpoints
that consume it.

All inputs are small SYNTHETIC fixtures written to tmp_path that follow the
verified teammate output contracts (analysis_ready_dataset v1/v2 CSV,
cluster_summary.json, LightGBM artefact directory). They are test data only —
not real measurements and not a real model. The model "binary" is an empty
placeholder file because the loader only checks its presence.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
from fastapi import status
from httpx import AsyncClient

from app.core.aqi import aqi_category
from app.core.config import Settings
from app.core.units import MOL_M2_TO_1E15_MOLEC_CM2
from app.data import sources as sources_module
from app.data.dataset import DatasetError, load_dataset
from app.data.fires import FireFileError, load_fires
from app.data.hotspots import HotspotFileError, load_hotspots
from app.data.model_artifact import ModelArtifactError, load_model_artifact
from app.data.sources import PLACEHOLDERS, load_configured_sources, sources

pytestmark = pytest.mark.unit

V1_HEADER = (
    "Station ID,Station Name,City,State,Latitude,Longitude,Date,Time,"
    "PM2.5,PM10,NO2,SO2,CO,O3,AQI,HCHO"
)
V1_ROWS = [
    "TST_001,Test Station A,Pune,Maharashtra,18.52,73.85,2026-07-14,00:00:00,"
    "40.0,80.0,20.0,5.0,1.0,30.0,105,0.0002",
    "TST_002,Test Station B,Chennai,Tamil Nadu,13.08,80.27,2026-07-14,00:00:00,"
    ",55.0,,4.0,0.8,25.0,62,0.0001",
    "TST_003,Test Station C,Patna,Bihar,25.59,85.13,2026-07-14,00:00:00,"
    "120.0,200.0,40.0,9.0,2.0,50.0,318,0.0003",
    # Invalid rows — must be skipped, never repaired:
    "TST_004,No AQI,Delhi,Delhi,28.61,77.20,2026-07-14,00:00:00,10,20,5,1,0.5,10,,0.0001",
    "TST_005,Bad Lat,Delhi,Delhi,,77.20,2026-07-14,00:00:00,10,20,5,1,0.5,10,80,0.0001",
]

V2_HEADER = (
    "station_id,station_name,city,state,station_latitude,station_longitude,network_source,"
    "timestamp_utc_str,PM2.5,PM10,NO2,SO2,CO,O3,AQI,HCHO,elevation"
)
V2_ROWS = [
    "ST_a,V2 Station A,Delhi,Delhi,28.63,77.29,CPCB,2026-07-12T06:00:00Z,"
    "90,180,60,20,1.5,40,250,0.0004,210",
    "ST_a,V2 Station A,Delhi,Delhi,28.63,77.29,CPCB,2026-07-13T06:00:00Z,"
    "80,170,55,18,1.4,38,230,0.0004,210",
    "ST_a,V2 Station A,Delhi,Delhi,28.63,77.29,CPCB,2026-07-13T18:00:00Z,"
    "70,150,50,15,1.2,35,190,0.0004,210",
    "ST_b,V2 Station B,Bengaluru,Karnataka,12.92,77.62,OpenAQ,2026-07-13T09:00:00Z,"
    "20,45,25,8,0.7,30,75,0.0001,920",
]


def _write(path: Path, lines: list[str]) -> Path:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def v1_csv(tmp_path: Path) -> Path:
    return _write(tmp_path / "analysis_ready_dataset.csv", [V1_HEADER, *V1_ROWS])


@pytest.fixture
def v2_csv(tmp_path: Path) -> Path:
    return _write(tmp_path / "analysis_ready_dataset_v2.csv", [V2_HEADER, *V2_ROWS])


CLUSTERS = [
    {
        "cluster_id": 0, "station_count": 3,
        "mean_latitude": 25.6, "mean_longitude": 85.1, "mean_hcho": 0.0003,
        "mean_co_column": 0.03, "stations": ["Test Station C", "X", "Y"],
    },
    {
        "cluster_id": 1, "station_count": 4,
        "mean_latitude": 13.1, "mean_longitude": 80.3, "mean_hcho": 0.00015,
        "stations": ["Test Station B"],
    },
]


@pytest.fixture
def hotspot_json(tmp_path: Path) -> Path:
    path = tmp_path / "cluster_summary.json"
    path.write_text(json.dumps(CLUSTERS), encoding="utf-8")
    return path


@pytest.fixture
def model_dir(tmp_path: Path) -> Path:
    root = tmp_path / "lightgbm_run"
    root.mkdir()
    (root / "lightgbm_model.joblib").write_bytes(b"")  # presence-only placeholder
    (root / "lightgbm_evaluation_metrics.json").write_text(
        json.dumps({"R2": 0.5, "RMSE": 40.0, "MAE": 30.0, "MBE": -1.5}), encoding="utf-8"
    )
    (root / "lightgbm_feature_importances.json").write_text(
        json.dumps({"Wind Speed": 30, "HCHO": 50, "Temperature": 20}), encoding="utf-8"
    )
    (root / "lightgbm_training_summary.json").write_text(
        json.dumps({
            "target_column": "AQI", "test_samples": 76,
            "reproducibility": {"lightgbm_version": "9.9.9"},
        }),
        encoding="utf-8",
    )
    return root


@pytest.fixture(autouse=True)
def _reset_sources():
    # Start each test from an empty registry (conftest loads placeholders first).
    sources.reset()
    yield
    sources.reset()


def _settings(**overrides: object) -> Settings:
    """Deterministic settings: no .env, no repository auto-discovery."""
    return Settings(_env_file=None, AUTO_DISCOVER_TEAM_OUTPUTS=False, **overrides)


# ── Dataset loader ─────────────────────────────────────────────────────────────

class TestDatasetLoader:
    def test_v1_schema_loads_and_skips_invalid_rows(self, v1_csv: Path) -> None:
        ds = load_dataset(v1_csv)
        assert len(ds) == 3
        assert ds.source_name == "analysis_ready_dataset.csv"
        assert ds.latest_date == date(2026, 7, 14)

    def test_missing_pollutant_stays_none(self, v1_csv: Path) -> None:
        obs = load_dataset(v1_csv).latest_for("TST_002")
        assert obs is not None
        assert obs.pm25 is None and obs.no2 is None
        assert obs.pm10 == 55.0

    def test_v2_schema_aliases_and_latest_per_station(self, v2_csv: Path) -> None:
        ds = load_dataset(v2_csv)
        assert ds.latest_date == date(2026, 7, 13)
        latest = {o.station_id: o for o in ds.latest_per_station(date(2026, 7, 13))}
        assert latest["ST_a"].aqi == 190  # 18:00 beats 06:00
        assert latest["ST_a"].network == "CPCB"
        assert latest["ST_a"].elevation_m == 210.0
        older = {o.station_id: o for o in ds.latest_per_station(date(2026, 7, 12))}
        assert set(older) == {"ST_a"}

    def test_offset_timestamps_are_normalised_to_utc(self, tmp_path: Path) -> None:
        row = V2_ROWS[3].replace("2026-07-13T09:00:00Z", "2026-07-14T02:00:00+05:30")
        ds = load_dataset(_write(tmp_path / "tz.csv", [V2_HEADER, row]))
        assert ds.latest_date == date(2026, 7, 13)  # 2026-07-13T20:30Z

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(DatasetError, match="not found"):
            load_dataset(tmp_path / "nope.csv")

    def test_missing_required_columns(self, tmp_path: Path) -> None:
        path = _write(tmp_path / "bad.csv", ["Station ID,Station Name,AQI", "A,B,10"])
        with pytest.raises(DatasetError, match="missing required columns") as err:
            load_dataset(path)
        for col in ("state", "latitude", "longitude", "timestamp|date"):
            assert col in str(err.value)

    def test_header_only_dataset(self, tmp_path: Path) -> None:
        with pytest.raises(DatasetError, match="no rows"):
            load_dataset(_write(tmp_path / "empty.csv", [V1_HEADER]))

    def test_all_rows_invalid(self, tmp_path: Path) -> None:
        with pytest.raises(DatasetError, match="no valid observations"):
            load_dataset(_write(tmp_path / "invalid.csv", [V1_HEADER, *V1_ROWS[3:]]))


# ── Hotspot loader ─────────────────────────────────────────────────────────────

class TestHotspotLoader:
    def test_cluster_summary_contract(self, hotspot_json: Path) -> None:
        records = load_hotspots(hotspot_json)
        assert [r.hotspot_id for r in records] == ["HS-0", "HS-1"]
        first = records[0]
        expected = 0.0003 * MOL_M2_TO_1E15_MOLEC_CM2
        assert first.column_density == pytest.approx(expected, abs=1e-3)
        # Fields the file does not provide stay empty — never invented
        assert first.radius_km is None and first.confidence is None
        assert first.observed_at is None and first.source_type == "unknown"

    def test_unit_conversion_factor(self) -> None:
        # 1 mol/m² = 6.022e23 molecules / 1e4 cm² = 6.022e19 = 6.022e4 × 10¹⁵ molec/cm²
        assert pytest.approx(6.02214076e4) == MOL_M2_TO_1E15_MOLEC_CM2

    def test_empty_list_is_valid(self, tmp_path: Path) -> None:
        path = tmp_path / "c.json"
        path.write_text("[]", encoding="utf-8")
        assert load_hotspots(path) == []

    @pytest.mark.parametrize(
        ("payload", "message"),
        [
            ('{"cluster_id": 0}', "JSON list"),
            ('[{"cluster_id": 0, "mean_latitude": 1, "mean_longitude": 2}]', "mean_hcho"),
            ('[{"cluster_id": 0, "mean_latitude": 99, "mean_longitude": 2, "mean_hcho": 1e-4}]',
             "invalid coordinates"),
            ('[{"cluster_id": 0, "mean_latitude": 1, "mean_longitude": 2, "mean_hcho": 1e-4,'
             ' "confidence": 1.7}]', "confidence"),
            ("not json", "Cannot read"),
        ],
    )
    def test_contract_violations(self, tmp_path: Path, payload: str, message: str) -> None:
        path = tmp_path / "c.json"
        path.write_text(payload, encoding="utf-8")
        with pytest.raises(HotspotFileError, match=message):
            load_hotspots(path)

    def test_missing_file(self, tmp_path: Path) -> None:
        with pytest.raises(HotspotFileError, match="not found"):
            load_hotspots(tmp_path / "missing.json")


# ── Model artefact loader ──────────────────────────────────────────────────────

class TestModelArtifactLoader:
    def test_valid_artifact(self, model_dir: Path) -> None:
        art = load_model_artifact(model_dir)
        names = [name for name, _ in art.feature_importances]
        assert names == ["HCHO", "Wind Speed", "Temperature"]
        assert sum(share for _, share in art.feature_importances) == pytest.approx(1.0)
        assert art.metrics["R2"] == 0.5
        assert art.model_version == "lightgbm 9.9.9"
        assert art.target_column == "AQI" and art.test_samples == 76

    def test_invalid_path(self, tmp_path: Path) -> None:
        with pytest.raises(ModelArtifactError, match="not found"):
            load_model_artifact(tmp_path / "no_such_dir")

    def test_missing_model_binary(self, model_dir: Path) -> None:
        (model_dir / "lightgbm_model.joblib").unlink()
        with pytest.raises(ModelArtifactError, match="lightgbm_model.joblib"):
            load_model_artifact(model_dir)

    def test_metrics_without_r2(self, model_dir: Path) -> None:
        (model_dir / "lightgbm_evaluation_metrics.json").write_text('{"RMSE": 1, "MAE": 1}')
        with pytest.raises(ModelArtifactError, match="R2"):
            load_model_artifact(model_dir)

    @pytest.mark.parametrize("payload", ["{}", '{"HCHO": -1}', '{"HCHO": 0}', "[1, 2]"])
    def test_bad_importances(self, model_dir: Path, payload: str) -> None:
        (model_dir / "lightgbm_feature_importances.json").write_text(payload)
        with pytest.raises(ModelArtifactError):
            load_model_artifact(model_dir)

    def test_corrupt_json(self, model_dir: Path) -> None:
        (model_dir / "lightgbm_evaluation_metrics.json").write_text("{oops")
        with pytest.raises(ModelArtifactError, match="Cannot read"):
            load_model_artifact(model_dir)


# ── Startup wiring ─────────────────────────────────────────────────────────────

class TestSourceResolution:
    def test_nothing_configured_uses_placeholders(self) -> None:
        load_configured_sources(_settings())
        d = sources.describe()
        assert d["aqi"] == "placeholder:placeholder_station_dataset.csv"
        assert d["stations"] == "placeholder:placeholder_station_dataset.csv"
        assert d["hcho"] == "placeholder:placeholder_hcho_clusters.json"
        assert d["fire"] == "placeholder:placeholder_fire_events.json"
        assert d["model"] == "unavailable"
        assert d["forecast"] == "simulated"
        assert d["xai_global"] == "unavailable"
        assert d["xai_local"] == "unavailable"
        assert d["spatial_rasters"] == "unavailable"
        assert sources.model is None

    def test_placeholders_disabled_means_unavailable(self) -> None:
        load_configured_sources(_settings(ENABLE_PLACEHOLDER_DATA=False))
        for domain in ("aqi", "stations", "hcho", "fire", "forecast"):
            assert sources.status(domain).kind == "unavailable"
        assert sources.dataset is None and sources.hotspots is None and sources.fires is None

    def test_explicit_paths_are_local(
        self, v1_csv: Path, hotspot_json: Path, model_dir: Path, tmp_path: Path
    ) -> None:
        fires = tmp_path / "fires.json"
        fires.write_text(PLACEHOLDERS["fire"].read_text(encoding="utf-8"), encoding="utf-8")
        load_configured_sources(_settings(
            DATASET_PATH=str(v1_csv), HCHO_HOTSPOTS_PATH=str(hotspot_json),
            FIRE_EVENTS_PATH=str(fires), ML_MODEL_PATH=str(model_dir), ENABLE_ML_ENDPOINTS=True,
        ))
        d = sources.describe()
        assert d["aqi"] == "local:analysis_ready_dataset.csv"
        assert d["hcho"] == "local:cluster_summary.json"
        assert d["fire"] == "local:fires.json"
        assert d["model"] == "local:lightgbm_run"
        assert d["xai_global"] == "local:lightgbm_run"
        assert d["forecast"] == "simulated"  # a loaded estimator never becomes a forecaster
        assert sources.status("stations").records == 3
        assert sources.status("aqi").as_of == "2026-07-14"

    def test_auto_discovered_team_output_is_used(
        self, v1_csv: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sources_module.DISCOVERY_PATHS, "dataset", (v1_csv,))
        load_configured_sources(Settings(_env_file=None))
        status_ = sources.status("aqi")
        assert (status_.kind, status_.name) == ("local", "analysis_ready_dataset.csv")
        assert "auto-discovered" in status_.detail

    def test_incompatible_discovered_output_falls_back_with_reason(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        bad = _write(tmp_path / "analysis_ready_dataset.csv", ["Station ID,AQI", "A,10"])
        monkeypatch.setitem(sources_module.DISCOVERY_PATHS, "dataset", (bad,))
        load_configured_sources(Settings(_env_file=None))
        status_ = sources.status("aqi")
        assert status_.kind == "placeholder"
        assert "incompatible" in status_.detail and "missing required columns" in status_.detail

    def test_model_not_loaded_when_ml_disabled(self, model_dir: Path) -> None:
        load_configured_sources(_settings(ML_MODEL_PATH=str(model_dir)))
        assert sources.model is None
        assert "ENABLE_ML_ENDPOINTS" in sources.status("model").detail

    @pytest.mark.parametrize(
        ("setting", "error"),
        [("DATASET_PATH", DatasetError), ("HCHO_HOTSPOTS_PATH", HotspotFileError),
         ("FIRE_EVENTS_PATH", FireFileError)],
    )
    def test_invalid_explicit_path_raises(
        self, tmp_path: Path, setting: str, error: type[Exception]
    ) -> None:
        with pytest.raises(error, match="not found"):
            load_configured_sources(_settings(**{setting: str(tmp_path / "missing")}))

    def test_invalid_model_path_raises(self, tmp_path: Path) -> None:
        with pytest.raises(ModelArtifactError):
            load_configured_sources(
                _settings(ML_MODEL_PATH=str(tmp_path / "nope"), ENABLE_ML_ENDPOINTS=True)
            )


class TestPlaceholderFixtures:
    """The bundled fixtures must satisfy the same contracts as the real sources."""

    def test_station_fixture_matches_dataset_contract(self) -> None:
        ds = load_dataset(PLACEHOLDERS["dataset"])
        assert len(ds) == 56 and len(ds.latest_per_station()) == 8
        assert ds.latest_date == date(2026, 7, 14)
        # Deliberate gaps exercise nullable pollutants
        assert all(o.so2 is None for o in ds.observations_for("CH001"))

    def test_hotspot_fixture_matches_cluster_contract(self) -> None:
        records = load_hotspots(PLACEHOLDERS["hcho"])
        assert len(records) == 4
        raw = json.loads(PLACEHOLDERS["hcho"].read_text(encoding="utf-8"))
        assert all(set(c) <= {"cluster_id", "station_count", "mean_latitude", "mean_longitude",
                              "mean_hcho", "stations"} for c in raw)  # no invented fields
        assert all(r.confidence is None and r.radius_km is None for r in records)

    def test_fire_fixture_matches_fire_contract(self) -> None:
        records = load_fires(PLACEHOLDERS["fire"])
        assert len(records) == 5
        assert all(r.event_id.startswith("PH-") for r in records)


class TestFireLoader:
    def test_offset_timestamp_is_normalised(self, tmp_path: Path) -> None:
        item = json.loads(PLACEHOLDERS["fire"].read_text(encoding="utf-8"))[0]
        item["detected_at"] = "2026-07-14T05:30:00+05:30"
        path = tmp_path / "f.json"
        path.write_text(json.dumps([item]), encoding="utf-8")
        (record,) = load_fires(path)
        assert record.detected_at.isoformat() == "2026-07-14T00:00:00+00:00"

    @pytest.mark.parametrize(
        ("mutate", "message"),
        [
            (lambda i: i.pop("frp"), "missing required keys"),
            (lambda i: i.update(brightness=120), "brightness"),
            (lambda i: i.update(latitude=123), "invalid coordinates"),
            (lambda i: i.update(detected_at="yesterday"), "detected_at"),
        ],
    )
    def test_contract_violations(self, tmp_path: Path, mutate, message: str) -> None:
        item = json.loads(PLACEHOLDERS["fire"].read_text(encoding="utf-8"))[0]
        mutate(item)
        path = tmp_path / "f.json"
        path.write_text(json.dumps([item]), encoding="utf-8")
        with pytest.raises(FireFileError, match=message):
            load_fires(path)

    def test_duplicate_ids_rejected(self, tmp_path: Path) -> None:
        item = json.loads(PLACEHOLDERS["fire"].read_text(encoding="utf-8"))[0]
        path = tmp_path / "f.json"
        path.write_text(json.dumps([item, item]), encoding="utf-8")
        with pytest.raises(FireFileError, match="duplicate"):
            load_fires(path)

    def test_not_a_list(self, tmp_path: Path) -> None:
        path = tmp_path / "f.json"
        path.write_text("{}", encoding="utf-8")
        with pytest.raises(FireFileError, match="JSON list"):
            load_fires(path)

    async def test_invalid_configured_dataset_fails_startup(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        import app.main as main_module

        bad = Settings(_env_file=None, DATASET_PATH=str(tmp_path / "missing.csv"))
        monkeypatch.setattr(main_module, "settings", bad)
        with pytest.raises(DatasetError, match="not found"):
            async with main_module.lifespan(main_module.app):
                pass


# ── Endpoints backed by the fixtures ───────────────────────────────────────────

class TestEndpointsWithDataset:
    @pytest.fixture(autouse=True)
    def _load(self, v1_csv: Path) -> None:
        sources.dataset = load_dataset(v1_csv)

    async def test_aqi_daily_serves_dataset(self, client_no_db: AsyncClient) -> None:
        summary = (await client_no_db.get("/api/v1/aqi/daily")).json()["summary"]
        assert summary["summary_date"] == "2026-07-14"
        assert summary["station_count"] == 3
        assert summary["dominant_pollutant"] == "N/A"
        by_id = {r["station_id"]: r for r in summary["readings"]}
        assert set(by_id) == {"TST_001", "TST_002", "TST_003"}
        for r in by_id.values():
            assert r["aqi_category"] == aqi_category(r["aqi_value"])
        assert by_id["TST_002"]["pm25"] is None

    async def test_region_filters_use_dataset_states(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get("/api/v1/aqi/daily", params={"region": "East India"})
        east = resp.json()
        assert [r["station_id"] for r in east["summary"]["readings"]] == ["TST_003"]
        resp = await client_no_db.get("/api/v1/aqi/daily", params={"region": "Delhi"})
        assert resp.status_code == status.HTTP_404_NOT_FOUND  # Delhi rows were invalid

    async def test_stations_and_forecast_share_dataset_ids(
        self, client_no_db: AsyncClient
    ) -> None:
        stations = (await client_no_db.get("/api/v1/stations")).json()["items"]
        assert [s["station_id"] for s in stations] == ["TST_001", "TST_002", "TST_003"]  # sorted
        assert all(s["network"] == "unknown" for s in stations)  # v1 has no network column
        for s in stations:
            resp = await client_no_db.get(
                "/api/v1/forecast", params={"station_id": s["station_id"], "horizon_hours": 1}
            )
            assert resp.status_code == status.HTTP_200_OK
        demo = await client_no_db.get("/api/v1/forecast", params={"station_id": "DL001"})
        assert demo.status_code == status.HTTP_404_NOT_FOUND

    async def test_forecast_stays_simulated(self, client_no_db: AsyncClient) -> None:
        data = (await client_no_db.get("/api/v1/forecast", params={"station_id": "TST_003"})).json()
        assert "Simulated" in data["model_metrics"]["model_name"]
        assert data["model_metrics"]["r_squared"] is None

    async def test_sources_and_version_report_dataset(
        self, client_no_db: AsyncClient, v1_csv: Path
    ) -> None:
        load_configured_sources(_settings(DATASET_PATH=str(v1_csv)))
        data = (await client_no_db.get("/api/v1/version")).json()
        assert data["data_sources"]["aqi"] == "local:analysis_ready_dataset.csv"
        assert data["data_sources"]["hcho"] == "placeholder:placeholder_hcho_clusters.json"
        listed = (await client_no_db.get("/api/v1/sources")).json()["sources"]
        by_domain = {s["domain"]: s for s in listed}
        assert by_domain["aqi"]["kind"] == "local" and by_domain["aqi"]["records"] == 3
        assert by_domain["model"]["kind"] == "unavailable"


class TestEndpointsWithV2Dataset:
    async def test_date_param_selects_that_day(
        self, client_no_db: AsyncClient, v2_csv: Path
    ) -> None:
        sources.dataset = load_dataset(v2_csv)
        resp = await client_no_db.get("/api/v1/aqi/daily", params={"date": "2026-07-12"})
        readings = resp.json()["summary"]["readings"]
        assert [(r["station_id"], r["aqi_value"]) for r in readings] == [("ST_a", 250)]
        missing = await client_no_db.get("/api/v1/aqi/daily", params={"date": "2026-07-01"})
        assert missing.status_code == status.HTTP_404_NOT_FOUND


class TestHCHOWithHotspotFile:
    @pytest.fixture(autouse=True)
    def _load(self, hotspot_json: Path) -> None:
        sources.hotspots = load_hotspots(hotspot_json)

    async def test_serves_clusters_with_nulls(self, client_no_db: AsyncClient) -> None:
        data = (await client_no_db.get("/api/v1/hcho/hotspots")).json()
        assert data["count"] == 2
        assert data["query_date"] is None
        for item in data["items"]:
            assert item["radius_km"] is None
            assert item["confidence"] is None
            assert item["detected_at"] is None
            assert item["source_type"] == "unknown"

    async def test_unscored_clusters_survive_confidence_filter(
        self, client_no_db: AsyncClient
    ) -> None:
        resp = await client_no_db.get("/api/v1/hcho/hotspots", params={"min_confidence": 0.99})
        data = resp.json()
        assert data["count"] == 2

    async def test_explicit_date_without_dated_clusters_404(
        self, client_no_db: AsyncClient
    ) -> None:
        resp = await client_no_db.get("/api/v1/hcho/hotspots", params={"date": "2026-07-14"})
        assert resp.status_code == status.HTTP_404_NOT_FOUND


class TestXAIGlobalImportance:
    async def test_404_without_model(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get("/api/v1/xai/global-importance")
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    async def test_serves_artifact_metadata(
        self, client_no_db: AsyncClient, model_dir: Path
    ) -> None:
        sources.model = load_model_artifact(model_dir)
        data = (await client_no_db.get("/api/v1/xai/global-importance")).json()
        m = data["model_metrics"]
        assert (m["r_squared"], m["rmse"], m["mae"]) == (0.5, 40.0, 30.0)
        assert m["training_date"] is None
        assert m["validation_period"] == "Held-out test split (76 rows)"
        assert data["mean_bias_error"] == -1.5
        assert data["target_column"] == "AQI"
        assert "not SHAP" in data["importance_method"]
        feats = data["feature_importances"]
        assert [f["feature"] for f in feats] == ["HCHO", "Wind Speed", "Temperature"]
        assert sum(f["importance"] for f in feats) == pytest.approx(1.0, abs=1e-5)

    async def test_model_does_not_leak_into_forecast(
        self, client_no_db: AsyncClient, model_dir: Path
    ) -> None:
        load_configured_sources(
            _settings(ML_MODEL_PATH=str(model_dir), ENABLE_ML_ENDPOINTS=True)
        )
        data = (await client_no_db.get("/api/v1/forecast", params={"station_id": "DL001"})).json()
        assert data["forecast_kind"] == "simulated"
        assert data["model_metrics"]["r_squared"] is None
        assert data["feature_importances"] == []
