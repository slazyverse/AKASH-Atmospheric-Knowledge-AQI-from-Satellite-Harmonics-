import logging
import json
from pathlib import Path
from typing import Any, Dict, Union

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, GradientBoostingRegressor
from sklearn.model_selection import KFold, cross_validate

try:
    from data_collection_pipeline import config
except ImportError:
    config = None

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


def prepare_features(df: pd.DataFrame, target_column: str) -> pd.DataFrame:
    """Prepares numerical features."""
    logger.info(f"Preparing features (excluding target '{target_column}')")
    numeric_df = df.select_dtypes(include=["number"]).copy()
    if target_column in numeric_df.columns:
        numeric_df = numeric_df.drop(columns=[target_column])
    numeric_df = numeric_df.fillna(numeric_df.mean(numeric_only=True)).fillna(0.0)
    logger.info(f"Prepared features shape: {numeric_df.shape}")
    return numeric_df


def prepare_target(df: pd.DataFrame, target_column: str) -> pd.Series:
    """Prepares the target variable."""
    logger.info(f"Preparing target '{target_column}'")
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found in dataset.")
    y = df[target_column].copy()
    y = y.fillna(y.mean()).fillna(0.0)
    logger.info(f"Prepared target shape: {y.shape}")
    return y


def perform_cross_validation(X: pd.DataFrame, y: pd.Series) -> pd.DataFrame:
    """Performs cross-validation on the specified models."""
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
    
    models = {
        "Linear Regression": LinearRegression(),
        "Random Forest Regressor": RandomForestRegressor(random_state=42),
        "Extra Trees Regressor": ExtraTreesRegressor(random_state=42),
        "Gradient Boosting Regressor": GradientBoostingRegressor(random_state=42)
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
        
        # Replace inf with nan for aggregation purposes so they don't corrupt means
        safe_df = model_df.replace([np.inf, -np.inf], np.nan)
        
        summary[model_name] = {
            "RMSE_mean": float(safe_df['RMSE'].mean()),
            "RMSE_std": float(safe_df['RMSE'].std() if len(safe_df) > 1 else 0.0),
            "MAE_mean": float(safe_df['MAE'].mean()),
            "MAE_std": float(safe_df['MAE'].std() if len(safe_df) > 1 else 0.0),
            "R2_mean": float(safe_df['R2'].mean()),
            "R2_std": float(safe_df['R2'].std() if len(safe_df) > 1 else 0.0)
        }
    
    # Handle NaN values to make sure it's serializable
    for model, metrics in summary.items():
        for k, v in metrics.items():
            if np.isnan(v):
                summary[model][k] = None

    logger.info("Summary computation completed.")
    return summary


def generate_cross_validation_report(results_df: pd.DataFrame, summary: Dict[str, Any], output_dir: Union[str, Path]) -> None:
    """Generates cross validation outputs: CSV, JSON, and Markdown."""
    logger.info(f"Generating cross-validation reports in {output_dir}")
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # 1. cross_validation_results.csv
    csv_path = out_path / "cross_validation_results.csv"
    results_df.to_csv(csv_path, index=False)
    
    # 2. cross_validation_summary.json
    json_path = out_path / "cross_validation_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4)
        
    # 3. cross_validation_report.md
    md_path = out_path / "cross_validation_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Team RAPTORS - Cross-Validation Report\n\n")
        f.write("## Overview\n")
        f.write("This report summarizes the performance of models evaluated using cross-validation on the training dataset.\n\n")
        
        f.write("## Performance Summary (Mean ± Std)\n")
        f.write("| Model | RMSE | MAE | R2 |\n")
        f.write("| :--- | :---: | :---: | :---: |\n")
        
        for model_name, metrics in summary.items():
            rmse_m = metrics.get('RMSE_mean')
            rmse_s = metrics.get('RMSE_std')
            mae_m = metrics.get('MAE_mean')
            mae_s = metrics.get('MAE_std')
            r2_m = metrics.get('R2_mean')
            r2_s = metrics.get('R2_std')
            
            rmse_str = f"{rmse_m:.4f} ± {rmse_s:.4f}" if rmse_m is not None else "N/A"
            mae_str = f"{mae_m:.4f} ± {mae_s:.4f}" if mae_m is not None else "N/A"
            r2_str = f"{r2_m:.4f} ± {r2_s:.4f}" if r2_m is not None else "N/A"
            
            f.write(f"| **{model_name}** | {rmse_str} | {mae_str} | {r2_str} |\n")
        f.write("\n")
        
        f.write("## Detailed Fold Results\n")
        f.write("| Model | Fold | RMSE | MAE | R2 |\n")
        f.write("| :--- | :---: | :---: | :---: | :---: |\n")
        
        for _, row in results_df.iterrows():
            rmse = f"{row['RMSE']:.4f}" if not np.isinf(row['RMSE']) else "inf"
            mae = f"{row['MAE']:.4f}" if not np.isinf(row['MAE']) else "inf"
            r2 = f"{row['R2']:.4f}" if not np.isinf(row['R2']) else "-inf"
            f.write(f"| **{row['Model']}** | {row['Fold']} | {rmse} | {mae} | {r2} |\n")
        f.write("\n")
        
    logger.info("All reports generated successfully.")


def run_cross_validation(train_path: Union[str, Path], output_dir: Union[str, Path]) -> None:
    """Executes the complete cross-validation pipeline."""
    target_col = "PM2.5"
    if config and hasattr(config, "REQUIRED_TARGET_COLUMN"):
        target_col = getattr(config, "REQUIRED_TARGET_COLUMN")
        
    df_train = load_training_dataset(train_path)
    
    if target_col not in df_train.columns:
        if "PM2.5" in df_train.columns:
            target_col = "PM2.5"
            
    X = prepare_features(df_train, target_col)
    y = prepare_target(df_train, target_col)
    
    results_df = perform_cross_validation(X, y)
    summary = summarize_cross_validation(results_df)
    generate_cross_validation_report(results_df, summary, output_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s [%(name)s] - %(message)s")
    workspace_root = Path(__file__).resolve().parent.parent.parent
    run_cross_validation(
        train_path=workspace_root / "train_dataset.csv",
        output_dir=workspace_root
    )
