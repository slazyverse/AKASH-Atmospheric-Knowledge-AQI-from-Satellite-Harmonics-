import pytest
import os
import json
import numpy as np
import pandas as pd
from pathlib import Path
import shutil
import joblib

from data_collection_pipeline.config_loader import config_instance
from data_collection_pipeline.spatial_analysis import (
    india_grid_generator,
    interpolation,
    color_scheme,
    map_renderer,
    spatial_mapper,
    hotspot_detector,
    biomass_analysis
)
from data_collection_pipeline.inference.prediction_pipeline import run_prediction_pipeline
from data_collection_pipeline.model_evaluation import evaluation_runner, report_generator
from data_collection_pipeline.model_training.experiment_manager import ExperimentManager

@pytest.fixture
def mock_dataset(tmp_path) -> Tuple[Path, pd.DataFrame]:
    """Generates a dummy dataset for testing."""
    df = pd.DataFrame({
        "Station ID": ["ST1", "ST2", "ST3", "ST4", "ST5"],
        "Station Name": ["Station A", "Station B", "Station C", "Station D", "Station E"],
        "Latitude": [12.0, 13.0, 28.0, 29.0, 30.0],
        "Longitude": [77.0, 78.0, 77.0, 78.0, 79.0],
        "AQI": [50.0, 60.0, 150.0, 160.0, 170.0],
        "HCHO": [0.0001, 0.00012, 0.00045, 0.00048, 0.0005],
        "CO Column": [0.02, 0.022, 0.045, 0.048, 0.05]
    })
    csv_path = tmp_path / "dummy_dataset.csv"
    df.to_csv(csv_path, index=False)
    return csv_path, df

def test_config_loader():
    assert config_instance.get("grid") is not None
    assert config_instance.get("grid", "default_resolution") == 300
    assert config_instance.get("interpolation", "method") == "linear"

def test_india_grid_generator():
    grid_x, grid_y = india_grid_generator.generate_grid(resolution=10)
    assert grid_x.shape == (10, 10)
    assert grid_y.shape == (10, 10)
    assert grid_x.min() >= 68.0
    assert grid_x.max() <= 98.0
    assert grid_y.min() >= 8.0
    assert grid_y.max() <= 38.0

def test_interpolation():
    grid_x, grid_y = india_grid_generator.generate_grid(resolution=5)
    lons = np.array([77.0, 78.0, 77.0])
    lats = np.array([12.0, 13.0, 14.0])
    vals = np.array([10.0, 20.0, 30.0])
    
    grid_z = interpolation.interpolate_points_to_grid(lons, lats, vals, grid_x, grid_y)
    assert grid_z.shape == (5, 5)

def test_color_scheme():
    assert isinstance(color_scheme.get_aqi_colormap(), str)
    assert isinstance(color_scheme.get_hcho_colormap(), str)
    assert isinstance(color_scheme.get_scatter_edge_color(), str)

def test_map_renderer(tmp_path):
    grid_z = np.zeros((10, 10))
    out_path = tmp_path / "test_map.png"
    map_renderer.render_map(
        grid_z, 
        out_path, 
        title="Test Map", 
        colorbar_label="Test", 
        colormap="viridis"
    )
    assert out_path.exists()
    
    # Test GeoTIFF graceful skip
    tiff_path = tmp_path / "test_map.tif"
    success = map_renderer.export_geotiff(grid_z, tiff_path)
    # geotiff export will return bool (True or False depending on rasterio presence)
    assert isinstance(success, bool)

def test_spatial_mapper(tmp_path, mock_dataset):
    csv_path, df = mock_dataset
    res = spatial_mapper.run_spatial_mapping_pipeline(
        df,
        values_column="AQI",
        output_dir=tmp_path,
        file_prefix="test_aqi_map"
    )
    assert Path(res["normal_map_png"]).exists()
    assert Path(res["high_res_map_png"]).exists()

