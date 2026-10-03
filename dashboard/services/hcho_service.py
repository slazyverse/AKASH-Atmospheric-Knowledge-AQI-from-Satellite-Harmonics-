"""
dashboard/services/hcho_service.py — HCHO hotspot service interface.

Returns exactly what the API returns (no hardcoded hotspots). Hotspot clusters
carry no radius / confidence / date in the team contract, so those stay None.

API endpoints consumed:
  GET /api/v1/hcho/hotspots — Hotspot clusters (10¹⁵ molecules/cm²)
  GET /api/v1/hcho/trend    — Daily station-collocated HCHO mean
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Any

from dashboard.services.api_client import APIClient, APIError


@dataclass
class HCHOHotspot:
    """A detected HCHO concentration hotspot cluster."""
    hotspot_id: str
    latitude: float
    longitude: float
    radius_km: float | None         # None = not provided by the source
    column_density: float           # molecules/cm² × 10¹⁵
    source_type: str                # industrial | biogenic | biomass_burning | unknown
    confidence: float | None        # 0.0 – 1.0; None = not scored
    detected_at: datetime | None    # None = source carries no date


@dataclass
class HCHOTrendPoint:
    """Daily mean HCHO column at the station dataset's stations."""
    obs_date: date
    mean_column_density: float     # molecules/cm² × 10¹⁵
    station_count: int


class HCHOService:
    """Fetches HCHO hotspot and trend data from the VAYU-DRISHTI backend."""

    def __init__(self, client: APIClient | None = None) -> None:
        self._client = client or APIClient()

    def get_hotspots(
        self,
        date_str: str | None = None,
        min_confidence: float = 0.6,
    ) -> list[HCHOHotspot]:
        """Hotspot clusters (GET /api/v1/hcho/hotspots); [] if none or backend unreachable."""
        params: dict[str, Any] = {"min_confidence": min_confidence}
        if date_str:
            params["date"] = date_str
        try:
            items = self._client.get("/hcho/hotspots", params=params).data.get("items", [])
            return [
                HCHOHotspot(
                    hotspot_id=h["hotspot_id"],
                    latitude=h["latitude"],
                    longitude=h["longitude"],
                    radius_km=h.get("radius_km"),
                    column_density=h["column_density"],
                    source_type=h["source_type"],
                    confidence=h.get("confidence"),
                    detected_at=(
                        datetime.fromisoformat(h["detected_at"].replace("Z", "+00:00"))
                        if h.get("detected_at") else None
                    ),
                )
                for h in items
            ]
        except (APIError, KeyError, TypeError, ValueError):
            return []

    def get_trend(self, days: int = 30) -> list[HCHOTrendPoint]:
        """Daily station-collocated HCHO means (GET /api/v1/hcho/trend); [] if unavailable."""
        try:
            points = self._client.get("/hcho/trend", params={"days": days}).data.get("points", [])
            return [
                HCHOTrendPoint(
                    obs_date=date.fromisoformat(p["obs_date"]),
                    mean_column_density=p["mean_column_density"],
                    station_count=p["station_count"],
                )
                for p in points
            ]
        except (APIError, KeyError, TypeError, ValueError):
            return []


hcho_service = HCHOService()
