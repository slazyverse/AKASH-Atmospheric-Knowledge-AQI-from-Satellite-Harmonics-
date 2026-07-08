"""Configurable temporal alignment helpers."""

from __future__ import annotations

from typing import Iterable

import pandas as pd

SUPPORTED_TEMPORAL_STRATEGIES = {"nearest", "hourly", "daily_average"}


def ensure_datetime(series: pd.Series) -> pd.Series:
    """Parse a series into timezone-tolerant pandas timestamps."""
    return pd.to_datetime(series, errors="coerce", format="mixed")


def add_temporal_keys(df: pd.DataFrame, timestamp_column: str) -> pd.DataFrame:
    """Add date, hour, and daily keys used for alignment."""
    keyed = df.copy()
    keyed["timestamp"] = ensure_datetime(keyed[timestamp_column])
    keyed["Date"] = keyed["timestamp"].dt.date.astype("string")
    keyed["Time"] = keyed["timestamp"].dt.time.astype("string")
    keyed["hour_timestamp"] = keyed["timestamp"].dt.floor("h")
    keyed["daily_timestamp"] = keyed["timestamp"].dt.floor("D")
    return keyed


def align_grid_temporally(
    observations: pd.DataFrame,
    grid: pd.DataFrame,
    feature_columns: Iterable[str],
    strategy: str,
    grid_time_column: str = "timestamp",
) -> pd.DataFrame:
    """Align grid feature rows to observation timestamps."""
    if strategy not in SUPPORTED_TEMPORAL_STRATEGIES:
        raise ValueError(f"Unsupported temporal alignment strategy: {strategy}")
    if grid.empty or grid_time_column not in grid.columns:
        return observations

    aligned = observations.copy()
    grid_copy = grid.copy()
    grid_copy[grid_time_column] = ensure_datetime(grid_copy[grid_time_column])

    if strategy == "daily_average":
        grid_copy["daily_timestamp"] = grid_copy[grid_time_column].dt.floor("D")
        daily = grid_copy.groupby("daily_timestamp", as_index=False)[list(feature_columns)].mean()
        return aligned.merge(daily, on="daily_timestamp", how="left")

    if strategy == "hourly":
        grid_copy["hour_timestamp"] = grid_copy[grid_time_column].dt.floor("h")
        hourly = grid_copy.groupby("hour_timestamp", as_index=False)[list(feature_columns)].mean()
        return aligned.merge(hourly, on="hour_timestamp", how="left")

    sorted_obs = aligned.sort_values("timestamp")
    sorted_grid = grid_copy.dropna(subset=[grid_time_column]).sort_values(grid_time_column)
    if sorted_grid.empty:
        return aligned

    nearest = pd.merge_asof(
        sorted_obs,
        sorted_grid[[grid_time_column, *feature_columns]],
        left_on="timestamp",
        right_on=grid_time_column,
        direction="nearest",
    )
    return nearest.sort_index()
