"""
Unit tests for the Google Earth Engine data pipeline package.
Mocks the 'ee' module to ensure tests are completely offline-capable.
"""

import sys
from unittest.mock import MagicMock

# Create a mock 'ee' module and insert it into sys.modules
mock_ee = MagicMock()
mock_ee.ImageCollection = MagicMock(return_value=MagicMock())
mock_ee.Geometry = MagicMock()
mock_ee.Geometry.Rectangle = MagicMock(return_value="mock_rectangle_geometry")
mock_ee.Geometry.Point = MagicMock(return_value="mock_point_geometry")
mock_ee.Geometry.Polygon = MagicMock(return_value="mock_polygon_geometry")
mock_ee.Feature = MagicMock(return_value="mock_feature")
mock_ee.FeatureCollection = MagicMock(return_value="mock_feature_collection")

sys.modules['ee'] = mock_ee

# Now we can safely import our modules, and they will use the mocked 'ee'
from data_collection_pipeline.earth_engine import (
    initialize_ee,
    is_ee_initialized,
    DatasetCatalog,
    AnalysisGrid,
    BaseGEELoader,
    TROPOMILoader,
    MODISAODLoader,
    ERA5Loader,
    VIIRSFireLoader,
    bbox_to_ee_geometry,
    geojson_to_ee_geometry
)
from data_collection_pipeline.earth_engine.config import INDIA_BBOX


def test_dataset_catalog():
    """Verify standard metadata is present in the DatasetCatalog."""
    aliases = DatasetCatalog.list_aliases()
    assert "TROPOMI_HCHO" in aliases
    assert "MODIS_MAIAC_AOD" in aliases
    assert "ERA5_LAND_HOURLY" in aliases
    assert "VIIRS_ACTIVE_FIRE" in aliases
    
    meta = DatasetCatalog.get("TROPOMI_HCHO")
    assert meta.collection_id == "COPERNICUS/S5P/OFFL/L3_HCHO"
    assert "HCHO_tropospheric_column_amount" in meta.bands
    assert meta.resolution_meters == 5500.0


def test_analysis_grid_coordinate_math():
    """Verify coordinate math of the 5 km grid generator."""
    bbox = [70.0, 20.0, 70.2, 20.2]
    grid = AnalysisGrid(bbox=bbox, resolution_km=5.0)
    
    assert 0.044 < grid.lat_step < 0.046
    
    centroids = grid.generate_python_grid_coords()
    assert len(centroids) > 0
    for lon, lat in centroids:
        assert 70.0 <= lon <= 70.2
        assert 20.0 <= lat <= 20.2


def test_analysis_grid_gee_export():
    """Verify grid converts correctly to GEE feature collections."""
    import data_collection_pipeline.earth_engine.initializer as init_mod
    init_mod._EE_INITIALIZED = True
    
    grid = AnalysisGrid(bbox=[70.0, 20.0, 70.2, 20.2])
    fc = grid.to_gee_feature_collection()
    
    assert fc == "mock_feature_collection"
    mock_ee.FeatureCollection.assert_called()


def test_base_gee_loader_filtering():
    """Verify BaseGEELoader correctly maps catalog keys and applies filters."""
    import data_collection_pipeline.earth_engine.initializer as init_mod
    init_mod._EE_INITIALIZED = True
    
    loader = BaseGEELoader(
        alias="TROPOMI_HCHO",
        region_geom="mock_geometry",
        start_date="2026-01-01",
        end_date="2026-01-15"
    )
    
    assert loader.collection_id == "COPERNICUS/S5P/OFFL/L3_HCHO"
    assert loader.resolution_meters == 5500.0
    
    mock_col = MagicMock()
    mock_ee.ImageCollection.return_value = mock_col
    
    mock_filtered_date = MagicMock()
    mock_col.filterDate.return_value = mock_filtered_date
    mock_filtered_bounds = MagicMock()
    mock_filtered_date.filterBounds.return_value = mock_filtered_bounds
    mock_selected_bands = MagicMock()
    mock_filtered_bounds.select.return_value = mock_selected_bands
    
    res = loader.get_collection()
    
    mock_ee.ImageCollection.assert_called_with("COPERNICUS/S5P/OFFL/L3_HCHO")
    mock_col.filterDate.assert_called_with("2026-01-01", "2026-01-15")
    mock_filtered_date.filterBounds.assert_called_with("mock_geometry")
    mock_filtered_bounds.select.assert_called_with(["HCHO_tropospheric_column_amount", "HCHO_tropospheric_column_amount_uncertainty"])
    assert res == mock_selected_bands


