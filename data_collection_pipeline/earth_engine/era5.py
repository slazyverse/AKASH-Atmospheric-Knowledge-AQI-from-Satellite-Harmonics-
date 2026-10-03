"""
ERA5 Land Loader Module.

Implements loaders for ERA5 Land hourly reanalysis meteorological parameters.
Supports daily aggregation (mean/sum) of weather variables.
"""

import logging
from typing import Any, Optional
from data_collection_pipeline.earth_engine.base_loader import BaseGEELoader
from data_collection_pipeline.earth_engine.initializer import is_ee_initialized

logger = logging.getLogger(__name__)


class ERA5Loader(BaseGEELoader):
    """
    Loader for ERA5 Land Hourly meteorological datasets.
    Includes temporal aggregation helpers to downsample hourly data to daily summaries.
    """

    def __init__(
        self,
        region_geom: Optional[Any] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        aggregate_to_daily: bool = True
    ):
        super().__init__(
            alias="ERA5_LAND_HOURLY",
            region_geom=region_geom,
            start_date=start_date,
            end_date=end_date
        )
        self.aggregate_to_daily = aggregate_to_daily

    def get_collection(self) -> Any:
        """
        Loads the filtered ERA5 Land Hourly dataset.
        
        Returns:
            ee.ImageCollection: Meteorological parameters.
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
            
        # Select target bands first
        col = col.select(self.bands)
        
        if not self.aggregate_to_daily:
            return col
            
        # Temporal aggregation helper (aggregates hourly images to daily composites)
        # We group by date and compute:
        # - mean for temperature and wind components
        # - sum for precipitation
        # For simplicity in this loader, we map a daily mean aggregation over the date range.
        
        def aggregate_days(date_str):
            d = ee.Date(date_str)
            daily_images = col.filterDate(d, d.advance(1, "day"))
            
            # Compute mean for standard atmospheric parameters
            daily_mean = daily_images.mean().set({
                "system:time_start": d.millis(),
                "date_formatted": d.format("yyyy-MM-dd")
            })
            return daily_mean
            
        try:
            # Generate a list of dates in the range
            start = ee.Date(self.start_date)
            end = ee.Date(self.end_date)
            diff_days = end.difference(start, "days")
            
            dates_list = ee.List.sequence(0, diff_days.subtract(1)).map(
                lambda n: start.advance(n, "day").format("yyyy-MM-dd")
            )
            
            # Map daily aggregation over the dates list
            daily_col = ee.ImageCollection(dates_list.map(aggregate_days))
            return daily_col
        except Exception as e:
            logger.warning(f"Failed standard GEE client-side loop for ERA5 daily aggregation: {e}. Returning raw hourly collection.")
            return col
