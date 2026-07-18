from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class CommonObservationSchema:
    location_id: str
    timestamp_utc: datetime
    timestamp_local: datetime
    pollutant: str
    value: float
    unit: str
    source_name: str
    qa_flag: str

@dataclass
class StationMetadataSchema:
    location_id: str
    source_station_id: str
    station_name: str
    latitude: float
    longitude: float
    elevation_m: Optional[float]
    city: str
    state: str
    country: str
    status: str
