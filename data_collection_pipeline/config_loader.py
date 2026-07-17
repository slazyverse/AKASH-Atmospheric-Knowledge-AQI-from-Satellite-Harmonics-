import os
import yaml
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Default config mapping if YAML loading fails
DEFAULT_CONFIG = {
    "grid": {
        "lon_min": 68.0,
        "lon_max": 98.0,
        "lat_min": 8.0,
        "lat_max": 38.0,
        "default_resolution": 300,
        "high_res_resolution": 600
    },
    "interpolation": {
        "method": "linear"
    },
    "dbscan": {
        "eps": 2.5,
        "min_samples": 3,
        "percentile": 0.90
    },
    "paths": {
        "experiments_dir": "experiments",
        "reports_dir": "reports",
        "plots_dir": "plots"
    },
    "colors": {
        "aqi_cmap": "YlOrRd",
        "hcho_cmap": "Purples",
        "scatter_edge": "k"
    }
}

class PipelineConfig:
    """Manages system configurations from YAML or fallback defaults."""
    
    def __init__(self, config_path: Optional[Path] = None):
        if config_path is None:
            # Look in the parent of the current package
            config_path = Path(__file__).parent / "config.yaml"
            
        self.config_data = DEFAULT_CONFIG.copy()
        
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        # Deep merge or simple update
                        for section, keys in data.items():
                            if isinstance(keys, dict) and section in self.config_data:
                                self.config_data[section].update(keys)
                            else:
                                self.config_data[section] = keys
                logger.info(f"Loaded pipeline configuration from {config_path}")
            except Exception as e:
                logger.warning(f"Error loading {config_path}: {e}. Using fallback defaults.")
        else:
            logger.info(f"Config file not found at {config_path}. Using fallback defaults.")
            
    def get(self, section: str, key: Optional[str] = None) -> Any:
        """Retrieves a configuration value or section."""
        if key is None:
            return self.config_data.get(section)
        return self.config_data.get(section, {}).get(key)

# Global configuration instance
from typing import Optional, Any
config_instance = PipelineConfig()
