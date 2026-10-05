"""
Integration of the team outputs from PR #7 / PR #8 through our adapters.

Deterministic, synthetic fixtures reproduce the SHAPE and the known defects of
the real outputs (no team data is copied here):
  - analysis_ready_dataset.csv: one date, many stations on shared fallback
    coordinates, an AQI reported without PM2.5 / PM10, CO in an implausible
    unit, satellite HCHO observed weeks before the station date
  - cluster_summary.json: DBSCAN clusters of those coordinates, no date /
    radius / confidence
  - LightGBM artefact metadata exactly as model_training/lightgbm_model.py
    writes it today (no feature_names / trained_at / split_strategy)
"""

from __future__ import annotations

import json
from datetime import date
from typing import TYPE_CHECKING

import pytest
from fastapi import status

from app.core.aqi import meets_cpcb_minimum
from app.core.config import Settings
from app.core.geo import in_india
from app.core.units import MOL_M2_TO_1E15_MOLEC_CM2
from app.data import sources as sources_module
from app.data.dataset import load_dataset
from app.data.model_artifact import ModelArtifactError, load_model_artifact
from app.data.sources import load_configured_sources, sources
from app.data.trust import assess_model

if TYPE_CHECKING:
    from pathlib import Path

    from httpx import AsyncClient

pytestmark = pytest.mark.unit

HEADER = (
    "Station ID,Station Name,City,State,Latitude,Longitude,Date,Time,"
    "PM2.5,PM10,NO2,SO2,CO,O3,AQI,HCHO,HCHO Obs Date,placeholder_used"
)
A = "19.0760,72.8777"   # shared fallback coordinate (six stations, different cities)
B = "26.9124,75.7873"   # shared by two stations
C = "28.6139,77.2090"   # unique
DAY = "2026-07-14,00:00:00"


def _row(sid: str, name: str, city: str, state: str, coord: str, pollutants: str, aqi: str,
         hcho: str, hcho_day: str) -> str:
    return f"{sid},{name},{city},{state},{coord},{DAY},{pollutants},{aqi},{hcho},{hcho_day},False"


TEAM_ROWS = [
    *[_row(f"STN_00{i}", f"Station A{i}", f"Town{i}", "Maharashtra", A,
           "40,80,20,5,25,30", "105", "0.0002", "2026-06-29") for i in range(1, 7)],
    _row("STN_011", "Station B1", "Jaipur", "Rajasthan", B, "60,120,25,6,30,35", "158",
         "0.0003", "2026-06-28"),
    _row("STN_012", "Station B2", "Ajmer", "Rajasthan", B, "50,90,22,4,28,33", "117",
         "0.0003", "2026-06-28"),
    _row("STN_021", "Station C1", "Delhi", "Delhi", C, "90,180,60,20,35,40", "300",
         "-0.0001", "2026-06-29"),
    # Defects that must be rejected at the adapter boundary. Their satellite HCHO
    # (same pixel as C1) does not depend on the ground AQI and still counts.
    _row("STN_031", "No PM", "Kanpur", "Uttar Pradesh", C, ",,0,10,12,16", "0",
         "-0.0001", "2026-06-27"),                               # below CPCB minimum
    _row("STN_032", "Off scale", "Agra", "Uttar Pradesh", C, "40,80,20,5,25,30", "612",
         "-0.0001", "2026-06-29"),                               # AQI outside 0–500
    _row("STN_033", "London", "London", "UK", "51.5072,-0.1276", "40,80,20,5,25,30", "105",
         "0.0002", "2026-06-29"),                                # outside India
    # Exact duplicate (collapsed) and conflicting duplicate (both dropped)
    _row("STN_001", "Station A1", "Town1", "Maharashtra", A, "40,80,20,5,25,30", "105",
         "0.0002", "2026-06-29"),
    _row("STN_041", "Conflict", "Pune", "Maharashtra", C, "40,80,20,5,25,30", "105",
         "-0.0001", "2026-06-29"),
    _row("STN_041", "Conflict", "Pune", "Maharashtra", C, "40,80,20,5,25,30", "140",
         "-0.0001", "2026-06-29"),
    # More valid stations on the shared fallback coordinate A: keeps the defect rate
    # realistic (5 of 21 rows rejected ≈ 24%; the team file has 12%) so the source
    # passes the contract gate and is used as UNVERIFIED
    *[_row(f"STN_1{i:02d}", f"Station A{6 + i}", f"Town{6 + i}", "Maharashtra", A,
           "40,80,20,5,25,30", "105", "0.0002", "2026-06-29") for i in range(1, 7)],
]

