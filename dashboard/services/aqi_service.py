"""
dashboard/services/aqi_service.py — Surface AQI data service interface.

Provides the contract between the Surface AQI dashboard page and the
VAYU-DRISHTI backend API. Returns exactly what the API returns — the dashboard
keeps no hardcoded station data. When the backend is unreachable or a query
matches nothing, results are empty and pages show an unavailable/empty state.

API endpoints consumed:
  GET /api/v1/aqi/daily    — Daily AQI summary + station readings
  GET /api/v1/aqi/history  — One station's observation history
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from dashboard.services.api_client import APIClient, APIError


# ── Data Models ───────────────────────────────────────────────────────────────

@dataclass
class AQIReading:
    """Represents a single AQI observation from a monitoring station."""
    station_id: str
    station_name: str
    latitude: float
    longitude: float
    aqi_value: int
    aqi_category: str              # Good / Satisfactory / Moderate / Poor / Very Poor / Severe
    pm25: float | None             # µg/m³ (None = not reported)
    pm10: float | None             # µg/m³
    no2: float | None              # µg/m³
    so2: float | None              # µg/m³
    co: float | None               # mg/m³
    o3: float | None               # µg/m³
    recorded_at: datetime          # observation time from the source (never "now")


@dataclass
class AQISummary:
    """Aggregated AQI summary for a region and date."""
    region: str
    date_from: date | None
    date_to: date | None
    station_count: int
    avg_aqi: float
    max_aqi: int
    min_aqi: int
    dominant_pollutant: str


def _parse_reading(r: dict[str, Any]) -> AQIReading:
    return AQIReading(
        station_id=r["station_id"],
        station_name=r["station_name"],
        latitude=r["latitude"],
        longitude=r["longitude"],
        aqi_value=r["aqi_value"],
        aqi_category=r["aqi_category"],
        pm25=r.get("pm25"),
        pm10=r.get("pm10"),
        no2=r.get("no2"),
        so2=r.get("so2"),
        co=r.get("co"),
        o3=r.get("o3"),
        recorded_at=datetime.fromisoformat(r["recorded_at"].replace("Z", "+00:00")),
    )


_EMPTY_SUMMARY = dict(station_count=0, avg_aqi=0.0, max_aqi=0, min_aqi=0, dominant_pollutant="—")


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
        limit: int = 1000,
    ) -> list[AQIReading]:
        """
        Latest reading per station in a region (GET /api/v1/aqi/daily).
        Returns [] when nothing matches or the backend is unreachable.
        """
        try:
            resp = self._client.get("/aqi/daily", params={"region": region, "limit": limit})
            return [_parse_reading(r) for r in resp.data.get("summary", {}).get("readings", [])]
        except (APIError, KeyError, TypeError, ValueError):
            return []

    def get_regional_summary(self, region: str = "India") -> AQISummary:
        """
        Aggregated statistics for a region. A zero-station summary means no
        data (no match, or backend unreachable).
        """
        try:
            s = self._client.get("/aqi/daily", params={"region": region}).data.get("summary", {})
            day = date.fromisoformat(s["summary_date"]) if s.get("summary_date") else None
            return AQISummary(
                region=s.get("region", region),
                date_from=day,
                date_to=day,
                station_count=s.get("station_count", 0),
                avg_aqi=s.get("avg_aqi", 0.0),
                max_aqi=s.get("max_aqi", 0),
                min_aqi=s.get("min_aqi", 0),
                dominant_pollutant=s.get("dominant_pollutant", "—"),
            )
        except (APIError, KeyError, TypeError, ValueError):
            return AQISummary(region=region, date_from=None, date_to=None, **_EMPTY_SUMMARY)

    def get_time_series(self, station_id: str, days: int = 30) -> list[AQIReading]:
        """
        Observed history for one station (GET /api/v1/aqi/history), oldest first.
        Real observations from the data source — never simulated. [] if unavailable.
        """
        try:
            resp = self._client.get("/aqi/history", params={"station_id": station_id, "days": days})
            return [_parse_reading(r) for r in resp.data.get("points", [])]
        except (APIError, KeyError, TypeError, ValueError):
            return []


# ── Module-level singleton ────────────────────────────────────────────────────
surface_aqi_service = SurfaceAQIService()
