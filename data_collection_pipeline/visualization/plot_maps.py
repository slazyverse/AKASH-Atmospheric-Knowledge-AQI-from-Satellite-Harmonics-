import logging
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Optional
from data_collection_pipeline.visualization.style import set_publication_style

logger = logging.getLogger(__name__)

def plot_interpolated_raster(
    grid_z: np.ndarray,
    output_path: Path,
    title: str,
    colorbar_label: str = "Values",
    colormap: str = "YlOrRd",
    points_lon: Optional[np.ndarray] = None,
    points_lat: Optional[np.ndarray] = None,
    points_val: Optional[np.ndarray] = None
) -> None:
    """Renders an interpolated 2D spatial raster and saves the map."""
    set_publication_style()
    logger.info(f"Rendering spatial raster map to {output_path}")
    
    plt.figure(figsize=(10, 8))
    
    # Transpose because imshow expects (row, col) i.e. (Y, X)
    im = plt.imshow(
        grid_z.T,
        extent=(68, 98, 8, 38),
        origin="lower",
        cmap=colormap,
        alpha=0.85
    )
    plt.colorbar(im, label=colorbar_label)
    
    if points_lon is not None and points_lat is not None and points_val is not None:
        plt.scatter(
            points_lon,
            points_lat,
            c=points_val,
            cmap=colormap,
            edgecolors="k",
            s=35,
            linewidths=0.5,
            label="Station Locations"
        )
        plt.legend(loc="upper right")
        
    plt.xlabel("Longitude (°E)")
    plt.ylabel("Latitude (°N)")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=150)
    plt.close()
    logger.info("Spatial raster map rendering complete.")
