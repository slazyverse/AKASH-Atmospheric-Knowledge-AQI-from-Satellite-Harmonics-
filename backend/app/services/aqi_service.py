"""
backend/app/services/aqi_service.py — AQI data service.

Business logic for Surface AQI data retrieval.
Endpoints delegate entirely to this service — no business logic in route handlers.

Data source: the team's station dataset when DATASET_PATH is configured
(see app.data.dataset); otherwise a static demo (stub) snapshot of 8 stations
dated "today" (UTC) — NOT real CPCB measurements.

SOLID compliance:
  - Single Responsibility: AQIService handles AQI domain only.
  - Dependency Inversion: endpoints depend on this service class, not raw DB calls.
  - Open/Closed: add new query methods without modifying existing ones.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from app.core.aqi import aqi_category
from app.core.logging import get_logger
from app.core.regions import region_matches
from app.data.sources import sources
from app.schemas.aqi import AQIDailyListResponse, AQIDailySummary, StationReading
from app.services.station_service import station_service

logger = get_logger(__name__)

# ── Demo (stub) readings — replaced by real data in a future sprint ────────────
# aqi_category is derived from aqi_value at read time (see app.core.aqi), never
# hardcoded, so the CPCB bands have a single source of truth.

_STUB_READINGS: list[dict[str, Any]] = [
    {
        "station_id": "DL001", "station_name": "Delhi – Anand Vihar",
        "latitude": 28.6469, "longitude": 77.3164, "aqi_value": 312,
        "pm25": 89.2, "pm10": 178.4, "no2": 62.1, "so2": 22.4, "co": 1.8, "o3": 44.2,
    },
    {
        "station_id": "MU001", "station_name": "Mumbai – Bandra Kurla",
        "latitude": 19.0600, "longitude": 72.8777, "aqi_value": 127,
        "pm25": 34.1, "pm10": 72.8, "no2": 41.3, "so2": 18.9, "co": 1.1, "o3": 31.5,
    },
    {
        "station_id": "BL001", "station_name": "Bengaluru – Silk Board",
        "latitude": 12.9170, "longitude": 77.6230, "aqi_value": 88,
        "pm25": 22.4, "pm10": 48.6, "no2": 29.4, "so2": 12.1, "co": 0.9, "o3": 28.7,
    },
    {
        "station_id": "HY001", "station_name": "Hyderabad – ICRISAT",
        "latitude": 17.5050, "longitude": 78.2764, "aqi_value": 51,
        "pm25": 14.2, "pm10": 31.7, "no2": 18.3, "so2": 8.6, "co": 0.6, "o3": 19.4,
    },
    {
        "station_id": "CH001", "station_name": "Chennai – Alandur",
        "latitude": 13.0012, "longitude": 80.2055, "aqi_value": 94,
        "pm25": 24.6, "pm10": 53.1, "no2": 32.7, "so2": 14.3, "co": 1.0, "o3": 22.1,
    },
    {
        "station_id": "KO001", "station_name": "Kolkata – Rabindra Bharati",
        "latitude": 22.5958, "longitude": 88.3699, "aqi_value": 198,
        "pm25": 56.3, "pm10": 112.4, "no2": 47.8, "so2": 21.2, "co": 1.4, "o3": 36.9,
    },
    {
        "station_id": "PU001", "station_name": "Pune – Lohegaon",
        "latitude": 18.5976, "longitude": 73.9144, "aqi_value": 76,
        "pm25": 19.8, "pm10": 42.3, "no2": 25.6, "so2": 10.4, "co": 0.8, "o3": 21.7,
    },
    {
        "station_id": "AH001", "station_name": "Ahmedabad – AUDA",
        "latitude": 23.0225, "longitude": 72.5714, "aqi_value": 152,
        "pm25": 42.7, "pm10": 89.4, "no2": 38.2, "so2": 17.6, "co": 1.3, "o3": 29.8,
    },
]


def _in_region(row: dict[str, Any], region: str) -> bool:
    station = station_service.get_station(row["station_id"], active_only=False) or {}
    return region_matches(region, station.get("state", ""), station.get("city", ""))


class AQIService:
    """
    Service class for Surface AQI data operations.

    All public methods are called exclusively from endpoint handlers.
    Route handlers must not contain any data-fetching or transformation logic.
    """

    def get_latest_aqi(self, station_id: str) -> int | None:
        """Return the latest AQI value for a station, or None if it has no reading."""
        if sources.dataset is not None:
            obs = sources.dataset.latest_for(station_id)
            return obs.aqi if obs else None
        for row in _STUB_READINGS:
            if row["station_id"] == station_id:
                return row["aqi_value"]
        return None

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
            query_date: Target date. Dataset: defaults to the latest date in the
                        dataset; each station's latest observation that day.
                        Demo: defaults to today UTC; other dates return nothing.
            limit:      Maximum number of station readings to include.

        Returns:
            AQIDailyListResponse. The summary aggregates every matched station;
            `readings` is capped at `limit`.
        """
        if sources.dataset is not None:
            query_date = query_date or sources.dataset.latest_date
            matched = [
                {
                    "station_id": o.station_id, "station_name": o.station_name,
                    "latitude": o.latitude, "longitude": o.longitude, "aqi_value": o.aqi,
                    "pm25": o.pm25, "pm10": o.pm10, "no2": o.no2,
                    "so2": o.so2, "co": o.co, "o3": o.o3,
                    "recorded_at": o.observed_at,
                }
                for o in sources.dataset.latest_per_station(query_date)
                if region_matches(region, o.state, o.city)
            ]
            # Needs CPCB sub-indices (team AQI calculator) — not computed yet.
            dominant_pollutant = "N/A"
        else:
            now = datetime.now(tz=timezone.utc)
            query_date = query_date or now.date()
            matched = (
                [{**row, "recorded_at": now} for row in _STUB_READINGS if _in_region(row, region)]
                if query_date == now.date()
                else []
            )
            dominant_pollutant = "PM2.5"  # demo value

        logger.info(
            "Fetching AQI daily summary",
            region=region,
            query_date=str(query_date),
            limit=limit,
            matched=len(matched),
        )

        readings: list[StationReading] = [
            StationReading(**row, aqi_category=aqi_category(row["aqi_value"]))
            for row in matched[:limit]
        ]

        aqi_values = [row["aqi_value"] for row in matched]

        summary = AQIDailySummary(
            region=region,
            summary_date=query_date,
            station_count=len(matched),
            avg_aqi=round(sum(aqi_values) / len(aqi_values), 1) if aqi_values else 0.0,
            max_aqi=max(aqi_values, default=0),
            min_aqi=min(aqi_values, default=0),
            dominant_pollutant=dominant_pollutant,
            readings=readings,
        )

        return AQIDailyListResponse(
            count=len(readings),
            region=region,
            summary=summary,
        )


# ── Module-level singleton (imported by endpoint dependency injection) ─────────
aqi_service = AQIService()
