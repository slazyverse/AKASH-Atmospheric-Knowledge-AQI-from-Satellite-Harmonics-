"""
dashboard/services/fire_service.py — Fire monitoring service interface.

Returns exactly what the API returns (no hardcoded fire events). Alerts are
the backend's FRP-rule alerts; `aqi_impact_score` is None because no impact
model exists.

API endpoints consumed:
  GET /api/v1/fire — Fire detections + FRP-rule alerts
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from dashboard.services.api_client import APIClient, APIError


def _ts(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


@dataclass
class FireEvent:
    """A single satellite fire detection."""
    event_id: str
    latitude: float
    longitude: float
    frp: float                      # Fire Radiative Power (MW)
    brightness: float               # Brightness temperature (K)
    satellite: str                  # MODIS | VIIRS-SNPP | VIIRS-NOAA20
    confidence: str                 # low | nominal | high
    land_cover: str
    state: str
    district: str
    detected_at: datetime


@dataclass
class FireAlert:
    """FRP-rule alert for a detection (critical >= 200 MW, high >= 100 MW)."""
    alert_id: str
    fire_event_id: str
    severity: str
    aqi_impact_score: float | None  # None: no impact model exists
    message: str
    issued_at: datetime


class FireMonitoringService:
    """Fetches fire detections and alerts from the VAYU-DRISHTI backend."""

    def __init__(self, client: APIClient | None = None) -> None:
        self._client = client or APIClient()

    def _fetch(self, params: dict[str, Any]) -> dict[str, Any]:
        try:
            return self._client.get("/fire", params=params).data or {}
        except APIError:
            return {}

    def get_active_fires(
        self,
        min_frp: float = 10.0,
        hours: int = 24,
        region: str = "All India",
    ) -> list[FireEvent]:
        """Detections in the window (ending at the source's latest detection); [] if unavailable."""
        data = self._fetch({"min_frp": min_frp, "hours": hours, "region": region})
        try:
            return [
                FireEvent(
                    event_id=e["event_id"],
                    latitude=e["latitude"],
                    longitude=e["longitude"],
                    frp=e["frp"],
                    brightness=e["brightness"],
                    satellite=e["satellite"],
                    confidence=e["confidence"],
                    land_cover=e["land_cover"],
                    state=e["state"],
                    district=e["district"],
                    detected_at=_ts(e["detected_at"]),
                )
                for e in data.get("events", [])
            ]
        except (KeyError, TypeError, ValueError):
            return []

    def get_active_alerts(self) -> list[FireAlert]:
        """FRP-rule alerts for the default window; [] if none or unavailable."""
        data = self._fetch({})
        try:
            return [
                FireAlert(
                    alert_id=a["alert_id"],
                    fire_event_id=a["fire_event_id"],
                    severity=a["severity"],
                    aqi_impact_score=a.get("aqi_impact_score"),
                    message=a["message"],
                    issued_at=_ts(a["issued_at"]),
                )
                for a in data.get("alerts", [])
            ]
        except (KeyError, TypeError, ValueError):
            return []


fire_service = FireMonitoringService()
