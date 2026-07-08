"""
dashboard/core/gis_interfaces.py — Reusable interfaces for Cloud Optimized GeoTIFF (COG) & Raster Support.

This module defines the architectural contracts and extension points for displaying
satellite raster data (AQI, HCHO, active fires) in Folium map components without
requiring dashboard design changes.

The design conforms to the Open/Closed Principle (OCP) of SOLID, allowing future
sprints (e.g., Day 5 GIS integration) to add concrete raster-fetching implementations
by simply subclassing the interfaces defined here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class RasterMetadata:
    """
    Geospatial and statistical metadata for a Cloud Optimized GeoTIFF (COG).
    Sourced from remote COG headers (e.g., via TiTiler or directly from S3/GDAL).
    """
    bounds: tuple[float, float, float, float]  # (min_lon, min_lat, max_lon, max_lat)
    crs: str                                  # Coordinate Reference System, e.g. "EPSG:4326"
    resolution: tuple[float, float]           # Grid resolution in degrees (x, y)
    width: int                                # Grid width in pixels
    height: int                               # Grid height in pixels
    min_value: float                          # Minimum statistical value in band
    max_value: float                          # Maximum statistical value in band
    band_name: str                            # Name of the active band, e.g. "HCHO_column_density"
    attributes: Dict[str, Any] = field(default_factory=dict)


class COGRasterInterface:
    """
    Abstract interface defining the contract for any Cloud Optimized GeoTIFF (COG) layer.

    Day 4: Architectural foundation.
    Day 5: Real implementations will communicate with a Titiler instance or backend
           COG endpoint to resolve spatial tiles and legends.
    """

    def __init__(
        self,
        layer_id: str,
        display_name: str,
        colormap_name: str = "viridis",
    ) -> None:
        self.layer_id = layer_id
        self.display_name = display_name
        self.colormap_name = colormap_name

    def get_tile_url(
        self,
        target_date: datetime,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
    ) -> str:
        """
        Generate a leaflet-compatible XYZ Tile URL template.

        Example:
            "https://titiler.vayu-drishti.org/cog/tiles/{z}/{x}/{y}@1x?url=s3://bucket/cog.tif"
        """
        raise NotImplementedError("COG tile generation must be implemented in concrete subclasses.")

    def fetch_metadata(self, target_date: datetime) -> RasterMetadata:
        """
        Retrieve COG spatial headers and statistics.
        """
        raise NotImplementedError("Metadata retrieval must be implemented in concrete subclasses.")

    def get_legend_colors(self) -> List[Dict[str, Any]]:
        """
        Return the color mapping table for rendering a map legend card.
        Format: [{'value': 10, 'color': '#hex'}, ...]
        """
        raise NotImplementedError("Legend mapping must be implemented in concrete subclasses.")


class AQIRasterInterface(COGRasterInterface):
    """
    Concrete contract for Surface AQI spatial interpolation rasters (e.g. IDW or Kriging results).
    """

    def __init__(self) -> None:
        super().__init__(
            layer_id="aqi_interpolation_raster",
            display_name="Interpolated AQI Raster",
            colormap_name="turbo",  # Vibrant color ramp suitable for multi-hazard AQI bands
        )

    def get_tile_url(
        self,
        target_date: datetime,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
    ) -> str:
        # Day 4: Return a dummy tile template or a placeholder URL pattern.
        # In production, this maps to titiler/cog/tiles/{z}/{x}/{y} targeting the backend S3 COG path.
        date_str = target_date.strftime("%Y-%m-%d")
        return (
            "https://tiles.stadiamaps.com/tiles/stamen_toner_labels/{z}/{x}/{y}.png"
            f"?date={date_str}"  # Placeholder
        )

    def fetch_metadata(self, target_date: datetime) -> RasterMetadata:
        # Day 4 placeholder metadata
        return RasterMetadata(
            bounds=(68.1, 8.0, 97.4, 35.5),  # Extent of India
            crs="EPSG:4326",
            resolution=(0.01, 0.01),
            width=2930,
            height=2750,
            min_value=0.0,
            max_value=500.0,
            band_name="CPCB_AQI_kriging",
        )

    def get_legend_colors(self) -> List[Dict[str, Any]]:
        # Map AQI categories to colors for the map legend card
        from dashboard.core.theme import AQI_GOOD, AQI_SATISFACTORY, AQI_MODERATE, AQI_POOR, AQI_VERY_POOR, AQI_SEVERE
        return [
            {"value": "0 - 50", "color": AQI_GOOD, "label": "Good"},
            {"value": "51 - 100", "color": AQI_SATISFACTORY, "label": "Satisfactory"},
            {"value": "101 - 200", "color": AQI_MODERATE, "label": "Moderate"},
            {"value": "201 - 300", "color": AQI_POOR, "label": "Poor"},
            {"value": "301 - 400", "color": AQI_VERY_POOR, "label": "Very Poor"},
            {"value": "401+", "color": AQI_SEVERE, "label": "Severe"},
        ]


class HCHORasterInterface(COGRasterInterface):
    """
    Concrete contract for Sentinel-5P TROPOMI HCHO column density rasters.
    """

    def __init__(self) -> None:
        super().__init__(
            layer_id="s5p_hcho_raster",
            display_name="Sentinel-5P HCHO Column Density",
            colormap_name="magma",  # Dark purple to bright yellow, excellent for density visualization
        )

    def get_tile_url(
        self,
        target_date: datetime,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
    ) -> str:
        date_str = target_date.strftime("%Y-%m-%d")
        return (
            "https://tiles.stadiamaps.com/tiles/stamen_toner_labels/{z}/{x}/{y}.png"
            f"?hcho_date={date_str}"  # Placeholder
        )

    def fetch_metadata(self, target_date: datetime) -> RasterMetadata:
        return RasterMetadata(
            bounds=(68.1, 8.0, 97.4, 35.5),
            crs="EPSG:4326",
            resolution=(0.035, 0.055),  # Sentinel-5P resolution is ~3.5x5.5 km
            width=840,
            height=500,
            min_value=0.0,
            max_value=30.0,
            band_name="HCHO_column_density",
        )

    def get_legend_colors(self) -> List[Dict[str, Any]]:
        return [
            {"value": "0 - 5", "color": "#220050", "label": "Low"},
            {"value": "5 - 10", "color": "#781C6B", "label": "Moderate"},
            {"value": "10 - 15", "color": "#D3436C", "label": "High"},
            {"value": "15+", "color": "#FBB07A", "label": "Extreme (×10¹⁵ mol/cm²)"},
        ]


class FireRasterInterface(COGRasterInterface):
    """
    Concrete contract for active fire radiative power (FRP) density / hot-spot heatmaps.
    """

    def __init__(self) -> None:
        super().__init__(
            layer_id="modis_viirs_fire_density",
            display_name="Fire Radiative Power Density",
            colormap_name="inferno",  # Dark orange to yellow, representing fire thermal output
        )

    def get_tile_url(
        self,
        target_date: datetime,
        min_val: Optional[float] = None,
        max_val: Optional[float] = None,
    ) -> str:
        date_str = target_date.strftime("%Y-%m-%d")
        return (
            "https://tiles.stadiamaps.com/tiles/stamen_toner_labels/{z}/{x}/{y}.png"
            f"?fire_date={date_str}"  # Placeholder
        )

    def fetch_metadata(self, target_date: datetime) -> RasterMetadata:
        return RasterMetadata(
            bounds=(68.1, 8.0, 97.4, 35.5),
            crs="EPSG:4326",
            resolution=(0.01, 0.01),  # MODIS ~1km resolution
            width=2930,
            height=2750,
            min_value=0.0,
            max_value=1500.0,  # Max FRP value observed
            band_name="FRP_density",
        )

    def get_legend_colors(self) -> List[Dict[str, Any]]:
        from dashboard.core.theme import ACCENT_ORANGE, ACCENT_YELLOW, PRIMARY
        return [
            {"value": "0 - 20", "color": PRIMARY, "label": "Low Intensity"},
            {"value": "20 - 100", "color": ACCENT_YELLOW, "label": "Moderate FRP"},
            {"value": "100 - 300", "color": ACCENT_ORANGE, "label": "High FRP"},
            {"value": "300+", "color": "#B71C1C", "label": "Critical (MW)"},
        ]
