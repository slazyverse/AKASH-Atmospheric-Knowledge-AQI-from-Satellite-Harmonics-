"""
Preprocessing Module.

Implements unified feature and target preprocessing, imputation, scaling, and
categorical encoding using scikit-learn Pipelines and ColumnTransformers.
"""

import logging
from typing import Any, Dict, List, Tuple
import pandas as pd
import numpy as np
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, OneHotEncoder

from data_collection_pipeline.feature_engineering.schema import FEATURE_SCHEMA
from data_collection_pipeline.feature_engineering.groups import FeatureGroupManager
from data_collection_pipeline.aqi_calculator import calculate_overall_aqi

logger = logging.getLogger(__name__)


def preprocess_target(df: pd.DataFrame) -> Tuple[pd.Series, str]:
    """
    Retrieves or reconstructs the target variable (AQI) from the DataFrame.
    If 'AQI' exists and has valid values, it is returned directly.
    If 'AQI' is missing or fully null, but pollutant concentrations exist,
    reconstructs AQI using the CPCB AQI calculator.
    
    Args:
        df: Input DataFrame.
        
    Returns:
        Tuple of:
          - Target variable Series (non-null)
          - Standard target column name ("AQI")
          
    Raises:
        ValueError: If no target can be found or reconstructed.
    """
    logger.info("Resolving target column AQI...")
    
    # List of recognized CPCB pollutant columns
    pollutants = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "NH3", "Pb"]
    
    # 1. Check if AQI already exists in columns and has non-null values
    if "AQI" in df.columns and df["AQI"].notna().sum() > 0:
        logger.info("Using existing 'AQI' column directly.")
        return df["AQI"], "AQI"
        
    # 2. Check if we can reconstruct AQI from pollutant concentrations
    available_pollutants = [p for p in pollutants if p in df.columns]
    
    if available_pollutants:
        logger.info(f"AQI column missing/empty. Reconstructing AQI from concentrations: {available_pollutants}")
        reconstructed_aqi = []
        
        for idx, row in df.iterrows():
            row_concentrations = {}
            for p in available_pollutants:
                val = row[p]
                if pd.notna(val):
                    row_concentrations[p] = float(val)
                    
            if row_concentrations:
                # Calculate overall AQI (allowing missing requirements since we are reconstructing)
                _, overall_aqi, _ = calculate_overall_aqi(row_concentrations, enforce_requirements=False)
                reconstructed_aqi.append(overall_aqi)
            else:
                reconstructed_aqi.append(np.nan)
                
        aqi_series = pd.Series(reconstructed_aqi, index=df.index, name="AQI")
        if aqi_series.notna().sum() > 0:
            logger.info("Successfully reconstructed AQI target variable.")
            return aqi_series, "AQI"
            
    raise ValueError("Target column 'AQI' is missing/empty, and no valid pollutant concentrations exist to reconstruct it.")


def build_preprocessing_pipeline(feature_cols: List[str]) -> Pipeline:
    """
    Constructs a scikit-learn Pipeline with ColumnTransformer for numeric and
    categorical variables.
    
    Args:
        feature_cols: List of features to include in the pipeline.
        
    Returns:
        sklearn.pipeline.Pipeline containing preprocessors.
    """
    numeric_features = []
    categorical_features = []
    
    for col in feature_cols:
        meta = FEATURE_SCHEMA.get(col)
        if meta:
            if meta.data_type in {"numeric", "boolean"}:
                numeric_features.append(col)
            elif meta.data_type == "categorical":
                categorical_features.append(col)
            else:
                # Default fallback
                numeric_features.append(col)
        else:
            # If not in schema, treat as numeric if type is numeric, otherwise categorical
            numeric_features.append(col)
            
    transformers = []
    
    if numeric_features:
        numeric_transformer = Pipeline(steps=[
            ("imputer", SimpleImputer(strategy="mean")),
            ("scaler", StandardScaler())
        ])
        transformers.append(("num", numeric_transformer, numeric_features))
        logger.info(f"Configured numerical preprocessor for {len(numeric_features)} columns.")
        
    if categorical_features:
        try:
            ohe = OneHotEncoder(handle_unknown="ignore", sparse_output=False)
        except TypeError:
            # Fallback for older scikit-learn versions
            ohe = OneHotEncoder(handle_unknown="ignore", sparse=False)
            
        categorical_transformer = Pipeline(steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", ohe)
        ])
        transformers.append(("cat", categorical_transformer, categorical_features))
        logger.info(f"Configured categorical preprocessor for {len(categorical_features)} columns.")
        
    preprocessor = ColumnTransformer(transformers=transformers)
    
    return Pipeline(steps=[("preprocessor", preprocessor)])
