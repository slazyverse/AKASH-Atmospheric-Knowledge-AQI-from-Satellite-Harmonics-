"""Consolidates and validates station metadata from CPCB and OpenAQ."""

import logging
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np

from data_collection_pipeline import config, utils
from data_collection_pipeline.data_cleaning.station_validation import validate_station_metadata

logger = logging.getLogger("data_collection_pipeline.metadata_builder")

def standardize_name(name: str) -> str:
    """Standardizes a station name for deduplication checking."""
    if not isinstance(name, str):
        return ""
    # Remove common monitoring suffixes and non-alphanumeric chars
    cleaned = re.sub(
        r'\s*-\s*(DPCC|MPCB|CPCB|TSPCB|WBPCB|GPCB|IITM|SAFAR|TNPCB|KSPCB|SPCB|UPPCB|BSPCB|CECB|IMC)\b',
        '',
        name,
        flags=re.IGNORECASE
    )
    return re.sub(r'[^a-zA-Z0-9]', '', cleaned).lower()

def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates distance in meters between two lat/lon pairs."""
    r = 6371000.0  # Earth radius in meters
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)
    
    a = np.sin(delta_phi / 2.0)**2 + \
        np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2.0)**2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return r * c

def build_master_station_metadata() -> pd.DataFrame:
    """Consolidates and validates stations list from CPCB and OpenAQ databases."""
    logger.info("Starting consolidation of master station metadata...")
    
    # 1. Load existing base metadata
    base_meta_path = config.METADATA_DIR / "station_metadata.csv"
    base_stations = []
    if base_meta_path.exists():
        try:
            df = pd.read_csv(base_meta_path)
            # Normalize columns
            df.columns = [c.strip() for c in df.columns]
            base_stations = df.to_dict(orient="records")
            logger.info(f"Loaded {len(base_stations)} stations from existing base registry.")
        except Exception as e:
            logger.error(f"Error loading existing station_metadata.csv: {e}")
            
    # 2. Load CPCB raw historical station names from raw drop folders
    cpcb_stations = set()
    cpcb_drop_dir = config.RAW_DATA_DIR / "historical" / "cpcb"
    if cpcb_drop_dir.exists():
        for csv_path in cpcb_drop_dir.glob("*.csv"):
            try:
                df = pd.read_csv(csv_path, usecols=lambda c: str(c).strip().lower() in ["station", "city", "state", "latitude", "longitude"])
                # normalize column keys
                df.columns = [str(c).strip().lower() for c in df.columns]
                if "station" in df.columns:
                    for _, row in df.iterrows():
                        name = str(row["station"]).strip()
                        city = str(row.get("city", "Unknown")).strip()
                        state = str(row.get("state", "")).strip()
                        lat = float(row["latitude"]) if pd.notna(row.get("latitude")) else None
                        lon = float(row["longitude"]) if pd.notna(row.get("longitude")) else None
                        cpcb_stations.add((name, city, state, lat, lon))
            except Exception as e:
                logger.debug(f"Could not parse CPCB drop file {csv_path.name} for metadata: {e}")
                
    logger.info(f"Found {len(cpcb_stations)} unique station candidates in raw CPCB drop files.")

    # 3. Load OpenAQ historical stations
    openaq_stations = set()
    openaq_dir = Path("historical_data/openaq")
    if openaq_dir.exists():
        for csv_path in openaq_dir.glob("**/*.csv"):
            try:
                df = pd.read_csv(csv_path, usecols=lambda c: str(c).strip().lower() in ["station_name", "location_id", "city", "latitude", "longitude"])
                df.columns = [str(c).strip().lower() for c in df.columns]
                # Try getting the station name
                name_col = "station_name" if "station_name" in df.columns else ("location_id" if "location_id" in df.columns else None)
                if name_col:
                    for _, row in df.iterrows():
                        name = str(row[name_col]).strip()
                        city = str(row.get("city", "Unknown")).strip()
                        lat = float(row["latitude"]) if pd.notna(row.get("latitude")) else None
                        lon = float(row["longitude"]) if pd.notna(row.get("longitude")) else None
                        openaq_stations.add((name, city, lat, lon))
            except Exception as e:
                logger.debug(f"Could not parse OpenAQ local file {csv_path.name} for metadata: {e}")

    logger.info(f"Found {len(openaq_stations)} unique station candidates in local OpenAQ caches.")

    # 4. Consolidate and Deduplicate candidates
    # Dict mapping standardized key -> consolidated record dict
    merged_map: Dict[str, Dict[str, Any]] = {}
    
    # Process base registry first (already formatted)
    for row in base_stations:
        raw_name = row.get("station_name") or row.get("Station Name")
        if not raw_name:
            continue
        key = standardize_name(str(raw_name))
        
        # Read fields with fallback keys
        lat = row.get("latitude") if pd.notna(row.get("latitude")) else row.get("Latitude")
        lon = row.get("longitude") if pd.notna(row.get("longitude")) else row.get("Longitude")
        city = row.get("city") or row.get("City", "Unknown")
        state = row.get("state") or row.get("State", "")
        source = row.get("data_source") or row.get("Source", "CPCB")
        
        merged_map[key] = {
            "Station Name": str(raw_name).strip(),
            "City": str(city).strip(),
            "State": str(state).strip(),
            "Latitude": float(lat) if pd.notna(lat) else 0.0,
            "Longitude": float(lon) if pd.notna(lon) else 0.0,
            "Source": str(source).strip(),
            "Last Updated": row.get("last_update") or row.get("Last Updated", "")
        }

    # Helper function to merge a new candidate station
    def add_or_merge_station(name: str, city: str, state: str, lat: Optional[float], lon: Optional[float], source: str):
        key = standardize_name(name)
        
        # Geolocation validation helper
        def is_valid_gps(lt, ln) -> bool:
            return lt is not None and ln is not None and (8.0 <= lt <= 38.0) and (68.0 <= ln <= 98.0)

        gps_valid = is_valid_gps(lat, lon)
        
        if key in merged_map:
            rec = merged_map[key]
            # Merge source
            if source not in rec["Source"]:
                rec["Source"] = f"{rec['Source']}, {source}"
            # Upgrade GPS coordinates if current are invalid/zero
            current_gps_valid = is_valid_gps(rec["Latitude"], rec["Longitude"])
            if not current_gps_valid and gps_valid:
                rec["Latitude"] = lat
                rec["Longitude"] = lon
            if state and not rec["State"]:
                rec["State"] = state
        else:
            # Resolve missing GPS with lookups
            final_lat = lat if gps_valid else 0.0
            final_lon = lon if gps_valid else 0.0
            
            if final_lat == 0.0:
                lk_lat, lk_lon = utils.get_coordinates_for_city(city)
                if is_valid_gps(lk_lat, lk_lon):
                    final_lat, final_lon = lk_lat, lk_lon
                else:
                    final_lat, final_lon = 20.5937, 78.9629  # India center default
                    
            merged_map[key] = {
                "Station Name": name,
                "City": city,
                "State": state,
                "Latitude": final_lat,
                "Longitude": final_lon,
                "Source": source,
                "Last Updated": ""
            }

    # Add CPCB candidates
    for name, city, state, lat, lon in cpcb_stations:
        add_or_merge_station(name, city, state, lat, lon, source="CPCB")
        
    # Add OpenAQ candidates
    for name, city, lat, lon in openaq_stations:
        add_or_merge_station(name, city, "", lat, lon, source="OpenAQ")

    # 5. Spatial Deduplication (merge stations closer than 100 meters in the same city)
    sorted_keys = sorted(list(merged_map.keys()))
    to_delete = set()
    
    for i in range(len(sorted_keys)):
        k1 = sorted_keys[i]
        if k1 in to_delete:
            continue
        r1 = merged_map[k1]
        
        for j in range(i + 1, len(sorted_keys)):
            k2 = sorted_keys[j]
            if k2 in to_delete:
                continue
            r2 = merged_map[k2]
            
            # Check proximity
            if r1["City"].lower() == r2["City"].lower():
                dist = haversine_distance(r1["Latitude"], r1["Longitude"], r2["Latitude"], r2["Longitude"])
                if dist < 100.0: # Closer than 100 meters
                    logger.info(f"Merging spatial duplicates: '{r1['Station Name']}' and '{r2['Station Name']}' (dist={dist:.1f}m)")
                    # Merge r2 into r1
                    if r2["Source"] not in r1["Source"]:
                        r1["Source"] = f"{r1['Source']}, {r2['Source']}"
                    # Prefer valid GPS coordinates
                    if r1["Latitude"] == 20.5937 and r2["Latitude"] != 20.5937:
                        r1["Latitude"] = r2["Latitude"]
                        r1["Longitude"] = r2["Longitude"]
                    to_delete.add(k2)
                    
    for k in to_delete:
        del merged_map[k]

    # Convert to sorted df and assign Station IDs
    rows = list(merged_map.values())
    rows.sort(key=lambda r: (r["City"], r["Station Name"]))
    
    final_rows = []
    for idx, r in enumerate(rows):
        stn_id = f"STN_{idx + 1:03d}"
        final_rows.append({
            "Station ID": stn_id,
            "Station Name": r["Station Name"],
            "City": r["City"],
            "State": r["State"] or r["City"], # Fallback state to city if empty
            "Latitude": r["Latitude"],
            "Longitude": r["Longitude"],
            "Source": r["Source"],
            "Last Updated": r["Last Updated"] or pd.Timestamp.now().strftime("%d-%m-%Y %H:%M:%S")
        })
        
    master_df = pd.DataFrame(final_rows)
    
    # Save files
    config.METADATA_DIR.mkdir(parents=True, exist_ok=True)
    master_csv_path = config.METADATA_DIR / "station_metadata.csv"
    master_df.to_csv(master_csv_path, index=False)
    logger.info(f"Master station metadata built with {len(master_df)} unique stations. Saved to {master_csv_path}")
    
    # Run the station validation engine on it
    validated_path = config.METADATA_DIR / "validated_station_metadata.csv"
    validate_station_metadata(
        station_metadata_path=master_csv_path,
        output_path=validated_path,
        metadata_dir=config.METADATA_DIR,
        logger=logger
    )
    logger.info(f"Validated master metadata written to {validated_path}")
    
    return master_df

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    build_master_station_metadata()
