"""
Feature Selection & Feature Analysis Module.
Analyzes feature correlation, model importance, and generates selection recommendations.
"""

import logging
import os
from pathlib import Path
from typing import Any, List, Optional, Union

import joblib
import numpy as np
import pandas as pd

from data_collection_pipeline import config

logger = logging.getLogger(__name__)


def load_analysis_dataset(file_path: Union[str, Path]) -> pd.DataFrame:
    """
    Loads the analysis ready dataset from a CSV file.

    Args:
        file_path: Path to the CSV file.

    Returns:
        pd.DataFrame: The loaded dataset.
    """
    logger.info(f"Loading analysis dataset from {file_path}")
    try:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found at: {path.resolve()}")
        df = pd.read_csv(path)
        logger.info(f"Successfully loaded dataset with {len(df)} rows and {len(df.columns)} columns.")
        return df
    except Exception as e:
        logger.error(f"Failed to load analysis dataset: {e}")
        raise


def identify_target_column(df: pd.DataFrame, target_name: Optional[str] = None) -> str:
    """
    Identifies and validates the target column in the dataset.

    Args:
        df: The dataset DataFrame.
        target_name: Optional name of the target column. If None, reads from config or defaults to "PM2.5".

    Returns:
        str: The name of the validated target column.
    """
    if target_name is None:
        target_name = getattr(config, "REQUIRED_TARGET_COLUMN", "AQI")

    logger.info(f"Identifying target column. Candidate name: '{target_name}'")
    if target_name not in df.columns:
        logger.warning(f"Target column '{target_name}' not found in dataset columns.")
        # Fallback to PM2.5 if available
        if "PM2.5" in df.columns:
            target_name = "PM2.5"
            logger.info("Falling back to target column: 'PM2.5'")
        else:
            numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
            if numeric_cols:
                target_name = numeric_cols[-1]
                logger.warning(f"Falling back to last numeric column: '{target_name}'")
            else:
                raise ValueError("No numeric columns found in the dataset to use as a target.")
    else:
        logger.info(f"Validated target column: '{target_name}'")

    return target_name


def identify_feature_columns(df: pd.DataFrame, target_column: str) -> List[str]:
    """
    Identifies numeric columns as features, excluding the target column.

    Args:
        df: The dataset DataFrame.
        target_column: The target column name to exclude.

    Returns:
        List[str]: List of feature column names.
    """
    logger.info(f"Identifying feature columns (excluding target: '{target_column}')")
    # Select only numeric columns
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()

    if target_column in numeric_cols:
        numeric_cols.remove(target_column)

    if not numeric_cols:
        raise ValueError("No numeric columns found to be used as features.")

    logger.info(f"Identified {len(numeric_cols)} numeric feature columns.")
    return numeric_cols


def compute_correlation_matrix(df: pd.DataFrame, feature_cols: List[str]) -> pd.DataFrame:
    """
    Computes the Pearson correlation matrix for the specified feature columns.
    Filters out features with zero variance.

    Args:
        df: The dataset DataFrame.
        feature_cols: List of feature column names.

    Returns:
        pd.DataFrame: Correlation matrix.
    """
    logger.info("Computing Pearson correlation matrix for features.")
    try:
        # Pre-process features to check variance: fill missing values with mean, then 0.0
        df_clean = df[feature_cols].copy()
        df_clean = df_clean.fillna(df_clean.mean(numeric_only=True)).fillna(0.0)

        # Detect and remove zero variance features
        variances = df_clean.var(ddof=1)
        zero_var_features = variances[variances == 0.0].index.tolist()
        if zero_var_features:
            logger.warning(f"Excluding zero-variance features from correlation matrix: {zero_var_features}")
            active_features = [col for col in feature_cols if col not in zero_var_features]
            df_clean = df_clean[active_features]
        else:
            active_features = feature_cols

        corr_matrix = df_clean.corr(method="pearson")
        logger.info(f"Successfully computed correlation matrix of size {corr_matrix.shape}")
        return corr_matrix
    except Exception as e:
        logger.error(f"Error computing correlation matrix: {e}")
        raise


