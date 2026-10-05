"""
Process-wide data-source registry: resolves, loads, validates, trust-gates and
describes the source behind every domain.

Availability is not trust. Each domain reports:
  kind / status   what is serving (local · placeholder · simulated · unavailable;
                  available · withheld · unavailable)
  origin          configured (explicit path) · discovered (team output at its
                  documented repo location) · bundled (placeholder) · generated
  trust           trusted · unverified · placeholder · simulated · unavailable
  promoted        True only when a team source passed EVERY check of its gate
  capabilities    what the source may be used for (e.g. aqi_tables, station_maps)
  candidate       a team source that exists but is not used, and why

Resolution per file-backed domain (dataset, hcho, fire):
  1. explicit path setting   → loaded strictly: a corrupt / unreadable file or a
                               schema it cannot read stops startup
  2. auto-discovered team output (DISCOVERY_PATHS order); an incompatible file
                               is skipped with the reason recorded
  A loaded team source is then gated (app.data.trust):
     contract fails          → not used; reported as the candidate
     contract passes only    → used as UNVERIFIED for the safe capabilities
                               (unless REQUIRE_TRUSTED_TEAM_DATA=true)
     every check passes      → PROMOTED, trust "trusted"
  3. bundled deterministic placeholder fixture (if ENABLE_PLACEHOLDER_DATA)
  4. otherwise "unavailable"

The model comes from ML_MODEL_PATH or the trainer's default output directory
(only with ENABLE_ML_ENDPOINTS), never from a placeholder, and is served only
when promoted (metadata contract + opt-in isolated load probe); otherwise it is
"withheld" as unverified. The forecast is "simulated"; rasters / trajectories /
per-prediction SHAP are "unavailable" until a real source exists.

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
    load_model_artifact,
)
from app.data.model_probe import run_probe
from app.data.trust import (
    Assessment,
    Capability,
    TrustLevel,
    assess_dataset,
    assess_fires,
    assess_hcho_trend,
    assess_hotspots,
    assess_model,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from app.core.config import Settings

logger = get_logger(__name__)

SourceKind = Literal["live", "local", "placeholder", "simulated", "unavailable"]
Origin = Literal["configured", "discovered", "bundled", "generated", "none"]
Status = Literal["available", "withheld", "unavailable"]

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
_DEFAULT_TRUST: dict[str, TrustLevel] = {
    "live": "unverified", "local": "unverified", "placeholder": "placeholder",
    "simulated": "simulated", "unavailable": "unavailable",
}


@dataclass(frozen=True)
class Limitation:
    """A known restriction of a source: machine-readable code + explanation."""

    code: str
    message: str


@dataclass(frozen=True)
class Candidate:
    """A team source that exists but is not this domain's source, and why."""

    origin: Origin
    location: str
    reason: str


@dataclass(frozen=True)
class SourceStatus:
    """What powers one domain and how far it is trusted — GET /api/v1/sources."""

    domain: str
    kind: SourceKind
    name: str
    detail: str
    records: int | None = None
    as_of: str | None = None
    limitations: tuple[Limitation, ...] = ()
    quality: dict[str, Any] = field(default_factory=dict)
    origin: Origin = "none"
    location: str | None = None
    status: Status | None = None          # None → derived from kind
    trust: TrustLevel | None = None       # None → derived from kind (never "trusted")
    promoted: bool = False
    reason: str = ""
    assessment: Assessment | None = None
    candidate: Candidate | None = None

    def __post_init__(self) -> None:
        if self.status is None:
            object.__setattr__(
                self, "status", "unavailable" if self.kind == "unavailable" else "available"
            )
        if self.trust is None:
            object.__setattr__(self, "trust", _DEFAULT_TRUST[self.kind])

    def compact(self) -> str:
        """'kind' or 'kind:name' — the form used by GET /version."""
        if self.kind in ("unavailable", "simulated"):
            return self.kind
        if self.status == "withheld":
            return f"withheld:{self.name}"
        return f"{self.kind}:{self.name}"

    def has(self, code: str) -> bool:
        return any(lim.code == code for lim in self.limitations)

    def capability(self, name: str) -> Capability | None:
        return self.assessment.capabilities.get(name) if self.assessment else None


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


def _where(path: Path) -> str:
    """Repo-relative location of a file; just the name when outside the repo."""
    try:
        return path.resolve().relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return path.name


