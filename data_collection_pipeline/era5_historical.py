"""Manages historical multi-year downloads, caching, and processing of ERA5 data."""

import logging
import os
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
import pandas as pd
import numpy as np

from data_collection_pipeline import config, utils
from data_collection_pipeline.dlq import handle_ingestion_failure
from data_collection_pipeline.era5_processor import VARIABLE_RENAME_MAP, OUTPUT_COLUMNS

logger = logging.getLogger("data_collection_pipeline.era5_historical")

def generate_mock_era5_netcdf(output_path: Path, year: int, month: int) -> None:
    """Generates a synthetic NetCDF file covering India to allow mock execution without credentials."""
    logger.info(f"Generating mock ERA5 NetCDF file for {year}-{month:02d} at {output_path.name}")
    try:
        import xarray as xr
    except ImportError:
        logger.error("xarray not installed. Cannot generate mock ERA5 NetCDF.")
        return

    # Spatial coordinates (coarse grid to save space)
    lats = np.arange(6.0, 39.0, 4.0)
    lons = np.arange(68.0, 99.0, 4.0)
    
    # Time coordinates
    start_date = pd.Timestamp(f"{year}-{month:02d}-01 00:00:00")
    end_date = start_date + pd.offsets.MonthEnd(1) + pd.Timedelta(hours=23)
    times = pd.date_range(start=start_date, end=end_date, freq="h")
    
    n_time = len(times)
    n_lat = len(lats)
    n_lon = len(lons)
    
    # Generate dummy variable grids
    t2m_vals = 273.15 + 25.0 + 5.0 * np.sin(np.arange(n_time) * (2 * np.pi / 24))[:, np.newaxis, np.newaxis] + \
               np.random.normal(0, 1, (n_time, n_lat, n_lon))
    u10_vals = np.random.normal(1.0, 0.5, (n_time, n_lat, n_lon))
    v10_vals = np.random.normal(-0.5, 0.5, (n_time, n_lat, n_lon))
    blh_vals = 800.0 + 400.0 * np.sin(np.arange(n_time) * (2 * np.pi / 24))[:, np.newaxis, np.newaxis] + np.zeros((n_time, n_lat, n_lon))
    sp_vals = 101325.0 + np.random.normal(0, 200, (n_time, n_lat, n_lon))
    r_vals = 50.0 + 20.0 * np.cos(np.arange(n_time) * (2 * np.pi / 24))[:, np.newaxis, np.newaxis] + np.zeros((n_time, n_lat, n_lon))
    
    # Build dataset
    ds = xr.Dataset(
        data_vars={
            "t2m": (["time", "latitude", "longitude"], t2m_vals.astype(np.float32)),
            "u10": (["time", "latitude", "longitude"], u10_vals.astype(np.float32)),
            "v10": (["time", "latitude", "longitude"], v10_vals.astype(np.float32)),
            "blh": (["time", "latitude", "longitude"], blh_vals.astype(np.float32)),
            "sp":  (["time", "latitude", "longitude"], sp_vals.astype(np.float32)),
            "r":   (["time", "latitude", "longitude"], r_vals.astype(np.float32)),
        },
        coords={
            "time": times,
            "latitude": lats.astype(np.float32),
            "longitude": lons.astype(np.float32),
        }
    )
    
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ds.to_netcdf(output_path)
    logger.info(f"Mock NetCDF successfully generated ({output_path.stat().st_size / 1024 / 1024:.2f} MB)")

