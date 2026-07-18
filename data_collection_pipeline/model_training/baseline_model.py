"""
Baseline Model Training Module.

Implements training, evaluation, and serialization of the baseline
Random Forest model, consuming the unified preprocessing and schema validations.
"""

import logging
import json
from pathlib import Path
from typing import Tuple, List, Dict, Any, Union, Optional

import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from data_collection_pipeline.feature_engineering import (
    FeatureGroupManager,
    FeatureValidator,
    preprocess_target,
    build_preprocessing_pipeline
)
from data_collection_pipeline import config

logger = logging.getLogger(__name__)


def select_target_column(df: pd.DataFrame) -> str:
    """Selects the target column based on the configuration."""
    target = getattr(config, "REQUIRED_TARGET_COLUMN", "AQI")
    
    if target not in df.columns:
        logger.warning(f"Target column '{target}' not found. Falling back to 'PM2.5' if available.")
        target = "PM2.5" if "PM2.5" in df.columns else df.select_dtypes(include=['number']).columns[-1]
        
    logger.info(f"Selected target column: {target}")
    return target


def load_training_data(file_path: Union[str, Path]) -> pd.DataFrame:
    """Loads the training dataset from a CSV file."""
    logger.info(f"Loading training data from {file_path}")
    return pd.read_csv(file_path)


