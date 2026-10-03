"""
dashboard/core/gis_interfaces.py — replaceable raster-layer sources for the maps.

A raster overlay (e.g. an interpolated AQI surface, an HCHO column COG or a
fire-density grid) is shown ONLY when a real XYZ tile source is configured via
its environment variable — for example a TiTiler endpoint serving the team's
Cloud-Optimised GeoTIFFs:

    VAYU_AQI_RASTER_TILES=https://tiles.example/aqi/{z}/{x}/{y}.png?date={date}

No raster source exists today (no interpolation, Gi*/LISA or HYSPLIT output is
produced), so no raster layer is added to any map. Nothing is faked: there are
no placeholder tile URLs and no invented raster metadata.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class RasterLayerSource:
    """One raster overlay; available only when its tile template env var is set."""

    layer_id: str
    display_name: str
    env_var: str
    attribution: str

    def tile_url(self, target_date: datetime) -> str | None:
        """XYZ tile URL for the date, or None when no raster source is configured."""
        template = os.getenv(self.env_var, "").strip()
        if not template:
            return None
        return template.replace("{date}", target_date.strftime("%Y-%m-%d"))

    @property
    def available(self) -> bool:
        return bool(os.getenv(self.env_var, "").strip())


AQI_RASTER = RasterLayerSource(
    "aqi_raster", "Interpolated AQI surface", "VAYU_AQI_RASTER_TILES", "Team AQI raster"
)
HCHO_RASTER = RasterLayerSource(
    "hcho_raster", "HCHO column (Sentinel-5P)", "VAYU_HCHO_RASTER_TILES", "Team HCHO raster"
)
FIRE_RASTER = RasterLayerSource(
    "fire_raster", "Fire radiative power density", "VAYU_FIRE_RASTER_TILES", "Team fire raster"
)
