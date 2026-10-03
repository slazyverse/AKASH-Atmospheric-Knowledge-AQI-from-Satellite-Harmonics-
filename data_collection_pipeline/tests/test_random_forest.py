"""
Unit and integration tests for the baseline Random Forest model pipeline.
Verifies splitting, metric computations, feature importances, and serialization.
"""

import tempfile
import json
from pathlib import Path
import pytest
import pandas as pd
import numpy as np
import joblib
from sklearn.pipeline import Pipeline

from data_collection_pipeline.model_training.baseline_model import (
    split_dataset,
    calculate_metrics,
    get_feature_importances,
    run_training_pipeline
)
from data_collection_pipeline import config


def test_split_dataset_temporal():
    """Verify temporal split sorts by date column."""
    df = pd.DataFrame({
        "Date": ["2026-01-05", "2026-01-01", "2026-01-03", "2026-01-02", "2026-01-04"],
        "Value": [50.0, 10.0, 30.0, 20.0, 40.0]
    })
    
    # 60% split ratio -> 3 train rows, 2 test rows
    train, test = split_dataset(df, train_ratio=0.6)
    
    # Ensure they are sorted and split chronologically
    assert list(train["Value"]) == [10.0, 20.0, 30.0]
    assert list(test["Value"]) == [40.0, 50.0]


def test_split_dataset_random():
    """Verify random split falls back if no date column is present."""
    df = pd.DataFrame({
        "Value": [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
    })
    train, test = split_dataset(df, train_ratio=0.8, random_state=42)
    assert len(train) == 8
    assert len(test) == 2


def test_calculate_metrics():
    """Verify standard metric calculations and MBE direction."""
    y_true = pd.Series([10.0, 20.0, 30.0])
    y_pred = np.array([12.0, 18.0, 32.0])  # Diff: +2, -2, +2
    
    metrics = calculate_metrics(y_true, y_pred)
    
    assert "R2" in metrics
    assert "RMSE" in metrics
    assert "MAE" in metrics
    assert "MBE" in metrics
    
    # MBE = ((12-10) + (18-20) + (32-30)) / 3 = (2 - 2 + 2) / 3 = 2/3 ~ 0.6667
    assert 0.66 < metrics["MBE"] < 0.67
    assert metrics["MAE"] == pytest.approx(2.0)


def test_random_forest_pipeline_e2e_serialization():
    """Verify end-to-end fitting, serialization, and deserialization."""
    # Create valid mock DataFrame passing FeatureValidator schema bounds
    df = pd.DataFrame({
        "AQI": [50.0, 100.0, 150.0, 200.0, 250.0, 300.0, 350.0, 400.0, 450.0, 500.0],
        "Temperature": [295.0, 301.0, 290.0, 310.0, 305.0, 298.0, 302.0, 293.0, 309.0, 304.0],
        "AOD": [0.3, 0.5, 0.2, 1.2, 0.8, 0.4, 0.6, 0.3, 1.1, 0.9],
        "Latitude": [28.5, 28.6, 28.4, 28.7, 28.5, 28.5, 28.6, 28.4, 28.7, 28.5],
        "Longitude": [77.2, 77.3, 77.1, 77.4, 77.2, 77.2, 77.3, 77.1, 77.4, 77.2],
        "Season": ["Winter", "Pre-Monsoon", "Monsoon", "Post-Monsoon", "Winter", "Winter", "Pre-Monsoon", "Monsoon", "Post-Monsoon", "Winter"]
    })
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        csv_file = tmp_path / "train_data.csv"
        df.to_csv(csv_file, index=False)
        
        # Run baseline ML training
        model_pipeline = run_training_pipeline(csv_file, tmp_path)
        
        # Verify output files exist
        assert (tmp_path / "baseline_model.joblib").exists()
        assert (tmp_path / "training_summary.json").exists()
        assert (tmp_path / "evaluation_metrics.json").exists()
        assert (tmp_path / "feature_importances.json").exists()
        
        # Verify deserialization
        loaded_pipeline = joblib.load(tmp_path / "baseline_model.joblib")
        assert isinstance(loaded_pipeline, Pipeline)
        
        # Make dummy prediction
        test_row = pd.DataFrame({
            "Temperature": [300.0],
            "AOD": [0.5],
            "Latitude": [28.5],
            "Longitude": [77.2],
            "Season": ["Winter"]
        })
        preds = loaded_pipeline.predict(test_row)
        assert len(preds) == 1
        assert preds[0] > 0
        
        # Verify feature importances are sorted
        with open(tmp_path / "feature_importances.json", "r") as f:
            importances = json.load(f)
            
        assert len(importances) > 0
        vals = list(importances.values())
        # Assert descending order
        assert all(vals[i] >= vals[i+1] for i in range(len(vals)-1))
