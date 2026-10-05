"""
Process-wide data-source registry: resolves, loads, validates and describes
the source behind every domain.

Resolution per file-backed domain (dataset, hcho, fire):
  1. explicit path setting   → kind "local"; invalid → raises (startup fails)
  2. auto-discovered team output at its documented repo location
                             → kind "local"; incompatible → skipped, reason
                               recorded in the status detail. When several
                               candidates exist the first compatible one in
                               DISCOVERY_PATHS order wins; the others are
                               named in the detail ("also found, not used").
  3. bundled deterministic placeholder fixture (app/data/fixtures)
                             → kind "placeholder" (if ENABLE_PLACEHOLDER_DATA)
  4. otherwise               → kind "unavailable"

The model (ENABLE_ML_ENDPOINTS) comes from ML_MODEL_PATH or the trainer's
default output directory, never from a placeholder, and is served only after
the production gate in app.data.model_artifact passes; a structurally valid but
insufficiently documented artefact is reported "found but not validated".
The forecast is "simulated"; rasters / trajectories / per-prediction SHAP are
"unavailable" until a real source exists.

Every status carries `limitations` (code + message) and a `quality` report, so
the API and dashboard can restrict what they show (e.g. no station maps when
the dataset's coordinates are shared fallbacks).

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
from app.data.hotspots import (
    HotspotFileError,
    HotspotRecord,
    load_hotspots,
    member_locations,
)
from app.data.model_artifact import (
    MODEL_FILE,
    ModelArtifact,
    ModelArtifactError,
    assess_production_readiness,
    load_model_artifact,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.core.config import Settings

logger = get_logger(__name__)

SourceKind = Literal["live", "local", "placeholder", "simulated", "unavailable"]

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURES = Path(__file__).resolve().parent / "fixtures"

# Documented output locations of the team pipeline, in priority order
# (see README "Connecting the team's outputs").
DISCOVERY_PATHS: dict[str, tuple[Path, ...]] = {
    # v1 snapshot committed on PR #7 / PR #8, then PR #8's historical ARD v2
    # (data_collection_pipeline/dataset_merger.py → processed_data/, git-ignored)
    "dataset": (
        REPO_ROOT / "analysis_ready_dataset.csv",
        REPO_ROOT / "data_collection_pipeline" / "processed_data" / "analysis_ready_dataset_v2.csv",
    ),
    # spatial_analysis/hotspot_detector.py via scripts/run_sprint07_pipeline.py
    "hcho": (REPO_ROOT / "reports" / "cluster_summary.json",),
    "fire": (),
}
# model_training/lightgbm_model.py writes to config.MODEL_OUTPUT_PATH, which
# defaults to the repository root (*.joblib is git-ignored: local runs only).
MODEL_DISCOVERY_DIRS: tuple[Path, ...] = (REPO_ROOT,)
PLACEHOLDERS: dict[str, Path] = {
    "dataset": FIXTURES / "placeholder_station_dataset.csv",
    "hcho": FIXTURES / "placeholder_hcho_clusters.json",
    "fire": FIXTURES / "placeholder_fire_events.json",
}
# Limitation codes that make plotting positions misleading
SPATIAL_LIMITATIONS = frozenset({"approximate_coordinates", "unverified_coordinates"})


@dataclass(frozen=True)
class Limitation:
    """A known restriction of a source: machine-readable code + explanation."""

    code: str
    message: str


@dataclass(frozen=True)
class SourceStatus:
    """What powers one domain — reported by GET /api/v1/sources."""

    domain: str
    kind: SourceKind
    name: str
    detail: str
    records: int | None = None
    as_of: str | None = None
    limitations: tuple[Limitation, ...] = ()
    quality: dict[str, Any] = field(default_factory=dict)

    def compact(self) -> str:
        """'kind' or 'kind:name' — the form used by GET /version."""
        if self.kind in ("unavailable", "simulated"):
            return self.kind
        return f"{self.kind}:{self.name}"

    def has(self, code: str) -> bool:
        return any(lim.code == code for lim in self.limitations)


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


def _limits(pairs: list[tuple[str, str]]) -> tuple[Limitation, ...]:
    return tuple(Limitation(code, message) for code, message in pairs)


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
        present = [p for p in DISCOVERY_PATHS[domain] if p.is_file()]
        for index, path in enumerate(present):
            try:
                loaded = loader(path)
            except error as exc:
                notes.append(f"Found {path.name} but it is incompatible: {exc}")
                logger.warning("Discovered team output rejected", domain=domain, reason=str(exc))
                continue
            others = [p.name for p in present[index + 1:]]
            detail = " ".join([
                *notes,
                "Team output (auto-discovered in repository).",
                *([f"Also found, not used: {others} (set the path setting to choose)."]
                  if others else []),
            ])
            return loaded, "local", path.name, detail

    if settings.ENABLE_PLACEHOLDER_DATA:
        detail = " ".join([*notes, "Deterministic placeholder fixture — not real data."])
        return loader(PLACEHOLDERS[domain]), "placeholder", PLACEHOLDERS[domain].name, detail

    return None, "unavailable", "none", " ".join([*notes, "No source configured."])


def _hotspot_findings(
    hotspots: list[HotspotRecord], kind: str, dataset: StationDataset | None
) -> tuple[list[tuple[str, str]], dict[str, Any]]:
    """Missing-metadata and coordinate-precision findings for the cluster source."""
    found: list[tuple[str, str]] = []
    quality: dict[str, Any] = {"clusters": len(hotspots)}
    if not hotspots:
        return found, quality

    if all(h.observed_at is None for h in hotspots):
        found.append(("no_observation_date",
                      "The cluster file records no observation date; the snapshot is undated."))
    if all(h.radius_km is None for h in hotspots) and all(h.confidence is None for h in hotspots):
        found.append(("no_radius_or_confidence",
                      "No cluster radius or detection confidence in the source."))
    if all(h.source_type == "unknown" for h in hotspots):
        found.append(("no_source_attribution",
                      "No source attribution (industrial / biogenic / biomass burning)."))

    by_name = dataset.locations_by_name() if dataset else {}
    locations = [member_locations(h, by_name) for h in hotspots]
    matched = [n for n in locations if n is not None]
    single = sum(1 for h, n in zip(hotspots, locations, strict=True)
                 if n == 1 and (h.station_count or len(h.stations)) > 1)
    quality.update(clusters_matched_to_stations=len(matched), single_location_clusters=single)
    if matched and dataset is not None and dataset.quality.approximate_coordinates:
        found.append((
            "approximate_coordinates",
            "Cluster centroids are means of approximate (shared) station coordinates; "
            f"{single} of {len(hotspots)} clusters have all member stations at one shared "
            "location — a duplicate-coordinate artefact, not a spatial cluster. The hotspot "
            "map is withheld; values remain available.",
        ))
    elif kind == "local" and not matched:
        found.append((
            "unverified_coordinates",
            "Cluster member stations could not be matched to the loaded station dataset, so "
            "the precision of the cluster coordinates cannot be verified. The hotspot map is "
            "withheld.",
        ))
    return found, quality


def _resolve_model(settings: Settings) -> tuple[ModelArtifact | None, SourceStatus]:
    """Load the model artefact (explicit or discovered) and apply the production gate."""
    def unavailable(name: str, detail: str, problems: tuple[str, ...] = ()) -> SourceStatus:
        return SourceStatus(
            "model", "unavailable", name, detail,
            limitations=_limits([("not_validated", p) for p in problems]),
        )

    if not settings.ENABLE_ML_ENDPOINTS:
        return None, unavailable(
            "none", "No trained-model artefact. ENABLE_ML_ENDPOINTS is false."
        )

    artifact: ModelArtifact | None = None
    notes: list[str] = []
    if settings.ML_MODEL_PATH:
        artifact = load_model_artifact(settings.ML_MODEL_PATH)  # strict: raises
    elif settings.AUTO_DISCOVER_TEAM_OUTPUTS:
        for directory in MODEL_DISCOVERY_DIRS:
            if not (directory / MODEL_FILE).is_file():
                continue
            try:
                artifact = load_model_artifact(directory)
                break
            except ModelArtifactError as exc:
                notes.append(
                    f"Found {MODEL_FILE} in {directory.name} but it is incompatible: {exc}"
                )
    if artifact is None:
        return None, unavailable(
            "none", " ".join([*notes, "No trained-model artefact (ML_MODEL_PATH not set and "
                                      f"no {MODEL_FILE} at the trainer's default output)."]),
        )

    problems = assess_production_readiness(artifact)
    if problems:
        logger.warning("Model artefact not validated", directory=artifact.directory_name,
                       problems=problems)
        return None, unavailable(
            artifact.directory_name,
            f"Artefact {artifact.directory_name} found but not validated for production: "
            + "; ".join(problems) + ".",
            tuple(problems),
        )
    return artifact, SourceStatus(
        "model", "local", artifact.directory_name,
        f"{artifact.model_name} — validated trained-model artefact metadata "
        f"(trained {artifact.trained_at:%Y-%m-%d}, split {artifact.split_strategy}).",
        quality={"features": len(artifact.feature_names or []),
                 "test_samples": artifact.test_samples, **artifact.library_versions},
    )


def load_configured_sources(settings: Settings) -> None:
    """
    Resolve and load every source. A configured-but-invalid explicit path raises
    (DatasetError / HotspotFileError / FireFileError / ModelArtifactError) so the
    API fails at startup instead of silently serving other data.
    """
    sources.reset()
    st: dict[str, SourceStatus] = {}

    # ── Station dataset (aqi, stations, hcho_trend) ────────────────────────────
    ds, kind, name, detail = _resolve(
        "dataset", settings.DATASET_PATH, load_dataset, DatasetError, settings
    )
    sources.dataset = ds
    if ds is not None and kind == "local":
        detail += " AQI values are as reported by the source (not recomputed by the API)."
    as_of = str(ds.latest_date) if ds else None
    station_limits = _limits(ds.quality.station_limitations()) if ds else ()
    quality = ds.quality.as_dict() if ds else {}
    st["aqi"] = SourceStatus(
        "aqi", kind, name, detail, records=len(ds) if ds else None, as_of=as_of,
        limitations=station_limits, quality=quality,
    )
    st["stations"] = SourceStatus(
        "stations", kind, name, detail,
        records=len(ds.latest_per_station()) if ds else None, as_of=as_of,
        limitations=station_limits, quality=quality,
    )
    hcho_dates = ds.quality.hcho_dates if ds else None
    st["hcho_trend"] = SourceStatus(
        "hcho_trend", kind, name,
        "Daily mean satellite HCHO column at the station dataset's sampling locations "
        f"({'satellite observation date' if hcho_dates else 'station observation date'}).",
        records=sum(o.hcho_mol_m2 is not None for o in ds.observations) if ds else None,
        as_of=str(hcho_dates[1]) if hcho_dates else as_of,
        limitations=_limits(ds.quality.hcho_limitations()) if ds else (),
    )

    # ── HCHO hotspot clusters ──────────────────────────────────────────────────
    hs, kind, name, detail = _resolve(
        "hcho", settings.HCHO_HOTSPOTS_PATH, load_hotspots, HotspotFileError, settings
    )
    sources.hotspots = hs
    findings, hs_quality = _hotspot_findings(hs or [], kind, ds)
    st["hcho"] = SourceStatus(
        "hcho", kind, name, detail, records=len(hs) if hs is not None else None,
        limitations=_limits(findings), quality=hs_quality if hs is not None else {},
    )

    # ── Fire detections ────────────────────────────────────────────────────────
    fr, kind, name, detail = _resolve(
        "fire", settings.FIRE_EVENTS_PATH, load_fires, FireFileError, settings
    )
    sources.fires = fr
    st["fire"] = SourceStatus(
        "fire", kind, name, detail,
        records=len(fr) if fr is not None else None,
        as_of=max(r.detected_at for r in fr).isoformat() if fr else None,
    )

    # ── Model, forecast, explanations, rasters ─────────────────────────────────
    sources.model, st["model"] = _resolve_model(settings)
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
        "Global feature importance from the validated model artefact." if sources.model
        else "Requires a validated trained-model artefact.",
    )
    st["xai_local"] = SourceStatus(
        "xai_local", "unavailable", "none",
        "No per-prediction SHAP output exists for the team model (the Day-5 explainer "
        "outputs use leaky features and are not served).",
    )
    st["spatial_rasters"] = SourceStatus(
        "spatial_rasters", "unavailable", "none",
        "No AQI/HCHO/fire raster (COG) source; interpolation, Gi*/LISA and HYSPLIT "
        "are not implemented.",
    )

    sources.statuses = st