TEAM_CLUSTERS = [
    {   # every member on coordinate A: a duplicate-coordinate artefact
        "cluster_id": 0, "station_count": 6, "mean_latitude": 19.076, "mean_longitude": 72.8777,
        "mean_hcho": 0.0002, "mean_co_column": 0.03,
        "stations": [f"Station A{i}" for i in range(1, 7)],
    },
    {
        "cluster_id": 1, "station_count": 3, "mean_latitude": 27.4, "mean_longitude": 76.5,
        "mean_hcho": 0.0003, "mean_co_column": 0.0,
        "stations": ["Station B1", "Station B2", "Station C1"],
    },
]


def _write(path: Path, lines: list[str]) -> Path:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


@pytest.fixture
def team_csv(tmp_path: Path) -> Path:
    return _write(tmp_path / "analysis_ready_dataset.csv", [HEADER, *TEAM_ROWS])


@pytest.fixture
def team_clusters(tmp_path: Path) -> Path:
    path = tmp_path / "cluster_summary.json"
    path.write_text(json.dumps(TEAM_CLUSTERS), encoding="utf-8")
    return path


def _model_dir(root: Path, summary: dict, importances: dict | None = None) -> Path:
    root.mkdir(parents=True)
    (root / "lightgbm_model.joblib").write_bytes(b"")  # presence only; never unpickled
    (root / "lightgbm_evaluation_metrics.json").write_text(
        json.dumps({"R2": 0.41, "RMSE": 52.0, "MAE": 38.0, "MBE": 1.2}), encoding="utf-8"
    )
    (root / "lightgbm_feature_importances.json").write_text(
        json.dumps(importances or {"Wind Speed": 30, "HCHO": 50, "Temperature": 20}),
        encoding="utf-8",
    )
    (root / "lightgbm_training_summary.json").write_text(json.dumps(summary), encoding="utf-8")
    return root


# Every key the trust gate requires (synthetic test values, not a real run)
VALIDATED = {
    "model_type": "LGBMRegressor", "task": "same_day_estimation",
    "target_column": "AQI", "test_samples": 76,
    "feature_names": ["Wind Speed", "HCHO", "Temperature"],
    "trained_at": "2026-07-20T10:00:00Z", "split_strategy": "temporal",
    "reproducibility": {"lightgbm_version": "4.5.0", "sklearn_version": "1.5.2"},
    "input_example": [{"Wind Speed": 2.1, "HCHO": 0.0002, "Temperature": 31.0}],
}
PROBE_CHECKS = {"artifact_loads", "model_object_type", "feature_schema_matches",
                "dependency_versions", "prediction_schema"}


def _probe(**overrides: object) -> dict:
    """What app.data.model_probe reports for a sound LightGBM pipeline (test double)."""
    report: dict = {
        "loaded": True, "error": None, "object_type": "sklearn.pipeline.Pipeline",
        "steps": [
            {"name": "preprocessor",
             "type": "sklearn.compose._column_transformer.ColumnTransformer"},
            {"name": "regressor", "type": "lightgbm.sklearn.LGBMRegressor"},
        ],
        "final_estimator": "lightgbm.sklearn.LGBMRegressor",
        "feature_names_in": ["Wind Speed", "HCHO", "Temperature"],
        "versions": {"lightgbm": "4.5.1", "sklearn": "1.5.0", "joblib": "1.4.2"},
        "prediction": {"rows": 1, "outputs": 1, "finite": True},
    }
    report.update(overrides)
    return report


def _failed(assessment) -> str:
    return " | ".join(c.detail for c in assessment.failed("blocking", "restricting"))
# Exactly the keys model_training/lightgbm_model.py (PR #7) writes today
TEAM_TRAINER = {
    "target_column": "AQI", "train_samples": 300, "validation_samples": 76,
    "test_samples": 76, "features_count": 3, "validation_status": "PASS",
    "reproducibility": {"python_version": "3.11.9", "lightgbm_version": "9.9.9",
                        "sklearn_version": "9.9.9", "random_seed": 42},
}