def _short(reasons: list[str], limit: int = 3) -> str:
    text = "; ".join(r.rstrip(".") for r in reasons[:limit])
    return text + (f" (+{len(reasons) - limit} more)" if len(reasons) > limit else "")


@dataclass
class _Resolved:
    obj: Any
    kind: SourceKind
    origin: Origin
    location: str | None
    name: str
    detail: str
    assessment: Assessment | None = None
    candidate: Candidate | None = None


def _resolve(
    domain: str,
    explicit: str | None,
    loader: Callable[[str | Path], Any],
    error: type[Exception],
    settings: Settings,
    assess: Callable[[Any, Origin], Assessment],
) -> _Resolved:
    """Load and gate one file-backed domain (see the module docstring)."""
    notes: list[str] = []
    candidate: Candidate | None = None

    def gate(obj: Any, origin: Origin, path: Path) -> _Resolved | Candidate:
        assessment = assess(obj, origin)
        if not assessment.usable:
            return Candidate(origin, _where(path),
                             f"failed the contract gate: {_short(assessment.reasons(), 2)}")
        if settings.REQUIRE_TRUSTED_TEAM_DATA and not assessment.promotable:
            return Candidate(origin, _where(path),
                             "is not promoted (REQUIRE_TRUSTED_TEAM_DATA=true): "
                             + _short(assessment.reasons(), 2))
        label = "configured path" if origin == "configured" else "auto-discovered in repository"
        return _Resolved(obj, "local", origin, _where(path), path.name,
                         f"Team output ({label}).", assessment)

    if explicit:
        path = Path(explicit)
        result = gate(loader(explicit), "configured", path)  # corrupt explicit file raises
        if isinstance(result, _Resolved):
            return result
        candidate = result
        notes.append(f"Configured {path.name} {result.reason}.")
    elif settings.AUTO_DISCOVER_TEAM_OUTPUTS:
        present = [p for p in DISCOVERY_PATHS[domain] if p.is_file()]
        for index, path in enumerate(present):
            try:
                loaded = loader(path)
            except error as exc:
                notes.append(f"Found {path.name} but it is incompatible: {exc}")
                candidate = candidate or Candidate("discovered", _where(path),
                                                   f"is incompatible: {exc}")
                logger.warning("Discovered team output rejected", domain=domain, reason=str(exc))
                continue
            result = gate(loaded, "discovered", path)
            if isinstance(result, Candidate):
                notes.append(f"Found {path.name} but it {result.reason}.")
                candidate = candidate or result
                logger.warning("Discovered team output not used", domain=domain,
                               reason=result.reason)
                continue
            others = [p.name for p in present[index + 1:]]
            result.detail = " ".join([
                *notes, result.detail,
                *([f"Also found, not used: {others} (set the path setting to choose)."]
                  if others else []),
            ])
            return result

    if settings.ENABLE_PLACEHOLDER_DATA:
        path = PLACEHOLDERS[domain]
        obj = loader(path)
        detail = " ".join([*notes, "Deterministic placeholder fixture — not real data."])
        return _Resolved(obj, "placeholder", "bundled", _where(path), path.name, detail,
                         assess(obj, "bundled"), candidate)
    return _Resolved(None, "unavailable", "none", None, "none",
                     " ".join([*notes, "No source configured."]), None, candidate)


def _trust(r: _Resolved, what: str) -> tuple[TrustLevel, bool, str]:
    """(trust, promoted, one-line reason) for a resolved file-backed domain."""
    if r.kind == "placeholder":
        if r.candidate:
            return ("placeholder", False,
                    f"Placeholder in use: the team {what} ({r.candidate.location}) "
                    f"{r.candidate.reason}.")
        return "placeholder", False, f"No team {what} found — bundled placeholder, not real data."
    if r.kind == "unavailable":
        return ("unavailable", False,
                f"Team {what} ({r.candidate.location}) {r.candidate.reason}; "
                "placeholders are disabled." if r.candidate else f"No {what} source.")
    assert r.assessment is not None
    if r.assessment.promotable:
        return "trusted", True, f"Team {what} promoted: passed every validation check."
    return ("unverified", False,
            f"Team {what} in use but not promoted: {_short(r.assessment.reasons())}.")


