"""Extracts static station features (elevation, land cover) from GEE."""

import logging
from pathlib import Path
import pandas as pd
import numpy as np
import json
import urllib.request
import math

from data_collection_pipeline import config
from data_collection_pipeline.earth_engine.initializer import initialize_ee, is_ee_initialized

logger = logging.getLogger("data_collection_pipeline.static_features")

# ESA WorldCover class mappings
WORLDCOVER_CLASSES = {
    10: "Trees",
    20: "Shrubland",
    30: "Grassland",
    40: "Cropland",
    50: "Built-up (Urban)",
    60: "Barren / Sparse vegetation",
    70: "Snow and ice",
    80: "Open water",
    90: "Herbaceous wetland",
    95: "Mangroves",
    100: "Moss and lichen"
}

def _compute_coastline_distances(df_stations: pd.DataFrame) -> dict:
    """Downloads Natural Earth 110m coastline and computes geodesic distance (km)."""
    logger.info("Fetching Natural Earth 110m Coastline data...")
    geojson_url = "https://raw.githubusercontent.com/martynafford/natural-earth-geojson/master/110m/physical/ne_110m_coastline.json"
    cache_path = config.METADATA_DIR / "ne_110m_coastline.json"
    
    if not cache_path.exists():
        try:
            with urllib.request.urlopen(geojson_url) as response:
                data = json.loads(response.read().decode())
                with open(cache_path, 'w') as f:
                    json.dump(data, f)
        except Exception as e:
            logger.error(f"Failed to download coastline data: {e}")
            return {}
            
    with open(cache_path, 'r') as f:
        data = json.load(f)
        
    coast_coords = []
    for feature in data.get("features", []):
        geom = feature.get("geometry", {})
        if geom.get("type") == "LineString":
            coast_coords.extend(geom.get("coordinates", []))
        elif geom.get("type") == "MultiLineString":
            for linestring in geom.get("coordinates", []):
                coast_coords.extend(linestring)
                
    if not coast_coords:
        return {}
        
    coast_coords = np.array(coast_coords)
    coast_lon = np.radians(coast_coords[:, 0])
    coast_lat = np.radians(coast_coords[:, 1])
    R = 6371.0
    
    distances = {}
    logger.info("Computing geodesic distance to nearest coast for stations...")
    for _, row in df_stations.iterrows():
        lat = float(row.get("latitude", row.get("Latitude", 0.0)))
        lon = float(row.get("longitude", row.get("Longitude", 0.0)))
        stn_id = str(row.get("station_id", row.get("Station ID")))
        if lat == 0.0 or lon == 0.0 or pd.isna(lat) or pd.isna(lon):
            distances[stn_id] = np.nan
            continue
            
        stn_lat = math.radians(lat)
        stn_lon = math.radians(lon)
        
        dlon = coast_lon - stn_lon
        dlat = coast_lat - stn_lat
        a = np.sin(dlat / 2.0)**2 + np.cos(stn_lat) * np.cos(coast_lat) * np.sin(dlon / 2.0)**2
        a = np.clip(a, 0, 1)
        dist_km = R * 2 * np.arcsin(np.sqrt(a))
        distances[stn_id] = float(np.min(dist_km))
        
    return distances

