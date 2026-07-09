"""
Unit tests for the new Preprocessing module and ML pipeline integrations.
"""

import tempfile
from pathlib import Path
import pytest
import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline

from data_collection_pipeline.feature_engineering.preprocessing import (
    preprocess_target,
    build_preprocessing_pipeline
)
from data_collection_pipeline.model_training.baseline_model import (
    run_training_pipeline
)
from data_collection_pipeline.model_validation.cross_validator import (
    run_cross_validation
)


def test_preprocess_target_exists():
    """Verify preprocess_target returns existing AQI directly."""
    df = pd.DataFrame({
        "AQI": [50.0, 100.0, 150.0],
        "PM2.5": [12.0, 35.0, 55.0]
    })
    y, name = preprocess_target(df)
    assert name == "AQI"
    assert list(y) == [50.0, 100.0, 150.0]


def test_preprocess_target_reconstruction():
    """Verify target AQI is reconstructed when missing but concentrations are present."""
    df = pd.DataFrame({
        "PM2.5": [15.0, 45.0],
        "PM10": [25.0, 75.0]
    })
    y, name = preprocess_target(df)
    assert name == "AQI"
    assert len(y) == 2
    assert y.isna().sum() == 0
    assert y.iloc[0] > 0


def test_preprocess_target_missing_raises_error():
    """Verify ValueError is raised if target cannot be found or reconstructed."""
    df = pd.DataFrame({
        "Temperature": [295.0, 298.0],
        "Relative Humidity": [50.0, 60.0]
    })
    with pytest.raises(ValueError, match="Target column 'AQI' is missing/empty"):
        preprocess_target(df)


def test_build_preprocessing_pipeline():
    """Verify that build_preprocessing_pipeline constructs working transformers."""
    feature_cols = ["Temperature", "AOD", "Season"]
    pipeline = build_preprocessing_pipeline(feature_cols)
    
    assert isinstance(pipeline, Pipeline)
    assert "preprocessor" in pipeline.named_steps
    
    df = pd.DataFrame({
        "Temperature": [290.0, 300.0, np.nan],
        "AOD": [0.3, np.nan, 0.8],
        "Season": ["Winter", "Monsoon", "Winter"]
    })
    
    transformed = pipeline.fit_transform(df)
    assert transformed.shape == (3, 4)
    assert np.isnan(transformed).sum() == 0


def test_baseline_and_cv_pipeline_flow():
    """Verify complete training and CV execution flow with mock data."""
    # Create valid mock DataFrame passing FeatureValidator schema bounds
    df = pd.DataFrame({
        "AQI": [45.0, 95.0, 150.0, 250.0, 350.0],
        "Temperature": [295.0, 301.0, 290.0, 310.0, 305.0],
        "AOD": [0.3, 0.5, 0.2, 1.2, 0.8],
        "Latitude": [28.5, 28.6, 28.4, 28.7, 28.5],
        "Longitude": [77.2, 77.3, 77.1, 77.4, 77.2],
        "Season": ["Winter", "Pre-Monsoon", "Monsoon", "Post-Monsoon", "Winter"]
    })
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        csv_file = tmp_path / "mock_train.csv"
        df.to_csv(csv_file, index=False)
        
        # 1. Run baseline model training
        model_pipeline = run_training_pipeline(csv_file, tmp_path)
        assert isinstance(model_pipeline, Pipeline)
        assert (tmp_path / "baseline_model.joblib").exists()
        assert (tmp_path / "training_summary.json").exists()
        assert (tmp_path / "data_validation_report.json").exists()
        
        # 2. Run cross validation pipeline
        run_cross_validation(csv_file, tmp_path)
        assert (tmp_path / "cross_validation_results.csv").exists()
        assert (tmp_path / "cross_validation_summary.json").exists()
