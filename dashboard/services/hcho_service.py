"""
dashboard/services/hcho_service.py — HCHO Hotspot detection service interface.

Provides HCHO column density data from Sentinel-5P TROPOMI for the dashboard.

Day 3: Methods call the live APIClient against GET /api/v1/hcho/hotspots.
       Falls back to stub data on any APIError.

API endpoints consumed:
  GET /api/v1/hcho/hotspots — Detected hotspot polygons with density values
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from dashboard.services.api_client import APIClient, APIError


@dataclass
class HCHOHotspot:
    """Represents a detected HCHO concentration hotspot."""
    hotspot_id: str
    latitude: float
    longitude: float
    radius_km: float
    column_density: float           # molecules/cm² × 10¹⁵
    source_type: str                # industrial | biogenic | biomass_burning | unknown
    confidence: float               # 0.0 – 1.0
    detected_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class HCHOTrend:
    """Monthly HCHO trend record for a region."""
    year_month: str                 # "YYYY-MM"
    region: str
    mean_column_density: float
    anomaly_score: float            # Deviation from climatological baseline


# ── Fallback stub data ─────────────────────────────────────────────────────────

_STUB_HOTSPOTS = [
    HCHOHotspot("HS-001", 22.572, 88.363, 45.2, 12.4, "industrial",     0.91),
    HCHOHotspot("HS-002", 13.083, 80.270, 28.7,  8.1, "biomass_burning", 0.74),
    HCHOHotspot("HS-003", 26.847, 80.946, 61.3, 15.9, "biogenic",       0.68),
]


class HCHOService:
    """Fetches HCHO hotspot and trend data from the VAYU-DRISHTI backend."""

    def __init__(self, client: APIClient | None = None) -> None:
        self._client = client or APIClient()

    def get_hotspots(
        self,
        date_str: str | None = None,
        min_confidence: float = 0.6,
        bbox: tuple[float, float, float, float] | None = None,
    ) -> list[HCHOHotspot]:
        """
        Return detected HCHO hotspots from GET /api/v1/hcho/hotspots.
        Falls back to stub data if the backend is offline.
        """
        try:
            params: dict[str, Any] = {"min_confidence": min_confidence}
            if date_str:
                params["date"] = date_str
            resp = self._client.get("/hcho/hotspots", params=params)
            items = resp.data.get("items", [])
            if not items:
                return _STUB_HOTSPOTS

            return [
                HCHOHotspot(
                    hotspot_id=h["hotspot_id"],
                    latitude=h["latitude"],
                    longitude=h["longitude"],
                    radius_km=h["radius_km"],
                    column_density=h["column_density"],
                    source_type=h["source_type"],
                    confidence=h["confidence"],
                    detected_at=datetime.fromisoformat(
                        h["detected_at"].replace("Z", "+00:00")
                    ),
                )
                for h in items
            ]
        except APIError:
            return _STUB_HOTSPOTS

    def get_monthly_trends(
        self,
        region: str = "India",
        months: int = 12,
    ) -> list[HCHOTrend]:
        """
        Return monthly HCHO trend data.

        Note: dedicated trend endpoint deferred to Day N. Returns empty list.
        """
        return []

    def get_source_attribution(self, hotspot_id: str) -> dict[str, Any]:
        """
        Return source-type breakdown for a specific hotspot.

        Note: dedicated source endpoint deferred to Day N. Returns stub attribution.
        """
        return {
            "hotspot_id": hotspot_id,
            "industrial": 0.55,
            "biogenic": 0.30,
            "biomass_burning": 0.10,
            "unknown": 0.05,
        }


hcho_service = HCHOService()