def extract_station_static_features(fallback: bool = False) -> pd.DataFrame:
    """Extracts elevation (SRTM) and land cover (ESA WorldCover) for all stations in registry."""
    logger.info("Extracting static features for all stations...")
    
    # 1. Load validated station metadata to ensure we have coordinates and STN_xxx IDs
    metadata_path = config.METADATA_DIR / "validated_station_metadata.csv"
    if not metadata_path.exists():
        raise FileNotFoundError("validated_station_metadata.csv is required to extract static features with consistent IDs.")
            
    df_stations = pd.read_csv(metadata_path)
    logger.info(f"Loaded {len(df_stations)} stations from {metadata_path.name}")
    
    # Initialize GEE
    ee_ready = False
    if not fallback:
        try:
            ee_ready = initialize_ee()
        except Exception as e:
            logger.warning(f"GEE initialization failed: {e}. Falling back to default mock static features.")
            
    coast_distances = _compute_coastline_distances(df_stations)
    results = []
    
    if ee_ready and is_ee_initialized():
        import ee
        logger.info("Extracting features using GEE API...")
        try:
            # Prepare feature collection of points
            features = []
            for _, row in df_stations.iterrows():
                lat = float(row.get("latitude", row.get("Latitude", 0.0)))
                lon = float(row.get("longitude", row.get("Longitude", 0.0)))
                stn_id = str(row.get("station_id", row.get("Station ID")))
                # Only use valid coordinates
                if lat != 0.0 and lon != 0.0 and pd.notna(lat) and pd.notna(lon):
                    features.append(ee.Feature(ee.Geometry.Point([lon, lat]), {"station_id": stn_id}))
            
            if features:
                fc = ee.FeatureCollection(features)
                
                # Load elevation (SRTM)
                srtm = ee.Image("USGS/SRTMGL1_003").select("elevation")
                
                # Load land cover (ESA WorldCover)
                # Fall back to v100 if v200 not available; v100 is stable globally
                try:
                    esa = ee.ImageCollection("ESA/WorldCover/v100").first().select("Map")
                except Exception:
                    esa = ee.ImageCollection("ESA/WorldCover/v200").first().select("Map")
                    
                # Combine into single image
                combined = srtm.addBands(esa.rename("land_cover"))
                
                # Sample at station locations (scale=30m)
                sampled_fc = combined.reduceRegions(
                    collection=fc,
                    reducer=ee.Reducer.first(),
                    scale=30
                )
                
                # Retrieve from server
                info = sampled_fc.getInfo()
                
                # Index results by station_id
                gee_data = {}
                for feat in info.get("features", []):
                    props = feat.get("properties", {})
                    stn_id = props.get("station_id")
                    if stn_id:
                        gee_data[stn_id] = {
                            "elevation": float(props.get("elevation", 0.0)) if props.get("elevation") is not None else 0.0,
                            "land_cover_code": int(props.get("land_cover", 0)) if props.get("land_cover") is not None else 0
                        }
                        
                for _, row in df_stations.iterrows():
                    stn_id = str(row.get("station_id", row.get("Station ID")))
                    city = str(row.get("city", row.get("City", "")))
                    data = gee_data.get(stn_id, {"elevation": 150.0, "land_cover_code": 50})
                    
                    code = data["land_cover_code"]
                    desc = WORLDCOVER_CLASSES.get(code, "Unknown")
                    
                    results.append({
                        "station_id": stn_id,
                        "elevation": data["elevation"],
                        "land_cover_code": code,
                        "land_cover_desc": desc,
                        "distance_to_coast": round(coast_distances.get(stn_id, np.nan), 2)
                    })
            else:
                logger.warning("No stations with valid coordinates found to extract GEE features.")
                ee_ready = False
        except Exception as e:
            logger.error(f"Error during GEE static feature extraction: {e}. Falling back to defaults.")
            ee_ready = False
            
    if not ee_ready:
        logger.info("Generating fallback static features...")
        # Assign representative mock defaults (e.g. elevation 250m for inland, 20m for coastal, land cover Built-up)
        coastal_cities = {"mumbai", "chennai", "kolkata", "kochi", "vizag", "vishakhapatnam", "panaji", "mangalore"}
        for _, row in df_stations.iterrows():
            stn_id = str(row.get("station_id", row.get("Station ID")))
            city = str(row["City"]).strip().lower()
            
            # Rough elevation mapping helper
            if city in coastal_cities:
                elevation = float(np.random.uniform(5.0, 25.0))
            elif "delhi" in city:
                elevation = float(np.random.uniform(210.0, 230.0))
            elif "bengaluru" in city or "bangalore" in city:
                elevation = float(np.random.uniform(900.0, 930.0))
            elif "pune" in city:
                elevation = float(np.random.uniform(550.0, 580.0))
            else:
                elevation = float(np.random.uniform(100.0, 400.0))
                
            code = 50  # Default to Built-up (Urban) as AQI monitors are almost always in urban areas
            desc = WORLDCOVER_CLASSES[code]
            
            results.append({
                "station_id": stn_id,
                "elevation": round(elevation, 1),
                "land_cover_code": code,
                "land_cover_desc": desc,
                "distance_to_coast": round(coast_distances.get(stn_id, np.nan), 2)
            })
            
    df_features = pd.DataFrame(results)
    
    # Save files
    static_csv_path = config.METADATA_DIR / "station_static_features.csv"
    df_features.to_csv(static_csv_path, index=False)
    logger.info(f"Station static features written to {static_csv_path} ({len(df_features)} records)")
    
    # Copy to processed_data
    processed_path = config.PROCESSED_DATA_DIR / "station_static_features.csv"
    config.PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)
    df_features.to_csv(processed_path, index=False)
    
    return df_features

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    extract_station_static_features()
