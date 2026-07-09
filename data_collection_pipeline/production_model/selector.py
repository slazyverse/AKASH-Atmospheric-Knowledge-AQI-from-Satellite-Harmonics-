import logging
import json
from pathlib import Path
from typing import Any, Dict, Union

import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def load_model_comparison_results(workspace_dir: Union[str, Path]) -> pd.DataFrame:
    """Loads model_comparison.csv."""
    path = Path(workspace_dir) / "model_comparison.csv"
    logger.info(f"Loading {path}")
    if not path.exists():
        logger.warning(f"{path} not found. Returning empty DataFrame.")
        return pd.DataFrame()
    return pd.read_csv(path)


def load_cross_validation_results(workspace_dir: Union[str, Path]) -> pd.DataFrame:
    """Loads cross_validation_results.csv."""
    path = Path(workspace_dir) / "cross_validation_results.csv"
    logger.info(f"Loading {path}")
    if not path.exists():
        logger.warning(f"{path} not found. Returning empty DataFrame.")
        return pd.DataFrame()
    return pd.read_csv(path)


def load_optimization_results(workspace_dir: Union[str, Path]) -> pd.DataFrame:
    """Loads optimization_results.csv."""
    path = Path(workspace_dir) / "optimization_results.csv"
    logger.info(f"Loading {path}")
    if not path.exists():
        logger.warning(f"{path} not found. Returning empty DataFrame.")
        return pd.DataFrame()
    return pd.read_csv(path)


def score_candidate_models(
    comparison_df: pd.DataFrame, 
    cv_df: pd.DataFrame, 
    opt_df: pd.DataFrame
) -> pd.DataFrame:
    """Scores candidate models based on performance across all stages using an adaptive weighted composite score."""
    logger.info("Scoring candidate models using weighted composite score.")
    
    # Extract unique models across all dataframes
    all_models = set()
    if not comparison_df.empty and 'Model' in comparison_df.columns:
        all_models.update(comparison_df['Model'].unique())
    if not opt_df.empty and 'Model' in opt_df.columns:
        all_models.update(opt_df['Model'].unique())
        
    scores = []
    
    for model in all_models:
        baseline_rmse = np.inf
        cv_rmse_mean = np.inf
        opt_rmse = np.inf
        
        # 1. Baseline Performance
        if not comparison_df.empty and 'Model' in comparison_df.columns and 'RMSE' in comparison_df.columns:
            m_comp = comparison_df[comparison_df['Model'] == model]
            if not m_comp.empty:
                baseline_rmse = m_comp.iloc[0]['RMSE']
                
        # 2. Cross Validation Stability
        if not cv_df.empty and 'Model' in cv_df.columns and 'RMSE' in cv_df.columns:
            m_cv = cv_df[cv_df['Model'] == model]
            if not m_cv.empty:
                cv_rmse_mean = m_cv['RMSE'].replace([np.inf, -np.inf], np.nan).mean()
                if np.isnan(cv_rmse_mean):
                    cv_rmse_mean = np.inf
                    
        # 3. Optimized Performance
        if not opt_df.empty and 'Model' in opt_df.columns and 'Best_RMSE' in opt_df.columns:
            m_opt = opt_df[opt_df['Model'] == model]
            if not m_opt.empty:
                opt_rmse = m_opt.iloc[0]['Best_RMSE']
                
        # Adaptive weighted composite score
        weights = {
            "Baseline": 0.20,
            "CV": 0.40,
            "Optimized": 0.40
        }
        
        valid_metrics = {}
        if not np.isinf(baseline_rmse) and not pd.isna(baseline_rmse):
            valid_metrics["Baseline"] = float(baseline_rmse)
        if not np.isinf(cv_rmse_mean) and not pd.isna(cv_rmse_mean):
            valid_metrics["CV"] = float(cv_rmse_mean)
        if not np.isinf(opt_rmse) and not pd.isna(opt_rmse):
            valid_metrics["Optimized"] = float(opt_rmse)
            
        applied_weights = {"Baseline": 0.0, "CV": 0.0, "Optimized": 0.0}
        
        if valid_metrics:
            total_valid_weight = sum(weights[k] for k in valid_metrics.keys())
            composite_score = 0.0
            
            for k in valid_metrics.keys():
                normalized_weight = weights[k] / total_valid_weight
                applied_weights[k] = normalized_weight
                composite_score += valid_metrics[k] * normalized_weight
        else:
            composite_score = np.inf
            
        scores.append({
            "Model": model,
            "Baseline_RMSE": float(baseline_rmse) if not np.isinf(baseline_rmse) else None,
            "CV_RMSE_Mean": float(cv_rmse_mean) if not np.isinf(cv_rmse_mean) else None,
            "Optimized_RMSE": float(opt_rmse) if not np.isinf(opt_rmse) else None,
            "Composite_Score": float(composite_score) if not np.isinf(composite_score) else None,
            "Weight_Baseline": applied_weights["Baseline"],
            "Weight_CV": applied_weights["CV"],
            "Weight_Optimized": applied_weights["Optimized"]
        })
        
    scores_df = pd.DataFrame(scores)
    
    # Sort and rank
    if not scores_df.empty:
        temp_score = scores_df["Composite_Score"].fillna(np.inf)
        scores_df["Final_Rank"] = temp_score.rank(method="min", ascending=True).astype(int)
        scores_df = scores_df.sort_values(by="Final_Rank", ascending=True).reset_index(drop=True)
        
    logger.info("Candidate scoring completed.")
    return scores_df


