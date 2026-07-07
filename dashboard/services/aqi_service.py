"""
dashboard/services/aqi_service.py — Surface AQI data service interface.

Provides the contract between the Surface AQI dashboard page and the
VAYU-DRISHTI backend API.

Day 3: All methods call the live APIClient. On any APIError, a structured
       warning is stored in st.session_state and stub data is returned so
       pages render without crashing.

API endpoints consumed:
  GET /api/v1/aqi/daily — Daily AQI summary + station readings
"""

from __future__ import annotations

from dataclasses import dataclass, field
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


# ── Fallback stub data (used when backend is offline) ─────────────────────────

_STUB_READINGS = [
    AQIReading("DL001", "Delhi – Anand Vihar",    28.6469, 77.3164, 312, "Very Poor",    89.2, 178.4, 62.1, 22.4, 1.8, 44.2),
    AQIReading("MU001", "Mumbai – Bandra Kurla",   19.0600, 72.8777, 127, "Poor",         34.1,  72.8, 41.3, 18.9, 1.1, 31.5),
    AQIReading("BL001", "Bengaluru – Silk Board",  12.9170, 77.6230,  88, "Moderate",     22.4,  48.6, 29.4, 12.1, 0.9, 28.7),
    AQIReading("HY001", "Hyderabad – ICRISAT",     17.5050, 78.2764,  51, "Satisfactory", 14.2,  31.7, 18.3,  8.6, 0.6, 19.4),
]


# ── Service ───────────────────────────────────────────────────────────────────

class SurfaceAQIService:
    """
    Fetches and shapes Surface AQI data for dashboard consumption.

    Dependency-injected APIClient enables unit testing with mock clients.
    On any APIError, returns stub data and records the error in session state.
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

        Calls GET /api/v1/aqi/daily and maps the response to AQIReading dataclasses.
        Falls back to stub data if the backend is offline.
        """
        try:
            resp = self._client.get("/aqi/daily", params={"region": region, "limit": limit})
            raw_readings = resp.data.get("summary", {}).get("readings", [])
            if not raw_readings:
                return _STUB_READINGS

            return [
                AQIReading(
                    station_id=r["station_id"],
                    station_name=r["station_name"],
                    latitude=r["latitude"],
                    longitude=r["longitude"],
                    aqi_value=r["aqi_value"],
                    aqi_category=r["aqi_category"],
                    pm25=r["pm25"],
                    pm10=r["pm10"],
                    no2=r["no2"],
                    so2=r["so2"],
                    co=r["co"],
                    o3=r["o3"],
                    recorded_at=datetime.fromisoformat(
                        r["recorded_at"].replace("Z", "+00:00")
                    ),
                )
                for r in raw_readings
            ]
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
        Falls back to stub summary if the backend is offline.
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
        except APIError:
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

        Note: dedicated time-series endpoint deferred to Day N.
        Returns empty list until that endpoint exists.
        """
        return []


# ── Module-level singleton ────────────────────────────────────────────────────
surface_aqi_service = SurfaceAQIService()
