"""
Feature Validation Module.

Implements structure, datatype, and value range checks on merged feature tables
before they are passed downstream to model training or inference steps.
"""

import logging
from typing import Any, Dict, List
import pandas as pd
import numpy as np
from data_collection_pipeline.feature_engineering.schema import FEATURE_SCHEMA

logger = logging.getLogger(__name__)


class FeatureValidator:
    """Validates Pandas DataFrames against the registered FEATURE_SCHEMA rules."""

    def __init__(self, schema: Dict[str, Any] = FEATURE_SCHEMA):
        self.schema = schema

    def validate_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """
        Performs full validations on a pandas DataFrame:
        - Schema completeness (missing expected columns)
        - Data type consistency
        - Out-of-bounds/Range violations
        - Missing percentages
        
        Args:
            df: DataFrame to validate.
            
        Returns:
            Dict containing detailed validation metrics, warnings, and pass/fail status.
        """
        logger.info("Executing feature validation checks on dataset...")
        
        total_rows = len(df)
        missing_columns: List[str] = []
        out_of_bounds_counts: Dict[str, int] = {}
        missing_percentages: Dict[str, float] = {}
        type_mismatches: List[str] = []
        warnings: List[str] = []
        
        if total_rows == 0:
            warnings.append("DataFrame is empty. Validation succeeded with zero rows.")
            return {
                "status": "PASSED",
                "total_rows": 0,
                "missing_columns": [],
                "warnings": warnings,
                "range_violations": {},
                "missing_percentages": {}
            }

        # Check each feature registered in the schema
        for name, meta in self.schema.items():
            if name not in df.columns:
                missing_columns.append(name)
                continue
                
            col_data = df[name]
            
            # Compute missing percentage
            null_count = int(col_data.isna().sum())
            missing_pct = round((null_count / total_rows) * 100.0, 2)
            missing_percentages[name] = missing_pct
            
            # Validate types and ranges (skip nulls)
            non_nulls = col_data.dropna()
            
            if meta.data_type == 'numeric':
                # Try converting to numeric
                try:
                    numeric_vals = pd.to_numeric(non_nulls, errors='raise')
                    if meta.valid_range:
                        lo, hi = meta.valid_range
                        violations = ((numeric_vals < lo) | (numeric_vals > hi)).sum()
                        if violations > 0:
                            out_of_bounds_counts[name] = int(violations)
                            warnings.append(
                                f"Feature '{name}' has {violations} values out of range [{lo}, {hi}]."
                            )
                except (ValueError, TypeError):
                    type_mismatches.append(name)
                    warnings.append(f"Feature '{name}' contains non-numeric values but is typed as numeric.")
                    
            elif meta.data_type == 'boolean':
                # Check boolean values
                invalid_bool = non_nulls.apply(
                    lambda x: not (isinstance(x, bool) or str(x).lower() in {'true', 'false', '0', '1', '0.0', '1.0'})
                ).sum()
                if invalid_bool > 0:
                    type_mismatches.append(name)
                    warnings.append(f"Feature '{name}' has {invalid_bool} values violating boolean constraints.")
                    
        status = "PASSED"
        if len(type_mismatches) > 0:
            status = "FAILED"
            
        report = {
            "status": status,
            "total_rows": total_rows,
            "missing_columns": missing_columns,
            "warnings": warnings,
            "range_violations": out_of_bounds_counts,
            "type_mismatches": type_mismatches,
            "missing_percentages": missing_percentages
        }
        
        logger.info(f"Feature validation completed with status: {status}")
        return report