def compute_feature_target_correlation(
    df: pd.DataFrame, feature_cols: List[str], target_col: str
) -> pd.Series:
    """
    Computes Pearson correlation coefficients between features and target column.
    Filters out features with zero variance. Validates that the target is numeric.

    Args:
        df: The dataset DataFrame.
        feature_cols: List of feature column names.
        target_col: The target column name.

    Returns:
        pd.Series: Correlation coefficients indexed by feature names.
    """
    logger.info(f"Computing feature-target correlations with target: '{target_col}'")
    
    # Target validation: exists and is numeric
    if target_col not in df.columns:
        raise ValueError(f"Target column '{target_col}' not found in the dataset.")
    if not pd.api.types.is_numeric_dtype(df[target_col]):
        raise ValueError(
            f"Target column '{target_col}' is not numeric (type: {df[target_col].dtype}). "
            f"Feature-target correlation calculation requires a numeric target column."
        )

    try:
        # Check and filter zero variance features
        df_clean_feats = df[feature_cols].copy()
        df_clean_feats = df_clean_feats.fillna(df_clean_feats.mean(numeric_only=True)).fillna(0.0)
        variances = df_clean_feats.var(ddof=1)
        zero_var_features = variances[variances == 0.0].index.tolist()
        
        if zero_var_features:
            logger.warning(f"Excluding zero-variance features from target correlation calculations: {zero_var_features}")
            active_features = [col for col in feature_cols if col not in zero_var_features]
        else:
            active_features = feature_cols

        cols_to_use = active_features + [target_col]
        df_clean = df[cols_to_use].copy()
        df_clean = df_clean.fillna(df_clean.mean(numeric_only=True)).fillna(0.0)

        correlations = df_clean[active_features].corrwith(df_clean[target_col], method="pearson")
        logger.info(f"Successfully computed target correlations for {len(correlations)} features.")
        return correlations
    except Exception as e:
        logger.error(f"Error computing feature-target correlations: {e}")
        raise


def extract_model_feature_importance(model: Any, feature_cols: List[str]) -> pd.Series:
    """
    Extracts the feature importance from a trained model.

    Args:
        model: Trained scikit-learn model.
        feature_cols: List of features to map importance to.

    Returns:
        pd.Series: Feature importances indexed by feature names.
    """
    logger.info("Extracting feature importances from baseline model.")
    try:
        if not hasattr(model, "feature_importances_"):
            raise AttributeError("The model object does not have 'feature_importances_' attribute.")

        importances = model.feature_importances_

        # Map to feature names if model has stored feature_names_in_
        if hasattr(model, "feature_names_in_"):
            model_features = list(model.feature_names_in_)
            importance_dict = dict(zip(model_features, importances))
            mapped_importances = [importance_dict.get(col, 0.0) for col in feature_cols]
        else:
            # Map by index position
            if len(importances) != len(feature_cols):
                logger.warning(
                    f"Model importance length ({len(importances)}) does not match "
                    f"features list length ({len(feature_cols)}). Mapping by position."
                )
                mapped_importances = [0.0] * len(feature_cols)
                for idx, imp in enumerate(importances[: len(feature_cols)]):
                    mapped_importances[idx] = imp
            else:
                mapped_importances = list(importances)

        importance_series = pd.Series(mapped_importances, index=feature_cols)
        logger.info("Successfully extracted and aligned model feature importances.")
        return importance_series
    except Exception as e:
        logger.error(f"Error extracting feature importances: {e}")
        raise