def download_historical_era5_month(
    year: int,
    month: int,
    output_path: Path,
    variables: List[str],
    max_retries: int = 3,
    backoff_factor: float = 2.0,
    force_fallback: bool = False
) -> bool:
    """Retrieves one month of ERA5 data, utilizing caching, retries, and failure handling."""
    if output_path.exists() and output_path.stat().st_size > 1024:
        logger.info(f"Found cached ERA5 file for {year}-{month:02d} at {output_path.name}. Skipping download.")
        return True

    # Check for credentials
    has_credentials = False
    cdsapirc = Path.home() / ".cdsapirc"
    if cdsapirc.exists() or os.environ.get("CDSAPI_KEY"):
        has_credentials = True

    if force_fallback or not has_credentials:
        handle_ingestion_failure(
            source="ERA5",
            operation="download_historical_month",
            message=f"CDS API credentials missing or force_fallback enabled for {year}-{month:02d}.",
            payload={"year": year, "month": month},
            logger_instance=logger,
        )

    # Setup request payload
    days_in_month = pd.Period(f"{year}-{month:02d}").days_in_month
    day_list = [f"{d:02d}" for d in range(1, days_in_month + 1)]
    
    request_dict = {
        "product_type": "reanalysis",
        "format": "netcdf",
        "variable": variables,
        "year": str(year),
        "month": f"{month:02d}",
        "day": day_list,
        "time": [f"{h:02d}:00" for h in range(24)],
        "area": config.ERA5_BOUNDING_BOX
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    last_exception: Optional[Exception] = None
    # Retry loop with exponential backoff
    for attempt in range(1, max_retries + 1):
        try:
            import cdsapi
            logger.info(f"Attempting live ERA5 download for {year}-{month:02d} (Attempt {attempt}/{max_retries})...")
            client = cdsapi.Client()
            client.retrieve("reanalysis-era5-single-levels", request_dict, str(output_path))
            logger.info(f"Successfully downloaded ERA5 {year}-{month:02d}")
            return True
        except Exception as e:
            last_exception = e
            logger.warning(f"Download attempt {attempt} failed: {e}")
            if attempt < max_retries:
                wait_sec = backoff_factor ** attempt
                logger.info(f"Retrying in {wait_sec} seconds...")
                time.sleep(wait_sec)
                
    handle_ingestion_failure(
        source="ERA5",
        operation="download_historical_month",
        message=f"All download attempts for {year}-{month:02d} failed.",
        original_exception=last_exception,
        payload={"year": year, "month": month},
        logger_instance=logger,
    )

def run_historical_era5_pipeline(
    start_year: int = 2023,
    end_year: int = 2025,
    variables: Optional[List[str]] = None,
    force_fallback: bool = False
) -> pd.DataFrame:
    """Executes multi-year downloads, processes NetCDF files, and writes Parquet/CSV databases."""
    logger.info(f"Running historical ERA5 Ingestion pipeline ({start_year} - {end_year})")
    
    variables = variables or config.ERA5_DEFAULT_VARIABLES.copy()
    if "surface_pressure" not in variables:
        variables.append("surface_pressure")
    if "2m_dewpoint_temperature" not in variables:
        variables.append("2m_dewpoint_temperature")

    era5_cache_dir = config.RAW_DATA_DIR / "historical" / "era5"
    era5_cache_dir.mkdir(parents=True, exist_ok=True)
    
    months_processed = []
    
    # Loop over years and months
    for year in range(start_year, end_year + 1):
        for month in range(1, 13):
            # Limit year=2026 or future months if running past current date
            if year == 2026 and month > 7:
                continue
                
            output_nc = era5_cache_dir / f"era5_{year}_{month:02d}.nc"
            success = download_historical_era5_month(year, month, output_nc, variables, force_fallback=force_fallback)
            if success:
                months_processed.append(output_nc)

    if not months_processed:
        handle_ingestion_failure(
            source="ERA5",
            operation="run_historical_era5_pipeline",
            message=f"No historical ERA5 NetCDF files could be fetched for period {start_year}-{end_year}.",
            payload={"start_year": start_year, "end_year": end_year},
            logger_instance=logger,
        )

    # Process files
    try:
        import xarray as xr
    except ImportError as e:
        handle_ingestion_failure(
            source="ERA5",
            operation="run_historical_era5_pipeline",
            message="xarray not installed. Cannot process NetCDF files.",
            original_exception=e,
            logger_instance=logger,
        )

    logger.info(f"Processing and consolidating {len(months_processed)} NetCDF files...")
    
    processed_dfs = []
    for nc_path in months_processed:
        try:
            logger.info(f"Reading {nc_path.name}...")
            ds = xr.open_dataset(nc_path)
            
            # Rename variables using the processor mapping
            rename_map = {
                var: VARIABLE_RENAME_MAP[var]
                for var in ds.data_vars
                if var in VARIABLE_RENAME_MAP
            }
            if rename_map:
                ds = ds.rename(rename_map)
                
            df = ds.to_dataframe().reset_index()
            ds.close()
            
            # Normalise dimension names
            dim_rename = {}
            for col in df.columns:
                col_lower = col.lower()
                if col_lower in {"time", "valid_time"}:
                    dim_rename[col] = "timestamp"
                elif col_lower in {"lat", "latitude"}:
                    dim_rename[col] = "latitude"
                elif col_lower in {"lon", "lng", "longitude"}:
                    dim_rename[col] = "longitude"
            if dim_rename:
                df = df.rename(columns=dim_rename)
                
            # Derive wind components
            u = df.get("u_wind_component", np.nan)
            v = df.get("v_wind_component", np.nan)
            df["Wind Speed"] = np.sqrt(u**2 + v**2)
            # Mathematical meteorological direction
            df["Wind Direction"] = (np.degrees(np.arctan2(u, v)) + 180.0) % 360.0
            
            # Format timestamp column as string for consistency
            df["timestamp"] = pd.to_datetime(df["timestamp"]).dt.strftime("%Y-%m-%d %H:%M:%S")
            
            # Keep only output columns
            available_cols = [c for c in OUTPUT_COLUMNS if c in df.columns]
            df_filtered = df[available_cols].copy()
            
            # Extract year/month partitions
            df_filtered["year"] = pd.to_datetime(df_filtered["timestamp"]).dt.year
            df_filtered["month"] = pd.to_datetime(df_filtered["timestamp"]).dt.month
            
            processed_dfs.append(df_filtered)
        except Exception as e:
            logger.error(f"Failed to process NetCDF {nc_path.name}: {e}")
            
    if not processed_dfs:
        handle_ingestion_failure(
            source="ERA5",
            operation="run_historical_era5_pipeline",
            message="No NetCDF files successfully parsed into DataFrames.",
            logger_instance=logger,
        )
        
    combined_df = pd.concat(processed_dfs, ignore_index=True)
    
    # Save partitioned Parquet warehouse
    parquet_path = config.PROCESSED_DATA_DIR / "era5_processed.parquet"
    combined_df.to_parquet(
        parquet_path,
        partition_cols=["year", "month"],
        compression="snappy",
        index=False
    )
    logger.info(f"Parquet database generated at {parquet_path}")
    
    # Save wide CSV for backward compatibility
    csv_path = config.PROCESSED_DATA_DIR / "era5_meteorology.csv"
    # To keep size manageable in CSV, save a coarse version of the coordinates
    coarse_df = combined_df.drop(columns=["year", "month"])
    coarse_df.to_csv(csv_path, index=False)
    logger.info(f"Compatibility CSV written to {csv_path} ({len(coarse_df)} rows)")
    
    return combined_df

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_historical_era5_pipeline()
