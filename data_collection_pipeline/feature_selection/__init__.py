"""
Feature Selection and Analysis Module for Team RAPTORS.
"""

from data_collection_pipeline.feature_selection.selector import (
    load_analysis_dataset,
    identify_feature_columns,
    identify_target_column,
    compute_correlation_matrix,
    compute_feature_target_correlation,
    extract_model_feature_importance,
    rank_features,
    generate_feature_selection_report,
)

__all__ = [
    "load_analysis_dataset",
    "identify_feature_columns",
    "identify_target_column",
    "compute_correlation_matrix",
    "compute_feature_target_correlation",
    "extract_model_feature_importance",
    "rank_features",
    "generate_feature_selection_report",
]
