"""
Loader for the trained-model artefact directory (ML_MODEL_PATH).

Contract (verified against model_training/lightgbm_model.py::save_trained_model
on PR #7) — one output directory containing:
  lightgbm_model.joblib               sklearn Pipeline (required, NOT unpickled here)
  lightgbm_evaluation_metrics.json    {"R2", "RMSE", "MAE", "MBE"}   (required)
  lightgbm_feature_importances.json   {feature: raw importance}      (required)
  lightgbm_training_summary.json      target / sample counts / versions (optional)

Only the JSON metadata is read. Unpickling the Pipeline would need the exact
scikit-learn / lightgbm versions it was trained with, and no endpoint serves
predictions yet, so the binary is only checked for presence.

Note: this model is a same-day AQI estimator (satellite + meteorology →
surface AQI), not a multi-step forecaster, so its metrics are exposed via the
XAI endpoint and are deliberately NOT attached to /forecast.

Production gate (assess_production_readiness): a structurally valid artefact
is served only when its training summary also records what is needed to trust
the numbers — target AQI, an explicit feature_names list, the training date
(trained_at), lightgbm / scikit-learn versions, the held-out test size and a
time-based split_strategy — and its features contain no ground pollutant / AQI
inputs (target leakage). An artefact that declares a forecasting task is
rejected here: forecasters plug in through the Forecaster interface instead.
The team trainer on PR #7 does not yet record feature_names, trained_at or
split_strategy, so its artefacts are reported as "found but not validated".
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

MODEL_FILE = "lightgbm_model.joblib"
METRICS_FILE = "lightgbm_evaluation_metrics.json"
IMPORTANCES_FILE = "lightgbm_feature_importances.json"
SUMMARY_FILE = "lightgbm_training_summary.json"

_REQUIRED_METRICS = ("R2", "RMSE", "MAE")

# Ground-truth columns the AQI target is computed from: using any of them as a
# model input leaks the target (satellite columns such as "NO2 Column" are fine).
LEAKY_FEATURES = frozenset({"aqi", "pm2.5", "pm25", "pm10", "no2", "so2", "co", "o3"})
TIME_BASED_SPLITS = frozenset({"temporal", "time", "time_series", "chronological"})
ESTIMATOR_TASKS = frozenset({"same_day_estimation", "estimation", "regression"})


class ModelArtifactError(ValueError):
    """The configured model artefact is missing or violates the contract."""


@dataclass(frozen=True)
class ModelArtifact:
    directory_name: str
    metrics: dict[str, float]
    # (feature, share of total importance), sorted descending; shares sum to 1.
    feature_importances: list[tuple[str, float]]
    summary: dict[str, Any] = field(default_factory=dict)

    @property
    def model_name(self) -> str:
        return "LightGBM regressor (same-day AQI estimator)"

    @property
    def model_version(self) -> str:
        version = self.summary.get("reproducibility", {}).get("lightgbm_version")
        return f"lightgbm {version}" if version else "unknown"

    @property
    def target_column(self) -> str | None:
        return self.summary.get("target_column")

    @property
    def test_samples(self) -> int | None:
        value = self.summary.get("test_samples")
        return value if isinstance(value, int) and not isinstance(value, bool) else None

    @property
    def feature_names(self) -> list[str] | None:
        names = self.summary.get("feature_names")
        if isinstance(names, list) and names and all(isinstance(n, str) and n for n in names):
            return names
        return None

    @property
    def trained_at(self) -> datetime | None:
        raw = self.summary.get("trained_at") or self.summary.get("training_date")
        if not isinstance(raw, str):
            return None
        try:
            return datetime.fromisoformat(raw.replace("Z", "+00:00"))
        except ValueError:
            return None

    @property
    def split_strategy(self) -> str | None:
        value = self.summary.get("split_strategy")
        return value if isinstance(value, str) and value else None

    @property
    def library_versions(self) -> dict[str, str]:
        repro = self.summary.get("reproducibility")
        repro = repro if isinstance(repro, dict) else {}
        return {
            k: str(repro[k]) for k in ("lightgbm_version", "sklearn_version", "python_version")
            if repro.get(k)
        }


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ModelArtifactError(f"Cannot read {path.name}: {exc}") from exc


def _finite(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool) and math.isfinite(value)


def load_model_artifact(directory: str | Path) -> ModelArtifact:
    """Validate the artefact directory and load its metadata. Raises ModelArtifactError."""
    root = Path(directory)
    if not root.is_dir():
        raise ModelArtifactError(f"Model artefact directory not found: {root}")

    missing = [n for n in (MODEL_FILE, METRICS_FILE, IMPORTANCES_FILE) if not (root / n).is_file()]
    if missing:
        raise ModelArtifactError(f"Model artefact in {root.name} is missing files: {missing}")

    metrics = _read_json(root / METRICS_FILE)
    if not isinstance(metrics, dict) or not all(_finite(metrics.get(k)) for k in _REQUIRED_METRICS):
        raise ModelArtifactError(f"{METRICS_FILE} must contain numeric {list(_REQUIRED_METRICS)}.")

    raw = _read_json(root / IMPORTANCES_FILE)
    if (
        not isinstance(raw, dict)
        or not raw
        or not all(isinstance(k, str) and _finite(v) and v >= 0 for k, v in raw.items())
    ):
        raise ModelArtifactError(
            f"{IMPORTANCES_FILE} must be a non-empty object of feature → non-negative number."
        )
    total = sum(raw.values())
    if total <= 0:
        raise ModelArtifactError(f"{IMPORTANCES_FILE} has no non-zero importance.")
    importances = sorted(
        ((name, value / total) for name, value in raw.items()),
        key=lambda item: item[1],
        reverse=True,
    )

    summary: dict[str, Any] = {}
    if (root / SUMMARY_FILE).is_file():
        loaded = _read_json(root / SUMMARY_FILE)
        if isinstance(loaded, dict):
            summary = loaded

    logger.info(
        "Model artefact metadata loaded",
        directory=root.name,
        features=len(importances),
        r2=metrics["R2"],
    )
    return ModelArtifact(
        directory_name=root.name,
        metrics={k: float(v) for k, v in metrics.items() if _finite(v)},
        feature_importances=importances,
        summary=summary,
    )


def _base_feature(name: str) -> str:
    # Pipeline output names look like "num__Wind Speed" or "cat__Season_Monsoon"
    return name.split("__")[-1].strip()


def assess_production_readiness(artifact: ModelArtifact) -> list[str]:
    """
    Problems that keep a structurally valid artefact out of production ([] = validated).

    Never inspects the pickled model; every check uses the JSON metadata.
    """
    problems: list[str] = []
    if not artifact.summary:
        return [f"{SUMMARY_FILE} is missing, so nothing about the training run is recorded"]

    if artifact.target_column != "AQI":
        problems.append(f"target_column is {artifact.target_column!r}, expected 'AQI'")
    features = artifact.feature_names
    if features is None:
        problems.append(
            "no explicit feature_names list in the training summary "
            "(features_count alone cannot verify the input schema)"
        )
    if artifact.trained_at is None:
        problems.append("training date (trained_at) not recorded")
    missing_libs = [
        k for k in ("lightgbm_version", "sklearn_version") if k not in artifact.library_versions
    ]
    if missing_libs:
        problems.append(f"library versions not recorded: {missing_libs}")
    if not artifact.test_samples:
        problems.append("held-out test sample count not recorded")
    split = artifact.split_strategy
    if split is None:
        problems.append("split_strategy not recorded (metrics may come from a random split)")
    elif split.lower() not in TIME_BASED_SPLITS:
        problems.append(
            f"split_strategy {split!r} is not time-based; metrics would be optimistic"
        )

    used = features or [name for name, _ in artifact.feature_importances]
    leaky = sorted({_base_feature(n) for n in used if _base_feature(n).lower() in LEAKY_FEATURES})
    if leaky:
        problems.append(f"target leakage: ground pollutant / AQI inputs {leaky}")
    if features is not None:
        unknown = [
            name for name, _ in artifact.feature_importances
            if not any(
                _base_feature(name) == f or _base_feature(name).startswith(f"{f}_")
                for f in features
            )
        ]
        if unknown:
            problems.append(
                f"feature importances name features not in feature_names: {unknown[:5]}"
            )

    task = artifact.summary.get("task")
    horizon = artifact.summary.get("forecast_horizon_hours")
    if (isinstance(task, str) and task.lower() not in ESTIMATOR_TASKS) or horizon:
        problems.append(
            f"artefact declares a forecasting task ({task or f'horizon {horizon} h'}); only "
            "same-day AQI estimators are served here — forecasters use the Forecaster interface"
        )
    return problems
