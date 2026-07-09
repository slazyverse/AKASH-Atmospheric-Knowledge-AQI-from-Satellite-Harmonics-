import logging
import json
from pathlib import Path
from typing import Any, Dict, Tuple, Union

import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, GradientBoostingRegressor
from sklearn.model_selection import GridSearchCV, KFold

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


def optimize_models(X: pd.DataFrame, y: pd.Series) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """Optimizes hyperparameters for selected models."""
    logger.info("Optimizing models: Random Forest, Extra Trees, Gradient Boosting")
    
    n_samples = len(X)
    target_folds = 3
    
    if n_samples < 2:
        logger.error("Dataset too small for cross-validation optimization.")
        raise ValueError(f"Dataset requires at least 2 samples for optimization CV, found {n_samples}.")
        
    cv_splits = min(target_folds, n_samples)
    logger.info(f"Using {cv_splits}-fold CV for optimization.")
    cv = KFold(n_splits=cv_splits, shuffle=True, random_state=42)
    
    if n_samples < 100:
        logger.info("Search strategy selected: Compact Search")
        models_and_grids = {
            "Random Forest Regressor": (
                RandomForestRegressor(random_state=42),
                {"n_estimators": [10, 50], "max_depth": [None, 3, 5]}
            ),
            "Extra Trees Regressor": (
                ExtraTreesRegressor(random_state=42),
                {"n_estimators": [10, 50], "max_depth": [None, 3, 5]}
            ),
            "Gradient Boosting Regressor": (
                GradientBoostingRegressor(random_state=42),
                {"n_estimators": [10, 50], "learning_rate": [0.01, 0.1], "max_depth": [3, 5]}
            )
        }
    else:
        logger.info("Search strategy selected: Expanded Search")
        models_and_grids = {
            "Random Forest Regressor": (
                RandomForestRegressor(random_state=42),
                {
                    "n_estimators": [10, 50, 100], 
                    "max_depth": [None, 3, 5, 10],
                    "min_samples_split": [2, 5],
                    "min_samples_leaf": [1, 2],
                    "max_features": ["sqrt", "log2", None]
                }
            ),
            "Extra Trees Regressor": (
                ExtraTreesRegressor(random_state=42),
                {
                    "n_estimators": [10, 50, 100], 
                    "max_depth": [None, 3, 5, 10],
                    "min_samples_split": [2, 5],
                    "min_samples_leaf": [1, 2],
                    "max_features": ["sqrt", "log2", None]
                }
            ),
            "Gradient Boosting Regressor": (
                GradientBoostingRegressor(random_state=42),
                {
                    "n_estimators": [10, 50, 100], 
                    "learning_rate": [0.01, 0.1, 0.2], 
                    "max_depth": [3, 5, 7],
                    "min_samples_split": [2, 5],
                    "min_samples_leaf": [1, 2],
                    "max_features": ["sqrt", "log2", None]
                }
            )
        }
    
    results = []
    best_parameters = {}
    
    for name, (model, param_grid) in models_and_grids.items():
        logger.info(f"Optimizing {name}...")
        try:
            # Optimize based on negative RMSE
            grid_search = GridSearchCV(
                estimator=model,
                param_grid=param_grid,
                cv=cv,
                scoring="neg_root_mean_squared_error",
                n_jobs=-1
            )
            grid_search.fit(X, y)
            
            best_rmse = -grid_search.best_score_
            best_params = grid_search.best_params_
            
            results.append({
                "Model": name,
                "Best_RMSE": float(best_rmse) if not np.isnan(best_rmse) else np.inf
            })
            best_parameters[name] = best_params
            
        except Exception as e:
            logger.error(f"Optimization failed for {name}: {e}")
            results.append({
                "Model": name,
                "Best_RMSE": np.inf
            })
            best_parameters[name] = {}
            
    results_df = pd.DataFrame(results)
    logger.info("Optimization process completed.")
    return results_df, best_parameters


def rank_optimized_models(results_df: pd.DataFrame) -> pd.DataFrame:
    """Ranks models based on Best_RMSE."""
    logger.info("Ranking optimized models.")
    ranking_df = results_df.copy()
    
    ranking_df["Best_RMSE"] = ranking_df["Best_RMSE"].fillna(np.inf)
    ranking_df["Final_Rank"] = ranking_df["Best_RMSE"].rank(ascending=True, method="min").astype(int)
    
    ranking_df = ranking_df.sort_values(by="Final_Rank", ascending=True).reset_index(drop=True)
    logger.info("Optimized model ranking completed.")
    return ranking_df


def generate_optimization_report(ranking_df: pd.DataFrame, best_params: Dict[str, Any], output_dir: Union[str, Path]) -> None:
    """Generates the optimization reports (CSV, JSON, Markdown)."""
    logger.info(f"Generating optimization reports in {output_dir}")
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # 1. optimization_results.csv
    csv_path = out_path / "optimization_results.csv"
    ranking_df.to_csv(csv_path, index=False)
    
    # 2. best_model_parameters.json
    json_path = out_path / "best_model_parameters.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(best_params, f, indent=4)
        
    # 3. optimization_report.md
    md_path = out_path / "optimization_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Team RAPTORS - Hyperparameter Optimization Report\n\n")
        f.write("## Overview\n")
        f.write("This report details the best hyperparameters found for the evaluated models and their corresponding cross-validated RMSE scores.\n\n")
        
        f.write("## Optimized Model Ranking\n")
        f.write("| Final Rank | Model | Best RMSE (CV) |\n")
        f.write("| :---: | :--- | :---: |\n")
        for _, row in ranking_df.iterrows():
            rmse_val = f"{row['Best_RMSE']:.4f}" if not np.isinf(row['Best_RMSE']) else "inf"
            f.write(f"| {row['Final_Rank']} | **{row['Model']}** | {rmse_val} |\n")
        f.write("\n")
        
        f.write("## Best Parameters\n")
        for _, row in ranking_df.iterrows():
            model_name = row['Model']
            params = best_params.get(model_name, {})
            f.write(f"### {model_name}\n")
            if not params:
                f.write("- Optimization failed or no parameters found.\n")
            else:
                for k, v in params.items():
                    f.write(f"- **{k}**: {v}\n")
            f.write("\n")
            
        best_model = ranking_df.iloc[0]['Model']
        f.write("## Recommendation\n")
        f.write(f"Based on the hyperparameter optimization, the recommended model is **{best_model}**.\n")
        
    logger.info("All optimization reports generated successfully.")


def run_model_optimization(train_path: Union[str, Path], output_dir: Union[str, Path]) -> None:
    """Runs the full model optimization pipeline."""
    target_col = "PM2.5"
    if config and hasattr(config, "REQUIRED_TARGET_COLUMN"):
        target_col = getattr(config, "REQUIRED_TARGET_COLUMN")
        
    df_train = load_training_dataset(train_path)
    
    if target_col not in df_train.columns:
        if "PM2.5" in df_train.columns:
            target_col = "PM2.5"
            
    X = prepare_features(df_train, target_col)
    y = prepare_target(df_train, target_col)
    
    results_df, best_params = optimize_models(X, y)
    ranking_df = rank_optimized_models(results_df)
    generate_optimization_report(ranking_df, best_params, output_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s [%(name)s] - %(message)s")
    workspace_root = Path(__file__).resolve().parent.parent.parent
    run_model_optimization(
        train_path=workspace_root / "train_dataset.csv",
        output_dir=workspace_root
    )
