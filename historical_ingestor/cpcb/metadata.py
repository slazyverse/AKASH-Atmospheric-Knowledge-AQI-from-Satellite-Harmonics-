import pandas as pd
import hashlib
from typing import Dict, List
from historical_ingestor.cpcb.schema import StationMetadataSchema

def generate_location_id(station_name: str, latitude: float, longitude: float) -> str:
    """Generate a reproducible unique ID for a station."""
    unique_str = f"{station_name}_{latitude}_{longitude}"
    return "CPCB_" + hashlib.md5(unique_str.encode('utf-8')).hexdigest()[:8]

def extract_metadata(df: pd.DataFrame) -> List[StationMetadataSchema]:
    """
    Extracts unique stations from the raw dataframe.
    Expects columns: ['station', 'city', 'state', 'country', 'latitude', 'longitude']
    """
    # Safely get available metadata columns
    meta_cols = []
    for col in ['station', 'city', 'state', 'country', 'latitude', 'longitude']:
        if col in df.columns:
            meta_cols.append(col)
            
    if not meta_cols:
        return []

    unique_stations = df.drop_duplicates(subset=['station']).copy() if 'station' in meta_cols else df.drop_duplicates(subset=meta_cols).copy()
    
    metadata_list = []
    for _, row in unique_stations.iterrows():
        station_name = str(row['station']) if 'station' in row else 'Unknown'
        lat = float(row['latitude']) if 'latitude' in row and pd.notnull(row['latitude']) else 0.0
        lon = float(row['longitude']) if 'longitude' in row and pd.notnull(row['longitude']) else 0.0
        
        loc_id = generate_location_id(station_name, lat, lon)
        
        meta = StationMetadataSchema(
            location_id=loc_id,
            source_station_id=station_name,
            station_name=station_name,
            latitude=lat,
            longitude=lon,
            elevation_m=None,
            city=str(row['city']) if 'city' in row else 'Unknown',
            state=str(row['state']) if 'state' in row else 'Unknown',
            country=str(row['country']) if 'country' in row else 'IN',
            status='ACTIVE'
        )
        metadata_list.append(meta)
        
    return metadata_list