def _hotspot_findings(
    hotspots: list[HotspotRecord],
    locations: list[int | None],
    kind: str,
    dataset: StationDataset | None,
) -> tuple[list[tuple[str, str]], dict[str, Any]]:
    """Missing-metadata and coordinate-precision limitations for the cluster source."""
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
    """Locate the artefact, run the trust gate, and serve it only when promoted."""
    if not settings.ENABLE_ML_ENDPOINTS:
        return None, SourceStatus(
            "model", "unavailable", "none",
            "No trained-model artefact. ENABLE_ML_ENDPOINTS is false.",
            reason="ML endpoints are disabled (ENABLE_ML_ENDPOINTS=false).",
        )

    artifact: ModelArtifact | None = None
    origin: Origin = "none"
    directory: Path | None = None
    notes: list[str] = []
    if settings.ML_MODEL_PATH:
        directory, origin = Path(settings.ML_MODEL_PATH), "configured"
        artifact = load_model_artifact(directory)  # strict: a corrupt artefact raises
    elif settings.AUTO_DISCOVER_TEAM_OUTPUTS:
        for candidate_dir in MODEL_DISCOVERY_DIRS:
            if not (candidate_dir / MODEL_FILE).is_file():
                continue
            try:
                artifact = load_model_artifact(candidate_dir)
                directory, origin = candidate_dir, "discovered"
                break
            except ModelArtifactError as exc:
                notes.append(
                    f"Found {MODEL_FILE} in {candidate_dir.name} but it is incompatible: {exc}"
                )
    if artifact is None or directory is None:
        return None, SourceStatus(
            "model", "unavailable", "none",
            " ".join([*notes, "No trained-model artefact (ML_MODEL_PATH not set and "
                              f"no {MODEL_FILE} at the trainer's default output)."]),
            reason="No trained-model artefact found." if not notes else _short(notes),
        )

    probe = run_probe(directory, settings.MODEL_PROBE_PYTHON) if settings.MODEL_LOAD_CHECK else None
    assessment = assess_model(artifact, probe)
    location = _where(directory) if directory.resolve() != REPO_ROOT else "."
    quality = {"features": len(artifact.feature_names or []),
               "test_samples": artifact.test_samples, **artifact.library_versions,
               "load_check": "run" if probe is not None else "disabled"}
    if assessment.promotable:
        return artifact, SourceStatus(
            "model", "local", artifact.directory_name,
            f"{artifact.model_name} — validated trained-model artefact "
            f"(trained {artifact.trained_at:%Y-%m-%d}, split {artifact.split_strategy}).",
            quality=quality, origin=origin, location=location, trust="trusted", promoted=True,
            reason="Model promoted: metadata contract and isolated load probe passed.",
            assessment=assessment,
        )
    failed = assessment.reasons()
    logger.warning("Model artefact not validated", directory=artifact.directory_name,
                   failed=[c.name for c in assessment.failed("blocking", "restricting")])
    return None, SourceStatus(
        "model", "local", artifact.directory_name,
        f"Artefact {artifact.directory_name} found but not validated for production: "
        + "; ".join(failed) + ".",
        limitations=_limits([("not_validated", r) for r in failed]),
        quality=quality, origin=origin, location=location, status="withheld",
        trust="unverified", promoted=False,
        reason=f"Model artefact found but not validated — not served: {_short(failed)}.",
        assessment=assessment,
    )


def _status(domain: str, r: _Resolved, what: str, **extra: Any) -> SourceStatus:
    trust, promoted, reason = _trust(r, what)
    return SourceStatus(
        domain, r.kind, r.name, r.detail, origin=r.origin, location=r.location, trust=trust,
        promoted=promoted, reason=reason, assessment=r.assessment, candidate=r.candidate,
        **extra,
    )


