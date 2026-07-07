"""
dashboard/services/fire_service.py — Fire Monitoring service interface.

Provides active fire detection data fused from MODIS/VIIRS satellite imagery.
Fire events are cross-correlated with AQI spikes to attribute pollution sources.

Day 2: All methods return typed stub data.
Day 3: Replace stub bodies with APIClient.get() calls.

API endpoints this service will consume (Day 3+):
  GET /api/v1/fire/active           — Currently active fire detections
  GET /api/v1/fire/history          — Historical fire events with FRP values
  GET /api/v1/fire/aqi-correlation  — Fire-to-AQI impact correlation scores
  GET /api/v1/fire/alerts           — High-severity fire alerts (FRP > threshold)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from dashboard.services.api_client import APIClient


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


class FireMonitoringService:
    """Fetches active fire detection and alert data."""

    def __init__(self, client: APIClient | None = None) -> None:
        self._client = client or APIClient()

    def get_active_fires(
        self,
        min_frp: float = 10.0,
        bbox: tuple[float, float, float, float] | None = None,
        hours: int = 24,
    ) -> list[FireEvent]:
        """
        Return currently active fire detections.

        Day 2: Returns 4 stub fire events.
        Day 3: resp = self._client.get("/fire/active", params={"min_frp": min_frp, "hours": hours})
        """
        return [
            FireEvent("F-2024-001", 23.312, 85.334, 142.4, 328.7, "VIIRS-SNPP", "high",     "forest",   "Jharkhand",    "Ranchi"),
            FireEvent("F-2024-002", 21.145, 81.684,  87.2, 312.4, "MODIS",      "nominal",  "cropland", "Chhattisgarh", "Bilaspur"),
            FireEvent("F-2024-003", 27.891, 95.421, 210.1, 341.2, "VIIRS-NOAA20","high",    "forest",   "Arunachal",    "Lohit"),
            FireEvent("F-2024-004", 15.312, 75.712,  34.6, 289.1, "MODIS",      "nominal",  "grassland","Karnataka",    "Dharwad"),
        ]

    def get_active_alerts(self) -> list[FireAlert]:
        """
        Return high-severity fire alerts.

        Day 2: Returns 2 stub alerts.
        Day 3: resp = self._client.get("/fire/alerts")
        """
        return [
            FireAlert("A-001", "F-2024-001", "critical", 87.4,
                      "Extreme fire activity in Jharkhand forest. AQI spike expected in 6–8 hours."),
            FireAlert("A-002", "F-2024-003", "high",     62.1,
                      "Large fire front detected near Arunachal Pradesh. Smoke trajectory towards Assam."),
        ]

    def get_fire_aqi_correlation(self, event_id: str) -> dict[str, Any]:
        """
        Return the predicted AQI impact for a specific fire event.

        Day 2: Returns stub correlation.
        Day 3: resp = self._client.get(f"/fire/aqi-correlation/{event_id}")
        """
        return {
            "event_id": event_id,
            "predicted_aqi_increase": 78,
            "affected_stations": ["DL001", "UP002"],
            "lag_hours": 6,
            "confidence": 0.82,
            "stub": True,
        }


fire_service = FireMonitoringService()
