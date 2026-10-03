"""
backend/app/services/fire_service.py — Fire Monitoring data service.

Business logic for active fire detection data from MODIS and VIIRS satellites.

Current state: serves 5 static demo (stub) events and 2 illustrative alerts —
NOT real FIRMS detections, and no smoke-trajectory model exists. `hours_ago`
gives each demo event a detection age so the `hours` filter is meaningful.
Planned: replace with a real fire-detection source.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.core.logging import get_logger
from app.core.regions import region_matches
from app.schemas.fire import FireAlertItem, FireEventItem, FireResponse

logger = get_logger(__name__)

# ── Demo (stub) data ───────────────────────────────────────────────────────────

_STUB_EVENTS: list[dict[str, Any]] = [
    {
        "event_id": "F-2024-001", "hours_ago": 2.0,
        "latitude": 23.312, "longitude": 85.334,
        "frp": 142.4, "brightness": 328.7,
        "satellite": "VIIRS-SNPP", "confidence": "high",
        "land_cover": "forest", "state": "Jharkhand", "district": "Ranchi",
    },
    {
        "event_id": "F-2024-002", "hours_ago": 5.5,
        "latitude": 21.145, "longitude": 81.684,
        "frp": 87.2, "brightness": 312.4,
        "satellite": "MODIS", "confidence": "nominal",
        "land_cover": "cropland", "state": "Chhattisgarh", "district": "Bilaspur",
    },
    {
        "event_id": "F-2024-003", "hours_ago": 9.0,
        "latitude": 27.891, "longitude": 95.421,
        "frp": 210.1, "brightness": 341.2,
        "satellite": "VIIRS-NOAA20", "confidence": "high",
        "land_cover": "forest", "state": "Arunachal Pradesh", "district": "Lohit",
    },
    {
        "event_id": "F-2024-004", "hours_ago": 14.0,
        "latitude": 15.312, "longitude": 75.712,
        "frp": 34.6, "brightness": 289.1,
        "satellite": "MODIS", "confidence": "nominal",
        "land_cover": "grassland", "state": "Karnataka", "district": "Dharwad",
    },
    {
        "event_id": "F-2024-005", "hours_ago": 20.0,
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
            region:  "All India" (all), a zone ("North", "Northeast India", ...),
                     or a state / district name (case-insensitive).
            min_frp: Minimum Fire Radiative Power threshold in megawatts.
            hours:   Time window in hours (detections older than this are excluded).

        Returns:
            FireResponse containing the filtered events and the alerts that
            refer to those events.
        """
        now = datetime.now(tz=timezone.utc)
        window_start = now - timedelta(hours=hours)

        logger.info(
            "Fetching fire data",
            region=region,
            min_frp=min_frp,
            hours=hours,
        )

        filtered_events: list[FireEventItem] = []
        for ev in _STUB_EVENTS:
            detected_at = now - timedelta(hours=ev["hours_ago"])
            if (
                ev["frp"] >= min_frp
                and detected_at >= window_start
                and region_matches(region, ev["state"], ev["district"])
            ):
                fields = {k: v for k, v in ev.items() if k != "hours_ago"}
                filtered_events.append(FireEventItem(**fields, detected_at=detected_at))

        returned_ids = {ev.event_id for ev in filtered_events}
        alerts = [
            FireAlertItem(**{**al, "issued_at": now})
            for al in _STUB_ALERTS
            if al["fire_event_id"] in returned_ids
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