def load_configured_sources(settings: Settings) -> None:
    """
    Resolve, load and gate every source. A configured-but-unreadable explicit path
    raises (DatasetError / HotspotFileError / FireFileError / ModelArtifactError) so
    the API fails at startup instead of silently serving other data; a readable
    explicit source that fails its gate falls back with the reason reported.
    """
    sources.reset()
    st: dict[str, SourceStatus] = {}

    # ── Station dataset (aqi, stations, hcho_trend) ────────────────────────────
    r = _resolve("dataset", settings.DATASET_PATH, load_dataset, DatasetError, settings,
                 lambda obj, _origin: assess_dataset(obj))
    ds: StationDataset | None = r.obj
    sources.dataset = ds
    if ds is not None and r.kind == "local":
        r.detail += " AQI values are as reported by the source (not recomputed by the API)."
    as_of = str(ds.latest_date) if ds else None
    station_limits = _limits(ds.quality.station_limitations()) if ds else ()
    quality = ds.quality.as_dict() if ds else {}
    st["aqi"] = _status("aqi", r, "dataset", records=len(ds) if ds else None, as_of=as_of,
                        limitations=station_limits, quality=quality)
    st["stations"] = _status("stations", r, "dataset",
                             records=len(ds.latest_per_station()) if ds else None,
                             as_of=as_of, limitations=station_limits, quality=quality)

    hcho_dates = ds.quality.hcho_dates if ds else None
    trend = _Resolved(ds, r.kind, r.origin, r.location, r.name, "", None, r.candidate)
    if ds is not None:
        trend.assessment = assess_hcho_trend(ds)
        basis = ds.hcho_date_basis.replace("_", " ")
        trend.detail = (
            f"Daily mean satellite HCHO column at the station dataset's sampling locations "
            f"(dated by {basis}); rows rejected only for their ground AQI still contribute "
            "their satellite sample."
        )
    st["hcho_trend"] = _status(
        "hcho_trend", trend, "HCHO trend source",
        records=len(ds.hcho_samples) if ds else None,
        as_of=str(hcho_dates[1]) if hcho_dates else None,
        limitations=_limits(ds.quality.hcho_limitations()) if ds else (),
    )

    # ── HCHO hotspot clusters ──────────────────────────────────────────────────
    by_name = ds.locations_by_name() if ds else {}

    def assess_clusters(records: list[HotspotRecord], origin: Origin) -> Assessment:
        return assess_hotspots(records, [member_locations(h, by_name) for h in records], ds,
                               placeholder=origin == "bundled")

    r = _resolve("hcho", settings.HCHO_HOTSPOTS_PATH, load_hotspots, HotspotFileError,
                 settings, assess_clusters)
    hs: list[HotspotRecord] | None = r.obj
    sources.hotspots = hs
    locations = [member_locations(h, by_name) for h in hs or []]
    findings, hs_quality = _hotspot_findings(hs or [], locations, r.kind, ds)
    st["hcho"] = _status("hcho", r, "hotspot clusters",
                         records=len(hs) if hs is not None else None,
                         limitations=_limits(findings),
                         quality=hs_quality if hs is not None else {})

    # ── Fire detections ────────────────────────────────────────────────────────
    r = _resolve("fire", settings.FIRE_EVENTS_PATH, load_fires, FireFileError, settings,
                 lambda obj, _origin: assess_fires(obj))
    fr: list[FireRecord] | None = r.obj
    sources.fires = fr
    st["fire"] = _status("fire", r, "fire source",
                         records=len(fr) if fr is not None else None,
                         as_of=max(x.detected_at for x in fr).isoformat() if fr else None)

    # ── Model, forecast, explanations, rasters ─────────────────────────────────
    sources.model, st["model"] = _resolve_model(settings)
    if sources.dataset is not None:
        st["forecast"] = SourceStatus(
            "forecast", "simulated", "simulated-baseline",
            "No forecasting model exists; forecasts are a simulated diurnal baseline. "
            "A loaded LightGBM artefact is a same-day estimator, not a forecaster.",
            origin="generated",
            reason="Simulated baseline — no forecasting model; never a model prediction.",
        )
    else:
        st["forecast"] = SourceStatus(
            "forecast", "unavailable", "none",
            "No station data to seed from, and no forecasting model exists.",
            reason="No station data to seed the simulated baseline.",
        )
    model = st["model"]
    st["xai_global"] = SourceStatus(
        "xai_global",
        "local" if sources.model else "unavailable",
        sources.model.directory_name if sources.model else "none",
        "Global feature importance from the validated model artefact." if sources.model
        else "Requires a validated trained-model artefact.",
        origin=model.origin if sources.model else "none",
        location=model.location if sources.model else None,
        trust="trusted" if sources.model else "unavailable",
        promoted=bool(sources.model),
        reason="Importances of the promoted model." if sources.model else model.reason,
    )
    st["xai_local"] = SourceStatus(
        "xai_local", "unavailable", "none",
        "No per-prediction SHAP output exists for the team model (the Day-5 explainer "
        "outputs use leaky features and are not served).",
        reason="No per-prediction SHAP output from a validated, non-leaky model.",
    )
    st["spatial_rasters"] = SourceStatus(
        "spatial_rasters", "unavailable", "none",
        "No AQI/HCHO/fire raster (COG) source; interpolation, Gi*/LISA and HYSPLIT "
        "are not implemented.",
        reason="No raster source exists.",
    )

    sources.statuses = st
