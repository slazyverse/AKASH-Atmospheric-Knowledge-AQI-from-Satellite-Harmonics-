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

Trust gate (app.data.trust.assess_model): a structurally valid artefact is
served only when its training summary records everything needed to trust the
numbers — model_type, target AQI, task "same_day_estimation", feature_names,
trained_at, a time-based split_strategy, held-out metrics and test size,
lightgbm / scikit-learn versions and an input_example — its features contain no
ground pollutant / AQI inputs, AND the opt-in isolated load probe
(app.data.model_probe, MODEL_LOAD_CHECK) confirms the pickle loads as a
preprocessing pipeline ending in LGBMRegressor with matching input columns,
matching library versions and a finite prediction for the input_example. The
team trainer on PR #7 records none of model_type, task, feature_names,
trained_at, split_strategy or input_example, so its artefacts stay
"unverified". Metadata is never filled in or guessed here.
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


def base_feature(name: str) -> str:
    """Pipeline output names look like "num__Wind Speed" or "cat__Season_Monsoon"."""
    return name.split("__")[-1].strip()
