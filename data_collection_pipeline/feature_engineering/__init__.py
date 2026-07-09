"""
Feature engineering and dataset integration package.
"""

from data_collection_pipeline.feature_engineering.merger import run_integration_pipeline
from data_collection_pipeline.feature_engineering.schema import FeatureMetadata, FEATURE_SCHEMA
from data_collection_pipeline.feature_engineering.groups import FeatureGroupManager
from data_collection_pipeline.feature_engineering.validation import FeatureValidator
from data_collection_pipeline.feature_engineering.selection import FeatureSelector

__all__ = [
    "run_integration_pipeline",
    "FeatureMetadata",
    "FEATURE_SCHEMA",
    "FeatureGroupManager",
    "FeatureValidator",
    "FeatureSelector",
]
