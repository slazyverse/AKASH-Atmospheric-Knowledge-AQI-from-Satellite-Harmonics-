"""
backend/app/schemas/aqi.py — Pydantic v2 response models for Surface AQI data.

Models:
  - StationReading    — per-station AQI observation with pollutant breakdown
  - AQIDailySummary   — regional daily AQI aggregate (min / max / avg)
  - AQIDailyListResponse — paginated list envelope for GET /api/v1/aqi/daily

AQI Categories follow the CPCB (Central Pollution Control Board) India scale:
  Good (0-50) | Satisfactory (51-100) | Moderate (101-200)
  Poor (201-300) | Very Poor (301-400) | Severe (401-500)
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Annotated

from pydantic import BaseModel, Field


# ── Shared type aliases ────────────────────────────────────────────────────────

Latitude  = Annotated[float, Field(ge=-90.0,  le=90.0,  description="WGS-84 latitude")]
Longitude = Annotated[float, Field(ge=-180.0, le=180.0, description="WGS-84 longitude")]
AQIValue  = Annotated[int,   Field(ge=0,      le=1000,  description="CPCB AQI index (0–500, may exceed during severe episodes)")]


# ── Station-level reading ──────────────────────────────────────────────────────

class StationReading(BaseModel):
    """
    A single AQI observation from one CPCB monitoring station.

    Pollutant concentrations follow CPCB reporting units:
      PM2.5, PM10, NO2, SO2, O3 — µg/m³
      CO                         — mg/m³
    """

    station_id: str = Field(
        description="CPCB station identifier (e.g., 'DL001').",
        examples=["DL001"],
    )
    station_name: str = Field(
        description="Human-readable station name.",
        examples=["Delhi – Anand Vihar"],
    )
    latitude: Latitude
    longitude: Longitude
    aqi_value: AQIValue
    aqi_category: str = Field(
        description=(
            "CPCB AQI category string. "
            "One of: Good | Satisfactory | Moderate | Poor | Very Poor | Severe."
        ),
        examples=["Very Poor"],
    )
    pm25: float = Field(ge=0, description="PM2.5 concentration in µg/m³.")
    pm10: float = Field(ge=0, description="PM10 concentration in µg/m³.")
    no2: float  = Field(ge=0, description="NO₂ concentration in µg/m³.")
    so2: float  = Field(ge=0, description="SO₂ concentration in µg/m³.")
    co: float   = Field(ge=0, description="CO concentration in mg/m³.")
    o3: float   = Field(ge=0, description="O₃ concentration in µg/m³.")
    recorded_at: datetime = Field(description="UTC timestamp of this observation.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "station_id": "DL001",
                "station_name": "Delhi – Anand Vihar",
                "latitude": 28.6469,
                "longitude": 77.3164,
                "aqi_value": 312,
                "aqi_category": "Very Poor",
                "pm25": 89.2,
                "pm10": 178.4,
                "no2": 62.1,
                "so2": 22.4,
                "co": 1.8,
                "o3": 44.2,
                "recorded_at": "2026-07-07T12:00:00Z",
            }
        }
    }


# ── Regional daily summary ─────────────────────────────────────────────────────

class AQIDailySummary(BaseModel):
    """
    Aggregated AQI statistics for a region over a calendar date.

    Used by dashboards to display national-level KPI cards without
    fetching every individual station reading.
    """

    region: str = Field(description="Region name (e.g., 'India', 'North India').")
    summary_date: date = Field(description="The calendar date this summary covers (UTC).")
    station_count: int = Field(ge=0, description="Number of active stations contributing to this summary.")
    avg_aqi: float = Field(ge=0, description="Population-weighted average AQI across all stations.")
    max_aqi: int   = Field(ge=0, description="Highest AQI recorded by any station.")
    min_aqi: int   = Field(ge=0, description="Lowest AQI recorded by any station.")
    dominant_pollutant: str = Field(description="Pollutant responsible for the highest AQI contribution.")
    readings: list[StationReading] = Field(
        default_factory=list,
        description="Individual station readings included in this summary.",
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "region": "India",
                "summary_date": "2026-07-07",
                "station_count": 412,
                "avg_aqi": 148,
                "max_aqi": 421,
                "min_aqi": 12,
                "dominant_pollutant": "PM2.5",
                "readings": [],
            }
        }
    }


# ── List response envelope ─────────────────────────────────────────────────────

class AQIDailyListResponse(BaseModel):
    """
    Paginated envelope for GET /api/v1/aqi/daily.

    The outer envelope allows the API to add pagination cursors or
    metadata in a non-breaking way without restructuring the array.
    """

    count: int = Field(ge=0, description="Total number of readings returned in this response.")
    region: str = Field(description="Region filter applied to this query.")
    summary: AQIDailySummary = Field(description="Aggregate summary for the queried region and date.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "count": 4,
                "region": "India",
                "summary": {
                    "region": "India",
                    "summary_date": "2026-07-07",
                    "station_count": 412,
                    "avg_aqi": 148,
                    "max_aqi": 421,
                    "min_aqi": 12,
                    "dominant_pollutant": "PM2.5",
                    "readings": [],
                },
            }
        }
    }
