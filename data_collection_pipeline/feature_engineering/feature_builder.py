"""Feature construction and missing-value handling."""

from __future__ import annotations

import math
from typing import Iterable

import pandas as pd

POLLUTANT_FEATURES = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]
METEOROLOGY_FEATURES = [
    "Temperature",
    "Relative Humidity",
    "Boundary Layer Height",
    "Wind Speed",
    "Wind Direction",
    "Surface Pressure",
]
SATELLITE_FEATURES = [
    "AOD",
    "HCHO",
    "NO2 Column",
    "SO2 Column",
    "CO Column",
    "O3 Column",
]
DERIVED_FEATURES = ["Day of Week", "Month", "Season", "Weekend Flag"]
ALL_FEATURES = POLLUTANT_FEATURES + METEOROLOGY_FEATURES + SATELLITE_FEATURES + DERIVED_FEATURES
SUPPORTED_MISSING_STRATEGIES = {"interpolation", "forward_fill", "station_median", "leave_missing"}


def wind_speed(u_component: object, v_component: object) -> object:
    """Calculate wind speed from U/V components when both are available."""
    u_value = pd.to_numeric(pd.Series([u_component]), errors="coerce").iloc[0]
    v_value = pd.to_numeric(pd.Series([v_component]), errors="coerce").iloc[0]
    if pd.isna(u_value) or pd.isna(v_value):
        return pd.NA
    return math.sqrt(float(u_value) ** 2 + float(v_value) ** 2)


def wind_direction(u_component: object, v_component: object) -> object:
    """Calculate meteorological wind direction in degrees from U/V components."""
    u_value = pd.to_numeric(pd.Series([u_component]), errors="coerce").iloc[0]
    v_value = pd.to_numeric(pd.Series([v_component]), errors="coerce").iloc[0]
    if pd.isna(u_value) or pd.isna(v_value):
        return pd.NA
    return (math.degrees(math.atan2(float(u_value), float(v_value))) + 360.0) % 360.0


def season_from_month(month: object) -> object:
    """Return an India-oriented meteorological season label."""
    if pd.isna(month):
        return pd.NA
    month_value = int(month)
    if month_value in {12, 1, 2}:
        return "Winter"
    if month_value in {3, 4, 5}:
        return "Pre-Monsoon"
    if month_value in {6, 7, 8, 9}:
        return "Monsoon"
    return "Post-Monsoon"


def build_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create derived features and ensure all expected ML-ready columns exist."""
    features = df.copy()

    if "u_wind_component" in features.columns and "v_wind_component" in features.columns:
        features["Wind Speed"] = features.apply(
            lambda row: wind_speed(row.get("u_wind_component"), row.get("v_wind_component")),
            axis=1,
        )
        features["Wind Direction"] = features.apply(
            lambda row: wind_direction(row.get("u_wind_component"), row.get("v_wind_component")),
            axis=1,
        )

    features["Day of Week"] = features["timestamp"].dt.dayofweek
    features["Month"] = features["timestamp"].dt.month
    features["Season"] = features["Month"].map(season_from_month)
    features["Weekend Flag"] = features["Day of Week"].isin([5, 6])

    for column in ALL_FEATURES:
        if column not in features.columns:
            features[column] = pd.NA

    return features


def apply_missing_strategy(
    df: pd.DataFrame,
    strategy: str,
    feature_columns: Iterable[str],
) -> pd.DataFrame:
    """Apply configured missing-value handling without dropping rows."""
    if strategy not in SUPPORTED_MISSING_STRATEGIES:
        raise ValueError(f"Unsupported missing value strategy: {strategy}")
    if strategy == "leave_missing":
        return df

    handled = df.copy()
    columns = [column for column in feature_columns if column in handled.columns]
    numeric_columns = [
        column
        for column in columns
        if pd.api.types.is_numeric_dtype(pd.to_numeric(handled[column], errors="coerce").dtype)
    ]

    if strategy == "interpolation":
        handled[numeric_columns] = handled.groupby("Station ID")[numeric_columns].transform(
            lambda group: group.interpolate(limit_direction="both")
        )
        return handled

    if strategy == "forward_fill":
        handled[columns] = handled.groupby("Station ID", group_keys=False)[columns].ffill()
        return handled

    medians = handled.groupby("Station ID")[numeric_columns].transform("median")
    handled[numeric_columns] = handled[numeric_columns].fillna(medians)
    return handled
