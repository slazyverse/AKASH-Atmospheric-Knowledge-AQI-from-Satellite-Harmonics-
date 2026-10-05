"""
GET /api/v1/sources — what powers each domain of the API.

Reports, per domain, whether data comes from a live feed, a team output file,
a bundled placeholder fixture, a simulation, or nothing at all — including
why an auto-discovered team output was rejected. The dashboard uses this to
label every page; operators use it to see missing dependencies at a glance.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.data.sources import SourceStatus, sources
from app.schemas.sources import (
    CandidateItem,
    CapabilityItem,
    SourceLimitationItem,
    SourcesResponse,
    SourceStatusItem,
    ValidationCheckItem,
    ValidationSummary,
)

router = APIRouter()


@router.get(
    "/sources",
    response_model=SourcesResponse,
    summary="Data Source Status",
    description=(
        "Lists the source behind every domain (aqi, stations, hcho_trend, hcho, fire, model, "
        "forecast, xai_global, xai_local, spatial_rasters) with its kind: `live`, `local` (team "
        "output file), `placeholder` (bundled deterministic fixture — not real data), "
        "`simulated` or `unavailable`, plus record counts, the latest date in the source, an "
        "explanation, known `limitations` (e.g. `approximate_coordinates`: do not map) and the "
        "adapter's `quality` report. Availability is not trust: each source also reports "
        "`status`, `origin`, `location`, `trust` (trusted · unverified · placeholder · "
        "simulated · unavailable), `promoted`, a one-line `reason`, its `validation` checks, "
        "per-feature `capabilities` and a rejected team `candidate`. `local` means team "
        "output; only `trust: trusted` / `promoted: true` means it passed every check."
    ),
    tags=["observability"],
)
async def get_sources() -> SourcesResponse:
    """Return the resolved source and trust status for every domain."""
    return SourcesResponse(sources=[_item(s) for s in sources.statuses.values()])


def _item(s: SourceStatus) -> SourceStatusItem:
    a = s.assessment
    validation = ValidationSummary(status="not_applicable")
    if a is not None:
        summary = a.summary()
        validation = ValidationSummary(
            status=summary["status"],
            failed=summary["failed"],
            checks=[
                ValidationCheckItem(name=c.name, passed=c.passed, severity=c.severity,
                                    detail=c.detail)
                for c in a.checks
            ],
        )
    return SourceStatusItem(
        domain=s.domain,
        kind=s.kind,
        name=s.name,
        detail=s.detail,
        records=s.records,
        as_of=s.as_of,
        limitations=[
            SourceLimitationItem(code=lim.code, message=lim.message) for lim in s.limitations
        ],
        quality=s.quality,
        status=s.status,
        origin=s.origin,
        location=s.location,
        trust=s.trust,
        promoted=s.promoted,
        reason=s.reason,
        validation=validation,
        capabilities={
            name: CapabilityItem(enabled=c.enabled, reason=c.reason)
            for name, c in (a.capabilities.items() if a else ())
        },
        candidate=CandidateItem(origin=s.candidate.origin, location=s.candidate.location,
                                reason=s.candidate.reason) if s.candidate else None,
    )
