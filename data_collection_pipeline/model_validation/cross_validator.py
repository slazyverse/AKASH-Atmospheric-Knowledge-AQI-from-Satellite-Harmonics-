"""
Cross-Validation Module.

Refactored to integrate with FeatureGroupManager, FeatureValidator,
and the shared preprocessing pipeline to prevent data leakage.
"""

import logging
import json
from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, GradientBoostingRegressor
from sklearn.model_selection import KFold, cross_validate
from sklearn.pipeline import Pipeline

from data_collection_pipeline.feature_engineering import (
    FeatureGroupManager,
    FeatureValidator,
    preprocess_target,
    build_preprocessing_pipeline
)

logger = logging.getLogger(__name__)


def load_training_dataset(file_path: Union[str, Path]) -> pd.DataFrame:
    """Loads the training dataset."""
    logger.info(f"Loading training dataset from {file_path}")
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Training dataset not found: {path}")
    df = pd.read_csv(path)
    logger.info(f"Loaded training dataset with shape {df.shape}")
    return df


def prepare_features(df: pd.DataFrame, target_column: str) -> Tuple[pd.DataFrame, List[str]]:
    """
    Selects expected predictor columns using FeatureGroupManager.
    
    Args:
        df: Input DataFrame.
        target_column: Target column to drop.
        
    Returns:
        Tuple of:
          - DataFrame of raw features
          - list of feature names
    """
    logger.info(f"Preparing features (excluding target '{target_column}') using FeatureGroupManager...")
    
    feature_groups = ["satellite", "meteorology", "geography", "temporal"]
    feature_cols = []
    
    for grp in feature_groups:
        feature_cols.extend(FeatureGroupManager.get_features_in_group(grp))
        
    actual_features = [col for col in feature_cols if col in df.columns]
    
    if not actual_features:
        raise ValueError("No schema-registered features found in the input DataFrame.")
        
    return df[actual_features].copy(), actual_features


def perform_cross_validation(X: pd.DataFrame, y: pd.Series, feature_cols: List[str]) -> pd.DataFrame:
    """
    Performs cross-validation wrapping preprocessor and models in Pipelines to prevent data leakage.
    
    Args:
        X: Input features DataFrame.
        y: Target series.
        feature_cols: List of features to process.
        
    Returns:
        pd.DataFrame containing detailed fold metrics.
    """
    logger.info("Performing cross-validation for multiple models.")
    
    n_samples = len(X)
    target_folds = 5
    
    if n_samples < 2:
        logger.error("Dataset too small for cross-validation.")
        raise ValueError(f"Dataset requires at least 2 samples for CV, found {n_samples}.")
        
    if n_samples < target_folds:
        logger.warning(f"Dataset too small for {target_folds} folds. Reducing to {n_samples} folds.")
        n_splits = n_samples
    else:
        n_splits = target_folds
        
    logger.info(f"Using {n_splits}-fold cross-validation.")
    cv = KFold(n_splits=n_splits, shuffle=True, random_state=42)
    
    prep_pipeline = build_preprocessing_pipeline(feature_cols)
    preprocessor = prep_pipeline.named_steps["preprocessor"]
    
    models = {
        "Linear Regression": Pipeline(steps=[
            ("preprocessor", preprocessor),
            ("regressor", LinearRegression())
        ]),
        "Random Forest Regressor": Pipeline(steps=[
            ("preprocessor", preprocessor),
            ("regressor", RandomForestRegressor(random_state=42))
        ]),
        "Extra Trees Regressor": Pipeline(steps=[
            ("preprocessor", preprocessor),
            ("regressor", ExtraTreesRegressor(random_state=42))
        ]),
        "Gradient Boosting Regressor": Pipeline(steps=[
            ("preprocessor", preprocessor),
            ("regressor", GradientBoostingRegressor(random_state=42))
        ])
    }
    
    metrics = ['neg_root_mean_squared_error', 'neg_mean_absolute_error', 'r2']
    all_results = []
    
    for name, model in models.items():
        logger.info(f"Cross-validating {name}...")
        try:
            scores = cross_validate(model, X, y, cv=cv, scoring=metrics, return_train_score=False)
            
            for fold_idx in range(n_splits):
                rmse = -scores['test_neg_root_mean_squared_error'][fold_idx]
                mae = -scores['test_neg_mean_absolute_error'][fold_idx]
                r2 = scores['test_r2'][fold_idx]
                
                all_results.append({
                    "Model": name,
                    "Fold": fold_idx + 1,
                    "RMSE": float(rmse) if not np.isnan(rmse) else np.inf,
                    "MAE": float(mae) if not np.isnan(mae) else np.inf,
                    "R2": float(r2) if not np.isnan(r2) else -np.inf
                })
        except Exception as e:
            logger.error(f"Cross-validation failed for {name}: {e}")
            for fold_idx in range(n_splits):
                all_results.append({
                    "Model": name,
                    "Fold": fold_idx + 1,
                    "RMSE": np.inf,
                    "MAE": np.inf,
                    "R2": -np.inf
                })
                
    results_df = pd.DataFrame(all_results)
    logger.info("Cross-validation completed successfully.")
    return results_df


