import logging
import numpy as np
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from typing import Optional
from data_collection_pipeline.spatial_analysis import color_scheme

logger = logging.getLogger(__name__)

def render_map(
    grid_z: np.ndarray,
    output_path: Path,
    title: str,
    colorbar_label: str,
    colormap: str,
    points_lon: Optional[np.ndarray] = None,
    points_lat: Optional[np.ndarray] = None,
    points_val: Optional[np.ndarray] = None,
    dpi: int = 150
) -> None:
    """Renders the interpolated raster grid and overlays coordinate scatter points."""
    logger.info(f"Rendering map and saving to {output_path} (DPI={dpi})")
    
    # Check if directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
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
        edge_col = color_scheme.get_scatter_edge_color()
        plt.scatter(
            points_lon,
            points_lat,
            c=points_val,
            cmap=colormap,
            edgecolors=edge_col,
            s=30,
            label="Station Locations"
        )
        plt.legend()
        
    plt.xlabel("Longitude (°E)")
    plt.ylabel("Latitude (°N)")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(output_path, dpi=dpi)
    plt.close()
    logger.info(f"Rendered map saved successfully to {output_path}")

def export_geotiff(
    grid_z: np.ndarray,
    output_path: Path,
    lon_bounds: tuple = (68.0, 98.0),
    lat_bounds: tuple = (8.0, 38.0)
) -> bool:
    """
    Attempts to export the raster grid as a GeoTIFF.
    Falls back gracefully if rasterio or GDAL is not installed.
    """
    try:
        import rasterio
        from rasterio.transform import from_bounds
        
        logger.info(f"Exporting grid as GeoTIFF to {output_path}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        width = grid_z.shape[0]
        height = grid_z.shape[1]
        
        transform = from_bounds(
            lon_bounds[0], lat_bounds[0],
            lon_bounds[1], lat_bounds[1],
            width, height
        )
        
        # Write to file
        with rasterio.open(
            output_path,
            'w',
            driver='GTiff',
            height=height,
            width=width,
            count=1,
            dtype=grid_z.dtype,
            crs='+proj=longlat +datum=WGS84 +no_defs',
            transform=transform,
        ) as dst:
            # Transpose grid to align with raster row/col orientation
            dst.write(grid_z.T, 1)
            
        logger.info(f"GeoTIFF exported successfully to {output_path}")
        return True
    except ImportError:
        logger.warning(f"rasterio package not available. GeoTIFF export to {output_path} skipped.")
        return False
    except Exception as e:
        logger.error(f"Failed to export GeoTIFF: {e}")
        return False
