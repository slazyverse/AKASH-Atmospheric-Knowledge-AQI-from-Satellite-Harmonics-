"""Consolidates all historical observation and predictor databases into a unified dataset."""

import logging
from pathlib import Path
import pandas as pd
import numpy as np

from data_collection_pipeline import config

logger = logging.getLogger("data_collection_pipeline.dataset_merger")

def collocate_era5_to_stations(
    era5_df: pd.DataFrame,
    stations_df: pd.DataFrame
) -> pd.DataFrame:
    """Collocates gridded ERA5 hourly parameters to stations using spatial nearest-neighbor."""
    logger.info("Performing spatial nearest-neighbor matching for ERA5 grid cells...")
    
    # Get unique ERA5 grid coordinates
    grid_coords = era5_df[["latitude", "longitude"]].drop_duplicates().values
    if len(grid_coords) == 0:
        logger.warning("No ERA5 coordinates available to collocate.")
        return pd.DataFrame()
        
    # Map station ID -> closest (lat, lon) grid cell
    station_grid_mapping = {}
    for _, stn in stations_df.iterrows():
        stn_id = stn["Station ID"]
        s_lat = float(stn["Latitude"])
        s_lon = float(stn["Longitude"])
        
        # Euclidean distance in degree space (sufficient for nearest-neighbor on fine grid)
        dists = np.sqrt((grid_coords[:, 0] - s_lat)**2 + (grid_coords[:, 1] - s_lon)**2)
        closest_idx = np.argmin(dists)
        closest_coords = grid_coords[closest_idx]
        station_grid_mapping[stn_id] = (closest_coords[0], closest_coords[1])
        
    logger.info(f"Mapped {len(station_grid_mapping)} stations to their closest ERA5 grid cells.")
    
    # Build collocated time-series
    collocated_records = []
    # Index ERA5 by coordinate for fast lookup
    era5_grouped = era5_df.groupby(["latitude", "longitude"])
    
    for stn_id, (g_lat, g_lon) in station_grid_mapping.items():
        try:
            grp = era5_grouped.get_group((g_lat, g_lon))
            # Copy and add station_id key
            stn_met = grp.copy()
            stn_met["station_id"] = stn_id
            collocated_records.append(stn_met)
        except KeyError:
            continue
            
    if not collocated_records:
        return pd.DataFrame()
        
    collocated_era5 = pd.concat(collocated_records, ignore_index=True)
    # Clean up grid coordinate columns to prevent conflicts with station coordinates
    collocated_era5 = collocated_era5.rename(columns={
        "latitude": "era5_latitude",
        "longitude": "era5_longitude"
    })
    return collocated_era5

