import logging
import os
from pathlib import Path
from typing import Any, Dict, Tuple, Union

import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, GradientBoostingRegressor
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score

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


def load_validation_dataset(file_path: Union[str, Path]) -> pd.DataFrame:
    """Loads the validation dataset."""
    logger.info(f"Loading validation dataset from {file_path}")
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Validation dataset not found: {path}")
    df = pd.read_csv(path)
    logger.info(f"Loaded validation dataset with shape {df.shape}")
    return df


def prepare_features(df: pd.DataFrame, target_column: str = "PM2.5") -> Tuple[pd.DataFrame, pd.Series]:
    """Prepares numerical features and target variable."""
    logger.info(f"Preparing features with target '{target_column}'")
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found.")
    
    numeric_df = df.select_dtypes(include=["number"]).copy()
    numeric_df = numeric_df.fillna(numeric_df.mean(numeric_only=True)).fillna(0.0)
    
    if target_column not in numeric_df.columns:
        numeric_df[target_column] = df[target_column]
        
    y = numeric_df[target_column]
    X = numeric_df.drop(columns=[target_column])
    
    logger.info(f"Prepared features X shape: {X.shape}, y shape: {y.shape}")
    return X, y


def train_models(X_train: pd.DataFrame, y_train: pd.Series) -> Dict[str, Any]:
    """Trains the specified models."""
    logger.info("Training models: Linear Regression, Random Forest, Extra Trees, Gradient Boosting")
    models = {
        "Linear Regression": LinearRegression(),
        "Random Forest Regressor": RandomForestRegressor(random_state=42),
        "Extra Trees Regressor": ExtraTreesRegressor(random_state=42),
        "Gradient Boosting Regressor": GradientBoostingRegressor(random_state=42)
    }
    
    trained_models = {}
    for name, model in models.items():
        logger.info(f"Training {name}...")
        try:
            model.fit(X_train, y_train)
            trained_models[name] = model
        except Exception as e:
            logger.error(f"Failed to train {name}: {e}")
        
    logger.info("All models trained successfully (or handled failures).")
    return trained_models


def evaluate_models(models: Dict[str, Any], X_val: pd.DataFrame, y_val: pd.Series) -> pd.DataFrame:
    """Evaluates the models on the validation set."""
    logger.info("Evaluating models on validation dataset.")
    results = []
    
    validation_samples = len(y_val)
    if validation_samples < 2:
        logger.warning("R² is undefined for fewer than two validation samples. Skipping R² calculation.")

    for name, model in models.items():
        try:
            preds = model.predict(X_val)
            rmse = float(np.sqrt(mean_squared_error(y_val, preds)))
            mae = float(mean_absolute_error(y_val, preds))
            
            if validation_samples < 2:
                r2 = np.nan
            else:
                r2 = float(r2_score(y_val, preds))
            
            results.append({
                "Model": name,
                "RMSE": rmse,
                "MAE": mae,
                "R2": r2
            })
        except Exception as e:
            logger.error(f"Failed to evaluate {name}: {e}")
            results.append({
                "Model": name,
                "RMSE": np.nan,
                "MAE": np.nan,
                "R2": np.nan
            })
        
    results_df = pd.DataFrame(results)
    logger.info("Model evaluation completed.")
    return results_df


def rank_models(results_df: pd.DataFrame) -> pd.DataFrame:
    """Ranks models based on RMSE (lower is better) and R2 (higher is better)."""
    logger.info("Ranking models based on evaluation metrics.")
    ranking_df = results_df.copy()
    # Apply safe fillna for missing values
    ranking_df["RMSE"] = ranking_df["RMSE"].fillna(np.inf)
    ranking_df["MAE"] = ranking_df["MAE"].fillna(np.inf)
    ranking_df["R2"] = ranking_df["R2"].fillna(-np.inf)
    
    # Rank RMSE ascending (lower is better, so rank 1 is lowest RMSE)
    ranking_df["RMSE_Rank"] = ranking_df["RMSE"].rank(ascending=True, method="min").astype(int)
    
    # Rank R2 descending (higher is better, so rank 1 is highest R2)
    ranking_df["R2_Rank"] = ranking_df["R2"].rank(ascending=False, method="min").astype(int)
    
    # Combined Score (average of ranks)
    ranking_df["Combined_Score"] = (ranking_df["RMSE_Rank"] + ranking_df["R2_Rank"]) / 2.0
    
    # Final Rank
    ranking_df["Final_Rank"] = ranking_df["Combined_Score"].rank(ascending=True, method="min").astype(int)
    
    # Sort by final rank
    ranking_df = ranking_df.sort_values(by="Final_Rank", ascending=True).reset_index(drop=True)
    logger.info("Model ranking completed.")
    return ranking_df


