"""
dashboard/services/hcho_service.py — HCHO Hotspot detection service interface.

Formaldehyde (HCHO) is a key secondary pollutant and industrial emission tracer.
This service fetches HCHO column density maps derived from Sentinel-5P TROPOMI data.

Day 2: All methods return typed stub data.
Day 3: Replace stub bodies with APIClient.get() calls.

API endpoints this service will consume (Day 3+):
  GET /api/v1/hcho/hotspots          — Detected hotspot polygons with density values
  GET /api/v1/hcho/grid              — Gridded HCHO column density (NetCDF metadata)
  GET /api/v1/hcho/trends            — Monthly trend data for a bounding box
  GET /api/v1/hcho/sources           — Source attribution (industrial, biogenic, biomass)
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

from dashboard.services.api_client import APIClient


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
        Return detected HCHO hotspots meeting confidence threshold.

        Day 2: Returns 3 stub hotspots.
        Day 3: resp = self._client.get("/hcho/hotspots", params={...})
        """
        return [
            HCHOHotspot("HS-001", 22.572, 88.363, 45.2, 12.4, "industrial",     0.91),
            HCHOHotspot("HS-002", 13.083, 80.270, 28.7,  8.1, "biomass_burning", 0.74),
            HCHOHotspot("HS-003", 26.847, 80.946, 61.3, 15.9, "biogenic",       0.68),
        ]

    def get_monthly_trends(
        self,
        region: str = "India",
        months: int = 12,
    ) -> list[HCHOTrend]:
        """
        Return monthly HCHO trend data.

        Day 2: Returns empty list.
        Day 3: resp = self._client.get("/hcho/trends", params={"region": region, "months": months})
        """
        return []

    def get_source_attribution(self, hotspot_id: str) -> dict[str, Any]:
        """
        Return source-type breakdown for a specific hotspot.

        Day 2: Returns stub attribution.
        Day 3: resp = self._client.get(f"/hcho/sources/{hotspot_id}")
        """
        return {
            "hotspot_id": hotspot_id,
            "industrial": 0.55,
            "biogenic": 0.30,
            "biomass_burning": 0.10,
            "unknown": 0.05,
            "stub": True,
        }


hcho_service = HCHOService()
