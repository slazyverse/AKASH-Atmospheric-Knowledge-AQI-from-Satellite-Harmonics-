import os
import json
import pandas as pd
from typing import List, Dict, Any
from historical_ingestor.config import OUTPUT_DIRECTORY, POLLUTANTS
from historical_ingestor.logger import logger

def get_state_filepath() -> str:
    """Return the absolute or relative path to the download state JSON file."""
    os.makedirs(OUTPUT_DIRECTORY, exist_ok=True)
    return os.path.join(OUTPUT_DIRECTORY, "download_state.json")

def load_state() -> dict:
    """Load the download progress state from disk."""
    state_file = get_state_filepath()
    if os.path.exists(state_file):
        try:
            with open(state_file, "r") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load download state: {e}. Starting fresh.")
    return {}

def save_state(state: dict):
    """Save the download progress state to disk."""
    state_file = get_state_filepath()
    try:
        # Create temp file first and rename to avoid corruption
        temp_file = state_file + ".tmp"
        with open(temp_file, "w") as f:
            json.dump(state, f, indent=2)
        if os.path.exists(state_file):
            os.remove(state_file)
        os.rename(temp_file, state_file)
    except Exception as e:
        logger.error(f"Failed to save download state: {e}")

def is_already_downloaded(state: dict, year: int, month: int, station: int, sensor: int) -> bool:
    """Check if a specific year, month, station, and sensor has already been downloaded."""
    year_str = str(year)
    month_str = str(month)
    key = f"{station}_{sensor}"
    return state.get(year_str, {}).get(month_str, {}).get(key, False)

def mark_as_downloaded(state: dict, year: int, month: int, station: int, sensor: int):
    """Mark a specific year, month, station, and sensor as successfully downloaded."""
    year_str = str(year)
    month_str = str(month)
    key = f"{station}_{sensor}"
    if year_str not in state:
        state[year_str] = {}
    if month_str not in state[year_str]:
        state[year_str][month_str] = {}
    state[year_str][month_str][key] = True
    save_state(state)

def get_station_file_path(year: int, location_id: int) -> str:
    """Get the CSV file path for a specific station and year."""
    year_dir = os.path.join(OUTPUT_DIRECTORY, str(year))
    os.makedirs(year_dir, exist_ok=True)
    return os.path.join(year_dir, f"station_{location_id}.csv")

