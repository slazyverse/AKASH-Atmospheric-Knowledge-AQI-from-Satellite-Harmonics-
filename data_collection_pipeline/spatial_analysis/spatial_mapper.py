import logging
from pathlib import Path
import numpy as np
import pandas as pd
from typing import Optional
from data_collection_pipeline.spatial_analysis import (
    india_grid_generator,
    interpolation,
    color_scheme,
    map_renderer
)

logger = logging.getLogger(__name__)

def run_spatial_mapping_pipeline(
    df: pd.DataFrame,
    values_column: str,
    output_dir: Path,
    file_prefix: str = "india_aqi_map",
    title_suffix: str = "Surface AQI",
    colorbar_label: str = "AQI",
    colormap: Optional[str] = None
) -> dict:
    """
    Orchestrates the entire spatial mapping pipeline.
    Generates normal and high-resolution spatial maps and exports GeoTIFFs if possible.
    """
    logger.info(f"Running spatial mapping pipeline for column: {values_column}")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    if colormap is None:
        if "aqi" in values_column.lower() or values_column == "AQI":
            colormap = color_scheme.get_aqi_colormap()
        else:
            colormap = color_scheme.get_hcho_colormap()
            
    # 1. Generate normal-res grid & interpolate
    grid_x, grid_y = india_grid_generator.generate_grid(resolution=300)
    grid_z = interpolation.interpolate_points_to_grid(
        df["Longitude"].values,
        df["Latitude"].values,
        df[values_column].values,
        grid_x,
        grid_y
    )
    
    # Render normal resolution map
    normal_path = output_dir / f"{file_prefix}.png"
    map_renderer.render_map(
        grid_z,
        normal_path,
        title=f"Spatial Interpolation of {title_suffix} over India",
        colorbar_label=colorbar_label,
        colormap=colormap,
        points_lon=df["Longitude"].values,
        points_lat=df["Latitude"].values,
        points_val=df[values_column].values,
        dpi=150
    )
    
    # 2. Generate high-res grid & interpolate
    grid_x_hr, grid_y_hr = india_grid_generator.generate_grid(resolution=600)
    grid_z_hr = interpolation.interpolate_points_to_grid(
        df["Longitude"].values,
        df["Latitude"].values,
        df[values_column].values,
        grid_x_hr,
        grid_y_hr
    )
    
    # Render high resolution map
    high_res_path = output_dir / f"{file_prefix}_high_res.png"
    map_renderer.render_map(
        grid_z_hr,
        high_res_path,
        title=f"High-Resolution Spatial Interpolation of {title_suffix} over India",
        colorbar_label=colorbar_label,
        colormap=colormap,
        points_lon=None,  # skip overlay for high-res to keep it clean
        points_lat=None,
        points_val=None,
        dpi=300
    )
    
    # 3. Export GeoTIFF
    geotiff_path = output_dir / f"{file_prefix}.tif"
    geotiff_success = map_renderer.export_geotiff(grid_z_hr, geotiff_path)
    
    return {
        "normal_map_png": str(normal_path),
        "high_res_map_png": str(high_res_path),
        "geotiff_export_path": str(geotiff_path) if geotiff_success else None,
        "geotiff_success": geotiff_success
    }
