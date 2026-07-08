"""
Reporting module for the Dataset Builder.
"""

import json
import logging
from typing import Any, Dict

import pandas as pd

logger = logging.getLogger(__name__)

def generate_dataset_summary(df: pd.DataFrame, X: pd.DataFrame, y: pd.Series) -> Dict[str, Any]:
    """Generates a summary of the dataset."""
    logger.info("Generating dataset summary.")
    summary = {
        "total_rows": len(df),
        "total_features": len(X.columns),
        "feature_columns": list(X.columns),
        "target_column": y.name,
        "missing_values_total": int(df.isna().sum().sum()),
    }
    return summary

def generate_feature_statistics(X: pd.DataFrame) -> pd.DataFrame:
    """Generates statistics for the feature matrix."""
    logger.info("Generating feature statistics.")
    # Exclude non-numeric columns for basic statistics or describe all
    stats_df = X.describe(include='all').transpose()
    return stats_df

def generate_quality_report(summary: Dict[str, Any], stats_df: pd.DataFrame) -> str:
    """Generates a markdown quality report for the dataset."""
    logger.info("Generating dataset quality report.")
    
    # Manually generate markdown table to avoid tabulate dependency
    columns = ["Feature"] + list(stats_df.columns)
    header = "| " + " | ".join(str(c) for c in columns) + " |"
    separator = "| " + " | ".join(["---"] * len(columns)) + " |"
    
    rows = []
    for idx, row in stats_df.iterrows():
        row_str = f"| {idx} | " + " | ".join(str(row[c]) for c in stats_df.columns) + " |"
        rows.append(row_str)
        
    md_table = "\n".join([header, separator] + rows)

    report = [
        "# Dataset Quality Report",
        "",
        "## Overview",
        f"- **Total Rows**: {summary.get('total_rows', 0)}",
        f"- **Total Features**: {summary.get('total_features', 0)}",
        f"- **Total Missing Values**: {summary.get('missing_values_total', 0)}",
        "",
        "## Feature Statistics",
        md_table,
        "",
        "## Notes",
        "- Data has been collocated.",
        "- No normalization, scaling, or imputation has been performed.",
        "- No train/test split has been applied."
    ]
    
    return "\n".join(report)
