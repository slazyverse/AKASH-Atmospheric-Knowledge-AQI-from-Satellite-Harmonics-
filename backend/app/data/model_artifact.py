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
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

MODEL_FILE = "lightgbm_model.joblib"
METRICS_FILE = "lightgbm_evaluation_metrics.json"
IMPORTANCES_FILE = "lightgbm_feature_importances.json"
SUMMARY_FILE = "lightgbm_training_summary.json"

_REQUIRED_METRICS = ("R2", "RMSE", "MAE")


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
        return value if isinstance(value, int) else None


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
