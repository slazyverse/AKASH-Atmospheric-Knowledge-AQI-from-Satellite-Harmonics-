"""
Google Earth Engine Data Pipeline Package.

Exposes initializer utilities, dataset catalogs, spatial grid systems,
modular dataset loaders, and cloud export hooks.
"""

from data_collection_pipeline.earth_engine.initializer import (
    initialize_ee,
    is_ee_initialized
)
from data_collection_pipeline.earth_engine.validator import (
    validate_gee_startup,
    GeeValidationResult
)
from data_collection_pipeline.earth_engine.dataset_catalog import (
    DatasetCatalog,
    DatasetMetadata
)
from data_collection_pipeline.earth_engine.analysis_grid import (
    AnalysisGrid
)
from data_collection_pipeline.earth_engine.base_loader import (
    BaseGEELoader
)
from data_collection_pipeline.earth_engine.tropomi import (
    TROPOMILoader
)
from data_collection_pipeline.earth_engine.modis import (
    MODISAODLoader
)
from data_collection_pipeline.earth_engine.era5 import (
    ERA5Loader
)
from data_collection_pipeline.earth_engine.viirs import (
    VIIRSFireLoader
)
from data_collection_pipeline.earth_engine.export import (
    export_image_to_drive,
    export_image_to_asset,
    export_image_to_cloud_storage
)
from data_collection_pipeline.earth_engine.utils import (
    CloudMaskStrategy,
    bbox_to_ee_geometry,
    geojson_to_ee_geometry
)

__all__ = [
    "initialize_ee",
    "is_ee_initialized",
    "validate_gee_startup",
    "GeeValidationResult",
    "DatasetCatalog",
    "DatasetMetadata",
    "AnalysisGrid",
    "BaseGEELoader",
    "TROPOMILoader",
    "MODISAODLoader",
    "ERA5Loader",
    "VIIRSFireLoader",
    "export_image_to_drive",
    "export_image_to_asset",
    "export_image_to_cloud_storage",
    "CloudMaskStrategy",
    "bbox_to_ee_geometry",
    "geojson_to_ee_geometry",
]
