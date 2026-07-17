import logging
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from data_collection_pipeline.visualization.style import set_publication_style

logger = logging.getLogger(__name__)

def plot_residuals(
    y_pred: np.ndarray,
    y_true: np.ndarray,
    output_path: Path,
    title: str = "Residual Analysis"
) -> None:
    """Plots residuals (y_true - y_pred) against predicted values to analyze homoscedasticity."""
    set_publication_style()
    logger.info(f"Rendering residual scatter plot to {output_path}")
    
    residuals = y_true - y_pred
    
    plt.figure(figsize=(8, 6))
    plt.scatter(y_pred, residuals, alpha=0.6, color="#d62728", edgecolors="k", s=35, linewidths=0.5)
    plt.axhline(0, color="black", linestyle="--", lw=1.5)
    
    plt.xlabel("Predicted Value")
    plt.ylabel("Residual (Actual - Predicted)")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    logger.info("Residual scatter plot rendering complete.")

def plot_residual_distribution(
    y_pred: np.ndarray,
    y_true: np.ndarray,
    output_path: Path,
    title: str = "Error Distribution"
) -> None:
    """Plots a histogram of the prediction errors to evaluate normality."""
    set_publication_style()
    logger.info(f"Rendering error distribution histogram to {output_path}")
    
    errors = y_true - y_pred
    
    plt.figure(figsize=(8, 6))
    plt.hist(errors, bins=20, edgecolor="k", color="#9467bd", alpha=0.7)
    plt.axvline(0, color="red", linestyle="--", lw=1.5)
    
    plt.xlabel("Error (Actual - Predicted)")
    plt.ylabel("Frequency")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    logger.info("Error distribution histogram rendering complete.")
