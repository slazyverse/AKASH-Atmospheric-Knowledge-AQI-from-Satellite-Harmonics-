"""
MODIS MAIAC AOD Loader Module.

Implements loaders for MODIS MAIAC daily AOD (MCD19A2) with QA-bitmask filtering.
"""

import logging
from typing import Any, Optional
from data_collection_pipeline.earth_engine.base_loader import BaseGEELoader
from data_collection_pipeline.earth_engine.initializer import is_ee_initialized

logger = logging.getLogger(__name__)


class MODISAODLoader(BaseGEELoader):
    """
    Loader for MODIS MAIAC Aerosol Optical Depth (MCD19A2) daily products.
    Includes AOD_QA bitmask filtering to select high-quality cloud-free pixels.
    """

    def __init__(
        self,
        region_geom: Optional[Any] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        best_quality_only: bool = True
    ):
        super().__init__(
            alias="MODIS_MAIAC_AOD",
            region_geom=region_geom,
            start_date=start_date,
            end_date=end_date
        )
        self.best_quality_only = best_quality_only

    def get_collection(self) -> Any:
        """
        Loads MODIS MAIAC AOD and applies QA bitmask cloud/aerosol filters.
        
        Returns:
            ee.ImageCollection: Filtered and QA-masked daily AOD granules.
        """
        if not is_ee_initialized():
            return None
            
        import ee
        
        # Load raw collection and apply dates/geometry
        col = ee.ImageCollection(self.collection_id)
        if self.start_date and self.end_date:
            col = col.filterDate(self.start_date, self.end_date)
        if self.region_geom:
            col = col.filterBounds(self.region_geom)
            
        # Define QA masking function
        def mask_maiac_qa(image):
            qa = image.select("AOD_QA")
            
            # MAIAC AOD_QA bit details:
            # Bits 0-2: Cloud Mask (001 = clear, 010 = cloudy)
            # Bits 8-11: QA level (0000 = best, 0001 = clean, etc.)
            # A common approach: Check bits indicating clear/cloud-free and high quality.
            
            if self.best_quality_only:
                # Bitwise operations:
                # Cloud mask: check if bits 0-2 represent 'clear' (1)
                # QA Level: check if bits 8-11 represent 'best' (0)
                cloud_mask = qa.bitwiseAnd(0x07).eq(1)
                qa_quality = qa.bitwiseAnd(0x0F00).eq(0)
                
                mask = cloud_mask.And(qa_quality)
                return image.updateMask(mask)
                
            return image
            
        # Apply QA mask to the collection
        masked_col = col.map(mask_maiac_qa)
        
        # Select target bands defined in DatasetCatalog
        return masked_col.select(self.bands)
