import logging
import json
from pathlib import Path
from typing import Any, Dict, Union, Tuple

import pandas as pd
import numpy as np
import joblib

try:
    from data_collection_pipeline import config
except ImportError:
    config = None

logger = logging.getLogger(__name__)


def load_production_model(workspace_dir: Union[str, Path]) -> Any:
    """Loads the serialized production model."""
    logger.info("Loading serialized production model.")
    model_path = Path(workspace_dir) / "production_model.joblib"
    
    if not model_path.exists():
        logger.error(f"Production model not found at {model_path}")
        raise FileNotFoundError(f"Missing {model_path}")
        
    model = joblib.load(model_path)
    logger.info(f"Loaded production model from {model_path}")
    return model


def load_test_dataset(file_path: Union[str, Path]) -> pd.DataFrame:
    """Loads the test dataset."""
    logger.info(f"Loading test dataset from {file_path}")
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Test dataset not found: {path}")
    df = pd.read_csv(path)
    logger.info(f"Loaded test dataset with shape {df.shape}")
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


def generate_predictions(model: Any, X: pd.DataFrame) -> np.ndarray:
    """Generates predictions using the loaded model."""
    logger.info("Generating predictions on test features.")
    return model.predict(X)


def analyze_residuals(y_true: pd.Series, y_pred: np.ndarray) -> Tuple[pd.DataFrame, Dict[str, float]]:
    """Calculates residual metrics and generates the residual dataframe."""
    logger.info("Analyzing residuals and calculating error metrics.")
    
    residuals = y_true - y_pred
    abs_error = np.abs(residuals)
    squared_error = residuals ** 2
    
    residual_df = pd.DataFrame({
        "Actual": y_true,
        "Predicted": y_pred,
        "Residual": residuals,
        "Absolute_Error": abs_error,
        "Squared_Error": squared_error
    })
    
    mae = float(np.mean(abs_error))
    mse = float(np.mean(squared_error))
    rmse = float(np.sqrt(mse))
    residual_mean = float(np.mean(residuals))
    residual_std = float(np.std(residuals, ddof=1) if len(residuals) > 1 else 0.0)
    
    metrics = {
        "MAE": mae,
        "MSE": mse,
        "RMSE": rmse,
        "Residual_Mean": residual_mean,
        "Residual_Standard_Deviation": residual_std,
        "Sample_Count": len(y_true)
    }
    
    logger.info(f"Error metrics calculated. RMSE: {rmse:.4f}, MAE: {mae:.4f}")
    return residual_df, metrics


def generate_error_analysis_report(
    residual_df: pd.DataFrame, 
    metrics: Dict[str, float], 
    output_dir: Union[str, Path]
) -> None:
    """Generates the error analysis reports (CSV, JSON, Markdown)."""
    logger.info(f"Generating error analysis reports in {output_dir}")
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # 1. residual_analysis.csv
    csv_path = out_path / "residual_analysis.csv"
    residual_df.to_csv(csv_path, index=False)
    
    # 2. error_metrics.json
    json_path = out_path / "error_metrics.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=4)
        
    # 3. error_analysis_report.md
    md_path = out_path / "error_analysis_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Team RAPTORS - Error Analysis & Residual Diagnostics Report\n\n")
        f.write("## Overview\n")
        f.write("This report provides an analysis of the production model's prediction errors on the test dataset.\n\n")
        
        f.write("## Error Metrics\n")
        f.write(f"- **Sample Count**: {metrics.get('Sample_Count', 0)}\n")
        f.write(f"- **RMSE (Root Mean Squared Error)**: {metrics.get('RMSE', 0.0):.4f}\n")
        f.write(f"- **MAE (Mean Absolute Error)**: {metrics.get('MAE', 0.0):.4f}\n")
        f.write(f"- **Residual Mean**: {metrics.get('Residual_Mean', 0.0):.4f}\n")
        f.write(f"- **Residual Standard Deviation**: {metrics.get('Residual_Standard_Deviation', 0.0):.4f}\n\n")
        
        f.write("## Residual Sample Data\n")
        f.write("The following table shows the actual vs predicted values and their corresponding errors for the first 10 samples in the test dataset.\n\n")
        
        f.write("| Actual | Predicted | Residual | Absolute Error | Squared Error |\n")
        f.write("| :---: | :---: | :---: | :---: | :---: |\n")
        
        for _, row in residual_df.head(10).iterrows():
            f.write(f"| {row['Actual']:.4f} | {row['Predicted']:.4f} | {row['Residual']:.4f} | {row['Absolute_Error']:.4f} | {row['Squared_Error']:.4f} |\n")
        f.write("\n")
        
    logger.info("All error analysis reports generated successfully.")


def run_error_analysis(workspace_dir: Union[str, Path]) -> None:
    """Executes the complete error analysis pipeline."""
    logger.info("Starting error analysis pipeline.")
    
    target_col = "PM2.5"
    if config and hasattr(config, "REQUIRED_TARGET_COLUMN"):
        target_col = getattr(config, "REQUIRED_TARGET_COLUMN")
        
    test_path = Path(workspace_dir) / "test_dataset.csv"
    df_test = load_test_dataset(test_path)
    
    if target_col not in df_test.columns:
        if "PM2.5" in df_test.columns:
            target_col = "PM2.5"
            
    X = prepare_features(df_test, target_col)
    y = prepare_target(df_test, target_col)
    
    model = load_production_model(workspace_dir)
    y_pred = generate_predictions(model, X)
    
    residual_df, metrics = analyze_residuals(y, y_pred)
    generate_error_analysis_report(residual_df, metrics, workspace_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s [%(name)s] - %(message)s")
    workspace_root = Path(__file__).resolve().parent.parent.parent
    run_error_analysis(workspace_dir=workspace_root)
