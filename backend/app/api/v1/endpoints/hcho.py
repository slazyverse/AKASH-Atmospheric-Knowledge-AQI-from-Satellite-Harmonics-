"""
GET /api/v1/hcho/hotspots — HCHO Hotspot detection endpoint.

Returns detected formaldehyde (HCHO) concentration hotspots from
Sentinel-5P TROPOMI data for a specified observation date and minimum
confidence threshold.

Design decisions:
  - min_confidence query param allows the dashboard to surface only
    high-confidence detections to non-scientific users while researchers
    can lower the threshold for exploratory analysis.
  - date param defaults to today (UTC) — the TROPOMI L2 product has a
    ~3 hour processing latency so yesterday's data is the most current
    fully-processed archive.
  - Business logic (filtering, aggregation) lives entirely in HCHOService.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Query, status

from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.schemas.hcho import HCHOHotspotsResponse
from app.services.hcho_service import HCHOService, hcho_service

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/hcho/hotspots",
    response_model=HCHOHotspotsResponse,
    summary="HCHO Hotspot Detections",
    description=(
        "Returns formaldehyde (HCHO) column density hotspots detected by Sentinel-5P TROPOMI "
        "for the specified observation date. "
        "Hotspots are clustered concentration anomalies exceeding a climatological baseline, "
        "classified by source type (industrial | biogenic | biomass_burning | unknown). "
        "Use `min_confidence` to filter by detection quality — 0.6 is recommended for "
        "operational use; lower values expose uncertain detections for research. "
        "Column density is reported in units of **10¹⁵ molecules/cm²**."
    ),
    tags=["hcho"],
    responses={
        status.HTTP_200_OK: {
            "description": "HCHO hotspots retrieved successfully.",
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "No hotspots found for the specified date and confidence threshold.",
        },
        status.HTTP_500_INTERNAL_SERVER_ERROR: {
            "description": "Unexpected server error.",
        },
    },
)
async def get_hcho_hotspots(
    date_str: str | None = Query(
        default=None,
        alias="date",
        description=(
            "TROPOMI observation date in ISO 8601 format (YYYY-MM-DD). "
            "Defaults to today (UTC). Note: full L2 products are available with ~3h delay."
        ),
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    min_confidence: float = Query(
        default=0.6,
        ge=0.0,
        le=1.0,
        description=(
            "Minimum detection confidence threshold [0.0, 1.0]. "
            "0.6 = operational threshold; lower values expose uncertain detections."
        ),
    ),
    service: HCHOService = Depends(lambda: hcho_service),
) -> HCHOHotspotsResponse:
    """Fetch HCHO hotspot detections from the HCHO service."""

    query_date: date | None = None
    if date_str:
        try:
            query_date = date.fromisoformat(date_str)
        except ValueError:
            raise NotFoundError(
                message=f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD.",
                detail={"received": date_str},
            )

    logger.info(
        "HCHO hotspots request",
        date=str(query_date or "today"),
        min_confidence=min_confidence,
    )

    result = service.get_hotspots(
        query_date=query_date,
        min_confidence=min_confidence,
    )

    if result.count == 0:
        raise NotFoundError(
            message=(
                f"No HCHO hotspots detected with confidence ≥ {min_confidence:.0%} "
                f"for {query_date or 'today'}."
            ),
            detail={"query_date": str(query_date), "min_confidence": min_confidence},
        )

    return result
