import logging
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from data_collection_pipeline.visualization.style import set_publication_style

logger = logging.getLogger(__name__)

def plot_actual_vs_predicted(
    y_true: np.ndarray,
    y_pred: np.ndarray,
    output_path: Path,
    title: str = "Actual vs. Predicted AQI",
    r2: Optional[float] = None
) -> None:
    """Plots a scatter plot comparing actual targets with predictions, overlaying a 1:1 line."""
    set_publication_style()
    logger.info(f"Rendering actual vs predicted plot to {output_path}")
    
    plt.figure(figsize=(7, 6))
    plt.scatter(y_true, y_pred, alpha=0.6, color="#1f77b4", edgecolors="k", s=35, linewidths=0.5)
    
    # 1:1 line
    min_val = min(y_true.min(), y_pred.min())
    max_val = max(y_true.max(), y_pred.max())
    plt.plot([min_val, max_val], [min_val, max_val], 'r--', lw=2, label="1:1 Perfect Fit")
    
    plt.xlabel("Actual Value")
    plt.ylabel("Predicted Value")
    
    title_text = title
    if r2 is not None:
        title_text += f" (R² = {r2:.3f})"
    plt.title(title_text)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    logger.info("Actual vs predicted plot rendering complete.")

from typing import Optional