def generate_model_comparison_report(results_df: pd.DataFrame, ranking_df: pd.DataFrame, output_dir: Union[str, Path]) -> None:
    """Generates the comparison reports (CSV and Markdown)."""
    logger.info(f"Generating model comparison reports in {output_dir}")
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # 1. model_comparison.csv
    comp_csv = out_path / "model_comparison.csv"
    results_df.to_csv(comp_csv, index=False)
    
    # 2. model_ranking.csv
    rank_csv = out_path / "model_ranking.csv"
    ranking_df.to_csv(rank_csv, index=False)
    
    # 3. model_comparison_report.md
    report_md = out_path / "model_comparison_report.md"
    with open(report_md, "w", encoding="utf-8") as f:
        f.write("# Team RAPTORS - Model Comparison Report\n\n")
        f.write("## Overview\n")
        f.write("This report evaluates the performance of different regression models on the validation dataset.\n\n")
        
        f.write("## Evaluation Metrics\n")
        f.write("| Model | RMSE | MAE | R2 |\n")
        f.write("| :--- | :---: | :---: | :---: |\n")
        r2_skipped = False
        for _, row in results_df.iterrows():
            if pd.isna(row['R2']):
                r2_str = "N/A"
                r2_skipped = True
            else:
                r2_str = f"{row['R2']:.4f}"
            f.write(f"| **{row['Model']}** | {row['RMSE']:.4f} | {row['MAE']:.4f} | {r2_str} |\n")
        f.write("\n")
        
        if r2_skipped:
            f.write("R²: N/A (Validation set contains fewer than 2 samples)\n\n")
        
        f.write("## Model Ranking\n")
        f.write("Models are ranked based on a combined score from RMSE (lower is better) and R2 (higher is better).\n\n")
        f.write("| Final Rank | Model | Combined Score | RMSE Rank | R2 Rank |\n")
        f.write("| :---: | :--- | :---: | :---: | :---: |\n")
        for _, row in ranking_df.iterrows():
            f.write(f"| {row['Final_Rank']} | **{row['Model']}** | {row['Combined_Score']:.1f} | {row['RMSE_Rank']} | {row['R2_Rank']} |\n")
        f.write("\n")
        
        best_model = ranking_df.iloc[0]['Model']
        f.write("## Recommendation\n")
        f.write(f"Based on the evaluation, the recommended model is **{best_model}**.\n")
        
    logger.info("Reports generated successfully.")


def run_model_comparison(train_path: Union[str, Path], val_path: Union[str, Path], output_dir: Union[str, Path]) -> None:
    """Runs the full model comparison pipeline."""
    target_col = "PM2.5"
    if config and hasattr(config, "REQUIRED_TARGET_COLUMN"):
        target_col = getattr(config, "REQUIRED_TARGET_COLUMN")
        
    df_train = load_training_dataset(train_path)
    df_val = load_validation_dataset(val_path)
    
    if target_col not in df_train.columns:
        if "PM2.5" in df_train.columns:
            target_col = "PM2.5"
            
    X_train, y_train = prepare_features(df_train, target_col)
    X_val, y_val = prepare_features(df_val, target_col)
    
    # Align columns
    missing_cols = set(X_train.columns) - set(X_val.columns)
    for c in missing_cols:
        X_val[c] = 0.0
    X_val = X_val[X_train.columns]
    
    models = train_models(X_train, y_train)
    results_df = evaluate_models(models, X_val, y_val)
    ranking_df = rank_models(results_df)
    generate_model_comparison_report(results_df, ranking_df, output_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s [%(name)s] - %(message)s")
    workspace_root = Path(__file__).resolve().parent.parent.parent
    run_model_comparison(
        train_path=workspace_root / "train_dataset.csv",
        val_path=workspace_root / "validation_dataset.csv",
        output_dir=workspace_root
    )
