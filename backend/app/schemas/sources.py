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


class SourceStatusItem(BaseModel):
    """What powers one domain of the API."""

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


class SourcesResponse(BaseModel):
    """Envelope for GET /api/v1/sources."""

    sources: list[SourceStatusItem]
