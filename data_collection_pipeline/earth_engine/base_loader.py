"""
Base Earth Engine Dataset Loader.

Defines the BaseGEELoader interface from which all dataset-specific loaders
inherit. Handles region/date filtering, metadata access, and export stubs.
"""

import logging
from typing import Any, List, Optional
from data_collection_pipeline.earth_engine.dataset_catalog import DatasetCatalog, DatasetMetadata
from data_collection_pipeline.earth_engine.initializer import is_ee_initialized

logger = logging.getLogger(__name__)


class BaseGEELoader:
    """
    Abstract base loader class defining the pipeline interface for
    retrieving, filtering, and exporting GEE image collections.
    """

    def __init__(
        self,
        alias: str,
        region_geom: Optional[Any] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ):
        self.alias = alias.upper()
        self.metadata: Optional[DatasetMetadata] = DatasetCatalog.get(self.alias)
        
        if not self.metadata:
            raise ValueError(f"Dataset alias '{alias}' is not registered in the DatasetCatalog.")
            
        self.region_geom = region_geom
        self.start_date = start_date
        self.end_date = end_date
        
    @property
    def collection_id(self) -> str:
        return self.metadata.collection_id
        
    @property
    def bands(self) -> List[str]:
        return self.metadata.bands
        
    @property
    def resolution_meters(self) -> float:
        return self.metadata.resolution_meters

    @property
    def projection(self) -> str:
        return self.metadata.projection

    def get_collection(self) -> Any:
        """
        Loads the GEE ImageCollection and applies spatial and temporal filters.
        
        Returns:
            ee.ImageCollection: Filtered image collection.
        """
        if not is_ee_initialized():
            logger.error("Earth Engine is not initialized. Cannot load collection.")
            return None
            
        import ee
        
        # Load the collection
        col = ee.ImageCollection(self.collection_id)
        
        # Apply date filters if available
        if self.start_date and self.end_date:
            col = col.filterDate(self.start_date, self.end_date)
        elif self.start_date:
            col = col.filterDate(self.start_date, "2100-01-01")
            
        # Apply spatial clip filters if a geometry is provided
        if self.region_geom:
            # ee.ImageCollection can filter by bounds
            col = col.filterBounds(self.region_geom)
            
        # Select standard bands defined in catalog
        col = col.select(self.bands)
        
        return col

    def export_to_drive(
        self,
        image: Any,
        description: str,
        folder: str = "Akaash_GEE_Exports",
        scale: Optional[float] = None
    ) -> Any:
        """
        Stub for exporting processed Earth Engine images to Google Drive.
        
        Args:
            image: ee.Image to export.
            description: Export task description.
            folder: Drive folder name.
            scale: Spatial resolution in meters (defaults to dataset resolution).
        """
        logger.info(f"[EXPORT STUB] Exporting {self.alias} to Google Drive: {folder}/{description}")
        return None

    def export_to_asset(
        self,
        image: Any,
        description: str,
        asset_id: str
    ) -> Any:
        """
        Stub for exporting processed Earth Engine images to Earth Engine Assets.
        
        Args:
            image: ee.Image to export.
            description: Export task description.
            asset_id: GEE asset path.
        """
        logger.info(f"[EXPORT STUB] Exporting {self.alias} to GEE Asset: {asset_id}")
        return None

    def export_to_cloud_storage(
        self,
        image: Any,
        description: str,
        bucket: str,
        scale: Optional[float] = None
    ) -> Any:
        """
        Stub for exporting processed Earth Engine images to Google Cloud Storage.
        
        Args:
            image: ee.Image to export.
            description: Export task description.
            bucket: Target GCS bucket.
            scale: Spatial resolution in meters.
        """
        logger.info(f"[EXPORT STUB] Exporting {self.alias} to GCS Bucket: {bucket}")
        return None
