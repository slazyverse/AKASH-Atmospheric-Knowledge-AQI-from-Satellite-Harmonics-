import logging
import json
from pathlib import Path
from typing import Any, Dict, Union, Tuple

import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestRegressor

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False

try:
    from data_collection_pipeline import config
except ImportError:
    config = None

logger = logging.getLogger(__name__)


def load_training_dataset(file_path: Union[str, Path]) -> pd.DataFrame:
    """Loads the training dataset."""
    logger.info(f"Loading training dataset from {file_path}")
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Training dataset not found: {path}")
    df = pd.read_csv(path)
    logger.info(f"Loaded training dataset with shape {df.shape}")
    return df


def prepare_features(df: pd.DataFrame, target_column: str) -> pd.DataFrame:
    """Prepares numerical features."""
    logger.info(f"Preparing features (excluding target '{target_column}')")
    numeric_df = df.select_dtypes(include=["number"]).copy()
    if target_column in numeric_df.columns:
        numeric_df = numeric_df.drop(columns=[target_column])
    numeric_df = numeric_df.fillna(numeric_df.mean(numeric_only=True)).fillna(0.0)
    logger.info(f"Prepared features shape: {numeric_df.shape}")
    return numeric_df


def prepare_target(df: pd.DataFrame, target_column: str) -> pd.Series:
    """Prepares the target variable."""
    logger.info(f"Preparing target '{target_column}'")
    if target_column not in df.columns:
        raise ValueError(f"Target column '{target_column}' not found in dataset.")
    y = df[target_column].copy()
    y = y.fillna(y.mean()).fillna(0.0)
    logger.info(f"Prepared target shape: {y.shape}")
    return y


def load_production_model(workspace_dir: Union[str, Path]) -> Any:
    """Loads the serialized production model."""
    logger.info("Loading serialized production model.")
    model_path = Path(workspace_dir) / "production_model.joblib"
    
    if not model_path.exists():
        logger.error(f"Production model not found at {model_path}")
        raise FileNotFoundError(f"Missing {model_path}")
        
    model = joblib.load(model_path)
    logger.info(f"Loaded production model from {model_path}")
    return model


def generate_global_feature_importance(model: Any, X: pd.DataFrame) -> pd.DataFrame:
    """Generates global feature importance."""
    logger.info("Generating global feature importance.")
    
    importances = []
    
    if SHAP_AVAILABLE:
        try:
            logger.info("Using SHAP for global feature importance.")
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X)
            # Global importance is the mean absolute SHAP value for each feature
            mean_abs_shap = np.mean(np.abs(shap_values), axis=0)
            
            for i, col in enumerate(X.columns):
                importances.append({
                    "Feature": col,
                    "Importance": float(mean_abs_shap[i]),
                    "Method": "SHAP_Mean_Absolute"
                })
        except Exception as e:
            logger.warning(f"SHAP global importance failed: {e}. Falling back to feature_importances_.")
            SHAP_AVAILABLE_FOR_LOCAL = False # Disable for local if global failed
    
    if not importances:
        logger.info("Using model's built-in feature_importances_ for global importance.")
        if hasattr(model, "feature_importances_"):
            fi = model.feature_importances_
            for i, col in enumerate(X.columns):
                importances.append({
                    "Feature": col,
                    "Importance": float(fi[i]),
                    "Method": "Built_in_Feature_Importance"
                })
        else:
            logger.warning("Model does not have feature_importances_. Returning empty.")
            
    imp_df = pd.DataFrame(importances)
    if not imp_df.empty:
        imp_df = imp_df.sort_values(by="Importance", ascending=False).reset_index(drop=True)
        
    return imp_df


