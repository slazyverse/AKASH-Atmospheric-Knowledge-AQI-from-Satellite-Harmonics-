"""
backend/app/schemas/sources.py — response models for GET /api/v1/sources.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class SourceStatusItem(BaseModel):
    """What powers one domain of the API."""

    domain: str = Field(
        description="aqi | stations | hcho | fire | model | forecast | xai_global | xai_local | "
        "spatial_rasters",
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


class SourcesResponse(BaseModel):
    """Envelope for GET /api/v1/sources."""

    sources: list[SourceStatusItem]
