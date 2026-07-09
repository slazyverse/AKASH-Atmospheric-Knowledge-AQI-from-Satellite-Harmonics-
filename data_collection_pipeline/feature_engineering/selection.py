"""
Feature Selection Utilities.

Provides reusable tools to select feature subsets by group, filter out constant
features (variance threshold), and eliminate collinear redundant features.
"""

import logging
from typing import List, Tuple, Optional
import pandas as pd
import numpy as np
from data_collection_pipeline.feature_engineering.groups import FeatureGroupManager

logger = logging.getLogger(__name__)


class FeatureSelector:
    """Provides methods for preprocessing and pruning feature spaces."""

    @staticmethod
    def select_by_group(
        df: pd.DataFrame,
        groups: List[str],
        keep_metadata: bool = True,
        keep_targets: bool = True
    ) -> pd.DataFrame:
        """
        Subsets the DataFrame columns based on selected feature groups.
        
        Args:
            df: Input DataFrame.
            groups: List of target groups to keep (e.g. ['satellite', 'temporal']).
            keep_metadata: Whether to unconditionally retain metadata features.
            keep_targets: Whether to unconditionally retain target/pollutant features.
            
        Returns:
            DataFrame containing only selected columns.
        """
        columns_to_keep = []
        
        # Determine columns associated with requested groups
        for group in groups:
            columns_to_keep.extend(FeatureGroupManager.get_features_in_group(group))
            
        if keep_metadata:
            columns_to_keep.extend(FeatureGroupManager.get_features_in_group("metadata"))
            
        if keep_targets:
            columns_to_keep.extend(FeatureGroupManager.get_features_in_group("target"))
            
        # Intersect with actual columns present in df
        actual_keep = [col for col in columns_to_keep if col in df.columns]
        
        # Preserve order but make unique
        seen = set()
        unique_keep = [x for x in actual_keep if not (x in seen or seen.add(x))]
        
        logger.info(f"Selected {len(unique_keep)} columns across groups: {groups}")
        return df[unique_keep].copy()

    @staticmethod
    def filter_by_variance(
        df: pd.DataFrame,
        threshold: float = 0.0,
        exclude_columns: Optional[List[str]] = None
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Removes numeric columns with variance strictly less than or equal to the threshold
        (e.g., constant columns).
        
        Args:
            df: Input DataFrame.
            threshold: Minimum variance threshold.
            exclude_columns: List of columns to exclude from variance filtering (e.g., targets).
            
        Returns:
            Tuple of:
              - Filtered DataFrame
              - List of dropped column names
        """
        exclude = exclude_columns or []
        numeric_cols = df.select_dtypes(include=[np.number]).columns
        cols_to_check = [col for col in numeric_cols if col not in exclude]
        
        dropped = []
        for col in cols_to_check:
            var = float(df[col].var(ddof=1))
            if pd.isna(var) or var <= threshold:
                dropped.append(col)
                
        logger.info(f"Variance threshold filtering (var <= {threshold}) dropped {len(dropped)} columns: {dropped}")
        return df.drop(columns=dropped), dropped

    @staticmethod
    def filter_by_correlation(
        df: pd.DataFrame,
        target_column: Optional[str] = None,
        correlation_threshold: float = 0.95,
        exclude_columns: Optional[List[str]] = None
    ) -> Tuple[pd.DataFrame, List[str]]:
        """
        Identifies and removes collinear features by comparing pairwise Pearson
        correlations. If two features are highly correlated, the one with lower
        correlation to the target variable is dropped (if target_column is provided),
        or simply the second feature is dropped.
        
        Args:
            df: Input DataFrame.
            target_column: Optional target variable to break ties.
            correlation_threshold: Pearson correlation limit.
            exclude_columns: List of columns to protect from dropping (e.g., metadata, target).
            
        Returns:
            Tuple of:
              - Filtered DataFrame
              - List of dropped column names
        """
        exclude = exclude_columns or []
        if target_column and target_column not in exclude:
            exclude.append(target_column)
            
        numeric_cols = [
            col for col in df.select_dtypes(include=[np.number]).columns
            if col not in exclude
        ]
        
        if len(numeric_cols) < 2:
            return df.copy(), []
            
        # Compute correlation matrix
        corr_matrix = df[numeric_cols].corr().abs()
        
        # Track correlations to target if available
        target_corr = {}
        if target_column and target_column in df.columns:
            for col in numeric_cols:
                # Compute absolute correlation with target
                c = df[[col, target_column]].corr().iloc[0, 1]
                target_corr[col] = abs(c) if not pd.isna(c) else 0.0
                
        dropped = set()
        
        for i in range(len(numeric_cols)):
            col_i = numeric_cols[i]
            if col_i in dropped:
                continue
                
            for j in range(i + 1, len(numeric_cols)):
                col_j = numeric_cols[j]
                if col_j in dropped:
                    continue
                    
                val = corr_matrix.loc[col_i, col_j]
                if not pd.isna(val) and val >= correlation_threshold:
                    # Resolve tie: keep the one with higher correlation to target
                    if target_column and target_corr:
                        corr_i = target_corr.get(col_i, 0.0)
                        corr_j = target_corr.get(col_j, 0.0)
                        if corr_i >= corr_j:
                            dropped.add(col_j)
                            logger.info(f"Redundant correlation ({val:.3f}) between '{col_i}' and '{col_j}'. Dropping '{col_j}' (lower target correlation).")
                        else:
                            dropped.add(col_i)
                            logger.info(f"Redundant correlation ({val:.3f}) between '{col_i}' and '{col_j}'. Dropping '{col_i}' (lower target correlation).")
                            break  # col_i is dropped, no need to compare it further
                    else:
                        # Default fallback: drop second feature
                        dropped.add(col_j)
                        logger.info(f"Redundant correlation ({val:.3f}) between '{col_i}' and '{col_j}'. Dropping '{col_j}'.")
                        
        dropped_list = list(dropped)
        return df.drop(columns=dropped_list), dropped_list