def select_production_model(scores_df: pd.DataFrame) -> Dict[str, Any]:
    """Selects the best model for production based on scores."""
    logger.info("Selecting production model.")
    if scores_df.empty:
        logger.error("No models available to select from.")
        return {}
        
    # The first row is the top ranked model
    best_row = scores_df.iloc[0]
    
    summary = {
        "Selected_Model": best_row["Model"],
        "Final_Rank": int(best_row["Final_Rank"]),
        "Performance_Metrics": {
            "Composite_Score": best_row["Composite_Score"],
            "Baseline_RMSE": best_row["Baseline_RMSE"],
            "CV_RMSE_Mean": best_row["CV_RMSE_Mean"],
            "Optimized_RMSE": best_row["Optimized_RMSE"]
        },
        "Applied_Weights": {
            "Baseline": best_row["Weight_Baseline"],
            "CV": best_row["Weight_CV"],
            "Optimized": best_row["Weight_Optimized"]
        },
        "Selection_Criteria": "Adaptive weighted composite score of available RMSE metrics."
    }
    
    logger.info(f"Selected {best_row['Model']} as production model with score {best_row['Composite_Score']:.4f}.")
    return summary


def generate_model_selection_report(scores_df: pd.DataFrame, summary: Dict[str, Any], output_dir: Union[str, Path]) -> None:
    """Generates the selection outputs: JSON and Markdown."""
    logger.info(f"Generating production model selection reports in {output_dir}")
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # 1. production_model_summary.json
    json_path = out_path / "production_model_summary.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=4)
        
    # 2. production_model_report.md
    md_path = out_path / "production_model_report.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("# Team RAPTORS - Production Model Selection Report\n\n")
        f.write("## Overview\n")
        f.write("This report details the final candidate models, their performance across evaluation stages, and the ultimate selection for production deployment.\n\n")
        
        selected_model = summary.get("Selected_Model", "Unknown")
        composite_score = summary.get('Performance_Metrics', {}).get('Composite_Score', 'N/A')
        
        # Handle string "N/A" formatting safely
        if isinstance(composite_score, (int, float)):
            comp_str = f"{composite_score:.4f}"
        else:
            comp_str = str(composite_score)
            
        f.write(f"### Selected Production Model: **{selected_model}**\n")
        f.write(f"**Final Composite Score**: {comp_str}\n\n")
        
        f.write(f"**Selection Criteria**: {summary.get('Selection_Criteria', 'N/A')}\n\n")
        
        f.write("## Candidate Model Scores\n")
        f.write("| Final Rank | Model | Composite Score | Baseline RMSE | CV Mean RMSE | Optimized RMSE | Weights (Base/CV/Opt) |\n")
        f.write("| :---: | :--- | :---: | :---: | :---: | :---: | :---: |\n")
        for _, row in scores_df.iterrows():
            comp = f"{row['Composite_Score']:.4f}" if pd.notnull(row['Composite_Score']) else "N/A"
            base = f"{row['Baseline_RMSE']:.4f}" if pd.notnull(row['Baseline_RMSE']) else "N/A"
            cv = f"{row['CV_RMSE_Mean']:.4f}" if pd.notnull(row['CV_RMSE_Mean']) else "N/A"
            opt = f"{row['Optimized_RMSE']:.4f}" if pd.notnull(row['Optimized_RMSE']) else "N/A"
            weights_str = f"{row['Weight_Baseline']:.2f} / {row['Weight_CV']:.2f} / {row['Weight_Optimized']:.2f}"
            
            f.write(f"| {row['Final_Rank']} | **{row['Model']}** | {comp} | {base} | {cv} | {opt} | {weights_str} |\n")
        f.write("\n")
        
    logger.info("All selection reports generated successfully.")


def run_production_model_selection(workspace_dir: Union[str, Path]) -> None:
    """Executes the complete production model selection pipeline."""
    logger.info("Starting production model selection pipeline.")
    
    comp_df = load_model_comparison_results(workspace_dir)
    cv_df = load_cross_validation_results(workspace_dir)
    opt_df = load_optimization_results(workspace_dir)
    
    scores_df = score_candidate_models(comp_df, cv_df, opt_df)
    summary = select_production_model(scores_df)
    generate_model_selection_report(scores_df, summary, workspace_dir)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s [%(name)s] - %(message)s")
    workspace_root = Path(__file__).resolve().parent.parent.parent
    run_production_model_selection(workspace_dir=workspace_root)
