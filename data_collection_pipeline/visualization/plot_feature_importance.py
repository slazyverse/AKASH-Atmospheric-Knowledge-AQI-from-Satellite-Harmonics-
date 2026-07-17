import logging
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import List
from data_collection_pipeline.visualization.style import set_publication_style

logger = logging.getLogger(__name__)

def plot_importance(
    feature_names: List[str],
    importances: List[float],
    output_path: Path,
    title: str = "Feature Importances",
    max_features: int = 15
) -> None:
    """Renders a horizontal bar chart displaying feature importances in descending order."""
    set_publication_style()
    logger.info(f"Rendering feature importance plot to {output_path}")
    
    # Sort and slice
    indices = np.argsort(importances)[::-1]
    sorted_names = [feature_names[i] for i in indices][:max_features]
    sorted_importances = [importances[i] for i in indices][:max_features]
    
    # Reverse to have highest at the top in barh
    sorted_names.reverse()
    sorted_importances.reverse()
    
    plt.figure(figsize=(9, 6))
    plt.barh(sorted_names, sorted_importances, color="#2ca02c", edgecolor="#1e6e1e", height=0.6)
    plt.xlabel("Importance Score")
    plt.ylabel("Predictor Variable")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    logger.info("Feature importance plot rendering complete.")
