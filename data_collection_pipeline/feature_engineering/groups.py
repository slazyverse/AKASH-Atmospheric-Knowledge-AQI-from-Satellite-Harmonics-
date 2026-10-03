"""
Feature Group Management Module.

Provides registry access and queries to categorize features into logical groups
such as satellite, meteorological, geographic, temporal, and metadata.
"""

from typing import Dict, List, Optional
from data_collection_pipeline.feature_engineering.schema import FEATURE_SCHEMA


class FeatureGroupManager:
    """Manages categorization of feature keys into distinct analytical groups."""

    @staticmethod
    def list_groups() -> List[str]:
        """Lists all unique feature groups defined in the schema."""
        groups = set()
        for meta in FEATURE_SCHEMA.values():
            groups.add(meta.group)
        return sorted(list(groups))

    @staticmethod
    def get_features_in_group(group_name: str) -> List[str]:
        """
        Retrieves a list of feature column names belonging to a specific group.
        
        Args:
            group_name: Name of the group (case-insensitive, e.g. 'satellite', 'meteorology').
            
        Returns:
            List of feature names matching the group.
        """
        target_group = group_name.upper()
        matching_features = []
        for name, meta in FEATURE_SCHEMA.items():
            if meta.group == target_group:
                matching_features.append(name)
        return matching_features

    @staticmethod
    def get_group_for_feature(feature_name: str) -> Optional[str]:
        """
        Looks up the group name for a specific feature key.
        
        Args:
            feature_name: The feature column name.
            
        Returns:
            The group name string in uppercase, or None if not found in schema.
        """
        meta = FEATURE_SCHEMA.get(feature_name)
        return meta.group if meta else None

    @staticmethod
    def get_all_feature_names() -> List[str]:
        """Returns a list of all feature names registered in the schema."""
        return list(FEATURE_SCHEMA.keys())
