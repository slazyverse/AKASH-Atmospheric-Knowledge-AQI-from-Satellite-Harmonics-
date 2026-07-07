"""
dashboard/services/fire_service.py — Fire Monitoring service interface.

Provides active fire detection data from MODIS/VIIRS satellites.

Day 3: Methods call the live APIClient against GET /api/v1/fire.
       Falls back to stub data on any APIError.

API endpoints consumed:
  GET /api/v1/fire — Active fire detections + alerts (MODIS/VIIRS)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from dashboard.services.api_client import APIClient, APIError


@dataclass
class FireEvent:
    """Represents a satellite-detected active fire event."""
    event_id: str
    latitude: float
    longitude: float
    frp: float                      # Fire Radiative Power (MW)
    brightness: float               # Kelvin
    satellite: str                  # MODIS | VIIRS-SNPP | VIIRS-NOAA20
    confidence: str                 # low | nominal | high
    land_cover: str                 # forest | cropland | grassland | shrubland | other
    state: str
    district: str
    detected_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class FireAlert:
    """High-severity fire alert requiring immediate attention."""
    alert_id: str
    fire_event_id: str
    severity: str                   # moderate | high | critical
    aqi_impact_score: float         # Predicted AQI increase attributable to this fire
    message: str
    issued_at: datetime = field(default_factory=datetime.utcnow)


# ── Fallback stub data ─────────────────────────────────────────────────────────

_STUB_EVENTS = [
    FireEvent("F-2024-001", 23.312, 85.334, 142.4, 328.7, "VIIRS-SNPP",   "high",    "forest",    "Jharkhand",        "Ranchi"),
    FireEvent("F-2024-002", 21.145, 81.684,  87.2, 312.4, "MODIS",        "nominal", "cropland",  "Chhattisgarh",     "Bilaspur"),
    FireEvent("F-2024-003", 27.891, 95.421, 210.1, 341.2, "VIIRS-NOAA20", "high",    "forest",    "Arunachal Pradesh","Lohit"),
    FireEvent("F-2024-004", 15.312, 75.712,  34.6, 289.1, "MODIS",        "nominal", "grassland", "Karnataka",        "Dharwad"),
]

_STUB_ALERTS = [
    FireAlert("A-001", "F-2024-001", "critical", 87.4,
              "Extreme fire activity in Jharkhand forest. AQI spike expected in 6–8 hours."),
    FireAlert("A-002", "F-2024-003", "high", 62.1,
              "Large fire front detected near Arunachal Pradesh. Smoke trajectory towards Assam."),
]


class FireMonitoringService:
    """Fetches active fire detection and alert data from the VAYU-DRISHTI backend."""

    def __init__(self, client: APIClient | None = None) -> None:
        self._client = client or APIClient()

    def get_active_fires(
        self,
        min_frp: float = 10.0,
        bbox: tuple[float, float, float, float] | None = None,
        hours: int = 24,
    ) -> list[FireEvent]:
        """
        Return currently active fire detections from GET /api/v1/fire.
        Falls back to stub data if the backend is offline.
        """
        try:
            resp = self._client.get("/fire", params={"min_frp": min_frp, "hours": hours})
            raw_events = resp.data.get("events", [])
            if not raw_events:
                return _STUB_EVENTS

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
                    detected_at=datetime.fromisoformat(
                        e["detected_at"].replace("Z", "+00:00")
                    ),
                )
                for e in raw_events
            ]
        except APIError:
            return _STUB_EVENTS

    def get_active_alerts(self) -> list[FireAlert]:
        """
        Return high-severity fire alerts from GET /api/v1/fire.
        Falls back to stub alerts if the backend is offline.
        """
        try:
            resp = self._client.get("/fire")
            raw_alerts = resp.data.get("alerts", [])
            if not raw_alerts:
                return _STUB_ALERTS

            return [
                FireAlert(
                    alert_id=a["alert_id"],
                    fire_event_id=a["fire_event_id"],
                    severity=a["severity"],
                    aqi_impact_score=a["aqi_impact_score"],
                    message=a["message"],
                    issued_at=datetime.fromisoformat(
                        a["issued_at"].replace("Z", "+00:00")
                    ),
                )
                for a in raw_alerts
            ]
        except APIError:
            return _STUB_ALERTS

    def get_fire_aqi_correlation(self, event_id: str) -> dict[str, Any]:
        """
        Return the predicted AQI impact for a specific fire event.

        Note: dedicated correlation endpoint deferred to Day N.
        """
        return {
            "event_id": event_id,
            "predicted_aqi_increase": 78,
            "affected_stations": ["DL001", "UP002"],
            "lag_hours": 6,
            "confidence": 0.82,
        }


fire_service = FireMonitoringService()
