"""
backend/app/services/hcho_service.py — HCHO Hotspot data service.

Business logic for Formaldehyde column density hotspot detection data.
Sourced from Sentinel-5P TROPOMI Level-2 HCHO product.

Data source: the team's hotspot clusters (cluster_summary.json) when
HCHO_HOTSPOTS_PATH is configured (see app.data.hotspots); otherwise a static
demo (stub) snapshot of 5 hotspots dated "today" (UTC) — NOT real TROPOMI
detections, with illustrative source_type / confidence.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from app.core.logging import get_logger
from app.data.sources import sources
from app.schemas.hcho import HCHOHotspotItem, HCHOHotspotsResponse

logger = get_logger(__name__)

# ── Demo (stub) data ───────────────────────────────────────────────────────────

_STUB_HOTSPOTS: list[dict] = [
    {
        "hotspot_id": "HS-001",
        "latitude": 22.572, "longitude": 88.363,
        "radius_km": 45.2, "column_density": 12.4,
        "source_type": "industrial", "confidence": 0.91,
    },
    {
        "hotspot_id": "HS-002",
        "latitude": 13.083, "longitude": 80.270,
        "radius_km": 28.7, "column_density": 8.1,
        "source_type": "biomass_burning", "confidence": 0.74,
    },
    {
        "hotspot_id": "HS-003",
        "latitude": 26.847, "longitude": 80.946,
        "radius_km": 61.3, "column_density": 15.9,
        "source_type": "biogenic", "confidence": 0.68,
    },
    {
        "hotspot_id": "HS-004",
        "latitude": 19.076, "longitude": 72.877,
        "radius_km": 33.8, "column_density": 9.7,
        "source_type": "industrial", "confidence": 0.82,
    },
    {
        "hotspot_id": "HS-005",
        "latitude": 28.644, "longitude": 77.216,
        "radius_km": 52.1, "column_density": 18.3,
        "source_type": "industrial", "confidence": 0.95,
    },
]


class HCHOService:
    """
    Service class for HCHO hotspot data retrieval and filtering.

    Methods are called exclusively from endpoint handlers.
    """

    def get_hotspots(
        self,
        query_date: date | None = None,
        min_confidence: float = 0.6,
    ) -> HCHOHotspotsResponse:
        """
        Return detected HCHO hotspots filtered by date and confidence threshold.

        Args:
            query_date:     Observation date. Hotspot file: omitted → the whole
                            latest snapshot; given → only clusters whose
                            observation_date matches (undated clusters never match).
                            Demo: defaults to today UTC; other dates return nothing.
            min_confidence: Minimum confidence threshold [0.0, 1.0]. Clusters
                            without a confidence score are not filtered out.

        Returns:
            HCHOHotspotsResponse with filtered hotspot list and query metadata.
        """
        logger.info(
            "Fetching HCHO hotspots",
            query_date=str(query_date),
            min_confidence=min_confidence,
        )

        if sources.hotspots is not None:
            filtered = [
                HCHOHotspotItem(
                    hotspot_id=h.hotspot_id,
                    latitude=h.latitude,
                    longitude=h.longitude,
                    radius_km=h.radius_km,
                    column_density=h.column_density,
                    source_type=h.source_type,
                    confidence=h.confidence,
                    detected_at=h.observed_at,
                )
                for h in sources.hotspots
                if (h.confidence is None or h.confidence >= min_confidence)
                and (
                    query_date is None
                    or (h.observed_at is not None and h.observed_at.date() == query_date)
                )
            ]
        else:
            now = datetime.now(tz=timezone.utc)
            query_date = query_date or now.date()
            snapshot = _STUB_HOTSPOTS if query_date == now.date() else []
            filtered = [
                HCHOHotspotItem(**{**h, "detected_at": now})
                for h in snapshot
                if h["confidence"] >= min_confidence
            ]

        logger.debug("HCHO hotspot query complete", returned=len(filtered))

        return HCHOHotspotsResponse(
            count=len(filtered),
            query_date=query_date,
            min_confidence=min_confidence,
            items=filtered,
        )


# ── Module-level singleton ─────────────────────────────────────────────────────
hcho_service = HCHOService()