def save_measurements(year: int, measurements: List[Dict[str, Any]], metadata: Dict[str, Any], parameter: str) -> int:
    """Save/append measurements for a station and pollutant in the yearly CSV.
    
    Strictly validates every single record and rejects records with:
    - Empty or missing values/parameters.
    - Invalid or missing timestamps.
    - Missing coordinates (latitude or longitude).
    - Missing pollutant names.
    
    Never replaces missing data with defaults.
    """
    if not measurements:
        return 0
        
    filepath = get_station_file_path(year, metadata.get("location_id"))
    
    records = []
    # Extract unit from metadata mapping if available
    sensor_info = metadata.get("sensors", {}).get(parameter, {})
    metadata_unit = "µg/m³"
    if isinstance(sensor_info, dict):
        metadata_unit = sensor_info.get("unit", "µg/m³")
    elif isinstance(sensor_info, str):
        metadata_unit = sensor_info
        
    for m in measurements:
        # Extract parameter name (pollutant name) from record if available
        rec_param_obj = m.get("parameter", {})
        rec_param_name = rec_param_obj.get("name") if isinstance(rec_param_obj, dict) else None
        
        api_to_standard = {
            "pm25": "PM2.5",
            "pm10": "PM10",
            "no2": "NO2",
            "so2": "SO2",
            "co": "CO",
            "o3": "O3"
        }
        
        m_param = parameter
        if rec_param_name and rec_param_name.lower() in api_to_standard:
            m_param = api_to_standard[rec_param_name.lower()]
            
        if not m_param or m_param not in POLLUTANTS:
            logger.warning(f"Rejected record: missing or invalid pollutant name '{m_param}'.")
            continue
            
        # Extract value (value must not be missing/None)
        val = m.get("value")
        if val is None or pd.isna(val):
            logger.warning("Rejected record: missing measurement value.")
            continue
            
        # Extract timestamps checking all variants in order of specificity
        date_utc = None
        date_local = None
        
        # Helper to extract from dict
        def extract_from_dict(d):
            if isinstance(d, dict):
                return d.get("utc"), d.get("local")
            return None, None
            
        # Try period.datetimeTo and period.datetimeFrom
        if isinstance(m.get("period"), dict):
            p = m["period"]
            for key in ["datetimeTo", "datetimeFrom"]:
                utc, local = extract_from_dict(p.get(key))
                if utc or local:
                    date_utc, date_local = utc, local
                    break
                elif isinstance(p.get(key), str) and p.get(key):
                    date_utc = p.get(key)
                    date_local = p.get(key)
                    break
                    
        # Try datetime
        if not date_utc and not date_local:
            utc, local = extract_from_dict(m.get("datetime"))
            if utc or local:
                date_utc, date_local = utc, local
            elif isinstance(m.get("datetime"), str) and m.get("datetime"):
                date_utc = m["datetime"]
                date_local = m["datetime"]
                
        # Try date
        if not date_utc and not date_local:
            utc, local = extract_from_dict(m.get("date"))
            if utc or local:
                date_utc, date_local = utc, local
            elif isinstance(m.get("date"), str) and m.get("date"):
                date_utc = m["date"]
                date_local = m["date"]
                
        # Try direct keys
        if not date_utc:
            date_utc = m.get("date_utc") or m.get("datetime_utc") or m.get("utc")
        if not date_local:
            date_local = m.get("date_local") or m.get("datetime_local") or m.get("local")
            
        # Fallback if one is missing but the other is present
        if date_utc and not date_local:
            date_local = date_utc
        elif date_local and not date_utc:
            date_utc = date_local
            
        if not date_utc or not date_local:
            # Instrument parser: log the complete raw JSON payload once per unique schema at DEBUG level
            schema_keys = tuple(sorted(m.keys()))
            global _seen_rejected_schemas
            if '_seen_rejected_schemas' not in globals():
                global _seen_rejected_schemas
                _seen_rejected_schemas = set()
            if schema_keys not in _seen_rejected_schemas:
                _seen_rejected_schemas.add(schema_keys)
                logger.debug(f"Rejected schema unique keys: {list(schema_keys)}. Full record JSON: {json.dumps(m)}")
            logger.warning(f"Rejected record: missing UTC or local timestamp. Complete record JSON: {json.dumps(m)}")
            continue
            
        try:
            # Validate ISO timestamp string
            pd.to_datetime(date_utc)
            pd.to_datetime(date_local)
        except Exception:
            logger.warning(f"Rejected record: invalid timestamp format '{date_utc}' or '{date_local}'.")
            continue
            
        # Extract coordinates
        coords = m.get("coordinates")
        lat = coords.get("latitude") if isinstance(coords, dict) else None
        lon = coords.get("longitude") if isinstance(coords, dict) else None
        
        # Fallback to station level only if station level is valid (never replace if both missing)
        if lat is None:
            lat = metadata.get("latitude")
        if lon is None:
            lon = metadata.get("longitude")
            
        if lat is None or lon is None or pd.isna(lat) or pd.isna(lon):
            logger.warning("Rejected record: missing coordinates.")
            continue
            
        # Extract unit directly from record if available, fallback to metadata unit
        rec_unit = rec_param_obj.get("units") if isinstance(rec_param_obj, dict) else None
        record_unit = rec_unit if rec_unit else metadata_unit
            
        record = {
            "location_id": metadata.get("location_id"),
            "station_name": metadata.get("station_name"),
            "latitude": float(lat),
            "longitude": float(lon),
            "city": metadata.get("city"),
            "state": metadata.get("state"),
            "country": metadata.get("country"),
            "parameter": m_param,
            "value": float(val),
            "unit": record_unit,
            "date_utc": date_utc,
            "date_local": date_local
        }
        records.append(record)
        
    if not records:
        return 0
        
    df = pd.DataFrame(records)
    
    # Append to file if it exists, otherwise write new with header
    file_exists = os.path.exists(filepath)
    try:
        df.to_csv(filepath, mode='a', index=False, header=not file_exists)
        return len(records)
    except Exception as e:
        logger.error(f"Failed to save measurements to {filepath}: {e}")
        raise
