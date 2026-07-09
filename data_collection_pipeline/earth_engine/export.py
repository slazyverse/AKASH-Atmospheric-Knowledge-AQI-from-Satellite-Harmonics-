"""
Earth Engine Export Module.

Defines the interfaces and helpers to export processed Earth Engine images and
ImageCollections to GEE Assets, Google Drive, or Google Cloud Storage.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def export_image_to_drive(
    image: Any,
    description: str,
    folder: str = "Akaash_GEE_Exports",
    scale: float = 1000.0,
    region: Optional[Any] = None
) -> Any:
    """
    Submits a task to Earth Engine to export an image to Google Drive as a GeoTIFF.
    
    Args:
        image: ee.Image to export.
        description: Unique name for the export task.
        folder: Name of the target Google Drive folder.
        scale: Spatial resolution scale in meters.
        region: Geographic region bounds (ee.Geometry) to clip the export.
        
    Returns:
        ee.batch.Task: The submitted GEE export task.
    """
    try:
        import ee
        from data_collection_pipeline.earth_engine.initializer import is_ee_initialized
    except ImportError:
        logger.error("earthengine-api not installed. Export failed.")
        return None
        
    if not is_ee_initialized():
        logger.error("Earth Engine not initialized. Export failed.")
        return None
        
    logger.info(f"Submitting GEE Export to Drive task: '{description}' (scale: {scale}m)")
    
    task = ee.batch.Export.image.toDrive(
        image=image,
        description=description,
        folder=folder,
        scale=scale,
        region=region,
        fileFormat="GeoTIFF",
        maxPixels=1e13
    )
    
    # In dry-run/pipeline prep, we do not start the task automatically to avoid costs,
    # but we expose it for programmatic starting: task.start()
    return task


def export_image_to_asset(
    image: Any,
    description: str,
    asset_id: str,
    scale: float = 1000.0,
    region: Optional[Any] = None
) -> Any:
    """
    Submits a task to Earth Engine to export an image to GEE Assets.
    
    Args:
        image: ee.Image to export.
        description: Unique name for the export task.
        asset_id: Full path for the target GEE asset (e.g. 'users/username/my_image').
        scale: Spatial resolution scale in meters.
        region: Geographic region bounds (ee.Geometry) to clip the export.
        
    Returns:
        ee.batch.Task: The submitted GEE export task.
    """
    try:
        import ee
        from data_collection_pipeline.earth_engine.initializer import is_ee_initialized
    except ImportError:
        logger.error("earthengine-api not installed. Export failed.")
        return None
        
    if not is_ee_initialized():
        logger.error("Earth Engine not initialized. Export failed.")
        return None
        
    logger.info(f"Submitting GEE Export to Asset task: '{description}' to '{asset_id}'")
    
    task = ee.batch.Export.image.toAsset(
        image=image,
        description=description,
        assetId=asset_id,
        scale=scale,
        region=region,
        maxPixels=1e13
    )
    return task


def export_image_to_cloud_storage(
    image: Any,
    description: str,
    bucket: str,
    scale: float = 1000.0,
    region: Optional[Any] = None
) -> Any:
    """
    Submits a task to Earth Engine to export an image to Google Cloud Storage.
    
    Args:
        image: ee.Image to export.
        description: Unique name for the export task.
        bucket: Target GCS bucket name.
        scale: Spatial resolution scale in meters.
        region: Geographic region bounds (ee.Geometry) to clip the export.
        
    Returns:
        ee.batch.Task: The submitted GEE export task.
    """
    try:
        import ee
        from data_collection_pipeline.earth_engine.initializer import is_ee_initialized
    except ImportError:
        logger.error("earthengine-api not installed. Export failed.")
        return None
        
    if not is_ee_initialized():
        logger.error("Earth Engine not initialized. Export failed.")
        return None
        
    logger.info(f"Submitting GEE Export to GCS task: '{description}' to bucket '{bucket}'")
    
    task = ee.batch.Export.image.toCloudStorage(
        image=image,
        description=description,
        bucket=bucket,
        scale=scale,
        region=region,
        fileFormat="GeoTIFF",
        maxPixels=1e13
    )
    return task