def rank_features(correlation_series: pd.Series, importance_series: pd.Series) -> pd.DataFrame:
    """
    Combines correlation coefficients and model feature importances into a unified feature ranking.

    Args:
        correlation_series: Pearson correlation coefficients with target.
        importance_series: Model feature importances.

    Returns:
        pd.DataFrame: Ranked features with correlation, absolute correlation, importance,
                      individual ranks, combined score, and final rank.
    """
    logger.info("Ranking features using correlation and model importance.")
    try:
        # Align index on features present in the correlation series (which excludes zero-variance features)
        active_features = correlation_series.index

        df_ranking = pd.DataFrame(index=active_features)
        df_ranking["Correlation"] = correlation_series
        df_ranking["Absolute_Correlation"] = df_ranking["Correlation"].abs()
        df_ranking["Importance"] = importance_series.reindex(active_features).fillna(0.0)

        # Rank Absolute Correlation descending (highest abs correlation gets rank 1)
        df_ranking["Correlation_Rank"] = (
            df_ranking["Absolute_Correlation"].rank(ascending=False, method="min").astype(int)
        )

        # Rank Model Importance descending (highest importance gets rank 1)
        df_ranking["Importance_Rank"] = (
            df_ranking["Importance"].rank(ascending=False, method="min").astype(int)
        )

        # Combined score: average rank (lower rank number is better)
        df_ranking["Combined_Score"] = (
            df_ranking["Correlation_Rank"] + df_ranking["Importance_Rank"]
        ) / 2.0

        # Final Rank: rank based on Combined Score ascending (lowest score gets final rank 1)
        df_ranking["Final_Rank"] = (
            df_ranking["Combined_Score"].rank(ascending=True, method="min").astype(int)
        )

        # Clean index and sort
        df_ranking = df_ranking.sort_values(by="Final_Rank", ascending=True)
        df_ranking.reset_index(inplace=True)
        df_ranking.rename(columns={"index": "Feature"}, inplace=True)

        logger.info("Successfully calculated combined feature ranking.")
        return df_ranking
    except Exception as e:
        logger.error(f"Error ranking features: {e}")
        raise