def test_hotspot_detector(tmp_path, mock_dataset):
    csv_path, df = mock_dataset
    res = hotspot_detector.run_hotspot_pipeline(
        df,
        output_dir=tmp_path,
        percentile=0.50, # low threshold for test points
        eps=5.0,
        min_samples=2
    )
    assert Path(res["cluster_summary_json"]).exists()
    assert Path(res["hcho_hotspots_png"]).exists()
    assert res["total_hotspots_count"] >= 2

def test_biomass_analysis(tmp_path, mock_dataset):
    csv_path, df = mock_dataset
    res = biomass_analysis.run_biomass_analysis(df, tmp_path)
    assert Path(res["correlation_report_json"]).exists()
    assert Path(res["correlation_plot_png"]).exists()
    assert -1.0 <= res["pearson_r"] <= 1.0

def test_prediction_pipeline(tmp_path, mock_dataset):
    # Create a dummy trained pipeline using joblib
    from sklearn.dummy import DummyRegressor
    from sklearn.pipeline import Pipeline
    from sklearn.compose import ColumnTransformer
    from sklearn.preprocessing import StandardScaler
    
    csv_path, df = mock_dataset
    
    # Simple Pipeline matching the feature registry columns
    preprocessor = ColumnTransformer(transformers=[
        ("num", StandardScaler(), ["Latitude", "Longitude"])
    ])
    pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("regressor", DummyRegressor(strategy="mean"))
    ])
    pipeline.fit(df[["Latitude", "Longitude"]], df["AQI"])
    
    model_path = tmp_path / "test_model.joblib"
    joblib.dump(pipeline, model_path)
    
    # Run prediction
    res_df, csv_out = run_prediction_pipeline(
        dataset_path=csv_path,
        model_path=model_path,
        output_dir=tmp_path,
        target_column="AQI"
    )
    
    assert Path(csv_out).exists()
    assert "Predicted_Target" in res_df.columns

def test_evaluation_runner(tmp_path):
    y_true = pd.Series([10.0, 20.0, 30.0, 40.0])
    y_pred = np.array([12.0, 18.0, 32.0, 38.0])
    
    metrics = evaluation_runner.run_evaluation_pipeline(
        y_true, 
        y_pred, 
        output_dir=tmp_path, 
        title_prefix="Test Eval"
    )
    assert "MAE" in metrics
    assert "RMSE" in metrics
    assert "MAPE" in metrics
    assert (tmp_path / "performance_summary.json").exists()

def test_experiment_manager(tmp_path):
    mgr = ExperimentManager(workspace_root=tmp_path)
    # Temporarily override config location to test pathing
    config_instance.config_data["paths"]["experiments_dir"] = "test_experiments"
    
    run_dir, run_id = mgr.create_experiment_run(model_name="test_rf")
    assert run_dir.exists()
    assert run_id.startswith("run_test_rf_")
    
    mgr.log_experiment_metadata(
        run_dir=run_dir,
        run_id=run_id,
        model_params={"n_estimators": 10},
        metrics={"R2": 0.5}
    )
    assert (run_dir / "experiment_metadata.json").exists()

def test_report_generator(tmp_path):
    perf = {"MAE": 2.0, "RMSE": 2.5, "R2": 0.9, "MBE": -0.1, "MAPE": 5.0}
    hotspot = {"hcho_90th_percentile_threshold": 0.90, "total_hotspot_stations": 10, "grouped_cluster_count": 2}
    biomass = {"overall_hcho_co_pearson_corr": 0.5, "hotspots_hcho_co_pearson_corr": 0.6}
    
    report_path = report_generator.compile_final_markdown_report(
        output_dir=tmp_path,
        performance_metrics=perf,
        hotspot_metrics=hotspot,
        biomass_metrics=biomass
    )
    assert report_path.exists()
    with open(report_path, "r") as f:
        content = f.read()
        assert "MAE" in content
        assert "HCHO Hotspot Detection Report" in content

from typing import Tuple
