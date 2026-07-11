"""
LightGBM Model Training Module.

Implements training, validation, early stopping, evaluation, and serialization
of the production LightGBM model, consuming the unified preprocessing and schema validations.
"""

import sys
import logging
import json
import sklearn
import lightgbm as lgb
from pathlib import Path
from typing import Tuple, List, Dict, Any, Union, Optional

import pandas as pd
import numpy as np
import joblib
from lightgbm import LGBMRegressor, early_stopping, log_evaluation
from sklearn.pipeline import Pipeline
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

from data_collection_pipeline.feature_engineering import (
    FeatureGroupManager,
    FeatureValidator,
    preprocess_target,
    build_preprocessing_pipeline
)
from data_collection_pipeline import config

logger = logging.getLogger(__name__)


def verify_training_dataset_integrity(df: pd.DataFrame, target_col: str) -> Dict[str, Any]:
    """
    Performs a thorough scientific audit of the training dataset before model training.
    
    Args:
        df: Input DataFrame.
        target_col: Expected target column name.
        
    Returns:
        Dict: Integrity report metrics.
    """
    logger.info("Performing pre-training dataset integrity verification...")
    
    report = {
        "dataset_exists": True,
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "target_column_present": target_col in df.columns,
        "duplicate_rows": int(df.duplicated().sum()),
        "missing_percentages": {},
        "placeholder_percentages": {},
        "constant_columns": [],
        "infinite_values": {},
        "status": "PASS"
    }
    
    if not report["target_column_present"]:
        report["status"] = "FAIL"
        logger.error(f"Target column '{target_col}' is missing from the dataset.")
        
    # Calculate missing and placeholder percentages
    for col in df.columns:
        # Missing values (NaN / None)
        null_count = df[col].isna().sum()
        report["missing_percentages"][col] = float(null_count / len(df))
        
        # Placeholders (exact pd.NA or similar)
        placeholder_count = int((df[col] == pd.NA).sum())
        report["placeholder_percentages"][col] = float(placeholder_count / len(df))
        
        # Check constant columns (variance = 0 or unique values <= 1)
        non_null_unique = df[col].dropna().nunique()
        if non_null_unique <= 1:
            report["constant_columns"].append(col)
            
    # Check for infinite values in numeric columns
    numeric_cols = df.select_dtypes(include=[np.number]).columns
    for col in numeric_cols:
        inf_count = int(np.isinf(df[col]).sum())
        if inf_count > 0:
            report["infinite_values"][col] = inf_count
            report["status"] = "FAIL"
            logger.error(f"Column '{col}' contains {inf_count} infinite values.")
            
    logger.info(f"Dataset integrity verification completed with status: {report['status']}")
    return report


def load_training_data(file_path: Union[str, Path]) -> pd.DataFrame:
    """Loads the training dataset from a CSV file."""
    logger.info(f"Loading training data from {file_path}")
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Training dataset not found at {path}")
    return pd.read_csv(path)