def generate_feature_selection_report(
    correlation_matrix: pd.DataFrame,
    feature_target_corr: pd.Series,
    feature_importance: pd.Series,
    feature_ranking: pd.DataFrame,
    zero_variance_cols: List[str],
    output_dir: Union[str, Path],
) -> None:
    """
    Generates reports:
    1. feature_correlation.csv (Feature-feature correlation matrix)
    2. feature_ranking.csv (Comprehensive ranking details)
    3. feature_selection_report.md (Markdown synthesis and suggestions)

    Args:
        correlation_matrix: Pearson correlation matrix.
        feature_target_corr: Pearson correlation with target.
        feature_importance: Model importances.
        feature_ranking: Final ranked features DataFrame.
        zero_variance_cols: List of zero variance features removed.
        output_dir: Folder to save the report files.
    """
    logger.info("Generating feature selection reports and markdown synthesis.")
    try:
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        # Save CSV files
        corr_csv_path = out_path / "feature_correlation.csv"
        correlation_matrix.to_csv(corr_csv_path)
        logger.info(f"Saved feature correlation matrix to {corr_csv_path}")

        ranking_csv_path = out_path / "feature_ranking.csv"
        feature_ranking.to_csv(ranking_csv_path, index=False)
        logger.info(f"Saved feature ranking to {ranking_csv_path}")

        # Perform collinearity analysis (|correlation| >= 0.8)
        collinear_pairs = []
        features = correlation_matrix.columns.tolist()
        for i in range(len(features)):
            for j in range(i + 1, len(features)):
                f1, f2 = features[i], features[j]
                val = correlation_matrix.loc[f1, f2]
                if abs(val) >= 0.8:
                    collinear_pairs.append((f1, f2, val))

        # Decision logic: build list of features to drop due to collinearity
        dropped_due_to_collinearity = set()
        for f1, f2, val in collinear_pairs:
            r1 = feature_ranking[feature_ranking["Feature"] == f1]["Final_Rank"].values[0]
            r2 = feature_ranking[feature_ranking["Feature"] == f2]["Final_Rank"].values[0]
            keep = f1 if r1 <= r2 else f2
            drop = f2 if keep == f1 else f1
            dropped_due_to_collinearity.add(drop)

        # Create markdown report
        report_md_path = out_path / "feature_selection_report.md"
        with open(report_md_path, "w", encoding="utf-8") as f:
            f.write("# Team RAPTORS - Feature Selection & Feature Analysis Report\n\n")

            f.write("## Overview\n")
            f.write(
                f"This report presents the feature analysis results for the VAYU-DRISHTI model pipeline. "
                f"A total of **{len(features) + len(zero_variance_cols)}** candidate features were analyzed. "
                "The analysis combines statistical Pearson correlation and Random Forest model-based importance "
                "to rank the features and identify redundancies.\n\n"
            )

            # Zero-Variance section
            f.write("## Zero-Variance Feature Filtering\n")
            if zero_variance_cols:
                f.write(
                    f"The following **{len(zero_variance_cols)}** features were detected as having zero variance "
                    "and were excluded from correlation analysis:\n"
                )
                for col in zero_variance_cols:
                    f.write(f"- **{col}**\n")
            else:
                f.write("*No zero-variance features were detected.*\n")
            f.write("\n")

            # Top Feature Rankings
            f.write("## Top Feature Rankings (Combined)\n")
            f.write(
                "Features are ranked using the average of their Correlation Rank (based on absolute correlation with target) "
                "and Model Importance Rank (based on baseline RandomForestRegressor importance).\n\n"
            )
            f.write(
                "| Final Rank | Feature | Correlation | Importance | Corr Rank | Importance Rank | Combined Score |\n"
            )
            f.write(
                "| :---: | :--- | :---: | :---: | :---: | :---: | :---: |\n"
            )
            for _, row in feature_ranking.iterrows():
                f.write(
                    f"| {row['Final_Rank']} | **{row['Feature']}** | {row['Correlation']:.4f} | "
                    f"{row['Importance']:.4f} | {row['Correlation_Rank']} | {row['Importance_Rank']} | {row['Combined_Score']:.1f} |\n"
                )
            f.write("\n")

            # Collinearity analysis section
            f.write("## Collinearity Analysis\n")
            f.write(
                "Strong feature-to-feature correlation (|r| >= 0.80) can introduce redundancy, "
                "increase model variance, and degrade interpretability. The following collinear pairs were identified:\n\n"
            )

            if collinear_pairs:
                f.write("| Feature 1 | Feature 2 | Correlation | Recommendation |\n")
                f.write("| :--- | :--- | :---: | :--- |\n")
                for f1, f2, val in collinear_pairs:
                    r1 = feature_ranking[feature_ranking["Feature"] == f1]["Final_Rank"].values[0]
                    r2 = feature_ranking[feature_ranking["Feature"] == f2]["Final_Rank"].values[0]
                    keep = f1 if r1 <= r2 else f2
                    drop = f2 if keep == f1 else f1
                    f.write(
                        f"| {f1} | {f2} | {val:.4f} | Keep **{keep}** (Rank {min(r1, r2)}), Drop **{drop}** (Rank {max(r1, r2)}) |\n"
                    )
            else:
                f.write("*No highly collinear feature pairs (|r| >= 0.80) were detected in the dataset.*\n")
            f.write("\n")

            # Recommendations section
            f.write("## Feature Selection Recommendations\n")
            f.write(
                "Based on the combined rankings, collinearity analysis, and variance filtering, we recommend the following feature selections:\n\n"
            )
            f.write("### 1. High Priority Features (Keep)\n")
            f.write(
                "These features have both strong correlation with target and high model importance, and are not recommended for drop due to collinearity:\n"
            )
            
            # Use same feature-selection decision logic (exclude dropped_due_to_collinearity)
            top_keepers = feature_ranking[~feature_ranking["Feature"].isin(dropped_due_to_collinearity)].head(5)
            for _, row in top_keepers.iterrows():
                f.write(
                    f"- **{row['Feature']}** (Final Rank {row['Final_Rank']}): Correlation={row['Correlation']:.4f}, Importance={row['Importance']:.4f}\n"
                )
            f.write("\n")

            f.write("### 2. Candidate Features for Removal\n")
            f.write(
                "These features are recommended for removal due to zero variance, low predictive power, or high collinearity (redundancy):\n\n"
            )
            
            # List zero-variance features
            if zero_variance_cols:
                f.write("**Zero-Variance Features:**\n")
                for col in zero_variance_cols:
                    f.write(f"- **{col}** (Removed prior to analysis)\n")
                f.write("\n")
                
            # List collinear drops
            if dropped_due_to_collinearity:
                f.write("**Collinear/Redundant Features (Drop):**\n")
                for col in sorted(list(dropped_due_to_collinearity)):
                    row = feature_ranking[feature_ranking["Feature"] == col].iloc[0]
                    f.write(
                        f"- **{col}** (Final Rank {row['Final_Rank']}): Importance={row['Importance']:.4f}, Correlation={row['Correlation']:.4f}\n"
                    )
                f.write("\n")
                
            # List low performers
            low_performers = feature_ranking[
                (feature_ranking["Importance"] == 0.0) & 
                (feature_ranking["Absolute_Correlation"] < 0.1) & 
                (~feature_ranking["Feature"].isin(dropped_due_to_collinearity))
            ]
            if not low_performers.empty:
                f.write("**Low Importance / Low Correlation Features:**\n")
                for _, row in low_performers.iterrows():
                    f.write(
                        f"- **{row['Feature']}** (Final Rank {row['Final_Rank']}): Importance={row['Importance']:.4f}, Correlation={row['Correlation']:.4f}\n"
                    )
                f.write("\n")

        logger.info(f"Saved feature selection report to {report_md_path}")
    except Exception as e:
        logger.error(f"Error generating reports: {e}")
        raise


