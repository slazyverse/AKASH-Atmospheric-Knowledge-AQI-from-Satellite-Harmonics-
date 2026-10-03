"""
Earth Engine Utility Helpers.

Implements reusable cloud masking logic, GeoJSON to GEE Geometry conversion,
and bounding box geometry helpers.
"""

import logging
from typing import Any, List, Optional

logger = logging.getLogger(__name__)


class CloudMaskStrategy:
    """
    Collection of static cloud masking strategies for common Earth Engine sensors.
    """

    @staticmethod
    def mask_s2_clouds(image: Any) -> Any:
        """
        Applies cloud masking to Sentinel-2 imagery using QA60 band.
        
        Args:
            image: ee.Image Sentinel-2 image.
            
        Returns:
            ee.Image masked Sentinel-2 image.
        """
        qa = image.select("QA60")
        
        # Bits 10 and 11 represent clouds and cirrus respectively
        cloud_bit_mask = 1 << 10
        cirrus_bit_mask = 1 << 11
        
        # Both flags should be set to zero for clear conditions
        mask = qa.bitwiseAnd(cloud_bit_mask).eq(0).And(
            qa.bitwiseAnd(cirrus_bit_mask).eq(0)
        )
        return image.updateMask(mask).divide(10000.0)

    @staticmethod
    def mask_landsat_sr_clouds(image: Any) -> Any:
        """
        Applies cloud masking to Landsat 8/9 Surface Reflectance using pixel_qa / QA_PIXEL.
        
        Args:
            image: ee.Image Landsat SR image.
            
        Returns:
            ee.Image masked Landsat image.
        """
        qa = image.select("QA_PIXEL")
        
        # Bit 3: Cloud, Bit 4: Cloud Shadow, Bit 5: Snow
        cloud_shadow_mask = 1 << 3
        clouds_mask = 1 << 4
        snow_mask = 1 << 5
        
        mask = qa.bitwiseAnd(cloud_shadow_mask).eq(0).And(
            qa.bitwiseAnd(clouds_mask).eq(0)
        ).And(
            qa.bitwiseAnd(snow_mask).eq(0)
        )
        return image.updateMask(mask)


def bbox_to_ee_geometry(bbox: List[float]) -> Optional[Any]:
    """
    Converts a bounding box [West, South, East, North] to an ee.Geometry.Rectangle.
    
    Args:
        bbox: Bounding box coordinates.
        
    Returns:
        ee.Geometry.Rectangle or None if Earth Engine is not initialized.
    """
    try:
        import ee
        from data_collection_pipeline.earth_engine.initializer import is_ee_initialized
    except ImportError:
        return None
        
    if not is_ee_initialized():
        return None
        
    w, s, e, n = bbox
    return ee.Geometry.Rectangle([w, s, e, n])


def geojson_to_ee_geometry(geojson_dict: dict) -> Optional[Any]:
    """
    Converts a raw GeoJSON dictionary to a GEE ee.Geometry object.
    
    Args:
        geojson_dict: Dictionary containing GeoJSON data.
        
    Returns:
        ee.Geometry representation or None if Earth Engine is not initialized.
    """
    try:
        import ee
        from data_collection_pipeline.earth_engine.initializer import is_ee_initialized
    except ImportError:
        return None
        
    if not is_ee_initialized():
        return None
        
    try:
        # Load raw geojson geometry using Earth Engine geometry constructor
        if "geometry" in geojson_dict:
            geom_data = geojson_dict["geometry"]
        else:
            geom_data = geojson_dict
            
        # Parse coordinates and type directly into ee geometry
        geom_type = geom_data.get("type")
        coords = geom_data.get("coordinates")
        
        if geom_type == "Polygon":
            return ee.Geometry.Polygon(coords)
        elif geom_type == "MultiPolygon":
            return ee.Geometry.MultiPolygon(coords)
        elif geom_type == "Point":
            return ee.Geometry.Point(coords)
        else:
            # Fallback to ee.Geometry parses anything standard
            return ee.Geometry(geom_data)
    except Exception as e:
        logger.error(f"Failed to parse GeoJSON to Earth Engine Geometry: {e}")
        return None
