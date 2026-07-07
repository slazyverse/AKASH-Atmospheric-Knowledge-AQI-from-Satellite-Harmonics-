"""
dashboard/services/aqi_service.py — Surface AQI data service interface.

Provides the contract between the Surface AQI dashboard page and the
VAYU-DRISHTI backend API.

Day 2: All methods return typed stub data so pages can render structure.
Day 3: Replace stub bodies with APIClient.get() calls — no page changes needed.

API endpoints this service will consume (Day 3+):
  GET /api/v1/aqi/surface          — Latest AQI readings by region
  GET /api/v1/aqi/surface/station  — Single station time series
  GET /api/v1/aqi/surface/summary  — Statistical summary (min/max/avg)
  GET /api/v1/aqi/pollutants       — Per-pollutant breakdown (PM2.5, NO2, O3…)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from dashboard.services.api_client import APIClient


# ── Data Models (typed stubs — real Pydantic schemas arrive Day 3) ───────────

@dataclass
class AQIReading:
    """Represents a single AQI observation from a monitoring station."""
    station_id: str
    station_name: str
    latitude: float
    longitude: float
    aqi_value: int
    aqi_category: str              # Good / Satisfactory / Moderate / Poor / Very Poor / Severe
    pm25: float                    # µg/m³
    pm10: float                    # µg/m³
    no2: float                     # µg/m³
    so2: float                     # µg/m³
    co: float                      # mg/m³
    o3: float                      # µg/m³
    recorded_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class AQISummary:
    """Aggregated AQI summary for a region and time window."""
    region: str
    date_from: date
    date_to: date
    station_count: int
    avg_aqi: float
    max_aqi: int
    min_aqi: int
    dominant_pollutant: str


# ── Service ───────────────────────────────────────────────────────────────────

class SurfaceAQIService:
    """
    Fetches and shapes Surface AQI data for dashboard consumption.

    Dependency-injected APIClient enables unit testing with mock clients.
    """

    def __init__(self, client: APIClient | None = None) -> None:
        self._client = client or APIClient()

    def get_latest_readings(
        self,
        region: str = "India",
        limit: int = 50,
    ) -> list[AQIReading]:
        """
        Return the latest AQI readings for all stations in a region.

        Day 2: Returns 4 illustrative stub records.
        Day 3: resp = self._client.get("/aqi/surface", params={"region": region, "limit": limit})
        """
        return [
            AQIReading("DL001", "Delhi – Anand Vihar",   28.6469, 77.3164, 312, "Very Poor",  89.2, 178.4, 62.1, 22.4, 1.8, 44.2),
            AQIReading("MU001", "Mumbai – Bandra Kurla",  19.0600, 72.8777, 127, "Poor",       34.1,  72.8, 41.3, 18.9, 1.1, 31.5),
            AQIReading("BL001", "Bengaluru – Silk Board",  12.9170, 77.6230,  88, "Moderate",  22.4,  48.6, 29.4, 12.1, 0.9, 28.7),
            AQIReading("HY001", "Hyderabad – ICRISAT",    17.5050, 78.2764,  51, "Satisfactory",14.2, 31.7, 18.3,  8.6, 0.6, 19.4),
        ]

    def get_regional_summary(
        self,
        region: str = "India",
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> AQISummary:
        """
        Return aggregated AQI statistics for a region over a time window.

        Day 2: Returns stub summary.
        Day 3: resp = self._client.get("/aqi/surface/summary", params={...})
        """
        return AQISummary(
            region=region,
            date_from=date_from or date.today(),
            date_to=date_to or date.today(),
            station_count=412,
            avg_aqi=148.3,
            max_aqi=421,
            min_aqi=12,
            dominant_pollutant="PM2.5",
        )

    def get_time_series(
        self,
        station_id: str,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        """
        Return AQI time series for a specific station.

        Day 2: Returns empty list.
        Day 3: resp = self._client.get(f"/aqi/surface/station/{station_id}/series", params={"days": days})
        """
        return []


# ── Module-level singleton ────────────────────────────────────────────────────
surface_aqi_service = SurfaceAQIService()
