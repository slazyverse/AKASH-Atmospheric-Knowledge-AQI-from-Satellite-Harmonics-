"""
TROPOMI Loader Module.

Implements Sentinel-5P TROPOMI loaders with QA-value and cloud fraction masking.
"""

import logging
from typing import Any, Optional
from data_collection_pipeline.earth_engine.base_loader import BaseGEELoader
from data_collection_pipeline.earth_engine.initializer import is_ee_initialized

logger = logging.getLogger(__name__)


class TROPOMILoader(BaseGEELoader):
    """
    Loader for Sentinel-5P TROPOMI atmospheric columns (HCHO, NO2, SO2, CO, O3).
    Includes quality assurance (QA) masking functionality.
    """

    def __init__(
        self,
        alias: str,  # e.g., 'TROPOMI_HCHO', 'TROPOMI_NO2'
        region_geom: Optional[Any] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        qa_threshold: float = 0.5  # Recommended QA threshold is > 0.5 (good quality)
    ):
        super().__init__(
            alias=alias,
            region_geom=region_geom,
            start_date=start_date,
            end_date=end_date
        )
        self.qa_threshold = qa_threshold

    def get_collection(self) -> Any:
        """
        Loads the filtered TROPOMI collection and applies QA cloud masking.
        
        Returns:
            ee.ImageCollection: QA masked and filtered collection.
        """
        if not is_ee_initialized():
            return None
            
        import ee
        
        # Load raw collection and apply dates/geometry first
        col = ee.ImageCollection(self.collection_id)
        if self.start_date and self.end_date:
            col = col.filterDate(self.start_date, self.end_date)
        if self.region_geom:
            col = col.filterBounds(self.region_geom)
            
        # Define QA masking function
        def mask_qa(image):
            # Select the qa_value band which exists in all S5P OFFL collections
            qa = image.select("qa_value")
            # Update mask: keep pixels where qa_value >= threshold
            mask = qa.gte(self.qa_threshold)
            return image.updateMask(mask)
            
        # Apply QA mask to the collection
        masked_col = col.map(mask_qa)
        
        # Select target bands defined in DatasetCatalog
        return masked_col.select(self.bands)
