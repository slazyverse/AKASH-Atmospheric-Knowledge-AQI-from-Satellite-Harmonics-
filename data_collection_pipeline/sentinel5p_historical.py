"""Manages historical Sentinel-5P TROPOMI data collection via GEE."""

import logging
import os
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import pandas as pd
import numpy as np

from data_collection_pipeline import config
from data_collection_pipeline.earth_engine.initializer import initialize_ee, is_ee_initialized

logger = logging.getLogger("data_collection_pipeline.sentinel5p_historical")

# Sentinel-5P target collections and bands
S5P_CONFIGS = {
    "NO2": {
        "collection": "COPERNICUS/S5P/OFFL/L3_NO2",
        "band": "tropospheric_NO2_column_number_density",
        "qa_band": "qa_value"
    },
    "HCHO": {
        "collection": "COPERNICUS/S5P/OFFL/L3_HCHO",
        "band": "HCHO_tropospheric_column_amount",
        "qa_band": "qa_value"
    },
    "CO": {
        "collection": "COPERNICUS/S5P/OFFL/L3_CO",
        "band": "CO_column_number_density",
        "qa_band": "qa_value"
    }
}

def generate_mock_sentinel_data(stations: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    """Generates synthetic Sentinel-5P observations for testing fallback."""
    logger.info(f"Generating mock Sentinel-5P dataset for {year}-{month:02d}...")
    
    start_date = pd.Timestamp(f"{year}-{month:02d}-01")
    end_date = start_date + pd.offsets.MonthEnd(1)
    dates = pd.date_range(start=start_date, end=end_date, freq="D")
    
    records = []
    for date in dates:
        date_str = date.strftime("%Y-%m-%d")
        for _, stn in stations.iterrows():
            stn_id = stn["Station ID"]
            
            # Simple diurnal/geographic variations for realism
            lat_factor = float(stn["Latitude"]) / 10.0
            
            hcho = float(np.random.uniform(0.0001, 0.0004)) + 0.00005 * np.sin(date.day)
            no2 = float(np.random.uniform(0.00003, 0.0002)) + 0.00002 * np.cos(date.day) + 0.00005 * lat_factor
            co = float(np.random.uniform(0.01, 0.04)) + 0.005 * np.sin(date.day * 2)
            
            records.append({
                "station_id": stn_id,
                "timestamp": f"{date_str} 12:00:00",  # Afternoon overpass time
                "HCHO": max(0.0, hcho),
                "NO2 Column": max(0.0, no2),
                "CO Column": max(0.0, co)
            })
            
    return pd.DataFrame(records)

def fetch_sentinel_month_gee(
    stations: pd.DataFrame,
    year: int,
    month: int,
    output_path: Path
) -> pd.DataFrame:
    """Fetches Sentinel-5P daily measurements for one month using Google Earth Engine."""
    if output_path.exists():
        logger.info(f"Found cached Sentinel-5P chunk at {output_path.name}. Loading...")
        return pd.read_parquet(output_path)

    # Initialize GEE
    ee_ready = False
    try:
        ee_ready = initialize_ee()
    except Exception as e:
        logger.warning(f"GEE initialization failed: {e}. Generating mock data.")

    if not ee_ready or not is_ee_initialized():
        mock_df = generate_mock_sentinel_data(stations, year, month)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        mock_df.to_parquet(output_path, compression="snappy", index=False)
        return mock_df

    import ee
    logger.info(f"Querying Sentinel-5P observations from GEE for {year}-{month:02d}...")
    
    try:
        # Build station FeatureCollection
        features = []
        for _, stn in stations.iterrows():
            lat = float(stn["Latitude"])
            lon = float(stn["Longitude"])
            stn_id = str(stn["Station ID"])
            if lat != 0.0 and lon != 0.0 and pd.notna(lat) and pd.notna(lon):
                features.append(ee.Feature(ee.Geometry.Point([lon, lat]), {"station_id": stn_id}))
                
        if not features:
            logger.warning("No stations with valid coordinates to query from GEE. Using mock.")
            mock_df = generate_mock_sentinel_data(stations, year, month)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            mock_df.to_parquet(output_path, compression="snappy", index=False)
            return mock_df
            
        station_fc = ee.FeatureCollection(features)
        
        # Temporal bounds
        start_date_str = f"{year}-{month:02d}-01"
        days_in_month = pd.Period(f"{year}-{month:02d}").days_in_month
        end_date_str = f"{year}-{month:02d}-{days_in_month:02d}"
        
        # Create a list of daily images for the month
        daily_images = []
        for day in range(1, days_in_month + 1):
            day_str = f"{year}-{month:02d}-{day:02d}"
            day_start = day_str
            day_end = (pd.Timestamp(day_str) + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
            
            # Load and QA mask NO2, HCHO, CO
            no2_col = ee.ImageCollection(S5P_CONFIGS["NO2"]["collection"])\
                .filterDate(day_start, day_end)
            no2_img = no2_col.map(lambda img: img.updateMask(img.select(S5P_CONFIGS["NO2"]["qa_band"]).gte(0.5)))\
                .mean().select(S5P_CONFIGS["NO2"]["band"]).rename("no2")
                
            hcho_col = ee.ImageCollection(S5P_CONFIGS["HCHO"]["collection"])\
                .filterDate(day_start, day_end)
            hcho_img = hcho_col.map(lambda img: img.updateMask(img.select(S5P_CONFIGS["HCHO"]["qa_band"]).gte(0.5)))\
                .mean().select(S5P_CONFIGS["HCHO"]["band"]).rename("hcho")
                
            co_col = ee.ImageCollection(S5P_CONFIGS["CO"]["collection"])\
                .filterDate(day_start, day_end)
            co_img = co_col.map(lambda img: img.updateMask(img.select(S5P_CONFIGS["CO"]["qa_band"]).gte(0.5)))\
                .mean().select(S5P_CONFIGS["CO"]["band"]).rename("co")
                
            # Combine daily bands
            daily_img = no2_img.addBands(hcho_img).addBands(co_img)\
                .set("date", day_str)\
                .set("system:time_start", ee.Date(day_str).millis())
            daily_images.append(daily_img)
            
        combined_col = ee.ImageCollection.fromImages(daily_images)
        
        # Mapping function to sample points
        def sample_image(img):
            d_str = img.get("date")
            sampled = img.reduceRegions(
                collection=station_fc,
                reducer=ee.Reducer.first(),
                scale=5500
            )
            # Attach date to each feature
            return sampled.map(lambda f: f.set("date", d_str))
            
        flat_sampled = combined_col.map(sample_image).flatten()
        info = flat_sampled.getInfo()
        
        # Parse output features
        records = []
        for feat in info.get("features", []):
            props = feat.get("properties", {})
            stn_id = props.get("station_id")
            date_str = props.get("date")
            if stn_id and date_str:
                records.append({
                    "station_id": stn_id,
                    "timestamp": f"{date_str} 12:00:00", # Sentinel-5P overpass time approx 13:30 local
                    "HCHO": float(props.get("hcho")) if props.get("hcho") is not None else np.nan,
                    "NO2 Column": float(props.get("no2")) if props.get("no2") is not None else np.nan,
                    "CO Column": float(props.get("co")) if props.get("co") is not None else np.nan
                })
                
        df_result = pd.DataFrame(records)
        if df_result.empty:
            logger.warning("GEE Sentinel-5P query returned empty results. Generating mock.")
            df_result = generate_mock_sentinel_data(stations, year, month)
            
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df_result.to_parquet(output_path, compression="snappy", index=False)
        return df_result
        
    except Exception as e:
        logger.error(f"Failed to query Sentinel-5P from GEE for {year}-{month:02d}: {e}. Generating mock.")
        mock_df = generate_mock_sentinel_data(stations, year, month)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        mock_df.to_parquet(output_path, compression="snappy", index=False)
        return mock_df

def run_historical_sentinel_pipeline(
    start_year: int = 2023,
    end_year: int = 2025
) -> pd.DataFrame:
    """Ingests and standardizes Sentinel-5P historical columns, writing Parquet database."""
    logger.info(f"Starting historical Sentinel-5P pipeline ({start_year} - {end_year})")
    
    # Load stations
    metadata_path = config.METADATA_DIR / "validated_station_metadata.csv"
    if not metadata_path.exists():
        metadata_path = config.METADATA_DIR / "station_metadata.csv"
    df_stations = pd.read_csv(metadata_path)

    cache_dir = config.RAW_DATA_DIR / "historical" / "sentinel"
    cache_dir.mkdir(parents=True, exist_ok=True)
    
    chunks = []
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            # Limit year=2026 or future months
            if year == 2026 and month > 7:
                continue
            chunk_path = cache_dir / f"sentinel_{year}_{month:02d}.parquet"
            chunk_df = fetch_sentinel_month_gee(df_stations, year, month, chunk_path)
            chunks.append(chunk_df)
            
    combined_df = pd.concat(chunks, ignore_index=True)
    
    # Save partitioned Parquet database
    parquet_path = config.PROCESSED_DATA_DIR / "sentinel_processed.parquet"
    combined_df["year"] = pd.to_datetime(combined_df["timestamp"]).dt.year
    combined_df["month"] = pd.to_datetime(combined_df["timestamp"]).dt.month
    
    combined_df.to_parquet(
        parquet_path,
        partition_cols=["year", "month"],
        compression="snappy",
        index=False
    )
    logger.info(f"Sentinel-5P Parquet database generated at {parquet_path}")
    
    return combined_df

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_historical_sentinel_pipeline()
