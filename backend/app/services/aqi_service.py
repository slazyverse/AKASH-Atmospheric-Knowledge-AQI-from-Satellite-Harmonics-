"""
backend/app/services/aqi_service.py — AQI data service.

Business logic for Surface AQI data retrieval.
Endpoints delegate entirely to this service — no business logic in route handlers.

Data comes only from the resolved station dataset (app.data.sources): the
team's analysis-ready dataset when available, otherwise the bundled
deterministic placeholder fixture. GET /api/v1/sources reports which one.
No station or pollutant values are hardcoded here.
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import TYPE_CHECKING

from app.core.aqi import aqi_category
from app.core.logging import get_logger
from app.core.regions import region_matches
from app.data.sources import sources
from app.schemas.aqi import (
    AQIDailyListResponse,
    AQIDailySummary,
    AQIHistoryResponse,
    StationReading,
)

if TYPE_CHECKING:
    from app.data.dataset import Observation

logger = get_logger(__name__)


def _reading(o: Observation) -> StationReading:
    return StationReading(
        station_id=o.station_id,
        station_name=o.station_name,
        latitude=o.latitude,
        longitude=o.longitude,
        aqi_value=o.aqi,
        aqi_category=aqi_category(o.aqi),
        pm25=o.pm25,
        pm10=o.pm10,
        no2=o.no2,
        so2=o.so2,
        co=o.co,
        o3=o.o3,
        recorded_at=o.observed_at,
    )


class AQIService:
    """
    Service class for Surface AQI data operations.

    All public methods are called exclusively from endpoint handlers.
    Route handlers must not contain any data-fetching or transformation logic.
    """

    def get_latest_observation(self, station_id: str) -> Observation | None:
        """Latest observation for a station, or None (unknown station / no source)."""
        if sources.dataset is None:
            return None
        return sources.dataset.latest_for(station_id)

    def get_daily_summary(
        self,
        region: str = "India",
        query_date: date | None = None,
        limit: int = 50,
    ) -> AQIDailyListResponse:
        """
        Return the daily AQI summary and station readings for a region.

        Args:
            region:     "India" (all), a zone ("North India", "South", ...),
                        or a state / city name (case-insensitive).
            query_date: Target date; defaults to the latest date in the source.
                        Each station's latest observation on that date is used.
            limit:      Maximum number of station readings to include.

        Returns:
            AQIDailyListResponse. The summary aggregates every matched station;
            `readings` is capped at `limit`.
        """
        ds = sources.dataset
        if ds is None:
            matched: list[Observation] = []
            query_date = query_date or date.today()
        else:
            query_date = query_date or ds.latest_date
            matched = [
                o for o in ds.latest_per_station(query_date)
                if region_matches(region, o.state, o.city)
            ]

        logger.info(
            "Fetching AQI daily summary",
            region=region,
            query_date=str(query_date),
            limit=limit,
            matched=len(matched),
        )

        readings = [_reading(o) for o in matched[:limit]]
        aqi_values = [o.aqi for o in matched]

        summary = AQIDailySummary(
            region=region,
            summary_date=query_date,
            station_count=len(matched),
            avg_aqi=round(sum(aqi_values) / len(aqi_values), 1) if aqi_values else 0.0,
            max_aqi=max(aqi_values, default=0),
            min_aqi=min(aqi_values, default=0),
            # Needs CPCB sub-indices (team AQI calculator) — not computed yet.
            dominant_pollutant="N/A",
            readings=readings,
        )

        return AQIDailyListResponse(
            count=len(readings),
            region=region,
            summary=summary,
        )

    def get_history(self, station_id: str, days: int = 30) -> AQIHistoryResponse | None:
        """
        Observations for one station over the last `days` days of the source
        (window ends at the source's latest date), oldest first.

        Returns None when the station is not in the source.
        """
        ds = sources.dataset
        latest = ds.latest_for(station_id) if ds else None
        if ds is None or latest is None:
            return None
        start = ds.latest_date - timedelta(days=days - 1)
        points = [
            _reading(o) for o in ds.observations_for(station_id)
            if o.observed_at.date() >= start
        ]
        return AQIHistoryResponse(
            station_id=station_id,
            station_name=latest.station_name,
            count=len(points),
            points=points,
        )


# ── Module-level singleton (imported by endpoint dependency injection) ─────────
aqi_service = AQIService()