def test_tropomi_loader_qa_masking():
    """Verify TROPOMI loader maps qa masks correctly."""
    import data_collection_pipeline.earth_engine.initializer as init_mod
    init_mod._EE_INITIALIZED = True
    
    loader = TROPOMILoader(
        alias="TROPOMI_NO2",
        region_geom="mock_geometry",
        start_date="2026-01-01",
        end_date="2026-01-15",
        qa_threshold=0.75
    )
    
    mock_col = MagicMock()
    mock_ee.ImageCollection.return_value = mock_col
    mock_filtered_date = MagicMock()
    mock_col.filterDate.return_value = mock_filtered_date
    mock_filtered_bounds = MagicMock()
    mock_filtered_date.filterBounds.return_value = mock_filtered_bounds
    
    # Mock the map call chain
    mock_mapped = MagicMock()
    mock_filtered_bounds.map.return_value = mock_mapped
    mock_selected_bands = MagicMock()
    mock_mapped.select.return_value = mock_selected_bands
    
    # Run loader
    col = loader.get_collection()
    
    mock_filtered_bounds.map.assert_called()
    mock_mapped.select.assert_called_with(["NO2_column_number_density", "tropospheric_NO2_column_number_density"])
    assert col == mock_selected_bands


def test_modis_loader_qa_masking():
    """Verify MODIS loader sets up bitwise masks."""
    import data_collection_pipeline.earth_engine.initializer as init_mod
    init_mod._EE_INITIALIZED = True
    
    loader = MODISAODLoader(
        region_geom="mock_geometry",
        start_date="2026-01-01",
        end_date="2026-01-15",
        best_quality_only=True
    )
    
    mock_col = MagicMock()
    mock_ee.ImageCollection.return_value = mock_col
    mock_filtered_date = MagicMock()
    mock_col.filterDate.return_value = mock_filtered_date
    mock_filtered_bounds = MagicMock()
    mock_filtered_date.filterBounds.return_value = mock_filtered_bounds
    
    # Mock map call chain
    mock_mapped = MagicMock()
    mock_filtered_bounds.map.return_value = mock_mapped
    mock_selected_bands = MagicMock()
    mock_mapped.select.return_value = mock_selected_bands
    
    col = loader.get_collection()
    
    mock_filtered_bounds.map.assert_called()
    mock_mapped.select.assert_called_with(["Optical_Depth_047", "Optical_Depth_055", "AOD_QA"])
    assert col == mock_selected_bands


def test_era5_loader():
    """Verify ERA5 Land hourly loader interface compiles."""
    import data_collection_pipeline.earth_engine.initializer as init_mod
    init_mod._EE_INITIALIZED = True
    
    loader = ERA5Loader(
        region_geom="mock_geometry",
        start_date="2026-01-01",
        end_date="2026-01-15",
        aggregate_to_daily=False
    )
    
    mock_col = MagicMock()
    mock_ee.ImageCollection.return_value = mock_col
    mock_filtered_date = MagicMock()
    mock_col.filterDate.return_value = mock_filtered_date
    mock_filtered_bounds = MagicMock()
    mock_filtered_date.filterBounds.return_value = mock_filtered_bounds
    mock_selected_bands = MagicMock()
    mock_filtered_bounds.select.return_value = mock_selected_bands
    
    col = loader.get_collection()
    mock_filtered_bounds.select.assert_called_with(["temperature_2m", "u_component_of_wind_10m", "v_component_of_wind_10m", "total_precipitation_hourly"])
    assert col == mock_selected_bands


def test_viirs_fire_loader():
    """Verify VIIRS active fire loader compiles and sets confidence filtering."""
    import data_collection_pipeline.earth_engine.initializer as init_mod
    init_mod._EE_INITIALIZED = True
    
    loader = VIIRSFireLoader(
        region_geom="mock_geometry",
        start_date="2026-01-01",
        end_date="2026-01-15",
        confidence_filter="high"
    )
    
    mock_col = MagicMock()
    mock_ee.ImageCollection.return_value = mock_col
    mock_filtered_date = MagicMock()
    mock_col.filterDate.return_value = mock_filtered_date
    mock_filtered_bounds = MagicMock()
    mock_filtered_date.filterBounds.return_value = mock_filtered_bounds
    
    # Mock map call chain
    mock_mapped = MagicMock()
    mock_filtered_bounds.map.return_value = mock_mapped
    mock_selected_bands = MagicMock()
    mock_mapped.select.return_value = mock_selected_bands
    
    col = loader.get_collection()
    
    mock_filtered_bounds.map.assert_called()
    mock_mapped.select.assert_called_with(["T21", "confidence", "fire"])
    assert col == mock_selected_bands


def test_utils_geometries():
    """Verify GeoJSON and bbox to geometry translations."""
    import data_collection_pipeline.earth_engine.initializer as init_mod
    init_mod._EE_INITIALIZED = True
    
    geom_box = bbox_to_ee_geometry(INDIA_BBOX)
    assert geom_box == "mock_rectangle_geometry"
    
    geojson = {
        "type": "Feature",
        "geometry": {
            "type": "Polygon",
            "coordinates": [[[70.0, 20.0], [72.0, 20.0], [72.0, 22.0], [70.0, 22.0], [70.0, 20.0]]]
        }
    }
    geom_geojson = geojson_to_ee_geometry(geojson)
    assert geom_geojson == "mock_polygon_geometry"
