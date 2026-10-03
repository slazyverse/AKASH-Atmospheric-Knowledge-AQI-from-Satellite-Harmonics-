"""
GET /api/v1/sources — what powers each domain of the API.

Reports, per domain, whether data comes from a live feed, a team output file,
a bundled placeholder fixture, a simulation, or nothing at all — including
why an auto-discovered team output was rejected. The dashboard uses this to
label every page; operators use it to see missing dependencies at a glance.
"""

from __future__ import annotations

from fastapi import APIRouter

from app.data.sources import sources
from app.schemas.sources import SourcesResponse, SourceStatusItem

router = APIRouter()


@router.get(
    "/sources",
    response_model=SourcesResponse,
    summary="Data Source Status",
    description=(
        "Lists the source behind every domain (aqi, stations, hcho, fire, model, forecast, "
        "xai_global, xai_local, spatial_rasters) with its kind: `live`, `local` (team output "
        "file), `placeholder` (bundled deterministic fixture — not real data), `simulated` or "
        "`unavailable`, plus record counts, the latest date in the source and an explanation."
    ),
    tags=["observability"],
)
async def get_sources() -> SourcesResponse:
    """Return the resolved source status for every domain."""
    return SourcesResponse(
        sources=[
            SourceStatusItem(
                domain=s.domain,
                kind=s.kind,
                name=s.name,
                detail=s.detail,
                records=s.records,
                as_of=s.as_of,
            )
            for s in sources.statuses.values()
        ]
    )
