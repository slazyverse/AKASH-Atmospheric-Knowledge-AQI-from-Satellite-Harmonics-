"""
backend/app/services/station_service.py — Station metadata service.

Business logic for CPCB monitoring station registry queries.
Station metadata is quasi-static (updates only when new stations are commissioned).

Data source: the team's station dataset when DATASET_PATH is configured
(one entry per station, from its latest observation); otherwise a static demo
(stub) list — not real CPCB data.
"""

from __future__ import annotations

from app.core.logging import get_logger
from app.data.sources import sources
from app.schemas.stations import StationItem, StationsResponse

logger = get_logger(__name__)

# ── Demo (stub) station registry ──────────────────────────────────────────────

_STUB_STATIONS: list[dict] = [
    {"station_id": "DL001", "station_name": "Delhi – Anand Vihar",       "latitude": 28.6469, "longitude": 77.3164, "state": "Delhi",       "city": "Delhi",       "network": "CPCB", "is_active": True,  "elevation_m": 216.0},
    {"station_id": "DL002", "station_name": "Delhi – Dwarka",             "latitude": 28.5921, "longitude": 77.0460, "state": "Delhi",       "city": "Delhi",       "network": "CPCB", "is_active": True,  "elevation_m": 214.0},
    {"station_id": "MU001", "station_name": "Mumbai – Bandra Kurla",      "latitude": 19.0600, "longitude": 72.8777, "state": "Maharashtra", "city": "Mumbai",      "network": "CPCB", "is_active": True,  "elevation_m": 14.0},
    {"station_id": "MU002", "station_name": "Mumbai – Worli",             "latitude": 19.0176, "longitude": 72.8156, "state": "Maharashtra", "city": "Mumbai",      "network": "SAFAR","is_active": True,  "elevation_m": 11.0},
    {"station_id": "BL001", "station_name": "Bengaluru – Silk Board",     "latitude": 12.9170, "longitude": 77.6230, "state": "Karnataka",   "city": "Bengaluru",   "network": "CPCB", "is_active": True,  "elevation_m": 920.0},
    {"station_id": "HY001", "station_name": "Hyderabad – ICRISAT",        "latitude": 17.5050, "longitude": 78.2764, "state": "Telangana",   "city": "Hyderabad",   "network": "CPCB", "is_active": True,  "elevation_m": 549.0},
    {"station_id": "CH001", "station_name": "Chennai – Alandur",          "latitude": 13.0012, "longitude": 80.2055, "state": "Tamil Nadu",  "city": "Chennai",     "network": "CPCB", "is_active": True,  "elevation_m": 16.0},
    {"station_id": "KO001", "station_name": "Kolkata – Rabindra Bharati", "latitude": 22.5958, "longitude": 88.3699, "state": "West Bengal", "city": "Kolkata",     "network": "CPCB", "is_active": True,  "elevation_m": 9.0},
    {"station_id": "PU001", "station_name": "Pune – Lohegaon",            "latitude": 18.5976, "longitude": 73.9144, "state": "Maharashtra", "city": "Pune",        "network": "CPCB", "is_active": True,  "elevation_m": 559.0},
    {"station_id": "AH001", "station_name": "Ahmedabad – AUDA",           "latitude": 23.0225, "longitude": 72.5714, "state": "Gujarat",     "city": "Ahmedabad",   "network": "CPCB", "is_active": True,  "elevation_m": 53.0},
    {"station_id": "JA001", "station_name": "Jaipur – Chandpole",         "latitude": 26.9260, "longitude": 75.8235, "state": "Rajasthan",   "city": "Jaipur",      "network": "SPCB", "is_active": True,  "elevation_m": 431.0},
    {"station_id": "LK001", "station_name": "Lucknow – Talkatora",        "latitude": 26.8467, "longitude": 80.9462, "state": "Uttar Pradesh","city": "Lucknow",    "network": "CPCB", "is_active": True,  "elevation_m": 111.0},
]


def _registry() -> list[dict]:
    """Station records from the configured dataset, or the demo list."""
    if sources.dataset is None:
        return _STUB_STATIONS
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
    Service class for CPCB station registry queries.

    Provides station metadata used for map rendering and station selectors.
    Does not include readings (use AQIService for those).

    This registry is the single source of valid station IDs: /forecast
    validates against it so /stations and /forecast always agree.
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
        Return a filtered list of CPCB monitoring stations.

        Args:
            state:       Filter by Indian state name (case-insensitive partial match).
            network:     Filter by monitoring network (CPCB | SPCB | SAFAR).
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
