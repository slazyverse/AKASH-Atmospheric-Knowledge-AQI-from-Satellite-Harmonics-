"""
backend/app/services/hcho_service.py — HCHO Hotspot data service.

Hotspots come only from the resolved cluster source (app.data.sources): the
team's cluster_summary.json when available, otherwise the bundled placeholder
fixture in the same contract. That contract carries no radius, confidence,
source attribution or observation date, so those fields stay null / "unknown".

The trend is the daily mean of the satellite HCHO column sampled at the
stations of the resolved station dataset (real or placeholder).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from app.core.logging import get_logger
from app.core.units import hcho_mol_m2_to_1e15_molec_cm2
from app.data.sources import sources
from app.schemas.hcho import (
    HCHOHotspotItem,
    HCHOHotspotsResponse,
    HCHOTrendPoint,
    HCHOTrendResponse,
)

logger = get_logger(__name__)


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
        Return HCHO hotspot clusters filtered by date and confidence threshold.

        Args:
            query_date:     Omitted → the whole latest snapshot. Given → only
                            clusters whose observation date matches (clusters
                            without a date never match).
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
            for h in sources.hotspots or []
            if (h.confidence is None or h.confidence >= min_confidence)
            and (
                query_date is None
                or (h.observed_at is not None and h.observed_at.date() == query_date)
            )
        ]

        logger.debug("HCHO hotspot query complete", returned=len(filtered))

        return HCHOHotspotsResponse(
            count=len(filtered),
            query_date=query_date,
            min_confidence=min_confidence,
            items=filtered,
        )

    def get_trend(self, days: int = 30) -> HCHOTrendResponse:
        """Daily mean HCHO column at dataset stations over the last `days` days of the source."""
        ds = sources.dataset
        if ds is None:
            return HCHOTrendResponse(count=0, points=[])

        start = ds.latest_date - timedelta(days=days - 1)
        by_day: dict[date, list[float]] = defaultdict(list)
        for o in ds.observations:
            day = o.observed_at.date()
            # Negative columns are valid TROPOMI retrieval noise but not meaningful
            # as a mean "concentration" for display; they are excluded, not altered.
            if day >= start and o.hcho_mol_m2 is not None and o.hcho_mol_m2 >= 0:
                by_day[day].append(o.hcho_mol_m2)

        points = [
            HCHOTrendPoint(
                obs_date=day,
                mean_column_density=hcho_mol_m2_to_1e15_molec_cm2(sum(v) / len(v)),
                station_count=len(v),
            )
            for day, v in sorted(by_day.items())
        ]
        return HCHOTrendResponse(count=len(points), points=points)


# ── Module-level singleton ─────────────────────────────────────────────────────
hcho_service = HCHOService()
