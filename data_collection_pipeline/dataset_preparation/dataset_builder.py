"""
Dataset Builder module.
"""

import logging
from pathlib import Path
from typing import Tuple, Optional, Union

import pandas as pd

from data_collection_pipeline.dataset_preparation.collocation import collocate_dataset

logger = logging.getLogger(__name__)

def validate_dataset_schema(df: pd.DataFrame) -> bool:
    """Validates the schema of the dataset."""
    logger.info("Validating dataset schema.")
    required_cols = ["Station ID", "Date", "Time", "Latitude", "Longitude"]
    for col in required_cols:
        if col not in df.columns:
            logger.error(f"Missing required column: {col}")
            return False
    return True

def prepare_feature_matrix(df: pd.DataFrame, target_col: str = "AQI") -> pd.DataFrame:
    """Extracts features from the collocated dataset without modification."""
    logger.info("Preparing feature matrix.")
    if target_col in df.columns:
        return df.drop(columns=[target_col]).copy()
    return df.copy()

def prepare_target_vector(df: pd.DataFrame, target_col: str = "AQI") -> pd.Series:
    """Extracts the target vector from the dataset without modification."""
    logger.info("Preparing target vector.")
    if target_col in df.columns:
        return df[target_col].copy()
    logger.warning(f"Target column '{target_col}' not found. Returning empty Series.")
    return pd.Series(dtype=float, name=target_col)

def build_analysis_dataset(
    file_path: Optional[Union[str, Path]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """
    Builds the final analysis-ready dataset.
    Uses collocated data, extracts features and targets.
    Does not perform scaling, imputation, or train/test splits.
    """
    logger.info("Building analysis dataset.")
    collocated_df, _ = collocate_dataset(file_path=file_path)
    
    is_valid = validate_dataset_schema(collocated_df)
    if not is_valid:
        logger.warning("Dataset schema validation failed.")
    
    X = prepare_feature_matrix(collocated_df)
    y = prepare_target_vector(collocated_df)
        
    return collocated_df, X, y
