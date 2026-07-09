"""
Unit tests for the Feature Engineering Framework.
"""

import pytest
import pandas as pd
import numpy as np
from data_collection_pipeline.feature_engineering import (
    FEATURE_SCHEMA,
    FeatureGroupManager,
    FeatureValidator,
    FeatureSelector
)


def test_feature_metadata_validation():
    """Verify FeatureMetadata validation bounds logic."""
    temp_meta = FEATURE_SCHEMA["Temperature"]
    assert temp_meta.validate_value(298.5) is True
    assert temp_meta.validate_value(150.0) is False  # below min (200K)
    assert temp_meta.validate_value(350.0) is False  # above max (330K)
    assert temp_meta.validate_value("invalid_temp") is False
    assert temp_meta.validate_value(None) is True    # missing values allowed at schema value level


def test_feature_group_manager():
    """Verify group mapping and queries."""
    groups = FeatureGroupManager.list_groups()
    assert "SATELLITE" in groups
    assert "METEOROLOGY" in groups
    assert "GEOGRAPHY" in groups
    
    satellite_features = FeatureGroupManager.get_features_in_group("satellite")
    assert "AOD" in satellite_features
    assert "HCHO" in satellite_features
    
    assert FeatureGroupManager.get_group_for_feature("Wind Speed") == "METEOROLOGY"
    assert FeatureGroupManager.get_group_for_feature("Weekend Flag") == "TEMPORAL"
    assert FeatureGroupManager.get_group_for_feature("Nonexistent") is None


def test_feature_validator():
    """Verify FeatureValidator handles range, completeness, and types checks."""
    validator = FeatureValidator()
    
    # Empty DataFrame check
    assert validator.validate_dataframe(pd.DataFrame())["status"] == "PASSED"
    
    # Valid dataset
    df_valid = pd.DataFrame({
        "Temperature": [290.0, 300.0, 310.0],
        "Relative Humidity": [45.0, 60.0, 75.0],
        "Weekend Flag": [False, True, False]
    })
    report_valid = validator.validate_dataframe(df_valid)
    assert report_valid["status"] == "PASSED"
    assert len(report_valid["missing_columns"]) > 0  # lists other unregistered columns in schema
    assert len(report_valid["range_violations"]) == 0
    
    # Dataset with out of bound range violations
    df_invalid_range = pd.DataFrame({
        "Temperature": [290.0, 100.0, 310.0],  # 100.0 K is out of range
        "Relative Humidity": [45.0, 60.0, 150.0]  # 150% is out of range
    })
    report_invalid = validator.validate_dataframe(df_invalid_range)
    assert report_invalid["range_violations"]["Temperature"] == 1
    assert report_invalid["range_violations"]["Relative Humidity"] == 1
    
    # Dataset with type mismatches
    df_type_mismatch = pd.DataFrame({
        "Temperature": ["hot", "cold", 300.0]
    })
    report_type = validator.validate_dataframe(df_type_mismatch)
    assert report_type["status"] == "FAILED"
    assert "Temperature" in report_type["type_mismatches"]


def test_feature_selector_select_by_group():
    """Verify selecting features by registered schema groups."""
    df = pd.DataFrame({
        "AOD": [0.5, 0.6],
        "Temperature": [295.0, 298.0],
        "Weekend Flag": [False, True],
        "Station ID": ["STN_1", "STN_2"],
        "PM2.5": [30.0, 45.0]
    })
    
    # Select only METEOROLOGY and TEMPORAL groups
    selected = FeatureSelector.select_by_group(
        df,
        groups=["meteorology", "temporal"],
        keep_metadata=True,
        keep_targets=True
    )
    
    assert "Temperature" in selected.columns
    assert "Weekend Flag" in selected.columns
    assert "Station ID" in selected.columns  # preserved
    assert "PM2.5" in selected.columns  # preserved
    assert "AOD" not in selected.columns  # dropped since it's satellite


def test_feature_selector_variance():
    """Verify low/zero-variance column pruning."""
    df = pd.DataFrame({
        "VariableFeature": [1.0, 2.0, 3.0, 4.0],
        "ConstantFeature": [5.0, 5.0, 5.0, 5.0],
        "PM2.5": [10.0, 12.0, 14.0, 16.0]
    })
    
    # Filter with threshold 0.0, exclude targets
    filtered, dropped = FeatureSelector.filter_by_variance(df, threshold=0.0, exclude_columns=["PM2.5"])
    assert "ConstantFeature" in dropped
    assert "ConstantFeature" not in filtered.columns
    assert "VariableFeature" in filtered.columns
    assert "PM2.5" in filtered.columns


def test_feature_selector_correlation():
    """Verify multicollinear column pruning."""
    x = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
    df = pd.DataFrame({
        "FeatureA": x,
        "FeatureB": x * 2.0 + 0.001,  # nearly 1.0 correlation with FeatureA
        "FeatureC": [0.5, 0.1, 0.9, 0.2, 0.4],  # unrelated
        "Target": x * 1.5 + np.random.normal(0, 0.1, 5)
    })
    
    # Run filter with threshold 0.95, targeting target column 'Target'
    filtered, dropped = FeatureSelector.filter_by_correlation(
        df,
        target_column="Target",
        correlation_threshold=0.95
    )
    
    assert len(dropped) == 1
    # Either FeatureA or FeatureB should be dropped
    assert ("FeatureA" in dropped) or ("FeatureB" in dropped)
    assert "FeatureC" in filtered.columns
    assert "Target" in filtered.columns
