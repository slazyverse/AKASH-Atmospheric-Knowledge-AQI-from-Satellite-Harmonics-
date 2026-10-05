"""
Data trust and promotion gates — availability is not trust.

A source can be AVAILABLE (a file exists and parses) without being TRUSTED.
Every major source is assessed by a gate made of validation checks:

  blocking     the contract: if one fails the source is not used at all
               (the domain falls back to the placeholder / unavailable)
  restricting  scientific quality: if one fails the source may still be used
               for the capabilities its checks allow, but it is not promoted
  info         reported for transparency, never decisive

Trust levels (per domain, reported by GET /api/v1/sources):

  trusted      team / live source that passed every blocking AND restricting
               check — promoted to the application's trusted primary source
  unverified   team source that passed the contract but failed at least one
               restricting check: in use only for the capabilities that are
               still safe (e.g. AQI tables), never presented as validated
  placeholder  bundled deterministic fixture — not real data
  simulated    synthetic algorithm (the forecast)
  unavailable  nothing is served

Capabilities are enabled per check, so a source with shared fallback
coordinates keeps its AQI tables but never enables station maps, and a model
whose metadata is incomplete never enables metrics or feature importance.

Nothing here modifies source data; the gates only read the adapters' reports.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal

from app.data.model_artifact import (
    ESTIMATOR_TASKS,
    LEAKY_FEATURES,
    TIME_BASED_SPLITS,
    base_feature,
)

if TYPE_CHECKING:
    from app.data.dataset import StationDataset
    from app.data.fires import FireRecord
    from app.data.hotspots import HotspotRecord
    from app.data.model_artifact import ModelArtifact

TrustLevel = Literal["trusted", "unverified", "placeholder", "simulated", "unavailable"]
Severity = Literal["blocking", "restricting", "info"]

# A source with more rejected rows than this is not used at all.
MAX_REJECTED_FRACTION_FOR_USE = 0.25
# A source with more rejected rows than this can be used but not promoted.
MAX_REJECTED_FRACTION_FOR_PROMOTION = 0.01

EXPECTED_MODEL_TYPES = frozenset({"lgbmregressor", "lightgbm", "lightgbm.lgbmregressor"})


@dataclass(frozen=True)
class Check:
    """One validation check: `detail` explains the outcome; `short` is the concise
    failure phrase used in one-line reasons (falls back to _SHORT, then detail)."""

    name: str
    passed: bool
    severity: Severity
    detail: str
    short: str = ""

    @property
    def phrase(self) -> str:
        return self.short or _SHORT.get(self.name) or self.detail.rstrip(".")


# Concise failure phrases for one-line reasons (badges); the full detail stays
# available in the validation report.
_SHORT: dict[str, str] = {
    "rows_usable": "too many rows rejected for use",
    "coordinate_quality": "coordinate quality insufficient for spatial maps",
    "co_unit": "CO unit unverified",
    "station_metadata": "conflicting station metadata",
    "numeric_cells": "unusable numeric cells",
    "hcho_samples_present": "no usable satellite HCHO samples",
    "hcho_numeric": "unusable HCHO cells",
    "hcho_observation_dates": "satellite overpass dates missing",
    "hcho_date_alignment": "satellite dates far from station dates",
    "hcho_conflicting_samples": "conflicting satellite samples",
    "hcho_sampling_locations": "sampled at shared fallback coordinates",
    "cluster_structure": "inconsistent cluster member counts",
    "members_matched": "cluster members not found in the station dataset",
    "cluster_coordinates": "cluster positions unsafe for maps",
    "observation_date": "clusters undated",
    "fire_provenance": "no fire provenance / promotion rule yet",
    "model_type_recorded": "model type not recorded",
    "target_aqi": "target is not AQI",
    "task_same_day_estimation": "not a recorded same-day estimator",
    "feature_names": "feature names not recorded",
    "no_target_leakage": "target leakage",
    "importances_match_features": "importances do not match the features",
    "training_date": "training date not recorded",
    "split_strategy": "no time-based split",
    "metrics": "held-out metrics incomplete",
    "library_versions": "library versions not recorded",
    "prediction_schema_recorded": "no input_example (prediction schema)",
    "model_object_type": "not a LightGBM preprocessing pipeline",
    "feature_schema_matches": "model inputs differ from feature_names",
    "dependency_versions": "library version mismatch with training",
    "prediction_schema": "prediction on input_example failed",
}


@dataclass(frozen=True)
class Capability:
    enabled: bool
    reason: str


@dataclass(frozen=True)
class Assessment:
    checks: tuple[Check, ...]
    capabilities: dict[str, Capability] = field(default_factory=dict)

    def failed(self, *severities: Severity) -> list[Check]:
        return [c for c in self.checks if not c.passed and c.severity in severities]

    @property
    def usable(self) -> bool:
        """Contract gate: every blocking check passed."""
        return not self.failed("blocking")

    @property
    def promotable(self) -> bool:
        """Promotion gate: every blocking and restricting check passed."""
        return not self.failed("blocking", "restricting")

    def summary(self) -> dict[str, Any]:
        status = ("passed" if self.promotable else "restricted" if self.usable else "failed")
        return {
            "status": status,
            "checks": len(self.checks),
            "failed": [c.name for c in self.failed("blocking", "restricting")],
        }

    def reasons(self) -> list[str]:
        """Concise, de-duplicated reasons the source is not promoted (blocking first)."""
        out: list[str] = []
        for c in [*self.failed("blocking"), *self.failed("restricting")]:
            if c.phrase not in out:
                out.append(c.phrase)
        return out


def _cap(enabled: bool, reason_on: str, reason_off: str) -> Capability:
    return Capability(enabled, reason_on if enabled else reason_off)


# ── Station dataset (AQI / stations) ───────────────────────────────────────────

def assess_dataset(ds: StationDataset) -> Assessment:
    q = ds.quality
    rejected_pct = f"{q.rejected_fraction:.1%}"
    reasons = ", ".join(f"{k} {v}" for k, v in q.rejected.items() if v) or "none"
    coords_ok = not q.approximate_coordinates and not q.locations_spanning_cities
    missing = ", ".join(f"{k} {v:.0%}" for k, v in q.pollutant_missing.items() if k != "hcho")
    checks = (
        Check("schema_compatible", True, "blocking",
              f"Required columns present ({q.schema_version} schema)."),
        Check("rows_usable", q.rejected_fraction <= MAX_REJECTED_FRACTION_FOR_USE, "blocking",
              f"{rejected_pct} of rows rejected (limit for use "
              f"{MAX_REJECTED_FRACTION_FOR_USE:.0%}; {reasons})."),
        Check("rows_clean", q.rejected_fraction <= MAX_REJECTED_FRACTION_FOR_PROMOTION,
              "restricting",
              f"{q.rows_rejected} of {q.rows_read} rows rejected ({reasons})"
              if q.rows_rejected else "No rows rejected.",
              short=f"{q.rows_rejected} of {q.rows_read} rows rejected"),
        Check("coordinate_quality", coords_ok, "restricting",
              "Coordinate quality insufficient for spatial maps: "
              f"{q.stations_sharing_coordinates} of {q.stations} stations on "
              f"{q.distinct_locations} shared points, {q.locations_spanning_cities} points "
              "shared by different cities." if not coords_ok
              else f"{q.distinct_locations} distinct station locations."),
        Check("co_unit", not q.co_unit_unverified, "restricting",
              f"CO unit unverified (median {q.co_median:g}, implausible in mg/m³)."
              if q.co_unit_unverified else "CO values plausible in mg/m³."),
        Check("pm_consistency", not q.pm_inconsistent, "restricting",
              f"PM2.5 exceeds PM10 in {q.pm25_above_pm10} of {q.pm_pairs} rows."
              if q.pm_inconsistent else "PM2.5 ≤ PM10 where both are reported.",
              short=f"PM2.5 exceeds PM10 in {q.pm25_above_pm10} rows"),
        Check("station_metadata", not q.station_metadata_conflicts, "restricting",
              f"{q.station_metadata_conflicts} station IDs with conflicting names / "
              "coordinates." if q.station_metadata_conflicts
              else "Station metadata consistent."),
        Check("numeric_cells", not any(q.invalid_cells.values()), "restricting",
              "Unusable numeric cells (treated as missing): "
              + ", ".join(f"{k} {v}" for k, v in q.invalid_cells.items() if v)
              if any(q.invalid_cells.values()) else "All numeric cells parse."),
        Check("missingness", True, "info", f"Missing pollutant values: {missing or 'n/a'}."),
        Check("date_coverage", True, "info",
              f"{q.first_date} … {q.last_date}" + (" (single date)."
                                                  if q.first_date == q.last_date else ".")),
        Check("duplicates", True, "info",
              f"{q.duplicates_collapsed} identical duplicates collapsed, "
              f"{q.conflicting_duplicates_dropped} conflicting duplicate rows dropped."),
    )
    usable = all(c.passed for c in checks if c.severity == "blocking")
    return Assessment(checks, {
        "aqi_tables": _cap(usable, "Accepted rows only; AQI as reported by the source.",
                           "Source not usable."),
        "station_history": _cap(usable, "Observed history from accepted rows.",
                                "Source not usable."),
        "station_maps": _cap(usable and coords_ok, "Station coordinates are distinct positions.",
                             "Coordinate quality insufficient for spatial maps."
                             if usable else "Source not usable."),
    })


def assess_hcho_trend(ds: StationDataset) -> Assessment:
    q = ds.quality
    dated = q.hcho_satellite_dated
    checks = (
        Check("hcho_samples_present", bool(ds.hcho_samples), "blocking",
              f"{q.hcho_distinct_samples} distinct location-date satellite samples."
              if ds.hcho_samples else "No usable satellite HCHO samples."),
        Check("hcho_numeric", not q.invalid_cells.get("hcho"), "restricting",
              f"{q.invalid_cells.get('hcho', 0)} unusable HCHO cells."
              if q.invalid_cells.get("hcho") else "All HCHO cells numeric."),
        Check("hcho_observation_dates", dated and not q.hcho_undated, "restricting",
              "Dated by satellite overpass date." if dated and not q.hcho_undated
              else f"{q.hcho_undated} HCHO values without an overpass date excluded."
              if dated else "No satellite overpass date recorded (dated by station date)."),
        Check("hcho_date_alignment", not q.satellite_date_mismatch, "restricting",
              f"Satellite values up to {q.max_satellite_offset_days} days from the station "
              "date." if q.satellite_date_mismatch else "Satellite and station dates aligned."),
        Check("hcho_conflicting_samples", not q.hcho_conflicting_samples, "restricting",
              f"{q.hcho_conflicting_samples} location-dates with conflicting values."
              if q.hcho_conflicting_samples else "No conflicting location-date samples."),
        Check("hcho_sampling_locations", not q.approximate_coordinates, "restricting",
              "Sampled at shared fallback coordinates, not station positions."
              if q.approximate_coordinates else "Sampled at distinct station positions."),
        Check("hcho_stacking", True, "info",
              f"{q.hcho_samples} station rows → {q.hcho_distinct_samples} distinct "
              "location-date samples; stations sharing a point count once."),
    )
    usable = bool(ds.hcho_samples)
    return Assessment(checks, {
        "hcho_trend": _cap(usable, "Daily mean of distinct satellite samples.",
                           "No usable satellite samples."),
    })


# ── HCHO hotspot clusters ──────────────────────────────────────────────────────

def assess_hotspots(
    hotspots: list[HotspotRecord],
    locations: list[int | None],
    dataset: StationDataset | None,
    placeholder: bool = False,
) -> Assessment:
    """
    `locations[i]` = distinct dataset locations of cluster i's members (None =
    unmatched). The bundled placeholder fixture is illustrative: its positions are
    not checked against station data (they are labelled placeholder instead).
    """
    inconsistent = [
        h.hotspot_id for h in hotspots
        if h.station_count is not None and h.stations and h.station_count != len(h.stations)
    ]
    unmatched = [h.hotspot_id for h, n in zip(hotspots, locations, strict=True) if n is None]
    single = [
        h.hotspot_id for h, n in zip(hotspots, locations, strict=True)
        if n == 1 and (h.station_count or len(h.stations)) > 1
    ]
    approx = dataset is not None and dataset.quality.approximate_coordinates
    if placeholder:
        unmatched, single, approx = [], [], False
    coords_ok = not unmatched and not single and not approx
    checks = (
        Check("cluster_contract", True, "blocking", f"{len(hotspots)} clusters parsed."),
        Check("cluster_structure", not inconsistent, "restricting",
              f"station_count differs from the member list in {inconsistent}."
              if inconsistent else "Member counts consistent."),
        Check("members_matched", not unmatched, "restricting",
              "Placeholder fixture — positions are illustrative, not checked." if placeholder
              else f"{len(unmatched)} of {len(hotspots)} clusters have no member in the station "
              "dataset (coordinate precision unverifiable)." if unmatched
              else "Every cluster's members found in the station dataset."),
        Check("cluster_coordinates", not single and not approx, "restricting",
              "Placeholder fixture — positions are illustrative, not checked." if placeholder
              else f"Hotspot map unsafe: {len(single)} of {len(hotspots)} clusters sit on one "
              "shared fallback point; centroids come from approximate coordinates."
              if (single or approx) else "Centroids from distinct station positions."),
        Check("observation_date", all(h.observed_at for h in hotspots), "restricting",
              "Clusters carry no observation date (undated snapshot)."
              if not all(h.observed_at for h in hotspots) else "Clusters dated."),
        Check("radius_confidence", True, "info",
              "No radius / confidence in the source contract (shown as not available)."
              if all(h.radius_km is None and h.confidence is None for h in hotspots)
              else "Radius / confidence present where provided."),
    )
    return Assessment(checks, {
        "hotspot_table": Capability(True, "Cluster values as reported (unit-converted)."),
        "hotspot_map": _cap(coords_ok,
                            "Placeholder positions — illustrative only." if placeholder
                            else "Cluster positions verified against station positions.",
                            "Hotspot map withheld: cluster positions are not verifiable "
                            "station positions."),
    })


# ── Fire detections ────────────────────────────────────────────────────────────

def assess_fires(fires: list[FireRecord]) -> Assessment:
    return Assessment((
        Check("fire_contract", True, "blocking", f"{len(fires)} detections parsed."),
        Check("fire_provenance", False, "restricting",
              "No promotion rule for fire detections yet: no team fire source exists and "
              "FIRMS provenance is not recorded."),
    ), {"fire_alerts": Capability(True, "Alerts by documented FRP rule.")})


# ── Model artefact ─────────────────────────────────────────────────────────────

def _finite(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def _major_minor(version: str | None) -> tuple[str, ...] | None:
    if not version:
        return None
    parts = str(version).split(".")
    return tuple(parts[:2]) if len(parts) >= 2 else None


def assess_model(artifact: ModelArtifact, probe: dict[str, Any] | None) -> Assessment:
    """
    Metadata contract + isolated load probe (see app.data.model_probe). A model
    whose metadata is complete but that was not load-checked stays unverified.
    """
    s = artifact.summary
    features = artifact.feature_names
    used = features or [name for name, _ in artifact.feature_importances]
    leaky = sorted({base_feature(n) for n in used if base_feature(n).lower() in LEAKY_FEATURES})
    unknown = [
        name for name, _ in artifact.feature_importances
        if features is not None and not any(
            base_feature(name) == f or base_feature(name).startswith(f"{f}_") for f in features
        )
    ]
    model_type = s.get("model_type")
    task = s.get("task")
    split = artifact.split_strategy
    versions = artifact.library_versions
    example = s.get("input_example")
    example_rows = example if isinstance(example, list) else [example] if example else []

    checks = [
        Check("artifact_files", True, "blocking", "Model file and JSON metadata present."),
        Check("model_type_recorded",
              isinstance(model_type, str) and model_type.lower() in EXPECTED_MODEL_TYPES,
              "restricting",
              f"model_type {model_type!r} recorded." if isinstance(model_type, str)
              else "model_type not recorded."),
        Check("target_aqi", artifact.target_column == "AQI", "restricting",
              f"target_column {artifact.target_column!r}" + ("." if artifact.target_column
                                                             == "AQI" else ", expected 'AQI'.")),
        Check("task_same_day_estimation",
              isinstance(task, str) and task.lower() in ESTIMATOR_TASKS
              and not s.get("forecast_horizon_hours"),
              "restricting",
              "Same-day AQI estimator." if isinstance(task, str) and task.lower()
              in ESTIMATOR_TASKS and not s.get("forecast_horizon_hours")
              else f"Task {task!r} is not a same-day estimator (forecasters use the Forecaster "
              "interface)." if task or s.get("forecast_horizon_hours")
              else "task not recorded."),
        Check("feature_names", features is not None, "restricting",
              f"{len(features)} feature names recorded." if features
              else "No explicit feature_names list (features_count alone cannot verify "
              "the input schema)."),
        Check("no_target_leakage", not leaky, "restricting",
              f"Target leakage: ground pollutant / AQI inputs {leaky}." if leaky
              else "No ground-pollutant inputs."),
        Check("importances_match_features", not unknown, "restricting",
              f"Importances name features not in feature_names: {unknown[:5]}." if unknown
              else "Importances match the feature list."),
        Check("training_date", artifact.trained_at is not None, "restricting",
              f"Trained {artifact.trained_at:%Y-%m-%d}." if artifact.trained_at
              else "Training date (trained_at) not recorded."),
        Check("split_strategy", split is not None and split.lower() in TIME_BASED_SPLITS,
              "restricting",
              f"Time-based split ({split})." if split and split.lower() in TIME_BASED_SPLITS
              else f"Split {split!r} is not time-based (metrics optimistic)." if split
              else "split_strategy not recorded (may be a random split)."),
        Check("metrics", all(_finite(artifact.metrics.get(k)) for k in ("R2", "RMSE", "MAE"))
              and bool(artifact.test_samples), "restricting",
              f"Held-out metrics on {artifact.test_samples} test rows."
              if artifact.test_samples else "Held-out test size not recorded."),
        Check("library_versions",
              "lightgbm_version" in versions and "sklearn_version" in versions, "restricting",
              "Training library versions recorded."
              if "lightgbm_version" in versions and "sklearn_version" in versions
              else "lightgbm / scikit-learn versions not recorded."),
        Check("prediction_schema_recorded", bool(example_rows), "restricting",
              f"input_example with {len(example_rows)} row(s) recorded." if example_rows
              else "No input_example recorded (prediction schema cannot be checked)."),
    ]
    checks += _probe_checks(probe, features, versions, len(example_rows))
    ok = all(c.passed for c in checks if c.severity in ("blocking", "restricting"))
    reason_off = "Model not validated — metrics and importances are not served."
    return Assessment(tuple(checks), {
        "model_metrics": _cap(ok, "Validated held-out metrics.", reason_off),
        "global_importance": _cap(ok, "Validated model importances.", reason_off),
        "model_forecast": Capability(False, "A same-day estimator is never a forecast."),
    })


def _probe_checks(
    probe: dict[str, Any] | None,
    features: list[str] | None,
    versions: dict[str, str],
    example_rows: int,
) -> list[Check]:
    names = ("artifact_loads", "model_object_type", "feature_schema_matches",
             "dependency_versions", "prediction_schema")
    if probe is None:
        return [Check(n, False, "restricting",
                      "Not checked: MODEL_LOAD_CHECK is disabled (a model that is never loaded "
                      "cannot be promoted).", short="load check not run (MODEL_LOAD_CHECK=false)")
                for n in names]
    if not probe.get("loaded"):
        return [Check(n, False, "restricting",
                      f"Load probe failed: {probe.get('error') or 'unknown error'}.",
                      short="artefact failed the load probe")
                for n in names]

    final = str(probe.get("final_estimator") or "").lower()
    steps = probe.get("steps") or []
    installed = probe.get("versions") or {}
    mismatched = [
        lib for lib, key in (("lightgbm", "lightgbm_version"), ("sklearn", "sklearn_version"))
        if _major_minor(installed.get(lib)) != _major_minor(versions.get(key))
    ]
    pred = probe.get("prediction") or {}
    pred_ok = (
        bool(pred) and pred.get("rows") == example_rows == pred.get("outputs")
        and pred.get("finite") is True
    )
    return [
        Check("artifact_loads", True, "restricting", "Artefact loads in the probe environment."),
        Check("model_object_type",
              final.endswith("lgbmregressor") and len(steps) >= 2, "restricting",
              f"Pipeline {[s.get('name') for s in steps]} → {probe.get('final_estimator')}."
              if steps else f"Not a preprocessing pipeline: {probe.get('object_type')}."),
        Check("feature_schema_matches", probe.get("feature_names_in") == features,
              "restricting",
              "Model input columns equal the recorded feature_names."
              if probe.get("feature_names_in") == features
              else "Model input columns differ from the recorded feature_names."),
        Check("dependency_versions", not mismatched, "restricting",
              "Installed lightgbm / scikit-learn match the training versions (major.minor)."
              if not mismatched else f"Version mismatch with training for {mismatched}: "
              f"installed {installed}."),
        Check("prediction_schema", pred_ok, "restricting",
              f"input_example → {pred.get('outputs')} finite prediction(s)." if pred_ok
              else f"Prediction on input_example failed: {pred.get('error') or pred}."),
    ]
