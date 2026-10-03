"""
VIIRS Active Fire Loader Module.

Implements loaders for VIIRS active fire / thermal anomalies (NASA/LANCE/SNPP_VIIRS/C2).
Supports filtering by fire detection confidence level.
"""

import logging
from typing import Any, Optional
from data_collection_pipeline.earth_engine.base_loader import BaseGEELoader
from data_collection_pipeline.earth_engine.initializer import is_ee_initialized

logger = logging.getLogger(__name__)


class VIIRSFireLoader(BaseGEELoader):
    """
    Loader for VIIRS Active Fire hotspot detections at 375m resolution.
    Includes confidence-based anomaly filtering.
    """

    def __init__(
        self,
        region_geom: Optional[Any] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        confidence_filter: str = "nominal"  # Options: 'low', 'nominal', 'high'
    ):
        super().__init__(
            alias="VIIRS_ACTIVE_FIRE",
            region_geom=region_geom,
            start_date=start_date,
            end_date=end_date
        )
        self.confidence_filter = confidence_filter.lower()

    def get_collection(self) -> Any:
        """
        Loads the filtered VIIRS active fire dataset and filters by confidence.
        
        Returns:
            ee.ImageCollection: Active fire anomalies.
        """
        if not is_ee_initialized():
            return None
            
        import ee
        
        # Load raw collection and apply standard filters
        col = ee.ImageCollection(self.collection_id)
        if self.start_date and self.end_date:
            col = col.filterDate(self.start_date, self.end_date)
        if self.region_geom:
            col = col.filterBounds(self.region_geom)
            
        # Define confidence filtering logic
        # In VIIRS LANCE C2, confidence is stored as:
        # 'low' (or coded value), 'nominal', 'high'.
        # Some versions use numbers: low=0, nominal=1, high=2 (or string flags 'l', 'n', 'h').
        # We will support standard string or bit mask matching.
        def filter_by_confidence(image):
            conf = image.select("confidence")
            
            # Match 'high' confidence only (highly certain fires)
            if self.confidence_filter == "high":
                # High confidence represents the highest level
                mask = conf.eq(ee.Image.constant(2)).Or(conf.eq(ee.Image.constant(104)))  # Or string character check if encoded as text
                return image.updateMask(mask)
                
            # Match 'nominal' or 'high' (excludes low confidence)
            elif self.confidence_filter == "nominal":
                # Exclude low confidence (typically 0 or string 'l')
                mask = conf.neq(ee.Image.constant(0)).And(conf.neq(ee.Image.constant(108)))
                return image.updateMask(mask)
                
            return image
            
        filtered_col = col.map(filter_by_confidence)
        
        # Select target bands defined in DatasetCatalog
        return filtered_col.select(self.bands)
