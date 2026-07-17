import logging
import json
from pathlib import Path
import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional
from data_collection_pipeline.visualization.plot_predictions import plot_actual_vs_predicted
from data_collection_pipeline.visualization.plot_metrics import plot_residuals, plot_residual_distribution

logger = logging.getLogger(__name__)

def calculate_mape(y_true: np.ndarray, y_pred: np.ndarray) -> float:
    """Computes Mean Absolute Percentage Error (MAPE) avoiding division by zero."""
    # Filter where y_true is 0 to avoid ZeroDivisionError
    mask = (y_true != 0)
    if np.sum(mask) == 0:
        return 0.0
    return float(np.mean(np.abs((y_true[mask] - y_pred[mask]) / y_true[mask])) * 100)

def run_evaluation_pipeline(
    y_true: pd.Series,
    y_pred: np.ndarray,
    output_dir: Path,
    title_prefix: str = "Model Evaluation"
) -> Dict[str, float]:
    """
    Orchestrates the model evaluation process.
    Computes RMSE, MAE, R2, MBE, MAPE, generates plots, and exports JSON summary.
    """
    logger.info("Initializing Automated Evaluation Pipeline...")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    y_t = y_true.values
    
    # 1. Compute metrics
    mae = float(np.mean(np.abs(y_t - y_pred)))
    rmse = float(np.sqrt(np.mean((y_t - y_pred) ** 2)))
    mbe = float(np.mean(y_pred - y_t))
    mape = calculate_mape(y_t, y_pred)
    
    # R2 calculation
    y_mean = np.mean(y_t)
    ss_tot = np.sum((y_t - y_mean) ** 2)
    ss_res = np.sum((y_t - y_pred) ** 2)
    r2 = float(1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0)
    
    metrics = {
        "MAE": mae,
        "RMSE": rmse,
        "R2": r2,
        "MBE": mbe,
        "MAPE": mape
    }
    
    logger.info(f"Evaluation Metrics calculated: {metrics}")
    
    # 2. Export summary JSON
    summary_path = output_dir / "performance_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=4)
    logger.info(f"Saved performance metrics JSON to {summary_path}")
    
    # 3. Generate diagnostic plots
    plot_actual_vs_predicted(
        y_t,
        y_pred,
        output_path=output_dir / "pred_vs_actual.png",
        title=f"{title_prefix}: Actual vs. Predicted",
        r2=r2
    )
    
    plot_residuals(
        y_pred,
        y_t,
        output_path=output_dir / "residuals.png",
        title=f"{title_prefix}: Residual Scatter"
    )
    
    plot_residual_distribution(
        y_pred,
        y_t,
        output_path=output_dir / "error_distribution.png",
        title=f"{title_prefix}: Error Distribution"
    )
    
    return metrics
