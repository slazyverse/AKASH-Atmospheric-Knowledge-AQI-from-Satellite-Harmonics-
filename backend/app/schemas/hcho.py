"""
backend/app/schemas/hcho.py — Pydantic v2 response models for HCHO Hotspot data.

Formaldehyde (HCHO) column density data is sourced from the Sentinel-5P
TROPOMI instrument at 3.5×5.5 km spatial resolution with daily global coverage.

Models:
  - HCHOHotspotItem      — a detected concentration hotspot polygon
  - HCHOHotspotsResponse — envelope for GET /api/v1/hcho/hotspots

Source type classification:
  industrial      — coal plants, chemical factories, refineries
  biogenic        — vegetation VOC emissions (isoprene oxidation)
  biomass_burning — crop stubble, forest fires
  unknown         — unattributed signal
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field


Latitude  = Annotated[float, Field(ge=-90.0,  le=90.0,  description="WGS-84 latitude of hotspot centroid")]
Longitude = Annotated[float, Field(ge=-180.0, le=180.0, description="WGS-84 longitude of hotspot centroid")]


class HCHOHotspotItem(BaseModel):
    """
    A detected HCHO concentration hotspot from Sentinel-5P TROPOMI.

    Column density is reported in units of 10¹⁵ molecules/cm²
    (the conventional scientific unit for tropospheric HCHO columns).
    Values above ~8×10¹⁵ mol/cm² are considered elevated above background.
    """

    hotspot_id: str = Field(
        description="Unique hotspot identifier for this detection event.",
        examples=["HS-001"],
    )
    latitude: Latitude
    longitude: Longitude
    radius_km: float = Field(
        ge=0,
        description="Approximate radius of the hotspot in kilometres.",
    )
    column_density: float = Field(
        ge=0,
        description="HCHO column density in units of 10¹⁵ molecules/cm².",
    )
    source_type: str = Field(
        description=(
            "Attributed emission source type. "
            "One of: industrial | biogenic | biomass_burning | unknown."
        ),
        examples=["industrial"],
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Detection confidence score between 0.0 and 1.0.",
    )
    detected_at: datetime = Field(
        description="UTC timestamp of the TROPOMI overpass that detected this hotspot.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "hotspot_id": "HS-001",
                "latitude": 22.572,
                "longitude": 88.363,
                "radius_km": 45.2,
                "column_density": 12.4,
                "source_type": "industrial",
                "confidence": 0.91,
                "detected_at": "2026-07-07T06:30:00Z",
            }
        }
    }


class HCHOHotspotsResponse(BaseModel):
    """
    Envelope for GET /api/v1/hcho/hotspots.

    Returns a filtered list of HCHO hotspots for a given date and
    minimum confidence threshold.
    """

    count: int = Field(ge=0, description="Number of hotspots returned after filtering.")
    query_date: date = Field(description="The TROPOMI observation date queried.")
    min_confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Minimum confidence threshold applied to filter results.",
    )
    items: list[HCHOHotspotItem] = Field(description="List of detected HCHO hotspots.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "count": 3,
                "query_date": "2026-07-07",
                "min_confidence": 0.6,
                "items": [
                    {
                        "hotspot_id": "HS-001",
                        "latitude": 22.572,
                        "longitude": 88.363,
                        "radius_km": 45.2,
                        "column_density": 12.4,
                        "source_type": "industrial",
                        "confidence": 0.91,
                        "detected_at": "2026-07-07T06:30:00Z",
                    }
                ],
            }
        }
    }
