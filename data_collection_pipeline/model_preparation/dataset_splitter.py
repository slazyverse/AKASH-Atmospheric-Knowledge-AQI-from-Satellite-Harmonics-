"""
ML Dataset Preparation module.
Handles chronological splitting of the analysis ready dataset.
"""

import logging
import json
from pathlib import Path
from typing import Tuple, List, Dict, Any, Union

import pandas as pd

logger = logging.getLogger(__name__)

def load_analysis_dataset(file_path: Union[str, Path]) -> pd.DataFrame:
    """Loads the analysis ready dataset."""
    logger.info(f"Loading dataset from {file_path}")
    df = pd.read_csv(file_path)
    return df

def identify_target_column(df: pd.DataFrame, target_name: str = "AQI") -> str:
    """Identifies and validates the target column."""
    logger.info(f"Validating target column: {target_name}")
    if target_name not in df.columns:
        raise ValueError(f"Target column '{target_name}' not found in the dataset.")
    return target_name

def identify_feature_columns(df: pd.DataFrame, target_name: str = "AQI") -> List[str]:
    """Identifies and validates feature columns."""
    logger.info("Identifying feature columns")
    features = [col for col in df.columns if col != target_name]
    if not features:
        raise ValueError("No feature columns found in the dataset.")
    return features

def remove_invalid_rows(df: pd.DataFrame, target_name: str = "AQI") -> pd.DataFrame:
    """Removes rows with invalid (missing) target values to prevent training issues."""
    logger.info(f"Removing rows with missing target values ({target_name})")
    initial_len = len(df)
    df_clean = df.dropna(subset=[target_name]).copy()
    dropped = initial_len - len(df_clean)
    if dropped > 0:
        logger.info(f"Removed {dropped} rows with missing target values.")
    return df_clean

def chronological_split(
    df: pd.DataFrame, 
    train_ratio: float = 0.70, 
    val_ratio: float = 0.15, 
    test_ratio: float = 0.15,
    date_col: str = "Date",
    time_col: str = "Time"
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, Dict[str, Any]]:
    """
    Splits the dataset chronologically into Train, Validation, and Test sets.
    Preserves chronological order and prevents data leakage.
    """
    logger.info(f"Performing chronological split: Train={train_ratio}, Val={val_ratio}, Test={test_ratio}")
    
    # Verify ratios sum to 1.0 (approximately)
    total_ratio = train_ratio + val_ratio + test_ratio
    if not (0.99 <= total_ratio <= 1.01):
        raise ValueError(f"Split ratios must sum to 1.0. Got {total_ratio}")

    # Ensure dataset is sorted chronologically
    df_sorted = df.copy()
    if date_col in df_sorted.columns and time_col in df_sorted.columns:
        df_sorted["_datetime_temp"] = pd.to_datetime(df_sorted[date_col].astype(str) + " " + df_sorted[time_col].astype(str))
        df_sorted.sort_values(by="_datetime_temp", inplace=True)
        df_sorted.drop(columns=["_datetime_temp"], inplace=True)
    elif date_col in df_sorted.columns:
        df_sorted["_datetime_temp"] = pd.to_datetime(df_sorted[date_col].astype(str))
        df_sorted.sort_values(by="_datetime_temp", inplace=True)
        df_sorted.drop(columns=["_datetime_temp"], inplace=True)
    else:
        logger.warning(f"Could not find '{date_col}' and '{time_col}' columns for sorting. Relying on existing index order.")
        
    n_total = len(df_sorted)
    n_train = int(n_total * train_ratio)
    n_val = int(n_total * val_ratio)
    
    train_df = df_sorted.iloc[:n_train].copy()
    val_df = df_sorted.iloc[n_train:n_train+n_val].copy()
    test_df = df_sorted.iloc[n_train+n_val:].copy()
    
    # Log statistics
    logger.info(f"Split complete. Train: {len(train_df)}, Val: {len(val_df)}, Test: {len(test_df)}")
    
    summary = {
        "total_rows": n_total,
        "train_rows": len(train_df),
        "validation_rows": len(val_df),
        "test_rows": len(test_df),
        "train_ratio_actual": len(train_df) / n_total if n_total > 0 else 0,
        "validation_ratio_actual": len(val_df) / n_total if n_total > 0 else 0,
        "test_ratio_actual": len(test_df) / n_total if n_total > 0 else 0
    }
    
    return train_df, val_df, test_df, summary

def export_datasets(
    train_df: pd.DataFrame, 
    val_df: pd.DataFrame, 
    test_df: pd.DataFrame, 
    summary: Dict[str, Any],
    output_dir: Union[str, Path]
) -> None:
    """Exports the split datasets and the split summary."""
    logger.info(f"Exporting datasets to {output_dir}")
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    train_df.to_csv(out_path / "train_dataset.csv", index=False)
    val_df.to_csv(out_path / "validation_dataset.csv", index=False)
    test_df.to_csv(out_path / "test_dataset.csv", index=False)
    
    with open(out_path / "dataset_split_summary.json", "w") as f:
        json.dump(summary, f, indent=4)
