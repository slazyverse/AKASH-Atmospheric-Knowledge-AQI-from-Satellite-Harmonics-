"""
Earth Engine Dataset Catalog.

Centralizes dataset identifier strings, resolution profiles, band names,
and metadata properties for Sentinel-5P, MODIS, ERA5, and VIIRS.
"""

from typing import Any, Dict, List, Optional


class DatasetMetadata:
    """Dataclass holding metadata definition for a GEE Collection."""

    def __init__(
        self,
        collection_id: str,
        name: str,
        bands: List[str],
        resolution_meters: float,
        projection: str = "EPSG:4326",
        version: str = "1.0",
        description: str = ""
    ):
        self.collection_id = collection_id
        self.name = name
        self.bands = bands
        self.resolution_meters = resolution_meters
        self.projection = projection
        self.version = version
        self.description = description


# Centralized catalog matching key datasets from the pipeline specification
DATASET_CATALOG: Dict[str, DatasetMetadata] = {
    "TROPOMI_HCHO": DatasetMetadata(
        collection_id="COPERNICUS/S5P/OFFL/L3_HCHO",
        name="Sentinel-5P TROPOMI HCHO Column",
        bands=["HCHO_tropospheric_column_amount", "HCHO_tropospheric_column_amount_uncertainty"],
        resolution_meters=5500.0,
        description="Formaldehyde (HCHO) tropospheric column density."
    ),
    "TROPOMI_NO2": DatasetMetadata(
        collection_id="COPERNICUS/S5P/OFFL/L3_NO2",
        name="Sentinel-5P TROPOMI NO2 Column",
        bands=["NO2_column_number_density", "tropospheric_NO2_column_number_density"],
        resolution_meters=5500.0,
        description="Nitrogen Dioxide (NO2) column number density."
    ),
    "TROPOMI_SO2": DatasetMetadata(
        collection_id="COPERNICUS/S5P/OFFL/L3_SO2",
        name="Sentinel-5P TROPOMI SO2 Column",
        bands=["SO2_column_number_density"],
        resolution_meters=5500.0,
        description="Sulfur Dioxide (SO2) column number density."
    ),
    "TROPOMI_CO": DatasetMetadata(
        collection_id="COPERNICUS/S5P/OFFL/L3_CO",
        name="Sentinel-5P TROPOMI CO Column",
        bands=["CO_column_number_density"],
        resolution_meters=5500.0,
        description="Carbon Monoxide (CO) column number density."
    ),
    "TROPOMI_O3": DatasetMetadata(
        collection_id="COPERNICUS/S5P/OFFL/L3_O3",
        name="Sentinel-5P TROPOMI O3 Column",
        bands=["O3_column_number_density"],
        resolution_meters=5500.0,
        description="Ozone (O3) column number density."
    ),
    "MODIS_MAIAC_AOD": DatasetMetadata(
        collection_id="MODIS/061/MCD19A2_GRANULES",
        name="MODIS MAIAC daily AOD at 1km",
        bands=["Optical_Depth_047", "Optical_Depth_055", "AOD_QA"],
        resolution_meters=1000.0,
        description="MODIS Multi-Angle Implementation of Atmospheric Correction (MAIAC) Aerosol Optical Depth."
    ),
    "ERA5_LAND_HOURLY": DatasetMetadata(
        collection_id="ECMWF/ERA5_LAND/HOURLY",
        name="ERA5 Land Hourly Reanalysis",
        bands=["temperature_2m", "u_component_of_wind_10m", "v_component_of_wind_10m", "total_precipitation_hourly"],
        resolution_meters=11132.0,  # ~0.1 arc-degrees
        description="ERA5-Land hourly reanalysis meteorological parameters."
    ),
    "VIIRS_ACTIVE_FIRE": DatasetMetadata(
        collection_id="NASA/LANCE/SNPP_VIIRS/C2",
        name="VIIRS active fire / thermal anomalies",
        bands=["T21", "confidence", "fire"],
        resolution_meters=375.0,
        description="VIIRS near real-time active fire anomalies derived from Suomi NPP satellite."
    )
}


class DatasetCatalog:
    """Accessor class to lookup metadata from the centralized GEE dataset catalog."""

    @staticmethod
    def get(alias: str) -> Optional[DatasetMetadata]:
        """Looks up a dataset by its shorthand alias."""
        return DATASET_CATALOG.get(alias.upper(), None)

    @staticmethod
    def list_aliases() -> List[str]:
        """Lists all registered dataset aliases."""
        return list(DATASET_CATALOG.keys())
