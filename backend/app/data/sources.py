"""
Process-wide data-source registry: resolves, loads and describes the source
behind every domain.

Resolution per file-backed domain (dataset, hcho, fire):
  1. explicit path setting   → kind "local"; invalid → raises (startup fails)
  2. auto-discovered team output at its documented repo location
                             → kind "local"; incompatible → skipped, reason
                               recorded in the status detail
  3. bundled deterministic placeholder fixture (app/data/fixtures)
                             → kind "placeholder" (if ENABLE_PLACEHOLDER_DATA)
  4. otherwise               → kind "unavailable"

The model is explicit-only (ML_MODEL_PATH + ENABLE_ML_ENDPOINTS) and never has a
placeholder. The forecast is "simulated"; rasters / trajectories / per-prediction
SHAP are "unavailable" until a real source exists.

Populated at startup by load_configured_sources() (see app.main lifespan).
Tests call it directly with explicit Settings.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

from app.core.logging import get_logger
from app.data.dataset import DatasetError, StationDataset, load_dataset
from app.data.fires import FireFileError, FireRecord, load_fires
from app.data.hotspots import HotspotFileError, HotspotRecord, load_hotspots
from app.data.model_artifact import ModelArtifact, load_model_artifact

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.core.config import Settings

logger = get_logger(__name__)

SourceKind = Literal["live", "local", "placeholder", "simulated", "unavailable"]

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES = Path(__file__).resolve().parent / "fixtures"

# Documented output locations of the team pipeline (see README "Connecting the team's outputs").
DISCOVERY_PATHS: dict[str, tuple[Path, ...]] = {
    "dataset": (REPO_ROOT / "analysis_ready_dataset.csv",),
    "hcho": (REPO_ROOT / "reports" / "cluster_summary.json",),
    "fire": (),
}
PLACEHOLDERS: dict[str, Path] = {
    "dataset": FIXTURES / "placeholder_station_dataset.csv",
    "hcho": FIXTURES / "placeholder_hcho_clusters.json",
    "fire": FIXTURES / "placeholder_fire_events.json",
}


@dataclass(frozen=True)
class SourceStatus:
    """What powers one domain — reported by GET /api/v1/sources."""

    domain: str
    kind: SourceKind
    name: str
    detail: str
    records: int | None = None
    as_of: str | None = None

    def compact(self) -> str:
        """'kind' or 'kind:name' — the form used by GET /version."""
        if self.kind in ("unavailable", "simulated"):
            return self.kind
        return f"{self.kind}:{self.name}"


@dataclass
class DataSources:
    dataset: StationDataset | None = None
    hotspots: list[HotspotRecord] | None = None
    fires: list[FireRecord] | None = None
    model: ModelArtifact | None = None
    statuses: dict[str, SourceStatus] = field(default_factory=dict)

    def status(self, domain: str) -> SourceStatus:
        default = SourceStatus(domain, "unavailable", "none", "Not loaded.")
        return self.statuses.get(domain) or default

    def describe(self) -> dict[str, str]:
        return {d: s.compact() for d, s in self.statuses.items()}

    def reset(self) -> None:
        self.dataset = None
        self.hotspots = None
        self.fires = None
        self.model = None
        self.statuses = {}


sources = DataSources()


def _resolve(
    domain: str,
    explicit: str | None,
    loader: Callable[[str | Path], Any],
    error: type[Exception],
    settings: Settings,
) -> tuple[Any, str, str, str]:
    """Return (loaded_object | None, kind, name, detail) for one file-backed domain."""
    if explicit:
        return loader(explicit), "local", Path(explicit).name, "Team output (configured path)."

    notes: list[str] = []
    if settings.AUTO_DISCOVER_TEAM_OUTPUTS:
        for path in DISCOVERY_PATHS[domain]:
            if not path.is_file():
                continue
            try:
                detail = "Team output (auto-discovered in repository)."
                return loader(path), "local", path.name, detail
            except error as exc:
                notes.append(f"Found {path.name} but it is incompatible: {exc}")
                logger.warning("Discovered team output rejected", domain=domain, reason=str(exc))

    if settings.ENABLE_PLACEHOLDER_DATA:
        detail = " ".join([*notes, "Deterministic placeholder fixture — not real data."])
        return loader(PLACEHOLDERS[domain]), "placeholder", PLACEHOLDERS[domain].name, detail

    return None, "unavailable", "none", " ".join([*notes, "No source configured."])


def load_configured_sources(settings: Settings) -> None:
    """
    Resolve and load every source. A configured-but-invalid explicit path raises
    (DatasetError / HotspotFileError / FireFileError / ModelArtifactError) so the
    API fails at startup instead of silently serving other data.
    """
    sources.reset()
    st: dict[str, SourceStatus] = {}

    ds, kind, name, detail = _resolve(
        "dataset", settings.DATASET_PATH, load_dataset, DatasetError, settings
    )
    sources.dataset = ds
    as_of = str(ds.latest_date) if ds else None
    st["aqi"] = SourceStatus(
        "aqi", kind, name, detail, records=len(ds) if ds else None, as_of=as_of
    )
    st["stations"] = SourceStatus(
        "stations", kind, name, detail,
        records=len(ds.latest_per_station()) if ds else None, as_of=as_of,
    )

    hs, kind, name, detail = _resolve(
        "hcho", settings.HCHO_HOTSPOTS_PATH, load_hotspots, HotspotFileError, settings
    )
    sources.hotspots = hs
    st["hcho"] = SourceStatus(
        "hcho", kind, name, detail, records=len(hs) if hs is not None else None
    )

    fr, kind, name, detail = _resolve(
        "fire", settings.FIRE_EVENTS_PATH, load_fires, FireFileError, settings
    )
    sources.fires = fr
    st["fire"] = SourceStatus(
        "fire", kind, name, detail,
        records=len(fr) if fr is not None else None,
        as_of=max(r.detected_at for r in fr).isoformat() if fr else None,
    )

    if settings.ENABLE_ML_ENDPOINTS and settings.ML_MODEL_PATH:
        sources.model = load_model_artifact(settings.ML_MODEL_PATH)
        st["model"] = SourceStatus(
            "model", "local", sources.model.directory_name,
            f"{sources.model.model_name} — trained-model artefact metadata.",
        )
    else:
        reason = (
            "ENABLE_ML_ENDPOINTS is false." if not settings.ENABLE_ML_ENDPOINTS
            else "ML_MODEL_PATH not set."
        )
        st["model"] = SourceStatus(
            "model", "unavailable", "none", f"No trained-model artefact. {reason}"
        )

    if sources.dataset is not None:
        st["forecast"] = SourceStatus(
            "forecast", "simulated", "simulated-baseline",
            "No forecasting model exists; forecasts are a simulated diurnal baseline. "
            "A loaded LightGBM artefact is a same-day estimator, not a forecaster.",
        )
    else:
        st["forecast"] = SourceStatus(
            "forecast", "unavailable", "none",
            "No station data to seed from, and no forecasting model exists.",
        )
    st["xai_global"] = SourceStatus(
        "xai_global",
        "local" if sources.model else "unavailable",
        sources.model.directory_name if sources.model else "none",
        "Global feature importance from the model artefact." if sources.model
        else "Requires a trained-model artefact.",
    )
    st["xai_local"] = SourceStatus(
        "xai_local", "unavailable", "none",
        "No per-prediction SHAP output exists for the team model.",
    )
    st["spatial_rasters"] = SourceStatus(
        "spatial_rasters", "unavailable", "none",
        "No AQI/HCHO/fire raster (COG) source; interpolation, Gi*/LISA and HYSPLIT "
        "are not implemented.",
    )

    sources.statuses = st
