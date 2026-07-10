"""
Dataset Builder module.

Builds the final analysis-ready dataset from the collocated feature table.
Enforces that the configured AQI target column is present, non-null, and
fully propagated — raising a descriptive ValueError if it is not.
"""

import logging
import datetime
from pathlib import Path
from typing import Tuple, Optional, Union

import pandas as pd

from data_collection_pipeline import config
from data_collection_pipeline.dataset_preparation.collocation import collocate_dataset

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Target column stage tracker
# ---------------------------------------------------------------------------

def _check_target_at_stage(
    df: pd.DataFrame,
    target_col: str,
    stage_name: str,
) -> dict:
    """
    Checks the target column in a dataframe at a named pipeline stage.
    Returns a dict with 'present', 'non_null', 'total', 'null_count' keys.
    Emits a structured INFO log entry.
    """
    present = target_col in df.columns
    total = len(df)
    if present:
        null_count = int(df[target_col].isna().sum())
        non_null = total - null_count
    else:
        null_count = 0
        non_null = 0

    if present:
        logger.info(
            "[TARGET COLUMN] Stage='%s' | column='%s' | present=True | "
            "total=%d | non-null=%d | null=%d",
            stage_name, target_col, total, non_null, null_count,
        )
    else:
        logger.warning(
            "[TARGET COLUMN] Stage='%s' | column='%s' | present=False | "
            "total=%d — target column is MISSING at this stage.",
            stage_name, target_col, total,
        )

    return {
        "stage": stage_name,
        "present": present,
        "total": total,
        "non_null": non_null,
        "null_count": null_count,
    }


# ---------------------------------------------------------------------------
# Core dataset operations
# ---------------------------------------------------------------------------

def validate_dataset_schema(df: pd.DataFrame) -> bool:
    """Validates the schema of the dataset."""
    logger.info("Validating dataset schema.")
    required_cols = ["Station ID", "Date", "Time", "Latitude", "Longitude"]
    for col in required_cols:
        if col not in df.columns:
            logger.error(f"Missing required column: {col}")
            return False
    return True


def prepare_feature_matrix(df: pd.DataFrame, target_col: str = "AQI") -> pd.DataFrame:
    """Extracts features from the collocated dataset without modification."""
    logger.info("Preparing feature matrix (target column '%s' will be excluded).", target_col)
    if target_col in df.columns:
        return df.drop(columns=[target_col]).copy()
    return df.copy()


def prepare_target_vector(df: pd.DataFrame, target_col: str = "AQI") -> pd.Series:
    """Extracts the target vector from the dataset without modification."""
    logger.info("Preparing target vector for column '%s'.", target_col)
    if target_col in df.columns:
        return df[target_col].copy()
    logger.warning(f"Target column '{target_col}' not found. Returning empty Series.")
    return pd.Series(dtype=float, name=target_col)


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------

def _write_validation_report(
    target_col: str,
    source_dataset: str,
    stage_checks: list,
    total_records: int,
    null_count: int,
    validation_status: str,
    warnings_list: list,
) -> None:
    """Writes the target column validation report to the project root."""
    report_path = config.BASE_DIR.parent / "target_column_validation_report.md"
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Build stage table
    stage_rows = []
    for check in stage_checks:
        present_str = "✅ Yes" if check["present"] else "❌ No"
        stage_rows.append(
            f"| {check['stage']} | {present_str} | "
            f"{check['total']} | {check['null_count']} |"
        )
    stage_table = "\n".join(stage_rows)

    warnings_section = (
        "\n".join(f"* ⚠️  {w}" for w in warnings_list)
        if warnings_list
        else "* None"
    )

    overall_icon = "✅ PASS" if validation_status == "PASS" else "❌ FAIL"

    report_content = f"""# Target Column Validation Report

> Generated: {timestamp}

## Configuration
| Key | Value |
|-----|-------|
| **Configured Target Column** | `{target_col}` |
| **Source Dataset** | `{source_dataset}` |

## Intermediate Pipeline Stages Checked
| Stage | Target Column Present | Total Records | Null Count |
|-------|-----------------------|---------------|------------|
{stage_table}

## Final Dataset Metrics
| Metric | Value |
|--------|-------|
| **Total Records** | {total_records} |
| **Null Count in Target** | {null_count} |
| **Non-Null Count** | {total_records - null_count} |
| **Null Percentage** | {(null_count / total_records * 100):.1f}% |

## Validation Result
**Overall Status: {overall_icon}**

## Warnings
{warnings_section}

## Final Summary
{"The configured target column `" + target_col + "` was successfully detected in the source CPCB dataset and propagated unchanged through all intermediate pipeline stages (feature engineering merge, build_features, apply_missing_strategy, collocation) into the final `analysis_ready_dataset.csv`. Validation PASSED." if validation_status == "PASS" else "Validation FAILED. The configured target column `" + target_col + "` was not found or contains only null values in the final collocated dataset. Review the pipeline stages above for the first stage at which the column goes missing."}
"""
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        logger.info("[TARGET COLUMN] Validation report written to: %s", report_path)
    except OSError as e:
        logger.error("[TARGET COLUMN] Failed to write validation report: %s", e)


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------

