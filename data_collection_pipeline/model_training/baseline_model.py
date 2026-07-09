"""
Baseline Model Training Module.

Refactored to integrate with FeatureGroupManager, FeatureValidator,
and the shared preprocessing pipeline.
"""

import logging
import json
from pathlib import Path
from typing import Tuple, List, Dict, Any, Union

import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline

from data_collection_pipeline.feature_engineering import (
    FeatureGroupManager,
    FeatureValidator,
    preprocess_target,
    build_preprocessing_pipeline
)

logger = logging.getLogger(__name__)


def load_training_data(file_path: Union[str, Path]) -> pd.DataFrame:
    """Loads the training dataset."""
    logger.info(f"Loading training data from {file_path}")
    return pd.read_csv(file_path)


def prepare_training_features(
    df: pd.DataFrame, 
    target_col: str
) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """
    Selects features dynamically using FeatureGroupManager and matches
    them with the target variable, cleaning rows with missing targets.
    
    Args:
        df: Input DataFrame.
        target_col: Name of the target column.
        
    Returns:
        Tuple of:
          - X features DataFrame (raw columns, to be processed by pipeline)
          - y target Series
          - list of feature column names
    """
    logger.info("Selecting features using FeatureGroupManager...")
    
    # Feature columns must come exclusively from FeatureGroupManager groups
    feature_groups = ["satellite", "meteorology", "geography", "temporal"]
    feature_cols = []
    
    for grp in feature_groups:
        feature_cols.extend(FeatureGroupManager.get_features_in_group(grp))
        
    # Intersect with columns actually present in the dataframe
    actual_features = [col for col in feature_cols if col in df.columns]
    
    if not actual_features:
        raise ValueError("No schema-registered features found in the input DataFrame columns.")
        
    # Drop rows where the target is missing
    df_clean = df.dropna(subset=[target_col]).copy()
    y = df_clean[target_col]
    X = df_clean[actual_features]
    
    logger.info(f"Selected {len(actual_features)} features for training. Rows: {len(X)}")
    return X, y, actual_features


def train_baseline_model(
    X: pd.DataFrame, 
    y: pd.Series, 
    feature_cols: List[str]
) -> Pipeline:
    """
    Constructs a training pipeline incorporating ColumnTransformers and trains
    a RandomForestRegressor.
    
    Args:
        X: Raw features DataFrame.
        y: Target series.
        feature_cols: List of features to process.
        
    Returns:
        sklearn.pipeline.Pipeline: Fully fitted pipeline.
    """
    logger.info("Configuring preprocessing pipeline...")
    prep_pipeline = build_preprocessing_pipeline(feature_cols)
    
    # Combine preprocessor and model inside a unified pipeline
    model_pipeline = Pipeline(steps=[
        ("preprocessor", prep_pipeline.named_steps["preprocessor"]),
        ("regressor", RandomForestRegressor(random_state=42))
    ])
    
    logger.info("Fitting baseline RandomForestRegressor pipeline...")
    model_pipeline.fit(X, y)
    logger.info("Baseline training completed successfully.")
    return model_pipeline


def save_trained_model(
    model_pipeline: Pipeline, 
    summary: Dict[str, Any],
    output_dir: Union[str, Path],
    validation_report: Optional[Dict[str, Any]] = None
) -> None:
    """Saves the trained pipeline, summary metadata, and optional validation reports."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # Save the full pipeline (preprocessors + model)
    model_path = out_path / "baseline_model.joblib"
    joblib.dump(model_pipeline, model_path)
    logger.info(f"Saved trained pipeline to {model_path}")
    
    # Save summary metadata
    summary_path = out_path / "training_summary.json"
    
    # Extract feature list from ColumnTransformer
    preprocessor = model_pipeline.named_steps["preprocessor"]
    features_in = []
    for _, _, cols in preprocessor.transformers_:
        features_in.extend(cols)
    summary["feature_columns"] = features_in
    
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4)
    logger.info(f"Saved training summary to {summary_path}")
    
    # Save validation reports
    if validation_report:
        val_path = out_path / "data_validation_report.json"
        with open(val_path, "w", encoding="utf-8") as f:
            json.dump(validation_report, f, indent=4)
        logger.info(f"Saved dataset validation report to {val_path}")


def run_training_pipeline(
    data_path: Union[str, Path],
    output_dir: Union[str, Path]
) -> Pipeline:
    """
    Orchestrates the entire training flow: loading, validating,
    preprocessing, fitting, and saving.
    
    Args:
        data_path: Path to dataset CSV.
        output_dir: Path to output directory.
        
    Returns:
        Pipeline: Trained pipeline model.
    """
    # 1. Load data
    df = load_training_data(data_path)
    
    # 2. Run Quality Validation before preprocessing
    validator = FeatureValidator()
    report = validator.validate_dataframe(df)
    
    if report["status"] == "FAILED":
        msg = f"Critical validation failures in dataset: {report['type_mismatches']}"
        logger.error(msg)
        raise ValueError(msg)
        
    # 3. Resolve target (using calculator reconstruction if needed)
    y, target_col = preprocess_target(df)
    # Add reconstructed target back for feature splitting alignment
    df[target_col] = y
    
    # 4. Select features and align
    X, y, feature_cols = prepare_training_features(df, target_col)
    
    # 5. Train
    model_pipeline = train_baseline_model(X, y, feature_cols)
    
    # 6. Save
    summary = {
        "target_column": target_col,
        "sample_count": len(X),
        "validation_status": report["status"]
    }
    save_trained_model(model_pipeline, summary, output_dir, validation_report=report)
    
    return model_pipeline
