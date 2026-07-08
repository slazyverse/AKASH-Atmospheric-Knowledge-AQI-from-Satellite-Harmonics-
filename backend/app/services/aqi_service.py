"""
backend/app/services/aqi_service.py — AQI data service.

Business logic for Surface AQI data retrieval.
Endpoints delegate entirely to this service — no business logic in route handlers.

Day 3: Returns realistic in-memory stub data.
Day N: Replace with async DB queries via SQLAlchemy AsyncSession.

SOLID compliance:
  - Single Responsibility: AQIService handles AQI domain only.
  - Dependency Inversion: endpoints depend on this service class, not raw DB calls.
  - Open/Closed: add new query methods without modifying existing ones.
"""

from __future__ import annotations

from datetime import date, datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.schemas.aqi import AQIDailyListResponse, AQIDailySummary, StationReading

logger = get_logger(__name__)

# ── Realistic stub data (replaced by DB queries in a future sprint) ────────────

_STUB_READINGS: list[dict[str, Any]] = [
    {
        "station_id": "DL001", "station_name": "Delhi – Anand Vihar",
        "latitude": 28.6469, "longitude": 77.3164,
        "aqi_value": 312, "aqi_category": "Very Poor",
        "pm25": 89.2, "pm10": 178.4, "no2": 62.1, "so2": 22.4, "co": 1.8, "o3": 44.2,
    },
    {
        "station_id": "MU001", "station_name": "Mumbai – Bandra Kurla",
        "latitude": 19.0600, "longitude": 72.8777,
        "aqi_value": 127, "aqi_category": "Poor",
        "pm25": 34.1, "pm10": 72.8, "no2": 41.3, "so2": 18.9, "co": 1.1, "o3": 31.5,
    },
    {
        "station_id": "BL001", "station_name": "Bengaluru – Silk Board",
        "latitude": 12.9170, "longitude": 77.6230,
        "aqi_value": 88, "aqi_category": "Moderate",
        "pm25": 22.4, "pm10": 48.6, "no2": 29.4, "so2": 12.1, "co": 0.9, "o3": 28.7,
    },
    {
        "station_id": "HY001", "station_name": "Hyderabad – ICRISAT",
        "latitude": 17.5050, "longitude": 78.2764,
        "aqi_value": 51, "aqi_category": "Satisfactory",
        "pm25": 14.2, "pm10": 31.7, "no2": 18.3, "so2": 8.6, "co": 0.6, "o3": 19.4,
    },
    {
        "station_id": "CH001", "station_name": "Chennai – Alandur",
        "latitude": 13.0012, "longitude": 80.2055,
        "aqi_value": 94, "aqi_category": "Moderate",
        "pm25": 24.6, "pm10": 53.1, "no2": 32.7, "so2": 14.3, "co": 1.0, "o3": 22.1,
    },
    {
        "station_id": "KO001", "station_name": "Kolkata – Rabindra Bharati",
        "latitude": 22.5958, "longitude": 88.3699,
        "aqi_value": 198, "aqi_category": "Moderate",
        "pm25": 56.3, "pm10": 112.4, "no2": 47.8, "so2": 21.2, "co": 1.4, "o3": 36.9,
    },
    {
        "station_id": "PU001", "station_name": "Pune – Lohegaon",
        "latitude": 18.5976, "longitude": 73.9144,
        "aqi_value": 76, "aqi_category": "Satisfactory",
        "pm25": 19.8, "pm10": 42.3, "no2": 25.6, "so2": 10.4, "co": 0.8, "o3": 21.7,
    },
    {
        "station_id": "AH001", "station_name": "Ahmedabad – AUDA",
        "latitude": 23.0225, "longitude": 72.5714,
        "aqi_value": 152, "aqi_category": "Moderate",
        "pm25": 42.7, "pm10": 89.4, "no2": 38.2, "so2": 17.6, "co": 1.3, "o3": 29.8,
    },
]


class AQIService:
    """
    Service class for Surface AQI data operations.

    All public methods are called exclusively from endpoint handlers.
    Route handlers must not contain any data-fetching or transformation logic.
    """

    def get_daily_summary(
        self,
        region: str = "India",
        query_date: date | None = None,
        limit: int = 50,
    ) -> AQIDailyListResponse:
        """
        Return the daily AQI summary and station readings for a region.

        Args:
            region:     Region name filter (currently accepts any value; DB will enforce).
            query_date: Target date (defaults to today UTC).
            limit:      Maximum number of station readings to include.

        Returns:
            AQIDailyListResponse with aggregate summary and individual readings.
        """
        query_date = query_date or date.today()
        now = datetime.now(tz=timezone.utc)

        logger.info(
            "Fetching AQI daily summary",
            region=region,
            query_date=str(query_date),
            limit=limit,
        )

        # Build typed StationReading objects from stub data
        readings: list[StationReading] = [
            StationReading(**{**row, "recorded_at": now})
            for row in _STUB_READINGS[:limit]
        ]

        if not readings:
            logger.warning("No AQI readings found", region=region, query_date=str(query_date))

        aqi_values = [r.aqi_value for r in readings]
        avg_aqi = sum(aqi_values) / len(aqi_values) if aqi_values else 0.0
        max_aqi = max(aqi_values) if aqi_values else 0
        min_aqi = min(aqi_values) if aqi_values else 0

        summary = AQIDailySummary(
            region=region,
            summary_date=query_date,
            station_count=412,          # Full network count (stub; replace with DB count)
            avg_aqi=round(avg_aqi, 1),
            max_aqi=max_aqi,
            min_aqi=min_aqi,
            dominant_pollutant="PM2.5",
            readings=readings,
        )

        return AQIDailyListResponse(
            count=len(readings),
            region=region,
            summary=summary,
        )


# ── Module-level singleton (imported by endpoint dependency injection) ─────────
aqi_service = AQIService()
