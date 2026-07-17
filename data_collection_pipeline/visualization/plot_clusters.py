import logging
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from data_collection_pipeline.visualization.style import set_publication_style

logger = logging.getLogger(__name__)

def plot_hotspot_clusters(
    lons: np.ndarray,
    lats: np.ndarray,
    cluster_ids: np.ndarray,
    output_path: Path,
    title: str = "HCHO Hotspot Clusters"
) -> None:
    """Renders clustered coordinates using a publication-ready color map."""
    set_publication_style()
    logger.info(f"Rendering hotspot cluster plot to {output_path}")
    
    plt.figure(figsize=(9, 7))
    unique_clusters = set(cluster_ids)
    colors = plt.cm.rainbow(np.linspace(0, 1, len(unique_clusters)))
    
    for i, cid in enumerate(unique_clusters):
        mask = (cluster_ids == cid)
        if cid == -1:
            # Noise points
            plt.scatter(
                lons[mask], 
                lats[mask], 
                c="black", 
                marker="x", 
                s=20, 
                label="Noise / Isolated Points"
            )
        else:
            plt.scatter(
                lons[mask],
                lats[mask],
                color=colors[i],
                edgecolors="k",
                s=70,
                linewidths=0.5,
                label=f"Cluster {cid} (N={np.sum(mask)})"
            )
            
    plt.xlabel("Longitude (°E)")
    plt.ylabel("Latitude (°N)")
    plt.title(title)
    plt.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    logger.info("Hotspot cluster visualization rendering complete.")
