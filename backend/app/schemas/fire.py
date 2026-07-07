"""
backend/app/schemas/fire.py — Pydantic v2 response models for Fire Monitoring data.

Active fire detections are sourced from two satellite instruments:
  - MODIS (Terra/Aqua) — 1 km resolution, 1-2 daily passes
  - VIIRS (SNPP / NOAA-20) — 375 m resolution, 1-2 daily passes

Fire Radiative Power (FRP) is measured in megawatts (MW) and is the primary
metric for fire intensity and smoke emission estimation.

Models:
  - FireEventItem  — individual active fire detection point
  - FireAlertItem  — high-severity fire alert requiring attention
  - FireResponse   — composite envelope for GET /api/v1/fire
"""

from __future__ import annotations

from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field


Latitude  = Annotated[float, Field(ge=-90.0,  le=90.0,  description="WGS-84 latitude of fire detection")]
Longitude = Annotated[float, Field(ge=-180.0, le=180.0, description="WGS-84 longitude of fire detection")]


class FireEventItem(BaseModel):
    """
    A single satellite-detected active fire point.

    FRP (Fire Radiative Power) correlates with smoke injection rate and
    is used to estimate PM2.5 contribution to downwind stations.
    Brightness temperature distinguishes true fires from warm surfaces.
    """

    event_id: str = Field(
        description="Unique fire event identifier.",
        examples=["F-2024-001"],
    )
    latitude: Latitude
    longitude: Longitude
    frp: float = Field(
        ge=0,
        description="Fire Radiative Power in megawatts (MW). Higher values indicate more intense fires.",
    )
    brightness: float = Field(
        ge=200,
        description="Brightness temperature in Kelvin at the fire pixel. Threshold for detection: ~310 K.",
    )
    satellite: str = Field(
        description="Detecting satellite instrument. One of: MODIS | VIIRS-SNPP | VIIRS-NOAA20.",
        examples=["VIIRS-SNPP"],
    )
    confidence: str = Field(
        description="Detection confidence class. One of: low | nominal | high.",
        examples=["high"],
    )
    land_cover: str = Field(
        description=(
            "Dominant land cover type at the fire location. "
            "One of: forest | cropland | grassland | shrubland | other."
        ),
        examples=["forest"],
    )
    state: str = Field(description="Indian state where the fire is located.", examples=["Jharkhand"])
    district: str = Field(description="District within the state.", examples=["Ranchi"])
    detected_at: datetime = Field(description="UTC timestamp of satellite overpass detection.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "event_id": "F-2024-001",
                "latitude": 23.312,
                "longitude": 85.334,
                "frp": 142.4,
                "brightness": 328.7,
                "satellite": "VIIRS-SNPP",
                "confidence": "high",
                "land_cover": "forest",
                "state": "Jharkhand",
                "district": "Ranchi",
                "detected_at": "2026-07-07T04:15:00Z",
            }
        }
    }


class FireAlertItem(BaseModel):
    """
    A high-severity fire alert generated when FRP exceeds thresholds
    or when predicted AQI impact at downwind stations is significant.
    """

    alert_id: str = Field(description="Unique alert identifier.", examples=["A-001"])
    fire_event_id: str = Field(description="Reference to the triggering FireEventItem.", examples=["F-2024-001"])
    severity: str = Field(
        description="Alert severity level. One of: moderate | high | critical.",
        examples=["critical"],
    )
    aqi_impact_score: float = Field(
        ge=0,
        description="Estimated AQI increase at the nearest downwind station attributable to this fire.",
    )
    message: str = Field(description="Human-readable alert message for operators.")
    issued_at: datetime = Field(description="UTC timestamp when this alert was generated.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "alert_id": "A-001",
                "fire_event_id": "F-2024-001",
                "severity": "critical",
                "aqi_impact_score": 87.4,
                "message": "Extreme fire activity in Jharkhand forest. AQI spike expected in 6–8 hours.",
                "issued_at": "2026-07-07T04:20:00Z",
            }
        }
    }


class FireResponse(BaseModel):
    """
    Composite envelope for GET /api/v1/fire.

    Returns both active fire detections and high-severity alerts in a
    single response to avoid multiple round-trips from the dashboard.
    """

    total_events: int = Field(ge=0, description="Total number of fire events returned.")
    total_alerts: int = Field(ge=0, description="Total number of active alerts.")
    hours_window: int = Field(ge=1, description="Time window in hours over which events were queried.")
    events: list[FireEventItem] = Field(description="Active fire detection points.")
    alerts: list[FireAlertItem] = Field(description="High-severity fire alerts.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total_events": 4,
                "total_alerts": 2,
                "hours_window": 24,
                "events": [],
                "alerts": [],
            }
        }
    }