def _settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, AUTO_DISCOVER_TEAM_OUTPUTS=False, **overrides)


@pytest.fixture(autouse=True)
def _reset_sources():
    sources.reset()
    yield
    sources.reset()


# ── Central rules ──────────────────────────────────────────────────────────────

class TestCentralRules:
    @pytest.mark.parametrize(
        ("pollutants", "ok"),
        [
            ({"pm25": 40.0, "no2": 20.0, "so2": 5.0}, True),
            ({"pm10": 80.0, "co": 1.0, "o3": 30.0}, True),
            ({"no2": 20.0, "so2": 5.0, "co": 1.0, "o3": 30.0}, False),  # no particulate
            ({"pm25": 40.0, "pm10": 80.0, "no2": None}, False),          # only two present
        ],
    )
    def test_cpcb_minimum(self, pollutants: dict, ok: bool) -> None:
        assert meets_cpcb_minimum(pollutants) is ok

    def test_india_bounds(self) -> None:
        assert in_india(28.61, 77.21) and in_india(11.62, 92.73)  # Delhi, Port Blair
        assert not in_india(51.5, -0.12) and not in_india(0.0, 0.0)


# ── Team dataset (PR #7 / PR #8 analysis_ready_dataset.csv) ─────────────────────

class TestTeamDataset:
    def test_rows_rejected_by_reason_and_duplicates(self, team_csv: Path) -> None:
        q = load_dataset(team_csv).quality
        assert q.rows_read == len(TEAM_ROWS) == 21
        assert q.rejected["below_cpcb_minimum"] == 1
        assert q.rejected["invalid_aqi"] == 1
        assert q.rejected["outside_india"] == 1
        assert q.duplicates_collapsed == 1
        assert q.conflicting_duplicates_dropped == 2
        assert q.rows_accepted == 15 and q.stations == 15

    def test_shared_coordinates_flag_approximate_locations(self, team_csv: Path) -> None:
        ds = load_dataset(team_csv)
        assert ds.quality.distinct_locations == 3
        assert ds.quality.stations_sharing_coordinates == 14
        assert ds.location_quality == "approximate"
        # Coordinates are preserved as reported — never "corrected"
        assert {o.location for o in ds.observations} == {
            (19.076, 72.8777), (26.9124, 75.7873), (28.6139, 77.209),
        }

    def test_values_preserved_and_flags(self, team_csv: Path) -> None:
        ds = load_dataset(team_csv)
        obs = ds.latest_for("STN_021")
        assert obs is not None
        assert (obs.aqi, obs.pm25, obs.co, obs.hcho_mol_m2) == (300, 90.0, 35.0, -0.0001)
        assert obs.hcho_observed_on == date(2026, 6, 29)
        codes = [code for code, _ in ds.quality.station_limitations()]
        assert codes == ["approximate_coordinates", "rows_rejected", "co_unit_unverified",
                         "single_date"]
        assert [c for c, _ in ds.quality.hcho_limitations()] == [
            "satellite_date_mismatch", "approximate_coordinates",
        ]

    def test_satellite_samples_independent_of_ground_aqi(self, team_csv: Path) -> None:
        ds = load_dataset(team_csv)
        # 21 rows: London is outside India; every other row has a valid satellite sample
        assert ds.quality.hcho_samples == len(ds.hcho_samples) == 20
        assert "STN_031" in {s.station_id for s in ds.hcho_samples}  # AQI rejected
        assert ds.quality.hcho_dates == (date(2026, 6, 27), date(2026, 6, 29))
        assert ds.hcho_date_basis == "satellite_observation_date"

    def test_undated_satellite_value_is_not_mixed_with_station_dates(
        self, tmp_path: Path
    ) -> None:
        undated = TEAM_ROWS[8].replace("-0.0001,2026-06-29", "-0.0001,")
        ds = load_dataset(_write(tmp_path / "u.csv", [HEADER, TEAM_ROWS[0], undated]))
        assert [s.station_id for s in ds.hcho_samples] == ["STN_001"]
        assert len(ds) == 2  # the observation itself is still accepted

    def test_dataset_with_only_rejected_rows_is_rejected(self, tmp_path: Path) -> None:
        from app.data.dataset import DatasetError

        path = _write(tmp_path / "bad.csv", [HEADER, TEAM_ROWS[9], TEAM_ROWS[10]])
        with pytest.raises(DatasetError, match="no valid observations"):
            load_dataset(path)


