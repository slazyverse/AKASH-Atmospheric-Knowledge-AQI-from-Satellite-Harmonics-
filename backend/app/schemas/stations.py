"""
backend/app/schemas/stations.py — Pydantic v2 response models for Station metadata.

Station data represents the physical CPCB (Central Pollution Control Board)
monitoring network across India. Station metadata is static between deployments
and is used by the dashboard to populate station selection dropdowns and maps.

Networks:
  CPCB    — National continuous ambient air quality monitoring (CAAQMS)
  SPCB    — State Pollution Control Board stations
  SAFAR   — System of Air Quality and Weather Forecasting and Research

Models:
  - StationItem      — metadata for a single monitoring station
  - StationsResponse — list envelope for GET /api/v1/stations
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, Field


Latitude  = Annotated[float, Field(ge=-90.0,  le=90.0,  description="WGS-84 latitude")]
Longitude = Annotated[float, Field(ge=-180.0, le=180.0, description="WGS-84 longitude")]


class StationItem(BaseModel):
    """
    Metadata for a single CPCB air quality monitoring station.

    Does not include real-time readings; use GET /api/v1/aqi/daily
    to fetch current observations.
    """

    station_id: str = Field(
        description="Unique CPCB station identifier.",
        examples=["DL001"],
    )
    station_name: str = Field(
        description="Full station display name.",
        examples=["Delhi – Anand Vihar"],
    )
    latitude: Latitude
    longitude: Longitude
    state: str = Field(description="Indian state the station is located in.", examples=["Delhi"])
    city: str = Field(description="City or urban agglomeration.", examples=["Delhi"])
    network: str = Field(
        description="Monitoring network. One of: CPCB | SPCB | SAFAR.",
        examples=["CPCB"],
    )
    is_active: bool = Field(
        description="Whether the station is currently transmitting data.",
        default=True,
    )
    elevation_m: float | None = Field(
        default=None,
        description="Station elevation above mean sea level in metres, if known.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "station_id": "DL001",
                "station_name": "Delhi – Anand Vihar",
                "latitude": 28.6469,
                "longitude": 77.3164,
                "state": "Delhi",
                "city": "Delhi",
                "network": "CPCB",
                "is_active": True,
                "elevation_m": 216.0,
            }
        }
    }


class StationsResponse(BaseModel):
    """
    List envelope for GET /api/v1/stations.

    Returns station metadata (not live readings). Used by the dashboard
    to build station selectors and base map layers.
    """

    count: int = Field(ge=0, description="Total number of stations returned.")
    items: list[StationItem] = Field(description="Station metadata records.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "count": 4,
                "items": [
                    {
                        "station_id": "DL001",
                        "station_name": "Delhi – Anand Vihar",
                        "latitude": 28.6469,
                        "longitude": 77.3164,
                        "state": "Delhi",
                        "city": "Delhi",
                        "network": "CPCB",
                        "is_active": True,
                        "elevation_m": 216.0,
                    }
                ],
            }
        }
    }
