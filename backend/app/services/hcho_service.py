"""
backend/app/services/hcho_service.py — HCHO Hotspot data service.

Hotspots come only from the resolved cluster source (app.data.sources): the
team's cluster_summary.json when available, otherwise the bundled placeholder
fixture in the same contract. That contract carries no radius, confidence,
source attribution or observation date, so those fields stay null / "unknown".

The trend is the daily mean of the satellite HCHO column sampled at the
stations of the resolved station dataset (real or placeholder). It is dated by
the satellite overpass date when the dataset records it ("HCHO Obs Date"), and
stations sharing one coordinate (one satellite sample) count once per day, so a
fallback coordinate shared by many stations does not dominate the mean.

Each hotspot reports how many distinct dataset locations its member stations
occupy and whether its centroid comes from approximate coordinates (see
GET /api/v1/sources → hcho limitations).
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta

from app.core.logging import get_logger
from app.core.units import hcho_mol_m2_to_1e15_molec_cm2
from app.data.hotspots import member_locations
from app.data.sources import SPATIAL_LIMITATIONS, sources
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

        ds = sources.dataset
        by_name = ds.locations_by_name() if ds else {}
        status = sources.status("hcho")
        quality = next(
            (lim.code for lim in status.limitations if lim.code in SPATIAL_LIMITATIONS), None
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
                station_count=h.station_count,
                member_locations=member_locations(h, by_name),
                location_quality=(
                    "approximate" if quality == "approximate_coordinates"
                    else "unverified" if quality == "unverified_coordinates"
                    else "reported"
                ),
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
        """
        Daily mean HCHO column at the dataset's sampling locations over the last
        `days` days (window ends at the latest HCHO date in the source).
        """
        ds = sources.dataset
        if ds is None:
            return HCHOTrendResponse(count=0, points=[])

        # Satellite samples are independent of ground-AQI validity, so rows rejected
        # only for their AQI still contribute (see app.data.dataset.HCHOSample).
        samples = ds.hcho_samples
        if not samples:
            return HCHOTrendResponse(date_basis=ds.hcho_date_basis, count=0, points=[])
        start = max(s.observed_on for s in samples) - timedelta(days=days - 1)
        # day → location → values (stations sharing a coordinate share one sample)
        by_day: dict[date, dict[tuple[float, float], list[float]]] = defaultdict(
            lambda: defaultdict(list)
        )
        stations: dict[date, set[str]] = defaultdict(set)
        for s in samples:
            # Small negative columns are valid TROPOMI retrieval noise; they are kept,
            # because dropping them would bias the daily mean upwards.
            if s.observed_on >= start:
                by_day[s.observed_on][s.location].append(s.value_mol_m2)
                stations[s.observed_on].add(s.station_id)

        points = []
        for day, locations in sorted(by_day.items()):
            location_means = [sum(v) / len(v) for v in locations.values()]
            points.append(HCHOTrendPoint(
                obs_date=day,
                mean_column_density=hcho_mol_m2_to_1e15_molec_cm2(
                    sum(location_means) / len(location_means)
                ),
                station_count=len(stations[day]),
                location_count=len(location_means),
            ))
        return HCHOTrendResponse(
            date_basis=ds.hcho_date_basis, count=len(points), points=points
        )


# ── Module-level singleton ─────────────────────────────────────────────────────
hcho_service = HCHOService()
