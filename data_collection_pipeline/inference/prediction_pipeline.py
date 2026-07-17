import logging
import json
from pathlib import Path
import pandas as pd
import numpy as np
import joblib
from typing import Optional, Union, Tuple
from data_collection_pipeline.config_loader import config_instance
from data_collection_pipeline.feature_engineering import preprocess_target

logger = logging.getLogger(__name__)

def load_model_pipeline(model_path: Union[str, Path]) -> Any:
    """Loads a serialized sklearn Pipeline or model from disk."""
    logger.info(f"Loading model pipeline from {model_path}")
    path = Path(model_path)
    if not path.exists():
        raise FileNotFoundError(f"Model path does not exist: {path}")
    model = joblib.load(path)
    logger.info("Model pipeline loaded successfully.")
    return model

def run_prediction_pipeline(
    dataset_path: Union[str, Path],
    model_path: Union[str, Path],
    output_dir: Union[str, Path],
    target_column: str = "AQI"
) -> Tuple[pd.DataFrame, str]:
    """
    Executes the prediction pipeline.
    Loads data and model, generates predictions, and exports results.
    """
    logger.info(f"Executing prediction pipeline for dataset {dataset_path}")
    
    # 1. Load data
    df = pd.read_csv(dataset_path)
    logger.info(f"Loaded dataset with shape {df.shape}")
    
    # 2. Resolve target if present
    try:
        y, resolved_target = preprocess_target(df)
        df[resolved_target] = y
    except Exception as e:
        logger.warning(f"Could not preprocess target column: {e}. Proceeding without target validation.")
        resolved_target = target_column
        
    # 3. Load model
    model = load_model_pipeline(model_path)
    
    from sklearn.pipeline import Pipeline
    from data_collection_pipeline.feature_engineering import build_preprocessing_pipeline
    from data_collection_pipeline.model_training.lightgbm_model import prepare_training_features
    
    if not isinstance(model, Pipeline):
        logger.info("Loaded model is a raw estimator. Dynamically wrapping it in a Pipeline...")
        _, _, feature_cols = prepare_training_features(df, resolved_target)
        prep_pipeline = build_preprocessing_pipeline(feature_cols)
        preprocessor = prep_pipeline.named_steps["preprocessor"]
        preprocessor.fit(df[feature_cols])
        model = Pipeline(steps=[
            ("preprocessor", preprocessor),
            ("regressor", model)
        ])
        feature_names = feature_cols
    else:
        preprocessor = model.named_steps["preprocessor"]
        feature_names = []
        for name, trans, cols in preprocessor.transformers_:
            feature_names.extend(cols)
            
    logger.info(f"Aligning {len(feature_names)} features for prediction.")
    
    # Verify columns exist
    missing_cols = [col for col in feature_names if col not in df.columns]
    if missing_cols:
        logger.warning(f"Missing feature columns in input dataset: {missing_cols}. Filling with NaNs.")
        for col in missing_cols:
            df[col] = np.nan
            
    X = df[feature_names]
    
    # 5. Run prediction
    logger.info("Executing prediction...")
    # sklearn Pipeline automatically runs transform() on preprocessor, then predict() on regressor
    y_pred = model.predict(X)
    logger.info(f"Generated {len(y_pred)} predictions.")
    
    # 6. Save outputs
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    df["Predicted_Target"] = y_pred
    csv_out = out_dir / "predictions.csv"
    df.to_csv(csv_out, index=False)
    logger.info(f"Exported prediction dataset to {csv_out}")
    
    # Compile execution summary log
    summary = {
        "dataset_path": str(dataset_path),
        "model_path": str(model_path),
        "samples_count": len(df),
        "features_aligned": len(feature_names),
        "mean_prediction": float(np.mean(y_pred)),
        "std_prediction": float(np.std(y_pred)),
        "max_prediction": float(np.max(y_pred)),
        "min_prediction": float(np.min(y_pred))
    }
    
    summary_path = out_dir / "prediction_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4)
    logger.info(f"Saved prediction summary to {summary_path}")
    
    return df, str(csv_out)

from typing import Any
