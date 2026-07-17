import logging
import pandas as pd
import numpy as np
from scipy.interpolate import griddata
from typing import Optional
from data_collection_pipeline.config_loader import config_instance

logger = logging.getLogger(__name__)

def interpolate_points_to_grid(
    lons: np.ndarray,
    lats: np.ndarray,
    values: np.ndarray,
    grid_x: np.ndarray,
    grid_y: np.ndarray,
    method: Optional[str] = None
) -> np.ndarray:
    """
    Interpolates unstructured spatial point observations onto a structured 2D grid.
    Supported methods: 'linear', 'nearest', 'cubic'.
    """
    if method is None:
        method = config_instance.get("interpolation", "method")
        
    logger.info(f"Interpolating {len(values)} points onto grid using method: {method}")
    
    # Mask NaNs in values or coordinates
    mask = (~np.isnan(lons)) & (~np.isnan(lats)) & (~np.isnan(values))
    clean_lons = lons[mask]
    clean_lats = lats[mask]
    clean_vals = values[mask]
    
    if len(clean_vals) == 0:
        logger.warning("No non-null data points available for interpolation. Returning empty grid.")
        return np.full(grid_x.shape, np.nan)
        
    grid_z = griddata((clean_lons, clean_lats), clean_vals, (grid_x, grid_y), method=method)
    return grid_z