def run_feature_selection_pipeline(
    dataset_path: Union[str, Path],
    model_path: Union[str, Path],
    output_dir: Union[str, Path],
) -> None:
    """
    Executes the complete feature selection process.
    """
    logger.info("Executing Day 5A - Feature Selection & Feature Analysis Pipeline")

    # 1. Load dataset
    df = load_analysis_dataset(dataset_path)

    # 2. Identify target
    target_col = identify_target_column(df)

    # 3. Identify features
    feature_cols = identify_feature_columns(df, target_col)

    # 4. Check for zero variance features before computing correlations
    df_clean_feats = df[feature_cols].copy()
    df_clean_feats = df_clean_feats.fillna(df_clean_feats.mean(numeric_only=True)).fillna(0.0)
    variances = df_clean_feats.var(ddof=1)
    zero_variance_cols = variances[variances == 0.0].index.tolist()
    
    if zero_variance_cols:
        logger.warning(f"Detected zero-variance features: {zero_variance_cols}")
        active_features = [col for col in feature_cols if col not in zero_variance_cols]
    else:
        active_features = feature_cols

    # 5. Compute correlation matrix
    corr_matrix = compute_correlation_matrix(df, active_features)

    # 6. Compute feature-target correlations (will validate target is numeric)
    feat_target_corr = compute_feature_target_correlation(df, active_features, target_col)

    # 7. Load baseline model
    logger.info(f"Loading baseline model from {model_path}")
    model = joblib.load(model_path)

    # 8. Extract feature importances
    feat_importance = extract_model_feature_importance(model, active_features)

    # 9. Rank features
    ranking_df = rank_features(feat_target_corr, feat_importance)

    # 10. Generate reports
    generate_feature_selection_report(
        corr_matrix, feat_target_corr, feat_importance, ranking_df, zero_variance_cols, output_dir
    )

    logger.info("Feature Selection & Feature Analysis Pipeline completed successfully.")


if __name__ == "__main__":
    # Standard logger setup for script run
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s [%(name)s] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    workspace_root = Path(__file__).resolve().parent.parent.parent

    # Use default paths relative to workspace root
    default_dataset = workspace_root / "analysis_ready_dataset.csv"
    default_model = workspace_root / "baseline_model.joblib"
    default_out_dir = workspace_root

    logger.info(f"Using default workspace root: {workspace_root}")

    run_feature_selection_pipeline(
        dataset_path=default_dataset,
        model_path=default_model,
        output_dir=default_out_dir,
    )
