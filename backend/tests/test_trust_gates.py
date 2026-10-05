"""
Data trust / promotion gates: availability is not trust.

Deterministic, synthetic fixtures shaped like the team's analysis_ready_dataset
(v1 columns incl. "HCHO Obs Date"): a CLEAN variant that must be promoted, and
variants that reproduce each defect class. No team file is read or modified.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import pytest

from app.core.config import Settings
from app.data import sources as sources_module
from app.data.dataset import load_dataset
from app.data.model_probe import run_probe
from app.data.sources import load_configured_sources, sources
from app.data.trust import assess_dataset, assess_hcho_trend

if TYPE_CHECKING:
    from pathlib import Path

    from httpx import AsyncClient

pytestmark = pytest.mark.unit

HEADER = (
    "Station ID,Station Name,City,State,Latitude,Longitude,Date,Time,"
    "PM2.5,PM10,NO2,SO2,CO,O3,AQI,HCHO,HCHO Obs Date"
)
# Six stations at distinct positions in six cities (synthetic values)
STATIONS = [
    ("CL_01", "Clean A", "Delhi", "Delhi", "28.6300", "77.2400"),
    ("CL_02", "Clean B", "Mumbai", "Maharashtra", "19.0700", "72.8800"),
    ("CL_03", "Clean C", "Chennai", "Tamil Nadu", "13.0800", "80.2700"),
    ("CL_04", "Clean D", "Kolkata", "West Bengal", "22.5700", "88.3600"),
    ("CL_05", "Clean E", "Pune", "Maharashtra", "18.5200", "73.8500"),
    ("CL_06", "Clean F", "Jaipur", "Rajasthan", "26.9100", "75.7900"),
]


def _rows(day: str, hcho_day: str, pm: str = "40,80", co: str = "1.1") -> list[str]:
    return [
        f"{sid},{name},{city},{state},{lat},{lon},{day},00:00:00,{pm},20,5,{co},30,105,"
        f"0.0002,{hcho_day}"
        for sid, name, city, state, lat, lon in STATIONS
    ]


CLEAN = [HEADER, *_rows("2026-07-13", "2026-07-13"), *_rows("2026-07-14", "2026-07-14")]


def _write(path: Path, lines: list[str]) -> Path:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _settings(**overrides: object) -> Settings:
    return Settings(_env_file=None, AUTO_DISCOVER_TEAM_OUTPUTS=False, **overrides)


@pytest.fixture(autouse=True)
def _reset_sources():
    sources.reset()
    yield
    sources.reset()


@pytest.fixture
def clean_csv(tmp_path: Path) -> Path:
    return _write(tmp_path / "analysis_ready_dataset.csv", CLEAN)


def _failed(assessment) -> set[str]:
    return {c.name for c in assessment.failed("blocking", "restricting")}


# ── Dataset gate ───────────────────────────────────────────────────────────────

class TestDatasetGate:
    def test_clean_team_source_is_promoted(self, clean_csv: Path) -> None:
        load_configured_sources(_settings(DATASET_PATH=str(clean_csv)))
        aqi = sources.status("aqi")
        assert (aqi.kind, aqi.trust, aqi.promoted, aqi.origin) == (
            "local", "trusted", True, "configured")
        assert aqi.assessment.summary()["status"] == "passed"
        assert aqi.capability("station_maps").enabled
        assert "promoted" in aqi.reason and not aqi.limitations

    def test_partially_valid_source_is_used_but_not_promoted(self, tmp_path: Path) -> None:
        # 6 stations on one fallback point (different cities): coordinates unsafe
        shared = [row.replace(row.split(",")[4] + "," + row.split(",")[5], "19.0760,72.8777")
                  for row in CLEAN[1:]]
        load_configured_sources(_settings(
            DATASET_PATH=str(_write(tmp_path / "a.csv", [HEADER, *shared]))))
        aqi = sources.status("aqi")
        assert (aqi.kind, aqi.status, aqi.trust, aqi.promoted) == (
            "local", "available", "unverified", False)
        assert aqi.capability("aqi_tables").enabled
        assert not aqi.capability("station_maps").enabled
        assert "coordinate quality insufficient for spatial maps" in aqi.reason
        assert aqi.quality["spatial"]["locations_spanning_cities"] == 1

    def test_multi_city_fallback_point_blocks_maps_even_when_rare(self, tmp_path: Path) -> None:
        # Only 2 of 26 stations share a point (< 10 %) — but from two different cities
        many = [f"S_{i:02d},Stn {i},City{i},Delhi,{20 + i * 0.5:.4f},78.0000,2026-07-14,"
                "00:00:00,40,80,20,5,1.1,30,105,0.0002,2026-07-14" for i in range(24)]
        twins = [f"T_{i},Twin {i},Town{i},Delhi,28.6139,77.2090,2026-07-14,00:00:00,"
                 "40,80,20,5,1.1,30,105,0.0002,2026-07-14" for i in (1, 2)]
        ds = load_dataset(_write(tmp_path / "m.csv", [HEADER, *many, *twins]))
        assert not ds.quality.approximate_coordinates
        assert ds.quality.locations_spanning_cities == 1
        assert "coordinate_quality" in _failed(assess_dataset(ds))

    def test_pm_inconsistency_is_restricting(self, tmp_path: Path) -> None:
        rows = [HEADER, *_rows("2026-07-14", "2026-07-14", pm="90,40")]
        ds = load_dataset(_write(tmp_path / "p.csv", rows))
        assert ds.quality.pm25_above_pm10 == 6
        assert "pm_consistency" in _failed(assess_dataset(ds))
        assert "pm_inconsistent" in [c for c, _ in ds.quality.station_limitations()]

    def test_row_structure_ids_dates_and_coordinates(self, tmp_path: Path) -> None:
        good = _rows("2026-07-14", "2026-07-14")
        bad = [
            "X1,Short row",                                                    # malformed
            good[0].replace("CL_01", "X" * 60),                                # invalid id
            good[1].replace("2026-07-14,00:00", "2999-01-01,00:00", 1),        # future
            good[2].replace("13.0800,80.2700", ","),                           # missing coords
            good[3] + ",extra",                                                # malformed
        ]
        ds = load_dataset(_write(tmp_path / "r.csv", [HEADER, *good, *bad]))
        r = ds.quality.rejected
        assert (r["malformed_row"], r["invalid_station_id"], r["future_timestamp"],
                r["missing_coordinates"]) == (2, 1, 1, 1)

    def test_unusable_numeric_cells_are_counted_not_repaired(self, tmp_path: Path) -> None:
        rows = [HEADER, *_rows("2026-07-14", "2026-07-14")]
        rows[1] = rows[1].replace(",40,80,", ",abc,80,")
        ds = load_dataset(_write(tmp_path / "n.csv", rows))
        assert ds.quality.invalid_cells["pm25"] == 1
        assert ds.latest_for("CL_01").pm25 is None
        assert "numeric_cells" in _failed(assess_dataset(ds))

    def test_contract_failure_falls_back_with_reason_not_crash(self, tmp_path: Path) -> None:
        # 4 of 6 rows below the CPCB minimum: readable but not usable (67 % rejected)
        rows = [HEADER, *_rows("2026-07-14", "2026-07-14")]
        for i in range(1, 5):
            rows[i] = rows[i].replace(",40,80,20,5,", ",,,20,5,")
        path = _write(tmp_path / "analysis_ready_dataset.csv", rows)
        load_configured_sources(_settings(DATASET_PATH=str(path)))  # explicit: no crash
        aqi = sources.status("aqi")
        assert (aqi.kind, aqi.trust, aqi.promoted) == ("placeholder", "placeholder", False)
        assert aqi.candidate is not None and aqi.candidate.origin == "configured"
        assert "contract gate" in aqi.candidate.reason
        assert aqi.reason.startswith("Placeholder in use: the team dataset")

    def test_malformed_discovered_source_is_named_as_candidate(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        bad = _write(tmp_path / "analysis_ready_dataset.csv", ["Station ID,AQI", "X,1"])
        monkeypatch.setitem(sources_module.DISCOVERY_PATHS, "dataset", (bad,))
        load_configured_sources(Settings(_env_file=None))
        aqi = sources.status("aqi")
        assert aqi.kind == "placeholder" and aqi.candidate.origin == "discovered"
        assert "incompatible" in aqi.candidate.reason

    def test_unreadable_explicit_source_still_fails_startup(self, tmp_path: Path) -> None:
        from app.data.dataset import DatasetError

        bad = _write(tmp_path / "bad.csv", ["Station ID,AQI", "X,1"])
        with pytest.raises(DatasetError):
            load_configured_sources(_settings(DATASET_PATH=str(bad)))

    def test_require_trusted_team_data_keeps_placeholder(self, tmp_path: Path) -> None:
        shared = [row.replace("28.6300,77.2400", "19.0700,72.8800") for row in CLEAN]
        path = _write(tmp_path / "analysis_ready_dataset.csv", shared)
        load_configured_sources(_settings(DATASET_PATH=str(path), REQUIRE_TRUSTED_TEAM_DATA=True))
        aqi = sources.status("aqi")
        assert aqi.kind == "placeholder" and "REQUIRE_TRUSTED_TEAM_DATA" in aqi.candidate.reason

    def test_require_trusted_still_uses_a_promoted_source(self, clean_csv: Path) -> None:
        load_configured_sources(_settings(DATASET_PATH=str(clean_csv),
                                          REQUIRE_TRUSTED_TEAM_DATA=True))
        assert sources.status("aqi").promoted

    def test_placeholders_disabled_reports_rejected_candidate(self, tmp_path: Path) -> None:
        rows = [HEADER, *[r.replace(",40,80,20,5,", ",,,20,5,")
                          for r in _rows("2026-07-14", "2026-07-14")[:4]],
                *_rows("2026-07-14", "2026-07-14")[4:]]
        path = _write(tmp_path / "analysis_ready_dataset.csv", rows)
        load_configured_sources(_settings(DATASET_PATH=str(path), ENABLE_PLACEHOLDER_DATA=False))
        aqi = sources.status("aqi")
        assert (aqi.kind, aqi.status, aqi.trust) == ("unavailable", "unavailable", "unavailable")
        assert "placeholders are disabled" in aqi.reason


# ── HCHO trend gate ────────────────────────────────────────────────────────────

class TestHCHOTrendGate:
    def test_aligned_satellite_dates_at_distinct_positions_are_promotable(
        self, clean_csv: Path
    ) -> None:
        ds = load_dataset(clean_csv)
        assessment = assess_hcho_trend(ds)
        assert assessment.promotable, _failed(assessment)
        assert ds.quality.hcho_distinct_samples == 12

    def test_without_overpass_dates_it_is_not_promotable(self, tmp_path: Path) -> None:
        rows = [line.rsplit(",", 1)[0] for line in CLEAN]  # drop the HCHO Obs Date column
        ds = load_dataset(_write(tmp_path / "nd.csv", rows))
        assert ds.hcho_date_basis == "station_observation_date"
        assert "hcho_observation_dates" in _failed(assess_hcho_trend(ds))

    def test_undated_values_are_excluded_and_counted(self, tmp_path: Path) -> None:
        rows = list(CLEAN)
        rows[1] = rows[1].rsplit(",", 1)[0] + ","
        ds = load_dataset(_write(tmp_path / "u.csv", rows))
        assert ds.quality.hcho_undated == 1 and len(ds.hcho_samples) == 11
        assert "hcho_observation_dates" in _failed(assess_hcho_trend(ds))

    def test_conflicting_samples_at_one_location_date(self, tmp_path: Path) -> None:
        twin = CLEAN[1].replace("CL_01", "CL_99").replace("0.0002", "0.0009")
        ds = load_dataset(_write(tmp_path / "c.csv", [*CLEAN, twin]))
        assert ds.quality.hcho_conflicting_samples == 1
        assert "hcho_conflicting_samples" in _failed(assess_hcho_trend(ds))

    def test_far_satellite_dates_are_restricting(self, tmp_path: Path) -> None:
        rows = [HEADER, *_rows("2026-07-14", "2026-06-28")]
        ds = load_dataset(_write(tmp_path / "f.csv", rows))
        assert "hcho_date_alignment" in _failed(assess_hcho_trend(ds))

    def test_trend_trust_is_independent_of_aqi_trust(self, tmp_path: Path) -> None:
        # CO in the wrong unit makes the AQI source unverified; HCHO is unaffected
        rows = [HEADER, *_rows("2026-07-13", "2026-07-13", co="27"),
                *_rows("2026-07-14", "2026-07-14", co="27")]
        load_configured_sources(_settings(
            DATASET_PATH=str(_write(tmp_path / "analysis_ready_dataset.csv", rows))))
        assert sources.status("aqi").trust == "unverified"
        assert sources.status("hcho_trend").trust == "trusted"


# ── Hotspot gate ───────────────────────────────────────────────────────────────

class TestHotspotGate:
    def _clusters(self, tmp_path: Path, clusters: list[dict]) -> Path:
        path = tmp_path / "cluster_summary.json"
        path.write_text(json.dumps(clusters), encoding="utf-8")
        return path

    def test_dated_clusters_on_distinct_positions_are_promoted(
        self, tmp_path: Path, clean_csv: Path
    ) -> None:
        path = self._clusters(tmp_path, [{
            "cluster_id": 0, "station_count": 2, "mean_latitude": 23.85, "mean_longitude": 75.06,
            "mean_hcho": 0.0002, "stations": ["Clean A", "Clean B"],
            "observation_date": "2026-07-14",
        }])
        load_configured_sources(_settings(DATASET_PATH=str(clean_csv),
                                          HCHO_HOTSPOTS_PATH=str(path)))
        hcho = sources.status("hcho")
        assert (hcho.trust, hcho.promoted) == ("trusted", True)
        assert hcho.capability("hotspot_map").enabled

    def test_inconsistent_member_count_and_undated(self, tmp_path: Path, clean_csv: Path) -> None:
        path = self._clusters(tmp_path, [{
            "cluster_id": 0, "station_count": 5, "mean_latitude": 23.85, "mean_longitude": 75.06,
            "mean_hcho": 0.0002, "stations": ["Clean A", "Clean B"],
        }])
        load_configured_sources(_settings(DATASET_PATH=str(clean_csv),
                                          HCHO_HOTSPOTS_PATH=str(path)))
        hcho = sources.status("hcho")
        assert hcho.trust == "unverified"
        assert {"cluster_structure", "observation_date"} <= _failed(hcho.assessment)
        assert hcho.capability("hotspot_table").enabled

    def test_duplicate_cluster_ids_break_the_contract(self, tmp_path: Path) -> None:
        from app.data.hotspots import HotspotFileError, load_hotspots

        item = {"cluster_id": 0, "mean_latitude": 20.0, "mean_longitude": 78.0,
                "mean_hcho": 0.0002}
        with pytest.raises(HotspotFileError, match="duplicate cluster_id"):
            load_hotspots(self._clusters(tmp_path, [item, item]))

    def test_placeholder_clusters_stay_mappable_with_a_team_dataset(self, clean_csv: Path) -> None:
        load_configured_sources(_settings(DATASET_PATH=str(clean_csv)))
        hcho = sources.status("hcho")
        assert hcho.trust == "placeholder"
        assert hcho.capability("hotspot_map").enabled
        assert "illustrative" in hcho.capability("hotspot_map").reason


# ── Fire, forecast, API ────────────────────────────────────────────────────────

class TestOtherDomains:
    def test_configured_fire_file_is_never_trusted_yet(self, tmp_path: Path) -> None:
        fires = tmp_path / "fires.json"
        fires.write_text(sources_module.PLACEHOLDERS["fire"].read_text(encoding="utf-8"),
                         encoding="utf-8")
        load_configured_sources(_settings(FIRE_EVENTS_PATH=str(fires)))
        fire = sources.status("fire")
        assert (fire.kind, fire.trust, fire.promoted) == ("local", "unverified", False)
        assert fire.capability("fire_alerts").enabled

    def test_forecast_is_simulated_even_with_a_promoted_dataset(self, clean_csv: Path) -> None:
        load_configured_sources(_settings(DATASET_PATH=str(clean_csv)))
        forecast = sources.status("forecast")
        assert (forecast.kind, forecast.trust, forecast.origin) == (
            "simulated", "simulated", "generated")


class TestSourcesAPI:
    async def test_trust_fields_for_every_domain(self, client_no_db: AsyncClient) -> None:
        load_configured_sources(_settings())
        listed = (await client_no_db.get("/api/v1/sources")).json()["sources"]
        for item in listed:
            assert {"status", "origin", "location", "trust", "promoted", "reason",
                    "validation", "capabilities", "candidate"} <= set(item)
            assert item["trust"] != "trusted" or item["promoted"]
            location = item["location"] or ""
            assert ":" not in location and not location.startswith("/")  # never absolute
        by_domain = {s["domain"]: s for s in listed}
        aqi = by_domain["aqi"]
        assert (aqi["trust"], aqi["origin"], aqi["status"]) == ("placeholder", "bundled",
                                                               "available")
        assert aqi["location"] == "backend/app/data/fixtures/placeholder_station_dataset.csv"
        assert aqi["validation"]["status"] == "passed"  # the fixture itself is clean
        assert aqi["capabilities"]["station_maps"]["enabled"] is True
        assert by_domain["forecast"]["validation"]["status"] == "not_applicable"
        assert by_domain["model"]["trust"] == "unavailable"

    async def test_unverified_team_source_in_api(
        self, client_no_db: AsyncClient, tmp_path: Path
    ) -> None:
        shared = [row.replace("28.6300,77.2400", "19.0700,72.8800") for row in CLEAN]
        path = _write(tmp_path / "analysis_ready_dataset.csv", shared)
        load_configured_sources(_settings(DATASET_PATH=str(path)))
        listed = (await client_no_db.get("/api/v1/sources")).json()["sources"]
        aqi = next(s for s in listed if s["domain"] == "aqi")
        assert (aqi["kind"], aqi["trust"], aqi["promoted"]) == ("local", "unverified", False)
        assert aqi["validation"]["status"] == "restricted"
        assert "coordinate_quality" in aqi["validation"]["failed"]
        assert aqi["capabilities"]["station_maps"]["enabled"] is False
        assert aqi["location"] == "analysis_ready_dataset.csv"  # outside the repo: name only


# ── Isolated model load probe ──────────────────────────────────────────────────

class TestModelProbe:
    def test_probe_runs_in_a_subprocess_and_never_raises(self, tmp_path: Path) -> None:
        (tmp_path / "lightgbm_model.joblib").write_bytes(b"not a pickle")
        (tmp_path / "lightgbm_training_summary.json").write_text("{}", encoding="utf-8")
        report = run_probe(tmp_path)
        assert report["loaded"] is False and report["error"]

    def test_probe_with_a_missing_interpreter(self, tmp_path: Path) -> None:
        report = run_probe(tmp_path, python=str(tmp_path / "no-such-python"))
        assert report["loaded"] is False and "could not run" in report["error"]