class TestTeamDatasetEndpoints:
    @pytest.fixture(autouse=True)
    def _load(self, team_csv: Path) -> None:
        load_configured_sources(_settings(DATASET_PATH=str(team_csv)))

    async def test_sources_report_limitations_and_quality(self, client_no_db: AsyncClient) -> None:
        listed = (await client_no_db.get("/api/v1/sources")).json()["sources"]
        aqi = next(s for s in listed if s["domain"] == "aqi")
        assert aqi["kind"] == "local"
        assert "not recomputed" in aqi["detail"]
        codes = {lim["code"] for lim in aqi["limitations"]}
        assert {"approximate_coordinates", "rows_rejected", "co_unit_unverified"} <= codes
        assert aqi["quality"]["coordinate_quality"] == "approximate"
        assert aqi["quality"]["rejected_below_cpcb_minimum"] == 1

    async def test_stations_and_readings_carry_location_quality(
        self, client_no_db: AsyncClient
    ) -> None:
        stations = (await client_no_db.get("/api/v1/stations", params={"limit": 50})).json()
        assert stations["count"] == 15
        assert {s["location_quality"] for s in stations["items"]} == {"approximate"}
        assert "STN_031" not in {s["station_id"] for s in stations["items"]}  # rejected row
        readings = (await client_no_db.get("/api/v1/aqi/daily")).json()["summary"]["readings"]
        assert {r["location_quality"] for r in readings} == {"approximate"}

    async def test_history_single_point(self, client_no_db: AsyncClient) -> None:
        data = (await client_no_db.get("/api/v1/aqi/history",
                                       params={"station_id": "STN_011"})).json()
        assert data["count"] == 1 and data["points"][0]["aqi_value"] == 158

    async def test_rejected_station_is_unknown(self, client_no_db: AsyncClient) -> None:
        resp = await client_no_db.get("/api/v1/aqi/history", params={"station_id": "STN_031"})
        assert resp.status_code == status.HTTP_404_NOT_FOUND

    async def test_hcho_trend_by_satellite_date_and_distinct_locations(
        self, client_no_db: AsyncClient
    ) -> None:
        data = (await client_no_db.get("/api/v1/hcho/trend")).json()
        assert data["date_basis"] == "satellite_observation_date"
        by_day = {p["obs_date"]: p for p in data["points"]}
        assert set(by_day) == {"2026-06-27", "2026-06-28", "2026-06-29"}
        # 06-27 exists only through a row rejected for its AQI: its satellite sample counts
        assert (by_day["2026-06-27"]["station_count"], by_day["2026-06-27"]["location_count"]) \
            == (1, 1)
        # 06-28: two stations on one coordinate = one satellite sample
        assert (by_day["2026-06-28"]["station_count"], by_day["2026-06-28"]["location_count"]) \
            == (2, 1)
        # 06-29: twelve stations on A (one sample) + C1, STN_032, STN_041 on C (negative
        # retrieval kept) = 2 locations; London (outside India) never counts
        june29 = by_day["2026-06-29"]
        assert (june29["station_count"], june29["location_count"]) == (15, 2)
        expected = (0.0002 + -0.0001) / 2 * MOL_M2_TO_1E15_MOLEC_CM2
        assert june29["mean_column_density"] == pytest.approx(expected, abs=1e-3)

    async def test_trend_window_anchors_on_latest_satellite_date(
        self, client_no_db: AsyncClient
    ) -> None:
        data = (await client_no_db.get("/api/v1/hcho/trend", params={"days": 1})).json()
        assert [p["obs_date"] for p in data["points"]] == ["2026-06-29"]

    async def test_forecast_stays_simulated(self, client_no_db: AsyncClient) -> None:
        data = (await client_no_db.get("/api/v1/forecast",
                                       params={"station_id": "STN_011"})).json()
        assert data["forecast_kind"] == "simulated"
        assert data["model_metrics"]["r_squared"] is None


