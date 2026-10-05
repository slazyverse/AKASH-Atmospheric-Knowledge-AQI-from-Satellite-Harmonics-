"""
backend/app/services/station_service.py — Station metadata service.

Business logic for monitoring-station registry queries.

The registry is derived from the resolved station dataset (app.data.sources):
one entry per station, from its latest observation, sorted by station ID. It
is the single source of valid station IDs — /forecast and /aqi/history
validate against it, so every endpoint agrees on which stations exist.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.data.sources import sources
from app.schemas.stations import StationItem, StationsResponse

logger = get_logger(__name__)


def _registry() -> list[dict]:
    """Station records from the resolved dataset ([] when no source is available)."""
    if sources.dataset is None:
        return []
    return [
        {
            "station_id": o.station_id,
            "station_name": o.station_name,
            "latitude": o.latitude,
            "longitude": o.longitude,
            "state": o.state,
            "city": o.city,
            "network": o.network or "unknown",
            "is_active": True,
            "elevation_m": o.elevation_m,
        }
        for o in sorted(sources.dataset.latest_per_station(), key=lambda o: o.station_id)
    ]


class StationService:
    """
    Service class for station registry queries.

    Provides station metadata used for map rendering and station selectors.
    Does not include readings (use AQIService for those).
    """

    def get_station(self, station_id: str, active_only: bool = True) -> dict | None:
        """Return the registry record for `station_id`, or None if unknown."""
        for s in _registry():
            if s["station_id"] == station_id and (s["is_active"] or not active_only):
                return s
        return None

    def list_stations(
        self,
        state: str | None = None,
        network: str | None = None,
        active_only: bool = True,
        limit: int = 100,
    ) -> StationsResponse:
        """
        Return a filtered list of monitoring stations.

        Args:
            state:       Filter by Indian state name (case-insensitive partial match).
            network:     Filter by monitoring network (e.g. CPCB | SPCB | unknown).
            active_only: If True, exclude stations not currently transmitting.
            limit:       Maximum number of stations to return.

        Returns:
            StationsResponse with filtered station metadata.
        """
        logger.info(
            "Listing stations",
            state=state,
            network=network,
            active_only=active_only,
            limit=limit,
        )

        filtered = _registry()

        if active_only:
            filtered = [s for s in filtered if s["is_active"]]

        if state:
            state_lower = state.lower()
            filtered = [s for s in filtered if state_lower in s["state"].lower()]

        if network:
            filtered = [s for s in filtered if s["network"].lower() == network.lower()]

        filtered = filtered[:limit]

        items = [StationItem(**s) for s in filtered]

        logger.debug("Station list query complete", returned=len(items))

        return StationsResponse(count=len(items), items=items)


# ── Module-level singleton ─────────────────────────────────────────────────────
station_service = StationService()