def run_dataset_merger() -> bool:
    """Merges all ingestion databases into a single v2 analytical dataset."""
    logger.info("=========================================")
    logger.info("Starting Dataset Consolidation and Merger (v2)")
    logger.info("=========================================")
    
    # 1. Load Station Metadata
    stn_path = config.METADATA_DIR / "validated_station_metadata.csv"
    if not stn_path.exists():
        stn_path = config.METADATA_DIR / "station_metadata.csv"
    if not stn_path.exists():
        logger.error("Station metadata file not found. Ingestion cannot proceed.")
        return False
    stations_df = pd.read_csv(stn_path)
    
    # 2. Load Station Static Features
    static_path = config.METADATA_DIR / "station_static_features.csv"
    if not static_path.exists():
        logger.error("Station static features file not found. Ingestion cannot proceed.")
        return False
    static_df = pd.read_csv(static_path)

    # 2.5 Load Station ID Bridge (Only for logging, not applied anymore since all use STN_xxx)
    bridge_path = config.METADATA_DIR / "station_id_bridge.csv"
    if bridge_path.exists():
        bridge_df = pd.read_csv(bridge_path)
        logger.info(f"Loaded station ID bridge (unused for ID mapping to maintain STN_xxx format).")
    else:
        logger.warning("station_id_bridge.csv not found.")

    # 3. Load Ground Observations (Parquet Warehouse)
    ground_dir = config.PROCESSED_DATA_DIR / "historical" / "ground"
    if not ground_dir.exists():
        logger.error(f"Ground observations directory not found at {ground_dir}.")
        return False
        
    try:
        logger.info(f"Loading ground observations from Parquet: {ground_dir} ...")
        # Load all parquet partitions
        ground_df = pd.read_parquet(ground_dir)
        logger.info(f"Loaded {len(ground_df)} long-format ground measurements.")
    except Exception as e:
        logger.error(f"Failed to read ground Parquet warehouse: {e}")
        return False
        
    # Pivot Ground long observations to wide format (one column per pollutant)
    logger.info("Pivoting long ground observations to wide format...")
    # Clean timestamps first
    ground_df["timestamp_utc_str"] = pd.to_datetime(ground_df["timestamp_utc"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    ground_df["timestamp_local_str"] = pd.to_datetime(ground_df["timestamp_local"]).dt.strftime("%Y-%m-%d %H:%M:%S")
    
    ground_wide = ground_df.pivot_table(
        index=["station_id", "timestamp_utc_str", "timestamp_local_str"],
        columns="pollutant",
        values="value",
        aggfunc="first"
    ).reset_index()
    
    # Ensure all columns exist
    for pol in ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "AQI"]:
        if pol not in ground_wide.columns:
            ground_wide[pol] = np.nan
            
    # Add a date column (YYYY-MM-DD) for matching daily satellite overpass data
    ground_wide["date"] = pd.to_datetime(ground_wide["timestamp_utc_str"]).dt.strftime("%Y-%m-%d")

    # Add an hour-aligned timestamp for ERA5 merge (e.g., floor HH:30 to HH:00)
    # Scientific rationale: CPCB observation at HH:30 correlates closest to ERA5 gridded output at HH:00
    ground_wide["timestamp_era5_str"] = pd.to_datetime(ground_wide["timestamp_utc_str"]).dt.floor('h').dt.strftime("%Y-%m-%d %H:%M:%S")

    # 4. Load ERA5 Meteorology
    era5_path = config.PROCESSED_DATA_DIR / "era5_processed.parquet"
    if not era5_path.exists():
        logger.error(f"ERA5 processed Parquet database not found at {era5_path}.")
        return False
    era5_df = pd.read_parquet(era5_path)
    
    # Collocate ERA5 to stations
    collocated_era5 = collocate_era5_to_stations(era5_df, stations_df)
    
    # Join Ground and ERA5
    # Both use hourly timestamp keys
    logger.info("Merging ground observations with hourly meteorological parameters...")
    merged = pd.merge(
        ground_wide,
        collocated_era5,
        left_on=["station_id", "timestamp_era5_str"],
        right_on=["station_id", "timestamp"],
        how="inner"
    )
    logger.info(f"Merged Ground + ERA5 dataset size: {len(merged)} rows.")
    if merged.empty:
        logger.warning("Empty intersection between Ground observations and ERA5 timestamps. Falling back to outer join.")
        merged = pd.merge(
            ground_wide,
            collocated_era5,
            left_on=["station_id", "timestamp_era5_str"],
            right_on=["station_id", "timestamp"],
            how="left"
        )

    # 5. Load Sentinel-5P Columns
    sentinel_path = config.PROCESSED_DATA_DIR / "sentinel_processed.parquet"
    if sentinel_path.exists():
        logger.info("Loading Sentinel-5P columns...")
        sentinel_df = pd.read_parquet(sentinel_path)
        # Extract date from timestamp for overpass join
        sentinel_df["date"] = pd.to_datetime(sentinel_df["timestamp"]).dt.strftime("%Y-%m-%d")
        sentinel_df = sentinel_df.drop(columns=["timestamp", "year", "month"], errors="ignore")
        
        # Merge Sentinel (on station_id and date)
        merged = pd.merge(
            merged,
            sentinel_df,
            on=["station_id", "date"],
            how="left"
        )
        logger.info("Merged Sentinel-5P columns.")
    else:
        logger.warning("Sentinel-5P processed database not found. Skipping join.")

    # 6. Load MODIS AOD
    modis_path = config.PROCESSED_DATA_DIR / "modis_processed.parquet"
    if modis_path.exists():
        logger.info("Loading MODIS AOD parameters...")
        modis_df = pd.read_parquet(modis_path)
        modis_df["date"] = pd.to_datetime(modis_df["timestamp"]).dt.strftime("%Y-%m-%d")
        modis_df = modis_df.drop(columns=["timestamp", "year", "month"], errors="ignore")
        
        # Merge MODIS
        merged = pd.merge(
            merged,
            modis_df,
            on=["station_id", "date"],
            how="left"
        )
        logger.info("Merged MODIS AOD features.")
    else:
        logger.warning("MODIS processed database not found. Skipping join.")

    # 7. Merge Station Metadata
    # Select metadata fields
    stn_meta_slice = stations_df[["Station ID", "Station Name", "City", "State", "Latitude", "Longitude", "Source"]].copy()
    stn_meta_slice = stn_meta_slice.rename(columns={
        "Station ID": "station_id",
        "Station Name": "station_name",
        "City": "city",
        "State": "state",
        "Latitude": "station_latitude",
        "Longitude": "station_longitude",
        "Source": "network_source"
    })
    
    merged = pd.merge(
        merged,
        stn_meta_slice,
        on="station_id",
        how="left"
    )
    
    # 8. Merge Static Features
    merged = pd.merge(
        merged,
        static_df,
        on="station_id",
        how="left"
    )

    # 9. Design and Attach Future Spatial Extension Columns (Task 7 placeholders)
    # The columns are added as float placeholders, estimated based on city properties for demonstration.
    logger.info("Attaching designed extension columns (population density, road density, nighttime lights)...")
    
    # Estimated values based on city classification
    urban_pop_map = {
        "delhi": 12000.0, "mumbai": 21000.0, "kolkata": 15000.0, 
        "chennai": 17000.0, "bengaluru": 11000.0, "hyderabad": 10000.0,
        "pune": 8000.0, "lucknow": 5000.0, "ahmedabad": 7000.0
    }
    
    coastal_cities = {"mumbai", "chennai", "kolkata"}
    
    pop_densities = []
    road_densities = []
    nighttime_lights = []
    dist_to_industrials = []
    
    for _, row in merged.iterrows():
        city_lower = str(row.get("city", "")).lower().strip()
        
        # Pop density estimate (people / km2)
        pop_densities.append(urban_pop_map.get(city_lower, 1500.0))
        # Road density (km / km2)
        road_densities.append(12.5 if city_lower in urban_pop_map else 2.5)
        # Nighttime lights (relative unit)
        nighttime_lights.append(55.0 if city_lower in urban_pop_map else 12.0)
        # Distance to industrial area (km)
        dist_to_industrials.append(8.0 if city_lower in urban_pop_map else 35.0)
        
    merged["ext_population_density"] = pop_densities
    merged["ext_road_density"] = road_densities
    merged["ext_nighttime_lights"] = nighttime_lights
    merged["ext_distance_to_industrial"] = dist_to_industrials

    # Final Clean-up and Export
    # Drop intermediate columns
    if "timestamp" in merged.columns:
        merged = merged.drop(columns=["timestamp"])
    if "date" in merged.columns:
        merged = merged.drop(columns=["date"])
        
    # Re-order columns for readability
    cols_order = [
        "station_id", "station_name", "city", "state", "station_latitude", "station_longitude", "network_source",
        "timestamp_utc_str", "timestamp_local_str",
        "PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "AQI",
        "Temperature", "Relative Humidity", "Boundary Layer Height", "Surface Pressure", "Wind Speed", "Wind Direction",
        "HCHO", "NO2 Column", "CO Column",
        "AOD_047", "AOD_055", "AOD",
        "elevation", "land_cover_code", "land_cover_desc", "distance_to_coast",
        "ext_population_density", "ext_road_density", "ext_nighttime_lights", "ext_distance_to_industrial"
    ]
    
    # Keep only columns that exist
    final_cols = [c for c in cols_order if c in merged.columns]
    merged_final = merged[final_cols].copy()
    
    # Save Parquet
    parquet_out = config.PROCESSED_DATA_DIR / "analysis_ready_dataset_v2.parquet"
    merged_final.to_parquet(parquet_out, compression="snappy", index=False)
    logger.info(f"Analytical Dataset v2 saved as Parquet: {parquet_out}")
    
    # Save CSV
    csv_out = config.PROCESSED_DATA_DIR / "analysis_ready_dataset_v2.csv"
    merged_final.to_csv(csv_out, index=False)
    logger.info(f"Analytical Dataset v2 saved as CSV: {csv_out}")
    
    logger.info(f"Ingestion merger completed successfully! Output rows: {len(merged_final)}")
    return True

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_dataset_merger()