# ── Team hotspot clusters (PR #7 cluster_summary.json) ──────────────────────────

class TestTeamHotspots:
    async def test_clusters_on_shared_coordinates_are_flagged(
        self, client_no_db: AsyncClient, team_csv: Path, team_clusters: Path
    ) -> None:
        load_configured_sources(_settings(
            DATASET_PATH=str(team_csv), HCHO_HOTSPOTS_PATH=str(team_clusters)
        ))
        status_ = sources.status("hcho")
        assert status_.kind == "local"
        assert status_.has("approximate_coordinates")
        assert status_.has("no_observation_date") and status_.has("no_radius_or_confidence")
        assert status_.quality["single_location_clusters"] == 1
        items = (await client_no_db.get("/api/v1/hcho/hotspots")).json()["items"]
        by_id = {i["hotspot_id"]: i for i in items}
        assert by_id["HS-0"]["member_locations"] == 1 and by_id["HS-0"]["station_count"] == 6
        assert by_id["HS-1"]["member_locations"] == 2  # B1, B2 share B; C1 on C
        assert {i["location_quality"] for i in items} == {"approximate"}
        # Values preserved (unit-converted only); nothing invented
        assert by_id["HS-0"]["column_density"] == pytest.approx(0.0002 * MOL_M2_TO_1E15_MOLEC_CM2,
                                                                abs=1e-3)
        assert by_id["HS-0"]["radius_km"] is None and by_id["HS-0"]["confidence"] is None
        assert by_id["HS-0"]["detected_at"] is None

    def test_unmatched_members_mean_unverified_coordinates(self, team_clusters: Path) -> None:
        # Team clusters but the placeholder station dataset: no member can be matched
        load_configured_sources(_settings(HCHO_HOTSPOTS_PATH=str(team_clusters)))
        assert sources.status("hcho").has("unverified_coordinates")
        assert not sources.status("hcho").has("approximate_coordinates")


# ── Model artefact production gate (PR #7 LightGBM) ─────────────────────────────

