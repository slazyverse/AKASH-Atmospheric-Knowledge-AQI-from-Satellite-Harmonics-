"""Nearest-neighbour spatial matching utilities."""

from __future__ import annotations

import math
from typing import Iterable, Optional

import pandas as pd

EARTH_RADIUS_KM = 6371.0088


def haversine_distance_km(
    latitude_a: float,
    longitude_a: float,
    latitude_b: float,
    longitude_b: float,
) -> float:
    """Return great-circle distance between two coordinate pairs."""
    lat_a = math.radians(latitude_a)
    lon_a = math.radians(longitude_a)
    lat_b = math.radians(latitude_b)
    lon_b = math.radians(longitude_b)

    delta_lat = lat_b - lat_a
    delta_lon = lon_b - lon_a
    haversine = (
        math.sin(delta_lat / 2.0) ** 2
        + math.cos(lat_a) * math.cos(lat_b) * math.sin(delta_lon / 2.0) ** 2
    )
    return 2.0 * EARTH_RADIUS_KM * math.asin(math.sqrt(haversine))


def _valid_coordinate(value: object) -> bool:
    return pd.notna(pd.to_numeric(pd.Series([value]), errors="coerce").iloc[0])


def nearest_grid_row(
    latitude: object,
    longitude: object,
    grid: pd.DataFrame,
    latitude_column: str = "latitude",
    longitude_column: str = "longitude",
) -> Optional[pd.Series]:
    """Find the closest grid row to a station coordinate."""
    if grid.empty or not _valid_coordinate(latitude) or not _valid_coordinate(longitude):
        return None
    if latitude_column not in grid.columns or longitude_column not in grid.columns:
        return None

    lat_value = float(latitude)
    lon_value = float(longitude)
    candidates = grid.dropna(subset=[latitude_column, longitude_column]).copy()
    if candidates.empty:
        return None

    distances = candidates.apply(
        lambda row: haversine_distance_km(
            lat_value,
            lon_value,
            float(row[latitude_column]),
            float(row[longitude_column]),
        ),
        axis=1,
    )
    nearest = candidates.loc[distances.idxmin()].copy()
    nearest["match_distance_km"] = float(distances.min())
    return nearest


def spatially_match_points(
    stations: pd.DataFrame,
    grid: pd.DataFrame,
    feature_columns: Iterable[str],
    prefix: str,
) -> pd.DataFrame:
    """Attach nearest grid features to each station row."""
    matched_rows = []
    for _, station in stations.iterrows():
        nearest = nearest_grid_row(station.get("Latitude"), station.get("Longitude"), grid)
        row = station.to_dict()
        for feature in feature_columns:
            row[feature] = pd.NA if nearest is None else nearest.get(feature, pd.NA)
        distance_column = f"{prefix}_match_distance_km"
        row[distance_column] = pd.NA if nearest is None else nearest["match_distance_km"]
        matched_rows.append(row)
    return pd.DataFrame(matched_rows)
