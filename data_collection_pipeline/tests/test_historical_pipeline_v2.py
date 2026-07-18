"""Unit tests for the V2 Historical Ingestion Pipeline."""

from __future__ import annotations

import os
from pathlib import Path
import tempfile
import numpy as np
import pandas as pd
import pytest

from data_collection_pipeline.metadata_builder import (
    standardize_name,
    haversine_distance,
    build_master_station_metadata
)
from data_collection_pipeline.static_features import extract_station_static_features
from data_collection_pipeline.era5_historical import generate_mock_era5_netcdf, run_historical_era5_pipeline
from data_collection_pipeline.sentinel5p_historical import generate_mock_sentinel_data
from data_collection_pipeline.modis_historical import generate_mock_modis_data
from data_collection_pipeline.dataset_merger import collocate_era5_to_stations


def test_standardize_name():
    """Verify suffix scrubbing and capitalization cleaning of station names."""
    assert standardize_name("Anand Vihar, Delhi - DPCC") == "anandvihardelhi"
    assert standardize_name("BTM Layout, Bengaluru - CPCB") == "btmlayoutbengaluru"
    assert standardize_name("Peenya, Bengaluru - KSPCB") == "peenyabengaluru"


def test_haversine_distance():
    """Verify spherical distance calculation on earth."""
    # Delhi to Mumbai distance approx 1150 km
    lat1, lon1 = 28.61, 77.20
    lat2, lon2 = 19.07, 72.87
    dist = haversine_distance(lat1, lon1, lat2, lon2)
    assert 1100000.0 < dist < 1200000.0


def test_static_features_fallback():
    """Verify extraction of static terrain features in fallback mode."""
    # Run in fallback mode
    df = extract_station_static_features(fallback=True)
    
    assert not df.empty
    assert "station_id" in df.columns
    assert "elevation" in df.columns
    assert "land_cover_code" in df.columns
    assert "land_cover_desc" in df.columns
    
    # Check that land cover values are within the valid set
    assert all(code in [10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100] for code in df["land_cover_code"])


def test_era5_mock_netcdf():
    """Verify mock NetCDF generation and processing pipelines."""
    try:
        import xarray as xr
    except ImportError:
        pytest.skip("xarray is not installed, skipping NetCDF generation test.")
        
    with tempfile.TemporaryDirectory() as tmp_dir:
        output_path = Path(tmp_dir) / "test_era5_mock.nc"
        generate_mock_era5_netcdf(output_path, 2025, 1)
        
        assert output_path.exists()
        assert output_path.stat().st_size > 1024
        
        # Test loading
        ds = xr.open_dataset(output_path)
        assert "t2m" in ds.data_vars
        assert "u10" in ds.data_vars
        assert "v10" in ds.data_vars
        assert "latitude" in ds.coords
        assert "longitude" in ds.coords
        ds.close()


def test_sentinel_and_modis_generators():
    """Verify that Sentinel-5P and MODIS synthetic data generators produce the expected format."""
    stations = pd.DataFrame([
        {"Station ID": "STN_001", "Latitude": 28.6, "Longitude": 77.2, "City": "Delhi"}
    ])
    
    s5p_df = generate_mock_sentinel_data(stations, 2025, 1)
    assert not s5p_df.empty
    assert "station_id" in s5p_df.columns
    assert "timestamp" in s5p_df.columns
    assert "HCHO" in s5p_df.columns
    assert "NO2 Column" in s5p_df.columns
    assert "CO Column" in s5p_df.columns
    
    modis_df = generate_mock_modis_data(stations, 2025, 1)
    assert not modis_df.empty
    assert "station_id" in modis_df.columns
    assert "timestamp" in modis_df.columns
    assert "AOD_047" in modis_df.columns
    assert "AOD_055" in modis_df.columns
    assert "AOD" in modis_df.columns


def test_spatial_collocation_era5():
    """Verify grid nearest-neighbor lookup matching logic."""
    era5_records = [
        {"latitude": 28.5, "longitude": 77.0, "timestamp": "2025-01-01 00:00:00", "Temperature": 290.0},
        {"latitude": 28.5, "longitude": 77.5, "timestamp": "2025-01-01 00:00:00", "Temperature": 291.0},
        {"latitude": 29.0, "longitude": 77.0, "timestamp": "2025-01-01 00:00:00", "Temperature": 292.0},
        {"latitude": 29.0, "longitude": 77.5, "timestamp": "2025-01-01 00:00:00", "Temperature": 293.0}
    ]
    era5_df = pd.DataFrame(era5_records)
    
    stations = pd.DataFrame([
        # Station is very close to 28.5, 77.0 grid cell
        {"Station ID": "STN_001", "Latitude": 28.52, "Longitude": 77.03}
    ])
    
    collocated = collocate_era5_to_stations(era5_df, stations)
    
    assert not collocated.empty
    assert len(collocated) == 1
    assert collocated.iloc[0]["station_id"] == "STN_001"
    # Nearest coordinate was 28.5, 77.0
    assert collocated.iloc[0]["era5_latitude"] == 28.5
    assert collocated.iloc[0]["era5_longitude"] == 77.0
    assert collocated.iloc[0]["Temperature"] == 290.0


def test_data_validation_v2():
    """Verify that ARDValidatorV2 successfully validates and writes output tables."""
    from data_collection_pipeline.data_validation_v2 import ARDValidatorV2
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        validator = ARDValidatorV2(
            ard_path="data_collection_pipeline/processed_data/analysis_ready_dataset_v2.parquet",
            metadata_path="data_collection_pipeline/metadata/station_metadata.csv",
            static_features_path="data_collection_pipeline/metadata/station_static_features.csv",
            ground_dir="data_collection_pipeline/processed_data/historical/ground",
            output_dir=tmp_path
        )
        
        summary = validator.run()
        
        assert summary is not None
        assert (tmp_path / "validation_summary.json").exists()
        assert (tmp_path / "validation_report_v2.md").exists()
        assert (tmp_path / "feature_statistics.csv").exists()
        assert (tmp_path / "missing_value_summary.csv").exists()
        assert (tmp_path / "station_statistics.csv").exists()
        assert (tmp_path / "correlation_matrix.csv").exists()
        assert (tmp_path / "outlier_summary.csv").exists()
        assert (tmp_path / "merge_statistics.csv").exists()