class TestModelGate:
    def test_valid_contract_and_load_probe_is_promotable(self, tmp_path: Path) -> None:
        artifact = load_model_artifact(_model_dir(tmp_path / "run", VALIDATED))
        assessment = assess_model(artifact, _probe())
        assert assessment.promotable, _failed(assessment)
        assert assessment.capabilities["model_metrics"].enabled
        assert not assessment.capabilities["model_forecast"].enabled

    def test_complete_metadata_without_load_check_stays_unverified(self, tmp_path: Path) -> None:
        artifact = load_model_artifact(_model_dir(tmp_path / "run", VALIDATED))
        assessment = assess_model(artifact, None)
        assert assessment.usable and not assessment.promotable
        assert {c.name for c in assessment.failed("restricting")} == PROBE_CHECKS
        assert not assessment.capabilities["global_importance"].enabled

    def test_team_trainer_output_is_not_validated(self, tmp_path: Path) -> None:
        artifact = load_model_artifact(_model_dir(tmp_path / "run", TEAM_TRAINER))
        failed = {c.name for c in assess_model(artifact, _probe()).failed("restricting")}
        assert {"model_type_recorded", "task_same_day_estimation", "feature_names",
                "training_date", "split_strategy", "prediction_schema_recorded"} <= failed

    @pytest.mark.parametrize(
        ("change", "importances", "expected"),
        [
            ({"split_strategy": "random"}, None, "not time-based"),
            ({"feature_names": ["PM2.5", "HCHO", "Temperature"]},
             {"num__PM2.5": 70, "HCHO": 20, "Temperature": 10}, "Target leakage"),
            ({"task": "forecast", "forecast_horizon_hours": 72}, None,
             "not a same-day estimator"),
            ({"target_column": "PM2.5"}, None, "expected 'AQI'"),
            ({}, {"Wind Speed": 30, "Rainfall": 70}, "not in feature_names"),
            ({"model_type": "RandomForestRegressor"}, None, "'RandomForestRegressor'"),
            ({"input_example": None}, None, "No input_example"),
        ],
    )
    def test_metadata_rejections(self, tmp_path: Path, change: dict, importances: dict | None,
                                 expected: str) -> None:
        artifact = load_model_artifact(
            _model_dir(tmp_path / "run", {**VALIDATED, **change}, importances)
        )
        assessment = assess_model(artifact, _probe())
        assert not assessment.promotable and expected in _failed(assessment)

    @pytest.mark.parametrize(
        ("probe", "check"),
        [
            ({"loaded": False, "error": "cannot load artefact: EOFError"}, "artifact_loads"),
            ({"final_estimator": "sklearn.ensemble.RandomForestRegressor"},
             "model_object_type"),
            ({"steps": []}, "model_object_type"),
            ({"feature_names_in": ["Wind Speed", "HCHO"]}, "feature_schema_matches"),
            ({"versions": {"lightgbm": "3.3.5", "sklearn": "1.5.0"}}, "dependency_versions"),
            ({"prediction": {"rows": 1, "outputs": 1, "finite": False}}, "prediction_schema"),
            ({"prediction": {"rows": 1, "error": "KeyError: 'HCHO'"}}, "prediction_schema"),
        ],
    )
    def test_load_probe_rejections(self, tmp_path: Path, probe: dict, check: str) -> None:
        artifact = load_model_artifact(_model_dir(tmp_path / "run", VALIDATED))
        failed = {c.name for c in assess_model(artifact, _probe(**probe)).failed("restricting")}
        assert check in failed

    def test_one_hot_importances_match_base_features(self, tmp_path: Path) -> None:
        summary = {**VALIDATED, "feature_names": ["Wind Speed", "Season"],
                   "input_example": [{"Wind Speed": 2.0, "Season": "Monsoon"}]}
        imps = {"num__Wind Speed": 60, "cat__Season_Monsoon": 40}
        artifact = load_model_artifact(_model_dir(tmp_path / "run", summary, imps))
        assert assess_model(artifact, _probe(feature_names_in=["Wind Speed", "Season"])).promotable

    async def test_unvalidated_artefact_is_withheld(
        self, client_no_db: AsyncClient, tmp_path: Path
    ) -> None:
        run = _model_dir(tmp_path / "run", TEAM_TRAINER)
        load_configured_sources(_settings(ML_MODEL_PATH=str(run), ENABLE_ML_ENDPOINTS=True))
        model = sources.status("model")
        assert (model.kind, model.status, model.trust, model.promoted) == (
            "local", "withheld", "unverified", False)
        assert model.has("not_validated") and "found but not validated" in model.detail
        assert sources.model is None and sources.status("xai_global").kind == "unavailable"
        resp = await client_no_db.get("/api/v1/xai/global-importance")
        assert resp.status_code == status.HTTP_404_NOT_FOUND
        assert "not validated" in json.dumps(resp.json())

    def test_complete_metadata_needs_the_load_check(self, tmp_path: Path) -> None:
        run = _model_dir(tmp_path / "run", VALIDATED)
        load_configured_sources(_settings(ML_MODEL_PATH=str(run), ENABLE_ML_ENDPOINTS=True))
        model = sources.status("model")
        assert model.status == "withheld" and "MODEL_LOAD_CHECK" in model.reason

    async def test_promoted_artefact_is_served(
        self, client_no_db: AsyncClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sources_module, "run_probe", lambda directory, python: _probe())
        run = _model_dir(tmp_path / "run", VALIDATED)
        load_configured_sources(_settings(ML_MODEL_PATH=str(run), ENABLE_ML_ENDPOINTS=True,
                                          MODEL_LOAD_CHECK=True))
        model = sources.status("model")
        assert (model.kind, model.trust, model.promoted) == ("local", "trusted", True)
        assert sources.status("xai_global").trust == "trusted"
        data = (await client_no_db.get("/api/v1/xai/global-importance")).json()
        assert data["model_metrics"]["r_squared"] == 0.41
        assert data["model_metrics"]["training_date"] == "2026-07-20"
        assert data["model_metrics"]["validation_period"] == "Held-out temporal split (76 rows)"
        forecast = (await client_no_db.get("/api/v1/forecast",
                                           params={"station_id": "DL001"})).json()
        assert forecast["forecast_kind"] == "simulated"  # an estimator never becomes a forecast

    def test_discovered_model_in_trainer_output_dir(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(sources_module, "run_probe", lambda directory, python: _probe())
        run = _model_dir(tmp_path / "repo", VALIDATED)
        monkeypatch.setattr(sources_module, "MODEL_DISCOVERY_DIRS", (run,))
        load_configured_sources(Settings(_env_file=None, ENABLE_ML_ENDPOINTS=True,
                                         MODEL_LOAD_CHECK=True))
        model = sources.status("model")
        assert (model.origin, model.promoted) == ("discovered", True)

    def test_discovered_broken_model_is_reported_not_fatal(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        run = tmp_path / "repo"
        run.mkdir()
        (run / "lightgbm_model.joblib").write_bytes(b"")  # metrics etc. missing
        monkeypatch.setattr(sources_module, "MODEL_DISCOVERY_DIRS", (run,))
        load_configured_sources(Settings(_env_file=None, ENABLE_ML_ENDPOINTS=True))
        model = sources.status("model")
        assert model.kind == "unavailable" and "incompatible" in model.detail

    def test_explicit_broken_model_fails_startup(self, tmp_path: Path) -> None:
        run = tmp_path / "run"
        run.mkdir()
        with pytest.raises(ModelArtifactError):
            load_configured_sources(_settings(ML_MODEL_PATH=str(run), ENABLE_ML_ENDPOINTS=True))


# ── After PR #7 / PR #8 merge: discovery of their documented locations ──────────

class TestPostMergeDiscovery:
    def test_v1_preferred_and_v2_named(
        self, tmp_path: Path, team_csv: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        v2 = _write(tmp_path / "analysis_ready_dataset_v2.csv", [
            "station_id,station_name,city,state,station_latitude,station_longitude,"
            "network_source,timestamp_utc_str,PM2.5,PM10,NO2,AQI",
            "ST_a1,V2 A,Delhi,Delhi,28.63,77.29,CPCB,2026-07-13T06:00:00Z,90,180,60,250",
        ])
        monkeypatch.setitem(sources_module.DISCOVERY_PATHS, "dataset", (team_csv, v2))
        load_configured_sources(Settings(_env_file=None))
        aqi = sources.status("aqi")
        assert (aqi.kind, aqi.name) == ("local", "analysis_ready_dataset.csv")
        assert "Also found, not used" in aqi.detail
        assert "analysis_ready_dataset_v2.csv" in aqi.detail

    def test_incompatible_v1_falls_through_to_v2(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        v1 = _write(tmp_path / "analysis_ready_dataset.csv", ["Station ID,AQI", "X,1"])
        v2 = _write(tmp_path / "analysis_ready_dataset_v2.csv", [
            "station_id,station_name,city,state,station_latitude,station_longitude,"
            "timestamp_utc_str,PM2.5,PM10,NO2,AQI",
            "ST_a1,V2 A,Delhi,Delhi,28.63,77.29,2026-07-13T06:00:00Z,90,180,60,250",
        ])
        monkeypatch.setitem(sources_module.DISCOVERY_PATHS, "dataset", (v1, v2))
        load_configured_sources(Settings(_env_file=None))
        aqi = sources.status("aqi")
        assert aqi.name == "analysis_ready_dataset_v2.csv"
        assert "incompatible" in aqi.detail

    def test_dataset_and_clusters_discovered_together(
        self, team_csv: Path, team_clusters: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setitem(sources_module.DISCOVERY_PATHS, "dataset", (team_csv,))
        monkeypatch.setitem(sources_module.DISCOVERY_PATHS, "hcho", (team_clusters,))
        load_configured_sources(Settings(_env_file=None))
        assert sources.status("aqi").kind == sources.status("hcho").kind == "local"
        assert sources.status("hcho").has("approximate_coordinates")
        assert sources.status("fire").kind == "placeholder"  # still no team fire source

    def test_missing_team_outputs_fall_back(self, tmp_path: Path,
                                            monkeypatch: pytest.MonkeyPatch) -> None:
        for domain in ("dataset", "hcho"):
            monkeypatch.setitem(sources_module.DISCOVERY_PATHS, domain, (tmp_path / "nope",))
        load_configured_sources(Settings(_env_file=None))
        assert sources.status("aqi").kind == sources.status("hcho").kind == "placeholder"
