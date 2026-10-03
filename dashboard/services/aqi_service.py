"""
dashboard/services/aqi_service.py — Surface AQI data service interface.

Provides the contract between the Surface AQI dashboard page and the
VAYU-DRISHTI backend API.

All methods call the backend APIClient. If the backend is unreachable
(connection / timeout / server error), built-in offline demo data is returned
so pages still render. A "no data" answer (404 / empty list) is passed through
as empty — it is never replaced by demo data.

API endpoints consumed:
  GET /api/v1/aqi/daily — Daily AQI summary + station readings
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from dashboard.core.theme import aqi_category
from dashboard.services.api_client import APIClient, APIError, APINotFoundError


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


# ── Offline demo data (used only when the backend is unreachable) ─────────────
# Category is derived from the AQI value, never hardcoded.

_STUB_READINGS = [
    AQIReading(sid, name, lat, lon, aqi, aqi_category(aqi), pm25, pm10, no2, so2, co, o3)
    for sid, name, lat, lon, aqi, pm25, pm10, no2, so2, co, o3 in [
        ("DL001", "Delhi – Anand Vihar",    28.6469, 77.3164, 312, 89.2, 178.4, 62.1, 22.4, 1.8, 44.2),
        ("MU001", "Mumbai – Bandra Kurla",  19.0600, 72.8777, 127, 34.1,  72.8, 41.3, 18.9, 1.1, 31.5),
        ("BL001", "Bengaluru – Silk Board", 12.9170, 77.6230,  88, 22.4,  48.6, 29.4, 12.1, 0.9, 28.7),
        ("HY001", "Hyderabad – ICRISAT",    17.5050, 78.2764,  51, 14.2,  31.7, 18.3,  8.6, 0.6, 19.4),
    ]
]


def _summarise(
    region: str,
    readings: list[AQIReading],
    date_from: date | None,
    date_to: date | None,
) -> AQISummary:
    """Build a summary from local readings (empty or offline demo data)."""
    values = [r.aqi_value for r in readings]
    return AQISummary(
        region=region,
        date_from=date_from or date.today(),
        date_to=date_to or date.today(),
        station_count=len(values),
        avg_aqi=sum(values) / len(values) if values else 0.0,
        max_aqi=max(values, default=0),
        min_aqi=min(values, default=0),
        dominant_pollutant="PM2.5" if values else "—",
    )


# ── Service ───────────────────────────────────────────────────────────────────

class SurfaceAQIService:
    """
    Fetches and shapes Surface AQI data for dashboard consumption.

    Dependency-injected APIClient enables unit testing with mock clients.
    Offline demo data is returned only when the backend is unreachable.
    """

    def __init__(self, client: APIClient | None = None) -> None:
        self._client = client or APIClient()

    def get_latest_readings(
        self,
        region: str = "India",
        limit: int = 1000,
    ) -> list[AQIReading]:
        """
        Return the latest AQI readings for all stations in a region.

        Calls GET /api/v1/aqi/daily and maps the response to AQIReading dataclasses.
        Returns [] when the region has no data; offline demo data only if the
        backend is unreachable.
        """
        try:
            resp = self._client.get("/aqi/daily", params={"region": region, "limit": limit})
            raw_readings = resp.data.get("summary", {}).get("readings", [])

            return [
                AQIReading(
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
                    recorded_at=datetime.fromisoformat(
                        r["recorded_at"].replace("Z", "+00:00")
                    ),
                )
                for r in raw_readings
            ]
        except APINotFoundError:
            return []
        except APIError:
            return _STUB_READINGS

    def get_regional_summary(
        self,
        region: str = "India",
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> AQISummary:
        """
        Return aggregated AQI statistics for a region.

        Calls GET /api/v1/aqi/daily and extracts the summary block.
        Returns an empty (zero-station) summary when the region has no data;
        a summary of the offline demo data only if the backend is unreachable.
        """
        try:
            params: dict[str, Any] = {"region": region}
            if date_from:
                params["date"] = str(date_from)
            resp = self._client.get("/aqi/daily", params=params)
            s = resp.data.get("summary", {})

            return AQISummary(
                region=s.get("region", region),
                date_from=date_from or date.today(),
                date_to=date_to or date.today(),
                station_count=s.get("station_count", 0),
                avg_aqi=s.get("avg_aqi", 0.0),
                max_aqi=s.get("max_aqi", 0),
                min_aqi=s.get("min_aqi", 0),
                dominant_pollutant=s.get("dominant_pollutant", "PM2.5"),
            )
        except APINotFoundError:
            return _summarise(region, [], date_from, date_to)
        except APIError:
            return _summarise(region, _STUB_READINGS, date_from, date_to)

    def get_time_series(
        self,
        station_id: str,
        days: int = 7,
    ) -> list[dict[str, Any]]:
        """
        Return AQI time series for a specific station.

        Note: dedicated time-series endpoint deferred to Day N.
        Returns empty list until that endpoint exists.
        """
        return []


# ── Module-level singleton ────────────────────────────────────────────────────
surface_aqi_service = SurfaceAQIService()