def build_analysis_dataset(
    file_path: Optional[Union[str, Path]] = None,
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series]:
    """
    Builds the final analysis-ready dataset.

    Reads the Day 3 merged feature table through the collocation pipeline,
    validates and propagates the configured target column unchanged, then
    returns (collocated_df, X, y).

    Raises:
        ValueError: If the configured target column is missing from the
            collocated dataset or contains only null values.
    """
    logger.info("Building analysis dataset.")

    # Retrieve configured target column dynamically
    target_col = getattr(config, "REQUIRED_TARGET_COLUMN", "AQI")
    source_dataset = "merged_feature_table.csv → analysis_ready_dataset.csv"
    cpcb_source = str(config.PROCESSED_DATA_DIR / "cpcb_cleaned_latest.csv")

    logger.info(
        "[TARGET COLUMN] Configured target column: '%s' | Source: %s",
        target_col, cpcb_source,
    )

    stage_checks = []

    # ------------------------------------------------------------------
    # Step 1: Run collocation pipeline (reads merged_feature_table.csv)
    # ------------------------------------------------------------------
    collocated_df, collocation_summary = collocate_dataset(file_path=file_path)

    # Stage 1: after collocation
    stage_checks.append(
        _check_target_at_stage(collocated_df, target_col, "collocation (collocate_dataset)")
    )

    # ------------------------------------------------------------------
    # Step 2: Schema validation
    # ------------------------------------------------------------------
    is_valid = validate_dataset_schema(collocated_df)
    if not is_valid:
        logger.warning("Dataset schema validation failed.")

    # Stage 2: after schema validation (no mutation, just a logged check)
    stage_checks.append(
        _check_target_at_stage(collocated_df, target_col, "schema_validation")
    )

    # ------------------------------------------------------------------
    # Step 3: Pre-save validation — target column must be present
    # ------------------------------------------------------------------
    if target_col not in collocated_df.columns:
        # Write FAIL report
        _write_validation_report(
            target_col=target_col,
            source_dataset=source_dataset,
            stage_checks=stage_checks,
            total_records=len(collocated_df),
            null_count=0,
            validation_status="FAIL",
            warnings_list=[
                f"Target column '{target_col}' is missing from the collocated dataset.",
                "Check that merger.py includes the target column in output_columns.",
            ],
        )
        raise ValueError(
            f"Configured target column '{target_col}' is missing from the collocated "
            "dataset. Verify that it is carried forward from the raw CPCB observations "
            "through the merge stage in feature_engineering/merger.py. "
            f"The merged_feature_table.csv must contain '{target_col}'."
        )

    # ------------------------------------------------------------------
    # Step 4: Pre-save validation — target column must have non-null values
    # ------------------------------------------------------------------
    null_count = int(collocated_df[target_col].isna().sum())
    total_records = len(collocated_df)
    non_null_count = total_records - null_count

    warnings_list = []
    if non_null_count == 0:
        warn_msg = (
            f"Target column '{target_col}' is present but contains only null values "
            f"(100% missing across {total_records} records)."
        )
        logger.warning("[TARGET COLUMN] %s", warn_msg)
        warnings_list.append(warn_msg)

    validation_status = "PASS" if non_null_count > 0 else "FAIL"

    logger.info(
        "[TARGET COLUMN] Pre-save validation: '%s' present=True | "
        "total=%d | non-null=%d | null=%d | status=%s",
        target_col, total_records, non_null_count, null_count, validation_status,
    )

    # Stage 3: after pre-save validation
    stage_checks.append(
        _check_target_at_stage(collocated_df, target_col, "pre_save_validation")
    )

    # Write the validation report
    _write_validation_report(
        target_col=target_col,
        source_dataset=source_dataset,
        stage_checks=stage_checks,
        total_records=total_records,
        null_count=null_count,
        validation_status=validation_status,
        warnings_list=warnings_list,
    )

    if validation_status == "FAIL":
        raise ValueError(
            f"Configured target column '{target_col}' contains only null values "
            f"({total_records} records, 0 non-null). The target values must be "
            "present and non-null in the CPCB source dataset."
        )

    logger.info(
        "[TARGET COLUMN] Validation PASSED. '%s' is present with %d non-null values "
        "across %d records. Propagation successful.",
        target_col, non_null_count, total_records,
    )

    # ------------------------------------------------------------------
    # Step 5: Extract feature matrix and target vector
    # ------------------------------------------------------------------
    X = prepare_feature_matrix(collocated_df, target_col=target_col)
    y = prepare_target_vector(collocated_df, target_col=target_col)

    return collocated_df, X, y
