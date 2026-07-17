import logging
from data_collection_pipeline.config_loader import config_instance

logger = logging.getLogger(__name__)

def get_aqi_colormap() -> str:
    """Returns the colormap name for AQI maps."""
    return config_instance.get("colors", "aqi_cmap")

def get_hcho_colormap() -> str:
    """Returns the colormap name for HCHO maps."""
    return config_instance.get("colors", "hcho_cmap")

def get_scatter_edge_color() -> str:
    """Returns the marker edge color for station overlay scatter points."""
    return config_instance.get("colors", "scatter_edge")
