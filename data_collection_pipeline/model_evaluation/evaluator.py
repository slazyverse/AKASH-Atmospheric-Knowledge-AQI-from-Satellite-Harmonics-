"""
Model Evaluation Module.
"""

import logging
import json
from pathlib import Path
from typing import Dict, Any, Union, List

import pandas as pd
import numpy as np
import joblib
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
from sklearn.ensemble import RandomForestRegressor

logger = logging.getLogger(__name__)

def load_trained_model(model_path: Union[str, Path]) -> RandomForestRegressor:
    """Loads a trained model from disk."""
    logger.info(f"Loading trained model from {model_path}")
    model = joblib.load(model_path)
    return model

def load_validation_dataset(file_path: Union[str, Path]) -> pd.DataFrame:
    """Loads the validation dataset."""
    logger.info(f"Loading validation dataset from {file_path}")
    return pd.read_csv(file_path)

def generate_predictions(model: RandomForestRegressor, X: pd.DataFrame) -> np.ndarray:
    """Generates predictions using the provided model and features."""
    logger.info("Generating predictions...")
    return model.predict(X)

def calculate_regression_metrics(y_true: pd.Series, y_pred: np.ndarray) -> Dict[str, float]:
    """Calculates regression metrics (RMSE, MAE, R2)."""
    logger.info("Calculating regression metrics...")
    mse = mean_squared_error(y_true, y_pred)
    rmse = float(np.sqrt(mse))
    mae = float(mean_absolute_error(y_true, y_pred))
    r2 = float(r2_score(y_true, y_pred))
    
    metrics = {
        "RMSE": rmse,
        "MAE": mae,
        "R2_Score": r2
    }
    logger.info(f"Metrics calculated: {metrics}")
    return metrics

def calculate_feature_importance(model: Any, feature_cols: List[str]) -> pd.DataFrame:
    """Calculates feature importance from the model."""
    logger.info("Extracting feature importance...")
    
    if hasattr(model, "steps"):  # sklearn Pipeline
        preprocessor = model.named_steps.get("preprocessor")
        regressor = model.named_steps.get("regressor")
        
        if preprocessor is not None and regressor is not None:
            # Extract feature names in order
            feature_names = []
            for name, trans, cols in preprocessor.transformers_:
                feature_names.extend(cols)
            
            importances = regressor.feature_importances_
            
            # Map clean names and importances
            importances_dict = {}
            for fname, imp in zip(feature_names, importances):
                clean_name = fname.split("__")[-1] if "__" in fname else fname
                importances_dict[clean_name] = float(imp)
            
            df_importance = pd.DataFrame(
                list(importances_dict.items()),
                columns=["Feature", "Importance"]
            ).sort_values(by="Importance", ascending=False)
            return df_importance

    if hasattr(model, "feature_importances_"):
        importances = model.feature_importances_
    else:
        raise ValueError("Model does not have feature_importances_ attribute.")
        
    df_importance = pd.DataFrame({
        "Feature": feature_cols,
        "Importance": importances
    }).sort_values(by="Importance", ascending=False)
    
    return df_importance

def generate_evaluation_report(
    metrics: Dict[str, float], 
    feature_importance_df: pd.DataFrame,
    output_dir: Union[str, Path]
) -> None:
    """Generates evaluation artifacts: metrics JSON, feature importance CSV, and a markdown report."""
    logger.info("Generating evaluation report...")
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # Save metrics JSON
    metrics_path = out_path / "evaluation_metrics.json"
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=4)
        
    # Save feature importance CSV
    importance_path = out_path / "feature_importance.csv"
    feature_importance_df.to_csv(importance_path, index=False)
        
    # Save report Markdown
    report_path = out_path / "evaluation_report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Model Evaluation Report\n\n")
        f.write("## Regression Metrics\n")
        f.write(f"- **RMSE:** {metrics['RMSE']:.4f}\n")
        f.write(f"- **MAE:** {metrics['MAE']:.4f}\n")
        
        r2_val = metrics['R2_Score']
        if np.isnan(r2_val):
            r2_display = "N/A (Single Sample)"
        else:
            r2_display = f"{r2_val:.4f}"
            
        f.write(f"- **R² Score:** {r2_display}\n\n")
        f.write("## Top 10 Feature Importances\n")
        f.write("| Feature | Importance |\n")
        f.write("| :--- | :--- |\n")
        for _, row in feature_importance_df.head(10).iterrows():
            f.write(f"| {row['Feature']} | {row['Importance']:.4f} |\n")
        f.write("\n")
        
    logger.info("Evaluation report generated successfully.")
