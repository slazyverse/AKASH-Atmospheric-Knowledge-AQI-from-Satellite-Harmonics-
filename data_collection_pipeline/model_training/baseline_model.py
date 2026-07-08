"""
Baseline Model Training module.
"""

import logging
import json
from pathlib import Path
from typing import Tuple, List, Dict, Any, Union

import pandas as pd
import joblib
from sklearn.ensemble import RandomForestRegressor

from data_collection_pipeline import config

logger = logging.getLogger(__name__)

def load_training_data(file_path: Union[str, Path]) -> pd.DataFrame:
    """Loads the training dataset."""
    logger.info(f"Loading training data from {file_path}")
    return pd.read_csv(file_path)

def select_target_column(df: pd.DataFrame) -> str:
    """Selects the target column based on the configuration."""
    target = getattr(config, "REQUIRED_TARGET_COLUMN", "AQI")
    
    if target not in df.columns:
        logger.warning(f"Target column '{target}' not found. Falling back to 'PM2.5' if available.")
        target = "PM2.5" if "PM2.5" in df.columns else df.select_dtypes(include=['number']).columns[-1]
        
    logger.info(f"Selected target column: {target}")
    return target

def prepare_training_features(df: pd.DataFrame, target_col: str) -> Tuple[pd.DataFrame, pd.Series, List[str]]:
    """Prepares the training features and target vector."""
    logger.info("Preparing training features.")
    
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in training dataset.")
        
    df_clean = df.dropna(subset=[target_col]).copy()
    y = df_clean[target_col]
    X_raw = df_clean.drop(columns=[target_col])
    
    # Select only numeric columns for features
    X = X_raw.select_dtypes(include=['number'])
    
    # Handle missing values in features to prevent sklearn errors
    X = X.fillna(X.mean(numeric_only=True)).fillna(0.0)
    
    feature_cols = list(X.columns)
    logger.info(f"Prepared {len(feature_cols)} numeric features for training.")
    return X, y, feature_cols

def train_baseline_model(X: pd.DataFrame, y: pd.Series) -> RandomForestRegressor:
    """Trains a baseline RandomForestRegressor model."""
    logger.info("Training baseline model (RandomForestRegressor) with random_state=42...")
    model = RandomForestRegressor(random_state=42)
    model.fit(X, y)
    logger.info("Training completion.")
    return model

def save_trained_model(
    model: RandomForestRegressor, 
    summary: Dict[str, Any],
    output_dir: Union[str, Path]
) -> None:
    """Saves the trained model and the training summary."""
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    model_path = out_path / "baseline_model.joblib"
    joblib.dump(model, model_path)
    logger.info(f"Saved trained model to {model_path}")
    
    summary_path = out_path / "training_summary.json"
    if hasattr(model, "feature_names_in_"):
        summary["feature_columns"] = list(model.feature_names_in_)
        
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=4)
    logger.info(f"Saved training summary to {summary_path}")