def summarize_cross_validation(results_df: pd.DataFrame) -> Dict[str, Any]:
    """Summarizes cross validation results calculating mean and std dev across folds."""
    logger.info("Summarizing cross-validation results.")
    summary = {}
    
    for model_name in results_df['Model'].unique():
        model_df = results_df[results_df['Model'] == model_name]
        safe_df = model_df.replace([np.inf, -np.inf], np.nan)
        
        summary[model_name] = {
            "RMSE_mean": float(safe_df['RMSE'].mean()) if not safe_df['RMSE'].isna().all() else None,
            "RMSE_std": float(safe_df['RMSE'].std() if len(safe_df) > 1 else 0.0) if not safe_df['RMSE'].isna().all() else 0.0,
            "MAE_mean": float(safe_df['MAE'].mean()) if not safe_df['MAE'].isna().all() else None,
            "MAE_std": float(safe_df['MAE'].std() if len(safe_df) > 1 else 0.0) if not safe_df['MAE'].isna().all() else 0.0,
            "R2_mean": float(safe_df['R2'].mean()) if not safe_df['R2'].isna().all() else None,
            "R2_std": float(safe_df['R2'].std() if len(safe_df) > 1 else 0.0) if not safe_df['R2'].isna().all() else 0.0
        }
        
    return summary


def generate_cross_validation_report(
    results_df: pd.DataFrame, 
    summary: Dict[str, Any], 
    output_dir: Union[str, Path]
) -> None:
    """Generates cross validation outputs: CSV, JSON, and Markdown."""
    logger.info(f"Generating cross-validation reports in {output_dir}")
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    csv_path = out_path / "cross_validation_results.csv"
    results_df.to_csv(csv_path, index=False)
    
    json_path = out_path / "cross_validation_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4)
        
    md_path = out_path / "cross_validation_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Team RAPTORS - Cross-Validation Report\n\n")
        f.write("## Performance Summary (Mean ± Std)\n")
        f.write("| Model | RMSE | MAE | R2 |\n")
        f.write("| :--- | :---: | :---: | :---: |\n")
        
        for model_name, metrics in summary.items():
            rmse_m = metrics.get('RMSE_mean')
            rmse_s = metrics.get('RMSE_std', 0.0)
            mae_m = metrics.get('MAE_mean')
            mae_s = metrics.get('MAE_std', 0.0)
            r2_m = metrics.get('R2_mean')
            r2_s = metrics.get('R2_std', 0.0)
            
            rmse_str = f"{rmse_m:.4f} ± {rmse_s:.4f}" if rmse_m is not None else "N/A"
            mae_str = f"{mae_m:.4f} ± {mae_s:.4f}" if mae_m is not None else "N/A"
            r2_str = f"{r2_m:.4f} ± {r2_s:.4f}" if r2_m is not None else "N/A"
            
            f.write(f"| **{model_name}** | {rmse_str} | {mae_str} | {r2_str} |\n")
        f.write("\n")


def run_cross_validation(train_path: Union[str, Path], output_dir: Union[str, Path]) -> None:
    """Executes the complete cross-validation pipeline with schema validations."""
    df_train = load_training_dataset(train_path)
    
    # 1. Validate DataFrame structure and ranges
    validator = FeatureValidator()
    report = validator.validate_dataframe(df_train)
    
    if report["status"] == "FAILED":
        msg = f"Critical validation failures in cross-validation dataset: {report['type_mismatches']}"
        logger.error(msg)
        raise ValueError(msg)
        
    # 2. Preprocess target variable
    y, target_col = preprocess_target(df_train)
    # Align rows with non-missing targets
    df_train[target_col] = y
    df_clean = df_train.dropna(subset=[target_col]).copy()
    y_clean = df_clean[target_col]
    
    # 3. Prepare features
    X, feature_cols = prepare_features(df_clean, target_col)
    
    # 4. Run
    results_df = perform_cross_validation(X, y_clean, feature_cols)
    summary = summarize_cross_validation(results_df)
    generate_cross_validation_report(results_df, summary, output_dir)
