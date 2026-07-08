"""
backend/app/services/fire_service.py — Fire Monitoring data service.

Business logic for active fire detection data from MODIS and VIIRS satellites.
Fire events are cross-referenced with AQI monitoring stations to estimate
smoke impact using trajectory modelling.

Day 3: Returns realistic in-memory stub data.
Day N: Replace with real-time NASA FIRMS API ingestion and PostGIS spatial queries.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.schemas.fire import FireAlertItem, FireEventItem, FireResponse

logger = get_logger(__name__)

# ── Realistic stub data ────────────────────────────────────────────────────────

_STUB_EVENTS: list[dict[str, Any]] = [
    {
        "event_id": "F-2024-001",
        "latitude": 23.312, "longitude": 85.334,
        "frp": 142.4, "brightness": 328.7,
        "satellite": "VIIRS-SNPP", "confidence": "high",
        "land_cover": "forest", "state": "Jharkhand", "district": "Ranchi",
    },
    {
        "event_id": "F-2024-002",
        "latitude": 21.145, "longitude": 81.684,
        "frp": 87.2, "brightness": 312.4,
        "satellite": "MODIS", "confidence": "nominal",
        "land_cover": "cropland", "state": "Chhattisgarh", "district": "Bilaspur",
    },
    {
        "event_id": "F-2024-003",
        "latitude": 27.891, "longitude": 95.421,
        "frp": 210.1, "brightness": 341.2,
        "satellite": "VIIRS-NOAA20", "confidence": "high",
        "land_cover": "forest", "state": "Arunachal Pradesh", "district": "Lohit",
    },
    {
        "event_id": "F-2024-004",
        "latitude": 15.312, "longitude": 75.712,
        "frp": 34.6, "brightness": 289.1,
        "satellite": "MODIS", "confidence": "nominal",
        "land_cover": "grassland", "state": "Karnataka", "district": "Dharwad",
    },
    {
        "event_id": "F-2024-005",
        "latitude": 29.934, "longitude": 78.162,
        "frp": 58.3, "brightness": 301.6,
        "satellite": "VIIRS-SNPP", "confidence": "high",
        "land_cover": "forest", "state": "Uttarakhand", "district": "Haridwar",
    },
]

_STUB_ALERTS: list[dict[str, Any]] = [
    {
        "alert_id": "A-001",
        "fire_event_id": "F-2024-001",
        "severity": "critical",
        "aqi_impact_score": 87.4,
        "message": (
            "Extreme fire activity in Jharkhand forest. "
            "AQI spike expected in 6–8 hours at Ranchi and Bokaro stations."
        ),
    },
    {
        "alert_id": "A-002",
        "fire_event_id": "F-2024-003",
        "severity": "high",
        "aqi_impact_score": 62.1,
        "message": (
            "Large fire front detected near Arunachal Pradesh. "
            "Smoke trajectory forecast towards Assam within 4 hours."
        ),
    },
]


class FireService:
    """
    Service class for active fire detection and alert data.

    Returns composite responses containing both fire events and high-severity alerts
    to minimise round-trips from dashboard consumers.
    """

    def get_fire_data(
        self,
        region: str = "All India",
        min_frp: float = 10.0,
        hours: int = 24,
    ) -> FireResponse:
        """
        Return active fire detections and alerts within the specified time window.

        Args:
            region:  Geographic filter (currently unimplemented; applied in Day N DB queries).
            min_frp: Minimum Fire Radiative Power threshold in megawatts.
            hours:   Time window in hours (detections older than this are excluded).

        Returns:
            FireResponse containing filtered events and all active alerts.
        """
        now = datetime.now(tz=timezone.utc)

        logger.info(
            "Fetching fire data",
            region=region,
            min_frp=min_frp,
            hours=hours,
        )

        filtered_events = [
            FireEventItem(**{**ev, "detected_at": now})
            for ev in _STUB_EVENTS
            if ev["frp"] >= min_frp
        ]

        alerts = [
            FireAlertItem(**{**al, "issued_at": now})
            for al in _STUB_ALERTS
        ]

        logger.debug(
            "Fire data query complete",
            events_returned=len(filtered_events),
            alerts_returned=len(alerts),
        )

        return FireResponse(
            total_events=len(filtered_events),
            total_alerts=len(alerts),
            hours_window=hours,
            events=filtered_events,
            alerts=alerts,
        )


# ── Module-level singleton ─────────────────────────────────────────────────────
fire_service = FireService()
