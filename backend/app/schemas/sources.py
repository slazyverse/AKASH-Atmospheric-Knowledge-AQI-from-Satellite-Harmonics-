"""
backend/app/schemas/sources.py — response models for GET /api/v1/sources.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SourceLimitationItem(BaseModel):
    """A known restriction of a source."""

    code: str = Field(
        description=(
            "Machine-readable code, e.g. approximate_coordinates, unverified_coordinates, "
            "rows_rejected, co_unit_unverified, single_date, satellite_date_mismatch, "
            "no_observation_date, no_radius_or_confidence, no_source_attribution, not_validated."
        ),
    )
    message: str = Field(description="Human-readable explanation with the evidence.")


class ValidationCheckItem(BaseModel):
    """One check of a source's trust gate."""

    name: str
    passed: bool
    severity: Literal["blocking", "restricting", "info"] = Field(
        description=(
            "blocking: contract - failure means the source is not used · restricting: "
            "scientific quality - failure blocks promotion and the affected capabilities · "
            "info: reported only."
        ),
    )
    detail: str


class ValidationSummary(BaseModel):
    """Outcome of a source's trust gate."""

    status: Literal["passed", "restricted", "failed", "not_applicable"] = Field(
        description=(
            "passed: every check passed (promotable) · restricted: contract passed, a "
            "restricting check failed · failed: contract failed · not_applicable: no gate "
            "(simulated / unavailable)."
        ),
    )
    failed: list[str] = Field(default_factory=list, description="Names of failed checks.")
    checks: list[ValidationCheckItem] = Field(default_factory=list)


class CapabilityItem(BaseModel):
    """Whether the source may be used for one feature."""

    enabled: bool
    reason: str


class CandidateItem(BaseModel):
    """A team source that exists but is not this domain's source."""

    origin: Literal["configured", "discovered"]
    location: str = Field(description="Repo-relative location or file name.")
    reason: str


class SourceStatusItem(BaseModel):
    """What powers one domain of the API, and how far it is trusted."""

    domain: str = Field(
        description="aqi | stations | hcho_trend | hcho | fire | model | forecast | xai_global | "
        "xai_local | spatial_rasters",
    )
    kind: Literal["live", "local", "placeholder", "simulated", "unavailable"] = Field(
        description=(
            "live: live external feed · local: team output file · placeholder: bundled "
            "deterministic fixture (not real data) · simulated: synthetic algorithm (forecast) · "
            "unavailable: no source."
        ),
    )
    name: str = Field(description="File / directory / component name (never a full path).")
    detail: str = Field(description="Human-readable explanation, incl. why a source was skipped.")
    records: int | None = Field(default=None, description="Rows / clusters / detections loaded.")
    as_of: str | None = Field(default=None, description="Latest date / timestamp in the source.")
    limitations: list[SourceLimitationItem] = Field(
        default_factory=list,
        description="Known restrictions; clients must not present restricted features as valid.",
    )
    quality: dict[str, Any] = Field(
        default_factory=dict,
        description="Adapter validation report (rows read / accepted / rejected by reason, ...).",
    )
    status: Literal["available", "withheld", "unavailable"] = Field(
        default="unavailable",
        description=(
            "available: serving data · withheld: a source exists but is not served (e.g. an "
            "unverified model) · unavailable: nothing to serve."
        ),
    )
    origin: Literal["configured", "discovered", "bundled", "generated", "none"] = Field(
        default="none",
        description=(
            "configured: explicit path setting · discovered: team output at its documented "
            "repo location · bundled: placeholder fixture · generated: computed (forecast)."
        ),
    )
    location: str | None = Field(
        default=None, description="Repo-relative location or file name - never an absolute path."
    )
    trust: Literal["trusted", "unverified", "placeholder", "simulated", "unavailable"] = Field(
        default="unavailable",
        description=(
            "trusted: team source that passed every check (promoted) · unverified: team source "
            "used only for its safe capabilities, not validated · placeholder · simulated · "
            "unavailable. A local kind is never trusted by default."
        ),
    )
    promoted: bool = Field(
        default=False, description="True only when a team source passed its whole trust gate."
    )
    reason: str = Field(default="", description="One-line trust / promotion explanation.")
    validation: ValidationSummary = Field(
        default_factory=lambda: ValidationSummary(status="not_applicable"),
    )
    capabilities: dict[str, CapabilityItem] = Field(
        default_factory=dict,
        description="Feature -> enabled + reason (e.g. station_maps, hotspot_map, model_metrics).",
    )
    candidate: CandidateItem | None = Field(
        default=None, description="A team source that exists but failed its gate."
    )


class SourcesResponse(BaseModel):
    """Envelope for GET /api/v1/sources."""

    sources: list[SourceStatusItem]
