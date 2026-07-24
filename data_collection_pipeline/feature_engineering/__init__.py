"""
Feature engineering and dataset integration package.
"""

from data_collection_pipeline.feature_engineering.merger import run_integration_pipeline
from data_collection_pipeline.feature_engineering.schema import FeatureMetadata, FEATURE_SCHEMA
from data_collection_pipeline.feature_engineering.groups import FeatureGroupManager
from data_collection_pipeline.feature_engineering.validation import FeatureValidator
from data_collection_pipeline.feature_engineering.selection import FeatureSelector
from data_collection_pipeline.feature_engineering.preprocessing import (
    preprocess_target,
    build_preprocessing_pipeline
)
from data_collection_pipeline.pbl_feature_engine import PBL_FEATURES, compute_pbl_features

__all__ = [
    "run_integration_pipeline",
    "FeatureMetadata",
    "FEATURE_SCHEMA",
    "FeatureGroupManager",
    "FeatureValidator",
    "FeatureSelector",
    "preprocess_target",
    "build_preprocessing_pipeline",
    "PBL_FEATURES",
    "compute_pbl_features",
]
