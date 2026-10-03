"""
backend/app/services/fire_service.py — Fire Monitoring data service.

Detections come only from the resolved fire source (app.data.sources): a
configured fire file (contract in app.data.fires) or the bundled placeholder
fixture. No team fire source exists yet.

The `hours` window ends at the source's latest detection (`as_of`), not at the
wall clock, so a file snapshot is filtered consistently.

Alerts are derived from detections by a documented FRP rule only:
  FRP >= 200 MW → critical · FRP >= 100 MW → high · otherwise no alert.
No AQI-impact score or smoke trajectory is produced — no such model exists.
"""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from app.core.logging import get_logger
from app.core.regions import region_matches
from app.data.sources import sources
from app.schemas.fire import FireAlertItem, FireEventItem, FireResponse

if TYPE_CHECKING:
    from app.data.fires import FireRecord

logger = get_logger(__name__)

ALERT_RULES: tuple[tuple[float, str], ...] = ((200.0, "critical"), (100.0, "high"))


def _severity(frp: float) -> str | None:
    for threshold, severity in ALERT_RULES:
        if frp >= threshold:
            return severity
    return None


def _event(r: FireRecord) -> FireEventItem:
    return FireEventItem(
        event_id=r.event_id,
        latitude=r.latitude,
        longitude=r.longitude,
        frp=r.frp,
        brightness=r.brightness,
        satellite=r.satellite,
        confidence=r.confidence,
        land_cover=r.land_cover,
        state=r.state,
        district=r.district,
        detected_at=r.detected_at,
    )


class FireService:
    """
    Service class for active fire detection and alert data.

    Returns composite responses containing both fire events and rule-based alerts
    to minimise round-trips from dashboard consumers.
    """

    def get_fire_data(
        self,
        region: str = "All India",
        min_frp: float = 10.0,
        hours: int = 24,
    ) -> FireResponse:
        """
        Return fire detections and FRP-rule alerts within the time window.

        Args:
            region:  "All India" (all), a zone ("North", "Northeast India", ...),
                     or a state / district name (case-insensitive).
            min_frp: Minimum Fire Radiative Power threshold in megawatts.
            hours:   Window length in hours, ending at the source's latest detection.

        Returns:
            FireResponse with the filtered events and the alerts for those events.
        """
        records = sources.fires or []
        as_of = max((r.detected_at for r in records), default=None)

        logger.info(
            "Fetching fire data",
            region=region,
            min_frp=min_frp,
            hours=hours,
            as_of=str(as_of),
        )

        window_start = as_of - timedelta(hours=hours) if as_of else None
        selected = [
            r for r in records
            if r.frp >= min_frp
            and window_start is not None and r.detected_at >= window_start
            and region_matches(region, r.state, r.district)
        ]

        alerts = [
            FireAlertItem(
                alert_id=f"ALERT-{r.event_id}",
                fire_event_id=r.event_id,
                severity=severity,
                aqi_impact_score=None,
                message=(
                    f"{r.satellite} detection with FRP {r.frp:.0f} MW "
                    f"in {r.district}, {r.state}."
                ),
                issued_at=r.detected_at,
            )
            for r in selected
            if (severity := _severity(r.frp)) is not None
        ]

        logger.debug(
            "Fire data query complete",
            events_returned=len(selected),
            alerts_returned=len(alerts),
        )

        return FireResponse(
            total_events=len(selected),
            total_alerts=len(alerts),
            hours_window=hours,
            as_of=as_of,
            events=[_event(r) for r in selected],
            alerts=alerts,
        )


# ── Module-level singleton ─────────────────────────────────────────────────────
fire_service = FireService()
