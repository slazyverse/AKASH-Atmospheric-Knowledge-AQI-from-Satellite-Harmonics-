import logging
import numpy as np
from typing import Tuple
from data_collection_pipeline.config_loader import config_instance

logger = logging.getLogger(__name__)

def generate_grid(
    resolution: Optional[int] = None
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Generates a 2D coordinate grid of longitude and latitude across India's boundary box.
    Uses bounds defined in the global configuration system.
    """
    grid_cfg = config_instance.get("grid")
    lon_min = grid_cfg.get("lon_min", 68.0)
    lon_max = grid_cfg.get("lon_max", 98.0)
    lat_min = grid_cfg.get("lat_min", 8.0)
    lat_max = grid_cfg.get("lat_max", 38.0)
    
    if resolution is None:
        resolution = grid_cfg.get("default_resolution", 300)
        
    logger.info(f"Generating spatial grid matching lon [{lon_min}, {lon_max}], lat [{lat_min}, {lat_max}] at resolution: {resolution}")
    
    grid_x, grid_y = np.mgrid[lon_min:lon_max:complex(resolution), lat_min:lat_max:complex(resolution)]
    return grid_x, grid_y

from typing import Optional
