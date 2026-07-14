import json
import tempfile
from pathlib import Path

import pandas as pd
import numpy as np
import pytest
import joblib

from data_collection_pipeline.model_training.lightgbm_model import (
    verify_training_dataset_integrity,
    partition_dataset,
    prepare_training_features,
    train_lightgbm_model,
    calculate_metrics,
    get_feature_importances,
    save_trained_model,
    run_training_pipeline
)
from data_collection_pipeline import config


@pytest.fixture
def synthetic_dataset():
    """Generates a synthetic DataFrame matching the schema expectations."""
    np.random.seed(42)
    n_samples = 100
    
    # Generate dates sorted sequentially for temporal partitioning
    dates = pd.date_range(start="2026-01-01", periods=n_samples, freq="D").strftime("%Y-%m-%d")
    
    data = {
        "Date": dates,
        "Station ID": ["ST001"] * n_samples,
        "AOD": np.random.uniform(0.1, 1.5, n_samples),
        "HCHO": np.random.uniform(1e15, 5e15, n_samples),
        "Temperature": np.random.uniform(280.0, 310.0, n_samples),
        "Wind Speed": np.random.uniform(0.5, 12.0, n_samples),
        "Wind Direction": np.random.uniform(0.0, 360.0, n_samples),
        "Latitude": [28.6] * n_samples,
        "Longitude": [77.2] * n_samples,
        "Day of Week": np.random.randint(0, 7, n_samples),
        "Month": np.random.randint(1, 13, n_samples),
        "Season": ["Monsoon"] * n_samples,
        "Weekend Flag": np.random.choice([0, 1], n_samples),
        "AQI": np.random.uniform(20.0, 450.0, n_samples)
    }
    
    return pd.DataFrame(data)


def test_verify_training_dataset_integrity(synthetic_dataset):
    # Standard clean check
    report = verify_training_dataset_integrity(synthetic_dataset, "AQI")
    assert report["status"] == "PASS"
    assert report["total_rows"] == 100
    assert report["duplicate_rows"] == 0
    
    # Check duplicate row detection
    df_dup = pd.concat([synthetic_dataset, synthetic_dataset.iloc[:5]], ignore_index=True)
    report_dup = verify_training_dataset_integrity(df_dup, "AQI")
    assert report_dup["duplicate_rows"] == 5
    
    # Check infinite values detection
    df_inf = synthetic_dataset.copy()
    df_inf.loc[10, "AOD"] = np.inf
    report_inf = verify_training_dataset_integrity(df_inf, "AQI")
    assert report_inf["status"] == "FAIL"
    assert "AOD" in report_inf["infinite_values"]
    
    # Check target absence
    report_missing_target = verify_training_dataset_integrity(synthetic_dataset, "PM2.5")
    assert report_missing_target["status"] == "FAIL"
    assert report_missing_target["target_column_present"] is False


def test_partition_dataset(synthetic_dataset):
    # Temporal splitting check
    train, val, test = partition_dataset(synthetic_dataset, 0.70, 0.15, 42)
    assert len(train) == 70
    assert len(val) == 15
    assert len(test) == 15
    
    # Preserves sort order
    assert pd.to_datetime(train["Date"]).max() <= pd.to_datetime(val["Date"]).min()
    assert pd.to_datetime(val["Date"]).max() <= pd.to_datetime(test["Date"]).min()
    
    # Random partition check (by removing date column)
    df_random = synthetic_dataset.drop(columns=["Date"])
    train_r, val_r, test_r = partition_dataset(df_random, 0.70, 0.15, 42)
    assert len(train_r) == 70
    assert len(val_r) == 15
    assert len(test_r) == 15


def test_prepare_training_features(synthetic_dataset):
    X, y, feature_cols = prepare_training_features(synthetic_dataset, "AQI")
    assert "AQI" not in X.columns
    assert "AOD" in X.columns
    assert "Temperature" in X.columns
    assert len(y) == 100
    
    # Handle all-null columns
    df_null = synthetic_dataset.copy()
    df_null["NO2 Column"] = np.nan
    X_null, y_null, feature_cols_null = prepare_training_features(df_null, "AQI")
    assert "NO2 Column" not in X_null.columns
    assert "NO2 Column" not in feature_cols_null


def test_train_lightgbm_model(synthetic_dataset):
    train, val, test = partition_dataset(synthetic_dataset, 0.70, 0.15, 42)
    X_train, y_train, feature_cols = prepare_training_features(train, "AQI")
    X_val, y_val, _ = prepare_training_features(val, "AQI", reference_cols=feature_cols)
    X_test, y_test, _ = prepare_training_features(test, "AQI", reference_cols=feature_cols)
    
    model = train_lightgbm_model(X_train, y_train, X_val, y_val, feature_cols)
    from sklearn.pipeline import Pipeline
    assert isinstance(model, Pipeline)
    assert "preprocessor" in model.named_steps
    assert "regressor" in model.named_steps
    
    # Predict and evaluate
    y_pred = model.predict(X_test)
    assert len(y_pred) == 15
    
    metrics = calculate_metrics(y_test, y_pred)
    assert "R2" in metrics
    assert "RMSE" in metrics
    assert "MAE" in metrics
    assert "MBE" in metrics
    
    # Feature importance check
    importances = get_feature_importances(model)
    assert isinstance(importances, dict)
    assert len(importances) > 0


def test_serialization(synthetic_dataset):
    train, val, test = partition_dataset(synthetic_dataset, 0.70, 0.15, 42)
    X_train, y_train, feature_cols = prepare_training_features(train, "AQI")
    X_val, y_val, _ = prepare_training_features(val, "AQI", reference_cols=feature_cols)
    X_test, y_test, _ = prepare_training_features(test, "AQI", reference_cols=feature_cols)
    
    model = train_lightgbm_model(X_train, y_train, X_val, y_val, feature_cols)
    y_pred = model.predict(X_test)
    metrics = calculate_metrics(y_test, y_pred)
    importances = get_feature_importances(model)
    val_report = verify_training_dataset_integrity(synthetic_dataset, "AQI")
    
    summary = {"features_count": len(feature_cols)}
    lgbm_config = getattr(config, "LIGHTGBM_PARAMS", {})
    
    with tempfile.TemporaryDirectory() as tmp_dir:
        save_trained_model(
            model,
            summary,
            metrics,
            importances,
            lgbm_config,
            val_report,
            tmp_dir
        )
        
        # Verify files exist
        tmp_path = Path(tmp_dir)
        assert (tmp_path / "lightgbm_model.joblib").exists()
        assert (tmp_path / "lightgbm_evaluation_metrics.json").exists()
        assert (tmp_path / "lightgbm_training_summary.json").exists()
        assert (tmp_path / "lightgbm_feature_importances.json").exists()
        assert (tmp_path / "lightgbm_config.json").exists()
        assert (tmp_path / "lightgbm_data_validation_report.json").exists()
        
        # Load and verify prediction
        loaded_model = joblib.load(tmp_path / "lightgbm_model.joblib")
        y_pred_loaded = loaded_model.predict(X_test)
        np.testing.assert_allclose(y_pred, y_pred_loaded)


def test_run_training_pipeline(synthetic_dataset):
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        csv_file = tmp_path / "train_data.csv"
        synthetic_dataset.to_csv(csv_file, index=False)
        
        model = run_training_pipeline(csv_file, tmp_path)
        from sklearn.pipeline import Pipeline
        assert isinstance(model, Pipeline)
        
        assert (tmp_path / "lightgbm_model.joblib").exists()
        assert (tmp_path / "lightgbm_feature_validation_report.md").exists()