def partition_dataset(
    df: pd.DataFrame,
    train_ratio: float = 0.70,
    val_ratio: float = 0.15,
    random_state: int = 42
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Partitions the dataset into Train, Validation, and Test sets.
    Performs a temporal partition if 'Date' or 'timestamp' columns exist,
    otherwise falls back to a deterministic random split.
    
    Args:
        df: Input DataFrame.
        train_ratio: Fraction of rows to allocate for training.
        val_ratio: Fraction of rows to allocate for validation.
        random_state: Random state seed.
        
    Returns:
        Tuple of (train_df, val_df, test_df).
    """
    # Look for date columns to sort for temporal partition
    date_col = None
    for col in ["Date", "date", "timestamp", "datetime"]:
        if col in df.columns:
            date_col = col
            break
            
    if date_col:
        logger.info(f"Performing temporal partition on sorted column '{date_col}'...")
        df_sorted = df.sort_values(by=date_col).copy()
        n = len(df_sorted)
        train_idx = int(n * train_ratio)
        val_idx = int(n * (train_ratio + val_ratio))
        
        train_df = df_sorted.iloc[:train_idx]
        val_df = df_sorted.iloc[train_idx:val_idx]
        test_df = df_sorted.iloc[val_idx:]
    else:
        logger.info("Performing random partition...")
        # Shuffle index deterministically to ensure precise split counts
        shuffled_df = df.sample(frac=1.0, random_state=random_state).copy()
        n = len(shuffled_df)
        train_idx = int(n * train_ratio)
        val_idx = int(n * (train_ratio + val_ratio))
        
        train_df = shuffled_df.iloc[:train_idx]
        val_df = shuffled_df.iloc[train_idx:val_idx]
        test_df = shuffled_df.iloc[val_idx:]
        
    logger.info(
        f"Partition results - Train rows: {len(train_df)}, "
        f"Val rows: {len(val_df)}, Test rows: {len(test_df)}"
    )
    return train_df, val_df, test_df


def prepare_training_features(
    df: pd.DataFrame, 
    target_col: str,
    reference_cols: Optional[List[str]] = None
) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """
    Selects features dynamically using FeatureGroupManager and aligns them
    with target values, dropping rows where the target is missing.
    
    Args:
        df: Input DataFrame.
        target_col: Target column name.
        reference_cols: If provided, forces output columns to match exactly.
        
    Returns:
        Tuple of:
          - X features DataFrame
          - y target Series
          - list of actual feature column names
    """
    logger.info("Selecting features using FeatureGroupManager...")
    
    if reference_cols is not None:
        actual_features = [col for col in reference_cols if col in df.columns]
    else:
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

    # If reference columns aren't provided, drop completely null columns dynamically
    if reference_cols is None:
        all_null_cols = [col for col in X.columns if X[col].isna().all()]
        if all_null_cols:
            logger.info(f"Removing all-null feature columns: {all_null_cols}")
            X = X.drop(columns=all_null_cols)
            
    feature_cols = list(X.columns)
    logger.info(f"Prepared {len(feature_cols)} features for training.")
    return X, y, feature_cols


def train_lightgbm_model(
    X_train: pd.DataFrame, 
    y_train: pd.Series, 
    X_val: pd.DataFrame,
    y_val: pd.Series,
    feature_cols: List[str]
) -> Pipeline:
    """
    Constructs a training pipeline incorporating ColumnTransformers and fits
    a LGBMRegressor with early stopping using central configuration parameters.
    
    Args:
        X_train: Training features.
        y_train: Training target.
        X_val: Validation features.
        y_val: Validation target.
        feature_cols: List of features to process.
        
    Returns:
        Pipeline: Fully fitted training pipeline.
    """
    logger.info("Configuring preprocessing pipeline...")
    prep_pipeline = build_preprocessing_pipeline(feature_cols)
    preprocessor = prep_pipeline.named_steps["preprocessor"]
    
    # Retrieve hyperparameters from central config
    lgbm_params = getattr(config, "LIGHTGBM_PARAMS", {})
    logger.info(f"Using LightGBM parameters from config: {lgbm_params}")
    
    # Transform validation set to pass to early stopping
    X_train_trans = preprocessor.fit_transform(X_train)
    X_val_trans = preprocessor.transform(X_val)
    
    regressor = LGBMRegressor(**lgbm_params)
    
    # Callbacks for early stopping and verbose control
    callbacks = [
        early_stopping(stopping_rounds=10, verbose=False),
        log_evaluation(period=0)
    ]
    
    logger.info("Fitting LGBMRegressor with early stopping callback...")
    regressor.fit(
        X_train_trans,
        y_train,
        eval_set=[(X_val_trans, y_val)],
        callbacks=callbacks
    )
    
    model_pipeline = Pipeline(steps=[
        ("preprocessor", preprocessor),
        ("regressor", regressor)
    ])
    
    logger.info("LightGBM training completed successfully.")
    return model_pipeline


def calculate_metrics(y_true: pd.Series, y_pred: np.ndarray) -> Dict[str, float]:
    """Computes regression performance metrics including R2, RMSE, MAE, and MBE."""
    rmse = float(np.sqrt(mean_squared_error(y_true, y_pred)))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))
    mbe = float(np.mean(y_pred - y_true))
    
    return {
        "R2": r2,
        "RMSE": rmse,
        "MAE": mae,
        "MBE": mbe
    }


def get_feature_importances(model_pipeline: Pipeline) -> Dict[str, float]:
    """Matches feature importances to their respective column names after OHE."""
    preprocessor = model_pipeline.named_steps["preprocessor"]
    regressor = model_pipeline.named_steps["regressor"]
    
    try:
        feature_names = list(preprocessor.get_feature_names_out())
    except Exception:
        feature_names = []
        for name, trans, cols in preprocessor.transformers_:
            if name == "remainder" and trans == "drop":
                continue
            if hasattr(trans, "get_feature_names_out"):
                feature_names.extend(trans.get_feature_names_out(cols))
            else:
                feature_names.extend(cols)
                
    importances = regressor.feature_importances_
    
    importances_dict = {}
    for name, imp in zip(feature_names, importances):
        clean_name = name.split("__")[-1] if "__" in name else name
        importances_dict[clean_name] = float(imp)
        
    return dict(sorted(importances_dict.items(), key=lambda x: x[1], reverse=True))


def save_trained_model(
    model_pipeline: Pipeline, 
    summary: Dict[str, Any],
    metrics: Dict[str, float],
    importances: Dict[str, float],
    lgbm_config: Dict[str, Any],
    val_report: Dict[str, Any],
    output_dir: Union[str, Path]
) -> None:
    """Serializes all pipeline models, configurations, and evaluation metrics."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # 1. Save pipeline
    model_path = out_path / "lightgbm_model.joblib"
    joblib.dump(model_pipeline, model_path)
    logger.info(f"Saved trained Pipeline to {model_path}")
    
    # 2. Save performance metrics
    metrics_path = out_path / "evaluation_metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=4)
        
    # 3. Save training summary
    summary_path = out_path / "training_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4)
        
    # 4. Save feature importances
    importances_path = out_path / "feature_importances.json"
    with open(importances_path, "w", encoding="utf-8") as f:
        json.dump(importances, f, indent=4)
        
    # 5. Save LightGBM config
    config_path = out_path / "lightgbm_config.json"
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(lgbm_config, f, indent=4)
        
    # 6. Save validation report
    val_path = out_path / "data_validation_report.json"
    with open(val_path, "w", encoding="utf-8") as f:
        json.dump(val_report, f, indent=4)


def generate_feature_validation_report(
    val_report: Dict[str, Any],
    feature_cols: List[str],
    metrics: Dict[str, float],
    output_dir: Union[str, Path]
) -> None:
    """Generates the Markdown validation report and compares LightGBM with RF baseline."""
    out_path = Path(output_dir)
    report_path = out_path / "lightgbm_feature_validation_report.md"
    
    # Attempt to load baseline RF metrics if they exist
    rf_metrics = None
    rf_metrics_path = out_path / "evaluation_metrics.json"  # (Usually in baseline output)
    # Wait, check standard baseline metrics file
    rf_alt_path = Path(config.MODEL_OUTPUT_PATH) / "evaluation_metrics.json"
    if rf_alt_path.exists():
        try:
            with open(rf_alt_path, "r", encoding="utf-8") as f:
                rf_metrics = json.load(f)
        except Exception:
            pass
            
    md_content = []
    md_content.append("# LightGBM Feature Validation & Comparison Report\n")
    md_content.append("## Dataset Audit")
    md_content.append(f"* **Total Rows:** {val_report.get('total_rows')}")
    md_content.append(f"* **Total Columns:** {val_report.get('total_columns')}")
    md_content.append(f"* **Duplicate Rows:** {val_report.get('duplicate_rows')}")
    md_content.append(f"* **Audit Status:** {val_report.get('status')}\n")
    
    md_content.append("## Columns Summary")
    md_content.append(f"* **Feature Count:** {len(feature_cols)}")
    md_content.append(f"* **Constant Columns:** {val_report.get('constant_columns', [])}")
    md_content.append(f"* **Infinite Value Columns:** {val_report.get('infinite_values', {})}\n")
    
    md_content.append("## Model Comparison")
    md_content.append("| Model | R² | RMSE | MAE | MBE |")
    md_content.append("| :--- | :---: | :---: | :---: | :---: |")
    
    # Add LightGBM row
    md_content.append(
        f"| **LightGBM (Prod)** | {metrics['R2']:.4f} | {metrics['RMSE']:.4f} | "
        f"{metrics['MAE']:.4f} | {metrics['MBE']:.4f} |"
    )
    
    # Add Random Forest row if available
    if rf_metrics:
        md_content.append(
            f"| **Random Forest (Baseline)** | {rf_metrics.get('R2', 0.0):.4f} | "
            f"{rf_metrics.get('RMSE', 0.0):.4f} | {rf_metrics.get('MAE', 0.0):.4f} | "
            f"{rf_metrics.get('MBE', 0.0):.4f} |"
        )
    else:
        md_content.append("| **Random Forest (Baseline)** | N/A | N/A | N/A | N/A |")
        
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write("\n".join(md_content))
        logger.info(f"Generated LightGBM feature validation report at {report_path}")
    except OSError as e:
        logger.error(f"Failed to write feature validation report: {e}")


def run_training_pipeline(
    data_path: Union[str, Path],
    output_dir: Union[str, Path]
) -> Pipeline:
    """
    Main orchestration function running the complete LightGBM ML pipeline.
    """
    df = load_training_data(data_path)
    
    # Run dynamic CPCB target preprocessing
    y, target_col = preprocess_target(df)
    df[target_col] = y
    
    # 1. Dataset Integrity Verification
    val_report = verify_training_dataset_integrity(df, target_col)
    if val_report["status"] == "FAIL":
        raise ValueError("Dataset integrity audit failed. Check logs for details.")
        
    # 2. Schema Validation
    validator = FeatureValidator()
    schema_report = validator.validate_dataframe(df)
    if schema_report["status"] == "FAILED":
        raise ValueError(f"FeatureValidator schema check failed: {schema_report['type_mismatches']}")
        
    # 3. Partition Dataset (Temporal Holdout Split)
    train_ratio = getattr(config, "TRAIN_RATIO", 0.70)
    val_ratio = getattr(config, "VALIDATION_RATIO", 0.15)
    seed = getattr(config, "RANDOM_STATE", 42)
    
    train_df, val_df, test_df = partition_dataset(
        df, 
        train_ratio=train_ratio, 
        val_ratio=val_ratio, 
        random_state=seed
    )
    
    # 4. Prepare Feature Matrices
    X_train, y_train, feature_cols = prepare_training_features(train_df, target_col)
    X_val, y_val, _ = prepare_training_features(val_df, target_col, reference_cols=feature_cols)
    X_test, y_test, _ = prepare_training_features(test_df, target_col, reference_cols=feature_cols)
    
    # 5. Fit Pipeline with Early Stopping
    model_pipeline = train_lightgbm_model(X_train, y_train, X_val, y_val, feature_cols)
    
    # 6. Predict & Evaluate
    y_pred = model_pipeline.predict(X_test)
    metrics = calculate_metrics(y_test, y_pred)
    importances = get_feature_importances(model_pipeline)
    
    # 7. Collect reproducibility info
    summary = {
        "target_column": target_col,
        "train_samples": len(X_train),
        "validation_samples": len(X_val),
        "test_samples": len(X_test),
        "features_count": len(feature_cols),
        "validation_status": schema_report["status"],
        "reproducibility": {
            "python_version": sys.version,
            "lightgbm_version": lgb.__version__,
            "sklearn_version": sklearn.__version__,
            "random_seed": seed
        }
    }
    
    # 8. Serialize all outputs
    save_trained_model(
        model_pipeline,
        summary,
        metrics,
        importances,
        getattr(config, "LIGHTGBM_PARAMS", {}),
        val_report,
        output_dir
    )
    
    # 9. Generate feature validation Markdown report
    generate_feature_validation_report(val_report, feature_cols, metrics, output_dir)
    
    logger.info("Entire LightGBM ML pipeline completed successfully.")
    return model_pipeline