def generate_local_feature_explanations(model: Any, X: pd.DataFrame) -> pd.DataFrame:
    """Generates local feature explanations for a sample of the dataset."""
    logger.info("Generating local feature explanations.")
    
    # We'll generate local explanations for the first 5 samples to keep it manageable
    sample_X = X.head(5)
    local_exp = []
    
    if SHAP_AVAILABLE:
        try:
            logger.info("Using SHAP for local feature explanations.")
            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(sample_X)
            
            for sample_idx in range(len(sample_X)):
                for feature_idx, col in enumerate(X.columns):
                    local_exp.append({
                        "Sample_Index": sample_idx,
                        "Feature": col,
                        "Feature_Value": float(sample_X.iloc[sample_idx, feature_idx]),
                        "Contribution": float(shap_values[sample_idx, feature_idx]),
                        "Method": "SHAP_Value"
                    })
        except Exception as e:
            logger.warning(f"SHAP local explanation failed: {e}. Falling back to pseudo-local explanation.")
            local_exp = []
            
    if not local_exp:
        logger.info("Using pseudo-local explanations based on global feature_importances_.")
        if hasattr(model, "feature_importances_"):
            fi = model.feature_importances_
            
            # Normalize feature importance to use as a proxy for local impact
            if np.sum(fi) > 0:
                norm_fi = fi / np.sum(fi)
            else:
                norm_fi = fi
                
            for sample_idx in range(len(sample_X)):
                for feature_idx, col in enumerate(X.columns):
                    local_exp.append({
                        "Sample_Index": sample_idx,
                        "Feature": col,
                        "Feature_Value": float(sample_X.iloc[sample_idx, feature_idx]),
                        "Contribution": float(norm_fi[feature_idx]),
                        "Method": "Pseudo_Local_Global_Importance"
                    })
                    
    return pd.DataFrame(local_exp)


def generate_explainability_report(
    global_df: pd.DataFrame, 
    local_df: pd.DataFrame, 
    output_dir: Union[str, Path]
) -> None:
    """Generates the model explainability reports."""
    logger.info(f"Generating explainability reports in {output_dir}")
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # 1. feature_importance_detailed.csv
    csv_path = out_path / "feature_importance_detailed.csv"
    if not global_df.empty:
        global_df.to_csv(csv_path, index=False)
        
    # 2. local_feature_explanations.csv
    local_csv_path = out_path / "local_feature_explanations.csv"
    if not local_df.empty:
        local_df.to_csv(local_csv_path, index=False)
        
    # 3. model_explainability_report.md
    md_path = out_path / "model_explainability_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Team RAPTORS - Model Explainability Report\n\n")
        f.write("## Overview\n")
        f.write("This report provides global feature importances and local explanations for the selected production model.\n\n")
        
        f.write("## Global Feature Importance\n")
        f.write("The following features are ranked by their overall impact on the model's predictions.\n\n")
        f.write("| Rank | Feature | Importance | Method |\n")
        f.write("| :---: | :--- | :---: | :--- |\n")
        if not global_df.empty:
            for idx, row in global_df.iterrows():
                f.write(f"| {idx + 1} | **{row['Feature']}** | {row['Importance']:.4f} | {row['Method']} |\n")
        else:
            f.write("| - | No data available | - | - |\n")
        f.write("\n")
        
        f.write("## Local Feature Explanations (Sample)\n")
        f.write("The following details the specific feature contributions for the first data sample.\n\n")
        f.write("| Feature | Value | Contribution | Method |\n")
        f.write("| :--- | :---: | :---: | :--- |\n")
        
        if not local_df.empty:
            sample_0_df = local_df[local_df['Sample_Index'] == 0].sort_values(by="Contribution", key=abs, ascending=False)
            # Display top 10 contributing features for sample 0
            for _, row in sample_0_df.head(10).iterrows():
                f.write(f"| **{row['Feature']}** | {row['Feature_Value']:.4f} | {row['Contribution']:.4f} | {row['Method']} |\n")
        else:
            f.write("| No data available | - | - | - |\n")
        f.write("\n")
        
    logger.info("All explainability reports generated successfully.")


def run_model_explainability(workspace_dir: Union[str, Path]) -> None:
    """Executes the complete model explainability pipeline."""
    logger.info("Starting model explainability pipeline.")
    
    target_col = "PM2.5"
    if config and hasattr(config, "REQUIRED_TARGET_COLUMN"):
        target_col = getattr(config, "REQUIRED_TARGET_COLUMN")
        
    train_path = Path(workspace_dir) / "train_dataset.csv"
    df_train = load_training_dataset(train_path)
    
    if target_col not in df_train.columns:
        if "PM2.5" in df_train.columns:
            target_col = "PM2.5"
            
    X = prepare_features(df_train, target_col)
    
    model = load_production_model(workspace_dir)
    
    global_df = generate_global_feature_importance(model, X)
    local_df = generate_local_feature_explanations(model, X)
    
    generate_explainability_report(global_df, local_df, workspace_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s [%(name)s] - %(message)s")
    workspace_root = Path(__file__).resolve().parent.parent.parent
    run_model_explainability(workspace_dir=workspace_root)
