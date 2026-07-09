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
    
    # Retrieve configured target column dynamically
    from data_collection_pipeline import config
    target_col = getattr(config, "REQUIRED_TARGET_COLUMN", "AQI")
    
    # Verify the target column exists
    target_found = "Yes" if target_col in collocated_df.columns else "No"
    if target_col not in collocated_df.columns:
        # Generate failure report first
        report_path = config.BASE_DIR.parent / "target_column_validation_report.md"
        report_content = f"""# Target Column Validation Report

## Configuration
* **Configured Target Column:** `{target_col}`
* **Source Dataset:** `analysis_ready_dataset.csv`

## Validation Metrics
* **Target Column Found:** No
* **Null Count:** 0
* **Total Records:** {len(collocated_df)}
* **Validation Result:** FAIL

## Warnings Encountered
* Target column '{target_col}' was missing from the dataset.
"""
        try:
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report_content)
        except OSError as e:
            logger.error(f"Failed to write target column validation report: {e}")
            
        raise ValueError(
            f"Configured target column '{target_col}' is missing from the collocated dataset. "
            "Verify that it is carried forward from the raw observations through the merge stage."
        )
        
    # Verify target column contains non-null values
    null_count = collocated_df[target_col].isna().sum()
    total_records = len(collocated_df)
    non_null_count = total_records - null_count
    
    warnings_list = []
    if non_null_count == 0:
        warn_msg = f"Target column '{target_col}' is present but contains only null values (100% missing)."
        logger.warning(warn_msg)
        warnings_list.append(warn_msg)
        
    validation_status = "PASS" if non_null_count > 0 else "FAIL"
    
    # Generate validation report
    report_path = config.BASE_DIR.parent / "target_column_validation_report.md"
    report_content = f"""# Target Column Validation Report

## Configuration
* **Configured Target Column:** `{target_col}`
* **Source Dataset:** `analysis_ready_dataset.csv`

## Validation Metrics
* **Target Column Found:** Yes
* **Null Count:** {null_count}
* **Total Records:** {total_records}
* **Validation Result:** {validation_status}

## Warnings Encountered
{chr(10).join(f"* {w}" for w in warnings_list) if warnings_list else "* None"}
"""
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        logger.info(f"Generated target column validation report at {report_path}")
    except OSError as e:
        logger.error(f"Failed to write target column validation report: {e}")
        
    X = prepare_feature_matrix(collocated_df, target_col=target_col)
    y = prepare_target_vector(collocated_df, target_col=target_col)
        
    return collocated_df, X, y