def split_dataset(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Splits the dataset into train and test sets.
    Performs a temporal split if 'Date' or 'timestamp' columns exist,
    otherwise falls back to a deterministic random split.
    
    Args:
        df: Input DataFrame.
        train_ratio: Fraction of rows to allocate for training.
        random_state: Random state seed.
        
    Returns:
        Tuple of (train_df, test_df).
    """
    # Look for date columns to sort for temporal hold-out split
    date_col = None
    for col in ["Date", "date", "timestamp", "datetime"]:
        if col in df.columns:
            date_col = col
            break
            
    if date_col:
        logger.info(f"Performing temporal split on sorted column '{date_col}'...")
        # Sort and split without shuffling to preserve time ordering
        df_sorted = df.sort_values(by=date_col).copy()
        split_idx = int(len(df_sorted) * train_ratio)
        train_df = df_sorted.iloc[:split_idx]
        test_df = df_sorted.iloc[split_idx:]
    else:
        logger.info("Performing random split...")
        train_df, test_df = train_test_split(
            df,
            train_size=train_ratio,
            random_state=random_state,
            shuffle=True
        )
        
    logger.info(f"Split results - Train rows: {len(train_df)}, Test rows: {len(test_df)}")
    return train_df, test_df


def prepare_training_features(
    df: pd.DataFrame, 
    target_col: str
) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """
    Selects features dynamically using FeatureGroupManager and aligns them
    with target values, dropping rows where the target is missing.
    
    Args:
        df: Input DataFrame.
        target_col: Target column name.
        
    Returns:
        Tuple of:
          - X features DataFrame
          - y target Series
          - list of actual feature column names
    """
    logger.info("Selecting features using FeatureGroupManager...")
    
    feature_groups = ["satellite", "meteorology", "geography", "temporal"]
    feature_cols = []
    
    for grp in feature_groups:
        feature_cols.extend(FeatureGroupManager.get_features_in_group(grp))
        
    actual_features = [col for col in feature_cols if col in df.columns]
    
    if not actual_features:
        raise ValueError("No schema-registered features found in the input DataFrame columns.")
        
    df_clean = df.dropna(subset=[target_col]).copy()
    y = df_clean[target_col]
    X = df_clean[actual_features]

    # Remove columns that are completely null
    total_features = len(X.columns)
    all_null_cols = [col for col in X.columns if X[col].isna().all()]

    if all_null_cols:
        logger.info(f"Removing all-null feature columns: {all_null_cols}")
        X = X.drop(columns=all_null_cols)

    warnings = []
    for col in X.columns:
        if X[col].isna().all():
            msg = f"Remaining column '{col}' is entirely NaN."
            logger.warning(msg)
            warnings.append(msg)

    # Median imputation for remaining numeric columns
    medians = X.median(numeric_only=True)
    X = X.fillna(medians)

    # Validation report
    report_path = config.BASE_DIR.parent / "baseline_feature_validation_report.md"

    report = f"""# Baseline Feature Validation Report

    ## Summary
    * Total Feature Count: {total_features}
    * Retained Feature Count: {len(X.columns)}
    * Removed Feature Count: {len(all_null_cols)}
    * Imputation Strategy: Column Median

    ## Removed Columns
    {chr(10).join(f"* {c}" for c in all_null_cols) if all_null_cols else "* None"}

    ## Warnings
    {chr(10).join(f"* {w}" for w in warnings) if warnings else "* None"}
    """

    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)

    logger.info(f"Generated baseline feature validation report at {report_path}")

    feature_cols = list(X.columns)

    logger.info(f"Prepared {len(feature_cols)} features for training.")

    return X, y, feature_cols


def train_baseline_model(
    X: pd.DataFrame, 
    y: pd.Series, 
    feature_cols: List[str]
) -> Pipeline:
    """
    Constructs a training pipeline incorporating ColumnTransformers and fits
    a RandomForestRegressor using central configuration parameters.
    
    Args:
        X: Training features.
        y: Training target.
        feature_cols: List of features to process.
        
    Returns:
        Pipeline: Fully fitted training pipeline.
    """
    logger.info("Configuring preprocessing pipeline...")
    prep_pipeline = build_preprocessing_pipeline(feature_cols)
    
    # Retrieve hyperparameters from central config
    rf_params = getattr(config, "RANDOM_FOREST_PARAMS", {})
    logger.info(f"Using RF parameters from config: {rf_params}")
    
    model_pipeline = Pipeline(steps=[
        ("preprocessor", prep_pipeline.named_steps["preprocessor"]),
        ("regressor", RandomForestRegressor(**rf_params))
    ])
    
    logger.info("Fitting baseline RandomForestRegressor pipeline...")
    model_pipeline.fit(X, y)
    logger.info("Baseline training completed successfully.")
    return model_pipeline


def calculate_metrics(y_true: pd.Series, y_pred: np.ndarray) -> Dict[str, float]:
    """
    Computes regression performance metrics including R2, RMSE, MAE, and MBE.
    
    Args:
        y_true: True target values.
        y_pred: Predicted values.
        
    Returns:
        Dict: Metric scores.
    """
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))
    mbe = float(np.mean(y_pred - y_true))  # Mean Bias Error: predicted - actual
    
    return {
        "R2": r2,
        "RMSE": rmse,
        "MAE": mae,
        "MBE": mbe
    }


def get_feature_importances(model_pipeline: Pipeline) -> Dict[str, float]:
    """
    Matches feature importances to their respective column names after OHE.
    
    Args:
        model_pipeline: Fitted Pipeline.
        
    Returns:
        Dict: Sorted feature importances.
    """
    preprocessor = model_pipeline.named_steps["preprocessor"]
    regressor = model_pipeline.named_steps["regressor"]
    
    # Retrieve transformed feature names
    try:
        feature_names = list(preprocessor.get_feature_names_out())
    except Exception:
        # Fallback for older scikit-learn versions
        feature_names = []
        for name, trans, cols in preprocessor.transformers_:
            if name == "remainder" and trans == "drop":
                continue
            if hasattr(trans, "get_feature_names_out"):
                feature_names.extend(trans.get_feature_names_out(cols))
            else:
                feature_names.extend(cols)
                
    importances = regressor.feature_importances_
    
    # Pair names and scores
    importances_dict = {}
    for name, imp in zip(feature_names, importances):
        # Format name for readability (remove pipeline prefixes like 'num__')
        clean_name = name.split("__")[-1] if "__" in name else name
        importances_dict[clean_name] = float(imp)
        
    # Sort descending
    return dict(sorted(importances_dict.items(), key=lambda x: x[1], reverse=True))


def save_trained_model(
    model_pipeline: Pipeline, 
    summary: Dict[str, Any],
    metrics: Dict[str, float],
    importances: Dict[str, float],
    output_dir: Union[str, Path],
    validation_report: Optional[Dict[str, Any]] = None
) -> None:
    """Serializes pipeline, metrics, feature importances, and validation reports."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # 1. Save pipeline
    model_path = out_path / "baseline_model.joblib"
    joblib.dump(model_pipeline, model_path)
    logger.info(f"Saved trained pipeline model to {model_path}")
    
    # 2. Save summary metadata
    summary_path = out_path / "training_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4)
        
    # 3. Save evaluation metrics
    metrics_path = out_path / "evaluation_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=4)
    logger.info(f"Saved performance metrics to {metrics_path}")
    
    # 4. Save feature importances
    importances_path = out_path / "feature_importances.json"
    with open(importances_path, "w", encoding="utf-8") as f:
        json.dump(importances, f, indent=4)
    logger.info(f"Saved feature importances to {importances_path}")
    
    # 5. Save validation report
    if validation_report:
        val_path = out_path / "data_validation_report.json"
        with open(val_path, "w", encoding="utf-8") as f:
            json.dump(validation_report, f, indent=4)


def run_training_pipeline(
    data_path: Union[str, Path],
    output_dir: Union[str, Path]
) -> Pipeline:
    """
    Main orchestration function running the complete ML pipeline.
    Loads, validates, splits, reconstructs target, preprocesses, fits, and serializes.
    
    Args:
        data_path: Path to dataset CSV.
        output_dir: Path to output directory.
        
    Returns:
        Pipeline: Trained pipeline.
    """
    # 1. Load raw dataset
    df = load_training_data(data_path)
    
    # 2. Run validations
    validator = FeatureValidator()
    report = validator.validate_dataframe(df)
    
    if report["status"] == "FAILED":
        msg = f"Critical validation failures in dataset: {report['type_mismatches']}"
        logger.error(msg)
        raise ValueError(msg)
        
    # 3. Split dataset
    train_ratio = getattr(config, "TRAIN_RATIO", 0.70)
    seed = getattr(config, "RANDOM_STATE", 42)
    train_df, test_df = split_dataset(df, train_ratio=train_ratio, random_state=seed)
    
    # 4. Resolve targets (AQI reconstruction)
    y_train, target_col = preprocess_target(train_df)
    train_df[target_col] = y_train
    
    y_test, _ = preprocess_target(test_df)
    test_df[target_col] = y_test
    
    # 5. Extract feature columns and prepare matrices
    X_train, y_train, feature_cols = prepare_training_features(train_df, target_col)
    X_test, y_test, _ = prepare_training_features(test_df, target_col)
    
    # Align X_test columns to match X_train columns exactly
    X_test = X_test.reindex(columns=X_train.columns, fill_value=np.nan)
    
    # 6. Fit Pipeline
    model_pipeline = train_baseline_model(X_train, y_train, feature_cols)
    
    # 7. Predict & Evaluate
    y_pred = model_pipeline.predict(X_test)
    metrics = calculate_metrics(y_test, y_pred)
    importances = get_feature_importances(model_pipeline)
    
    # 8. Serialize all artifacts
    summary = {
        "target_column": target_col,
        "train_samples": len(X_train),
        "test_samples": len(X_test),
        "features_count": len(feature_cols),
        "validation_status": report["status"]
    }
    save_trained_model(
        model_pipeline,
        summary,
        metrics,
        importances,
        output_dir,
        validation_report=report
    )
    
    logger.info("Entire baseline ML pipeline completed successfully.")
    return model_pipeline
