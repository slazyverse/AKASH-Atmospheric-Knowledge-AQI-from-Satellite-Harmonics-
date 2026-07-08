"""
Feature-Target Collocation module for the AKASH data collection pipeline.

Provides functions to collocate station observations from the Day 3 merged
feature table, ensuring one observation per station-time, filtering by
configurable temporal and spatial tolerances, and rejecting invalid matches
with logged reasons.
"""

import logging
import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd

from data_collection_pipeline import config
from data_collection_pipeline.utils import logger

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default tolerances
DEFAULT_TEMPORAL_TOLERANCE_HOURS: float = 1.0   # ±1 hour window
DEFAULT_SPATIAL_TOLERANCE_KM: float = 50.0      # ±50 km radius

# Key column names used by the merged feature table
COL_STATION_ID: str = "Station ID"
COL_STATION_NAME: str = "Station Name"
COL_DATE: str = "Date"
COL_TIME: str = "Time"
COL_LATITUDE: str = "Latitude"
COL_LONGITUDE: str = "Longitude"
COL_SAT_DIST: str = "satellite_match_distance_km"
COL_ERA5_DIST: str = "era5_match_distance_km"

# Columns required for collocation to proceed
COLLOCATION_REQUIRED_COLS: List[str] = [
    COL_STATION_ID,
    COL_DATE,
    COL_TIME,
    COL_LATITUDE,
    COL_LONGITUDE,
]

# Internal column names added during processing
_COL_DATETIME: str = "_parsed_datetime"
_COL_REJECT_REASON: str = "_rejection_reason"


# ---------------------------------------------------------------------------
# Helper: haversine distance
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Computes the great-circle distance in kilometres between two geographic
    points using the Haversine formula.

    Args:
        lat1: Latitude of point 1 in decimal degrees.
        lon1: Longitude of point 1 in decimal degrees.
        lat2: Latitude of point 2 in decimal degrees.
        lon2: Longitude of point 2 in decimal degrees.

    Returns:
        Distance in kilometres.
    """
    R_KM: float = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0) ** 2
    return 2.0 * R_KM * np.arcsin(np.sqrt(a))


# ---------------------------------------------------------------------------
# Helper: standardized rejection record
# ---------------------------------------------------------------------------

def _build_rejection_record(row_data: Union[pd.Series, Dict[str, Any]], reason: str, row_index: Any = None) -> Dict[str, Any]:
    """Builds a standardized rejection log dictionary."""
    record: Dict[str, Any] = {"row_index": row_index, "rejection_reason": reason}
    if isinstance(row_data, pd.Series):
        for col in [COL_STATION_ID, COL_STATION_NAME, COL_DATE, COL_TIME]:
            if col in row_data.index:
                record[col] = row_data[col]
    else:
        for col in [COL_STATION_ID, COL_STATION_NAME, COL_DATE, COL_TIME]:
            if col in row_data:
                record[col] = row_data[col]
    return record


# ---------------------------------------------------------------------------
# Helper: parse datetime column
# ---------------------------------------------------------------------------

def _parse_datetime(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds an internal ``_parsed_datetime`` column by combining the Date and Time
    columns. Rows that cannot be parsed are left with NaT.

    Args:
        df: Input DataFrame. Must contain ``Date`` and ``Time`` columns.

    Returns:
        DataFrame with the ``_parsed_datetime`` column added.
    """
    out_df = df.copy()
    try:
        out_df[_COL_DATETIME] = pd.to_datetime(
            out_df[COL_DATE].astype(str).str.strip()
            + " "
            + out_df[COL_TIME].astype(str).str.strip(),
            format="%Y-%m-%d %H:%M:%S",
            errors="coerce",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Datetime parsing encountered an unexpected error: {exc}")
        out_df[_COL_DATETIME] = pd.NaT
    return out_df


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def match_nearest_timestamp(
    df: pd.DataFrame,
    reference_times: Optional[List[datetime.datetime]] = None,
    tolerance_hours: float = DEFAULT_TEMPORAL_TOLERANCE_HOURS,
) -> pd.DataFrame:
    """
    For each station, retains only the observation whose timestamp is nearest
    to a given reference time (or, when no reference list is supplied, treats
    all distinct station-time combinations as self-contained and deduplicates
    to the nearest timestamp per station-date group).

    Args:
        df: Input DataFrame with ``Date``, ``Time``, and ``Station ID`` columns.
        reference_times: Optional list of reference ``datetime.datetime`` objects.
                         When provided, each station row is matched to the
                         closest reference time within *tolerance_hours*.
                         When ``None``, the function deduplicates to the
                         lexicographically earliest timestamp per station-date.
        tolerance_hours: Maximum allowed deviation in hours when matching to
                         reference times. Rows outside the window are dropped.

    Returns:
        Filtered DataFrame, deduplicated to one observation per station–time.
    """
    logger.info(
        f"match_nearest_timestamp: processing {len(df)} rows "
        f"(tolerance={tolerance_hours}h, references={'provided' if reference_times else 'none'})"
    )

    if df.empty:
        logger.warning("match_nearest_timestamp: received an empty DataFrame.")
        return df.copy()

    processed_df = _parse_datetime(df.copy().reset_index(drop=True))

    if reference_times is not None:
        if not reference_times:
            logger.warning("match_nearest_timestamp: reference_times is empty.")
            processed_df = processed_df.iloc[0:0].copy()
        else:
            ref_arr = np.array([t.timestamp() for t in reference_times])
            matched_indices: List[int] = []

            for idx, row in processed_df.iterrows():
                if pd.isna(row[_COL_DATETIME]):
                    continue
                obs_ts = row[_COL_DATETIME].timestamp()
                diff_hours = np.abs(ref_arr - obs_ts) / 3600.0
                nearest_diff = float(np.min(diff_hours))
                if nearest_diff <= tolerance_hours:
                    matched_indices.append(idx)
                else:
                    logger.debug(
                        f"match_nearest_timestamp: row {idx} (station={row.get(COL_STATION_ID)}) "
                        f"dropped — nearest reference gap {nearest_diff:.2f}h > {tolerance_hours}h"
                    )

            processed_df = processed_df.loc[matched_indices].copy().reset_index(drop=True)
        logger.info(f"match_nearest_timestamp: {len(processed_df)} rows retained after reference matching.")
    else:
        # Deduplicate to earliest timestamp per station-date (deterministic)
        key_cols = [COL_STATION_ID, COL_DATE]
        valid_key_cols = [c for c in key_cols if c in processed_df.columns]
        if valid_key_cols and _COL_DATETIME in processed_df.columns:
            processed_df = (
                processed_df.sort_values(_COL_DATETIME)
                .drop_duplicates(subset=valid_key_cols, keep="first")
                .reset_index(drop=True)
            )
            logger.info(
                f"match_nearest_timestamp: deduplicated to {len(processed_df)} rows "
                f"(earliest timestamp per station-date)."
            )

    # Remove internal helper column before returning
    processed_df = processed_df.drop(columns=[_COL_DATETIME], errors="ignore")
    return processed_df


def match_station_records(
    df: pd.DataFrame,
    station_ids: Optional[List[str]] = None,
) -> pd.DataFrame:
    """
    Filters the dataset to only include records belonging to the specified
    station IDs. When ``station_ids`` is ``None`` all stations are kept.

    Args:
        df: Input DataFrame with a ``Station ID`` column.
        station_ids: Optional allow-list of station identifier strings.

    Returns:
        Filtered DataFrame containing only matched station records.
    """
    logger.info(
        f"match_station_records: {len(df)} rows in, "
        f"filter={'all stations' if station_ids is None else station_ids}"
    )

    if df.empty:
        logger.warning("match_station_records: received an empty DataFrame.")
        return df.copy()

    if station_ids is None:
        logger.info("match_station_records: no station filter applied, returning all records.")
        return df.copy()

    if COL_STATION_ID not in df.columns:
        logger.error(
            f"match_station_records: column '{COL_STATION_ID}' not found in DataFrame. "
            "Returning empty DataFrame."
        )
        return df.iloc[0:0].copy()

    station_set = set(station_ids)
    matched = df[df[COL_STATION_ID].isin(station_set)].copy().reset_index(drop=True)
    unmatched_ids = station_set - set(matched[COL_STATION_ID].unique())

    if unmatched_ids:
        logger.warning(
            f"match_station_records: {len(unmatched_ids)} requested station(s) not found "
            f"in dataset: {sorted(unmatched_ids)}"
        )

    logger.info(
        f"match_station_records: {len(matched)} rows retained from "
        f"{matched[COL_STATION_ID].nunique()} station(s)."
    )
    return matched


def apply_temporal_tolerance(
    df: pd.DataFrame,
    reference_datetime: Optional[datetime.datetime] = None,
    tolerance_hours: float = DEFAULT_TEMPORAL_TOLERANCE_HOURS,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Partitions the dataset into rows within and outside a temporal tolerance
    window centred on *reference_datetime*.

    When *reference_datetime* is ``None`` the median observation timestamp of
    the dataset is used as the reference.

    Args:
        df: Input DataFrame with ``Date`` and ``Time`` columns.
        reference_datetime: Centre of the acceptable time window.
        tolerance_hours: Half-width of the tolerance window in hours.

    Returns:
        A tuple ``(accepted, rejected)`` where *accepted* contains rows within
        the window and *rejected* contains rows outside it.
    """
    logger.info(
        f"apply_temporal_tolerance: {len(df)} rows, tolerance=±{tolerance_hours}h, "
        f"reference={'auto-median' if reference_datetime is None else reference_datetime.isoformat()}"
    )

    if df.empty:
        logger.warning("apply_temporal_tolerance: received an empty DataFrame.")
        return df.copy(), df.copy()

    processed_df = _parse_datetime(df.copy().reset_index(drop=True))
    valid_mask = processed_df[_COL_DATETIME].notna()

    eff_ref_dt = reference_datetime
    if eff_ref_dt is None:
        valid_times = processed_df.loc[valid_mask, _COL_DATETIME]
        if valid_times.empty:
            logger.error("apply_temporal_tolerance: no parseable timestamps found.")
            rejected = processed_df.drop(columns=[_COL_DATETIME], errors="ignore")
            return processed_df.iloc[0:0].drop(columns=[_COL_DATETIME], errors="ignore"), rejected

        median_ts = valid_times.sort_values().iloc[len(valid_times) // 2]
        eff_ref_dt = median_ts.to_pydatetime()
        logger.info(f"apply_temporal_tolerance: using median reference datetime {eff_ref_dt.isoformat()}")

    ref_ts = pd.Timestamp(eff_ref_dt)
    delta = pd.Timedelta(hours=tolerance_hours)
    lower = ref_ts - delta
    upper = ref_ts + delta

    within_window = valid_mask & (processed_df[_COL_DATETIME] >= lower) & (processed_df[_COL_DATETIME] <= upper)
    accepted = processed_df[within_window].drop(columns=[_COL_DATETIME], errors="ignore").reset_index(drop=True)
    rejected = processed_df[~within_window].drop(columns=[_COL_DATETIME], errors="ignore").reset_index(drop=True)

    logger.info(
        f"apply_temporal_tolerance: accepted={len(accepted)}, rejected={len(rejected)} "
        f"(window: {lower.isoformat()} – {upper.isoformat()})"
    )
    return accepted, rejected


def apply_spatial_tolerance(
    df: pd.DataFrame,
    reference_lat: Optional[float] = None,
    reference_lon: Optional[float] = None,
    tolerance_km: float = DEFAULT_SPATIAL_TOLERANCE_KM,
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Partitions the dataset into rows whose station coordinates are within and
    outside a spatial tolerance radius from a reference location.

    When both *reference_lat* and *reference_lon* are ``None``, the geographic
    centroid of all valid station coordinates is used as the reference.

    Args:
        df: Input DataFrame with ``Latitude`` and ``Longitude`` columns.
        reference_lat: Reference latitude in decimal degrees.
        reference_lon: Reference longitude in decimal degrees.
        tolerance_km: Radius of the acceptable spatial window in kilometres.

    Returns:
        A tuple ``(accepted, rejected)`` where *accepted* contains rows within
        the radius and *rejected* contains rows outside it.
    """
    logger.info(
        f"apply_spatial_tolerance: {len(df)} rows, tolerance={tolerance_km}km, "
        f"reference={'auto-centroid' if reference_lat is None else f'({reference_lat}, {reference_lon})'}"
    )

    if df.empty:
        logger.warning("apply_spatial_tolerance: received an empty DataFrame.")
        return df.copy(), df.copy()

    if COL_LATITUDE not in df.columns or COL_LONGITUDE not in df.columns:
        logger.error("apply_spatial_tolerance: Latitude or Longitude column missing.")
        return df.copy(), df.iloc[0:0].copy()

    processed_df = df.copy().reset_index(drop=True)
    processed_df["_lat_numeric"] = pd.to_numeric(processed_df[COL_LATITUDE], errors="coerce")
    processed_df["_lon_numeric"] = pd.to_numeric(processed_df[COL_LONGITUDE], errors="coerce")
    valid_coord_mask = processed_df["_lat_numeric"].notna() & processed_df["_lon_numeric"].notna()

    eff_ref_lat = reference_lat
    eff_ref_lon = reference_lon

    if eff_ref_lat is None or eff_ref_lon is None:
        valid_lats = processed_df.loc[valid_coord_mask, "_lat_numeric"]
        valid_lons = processed_df.loc[valid_coord_mask, "_lon_numeric"]
        if valid_lats.empty:
            logger.error("apply_spatial_tolerance: no valid coordinates to compute centroid.")
            processed_df = processed_df.drop(columns=["_lat_numeric", "_lon_numeric"], errors="ignore")
            return processed_df.iloc[0:0].copy(), processed_df.copy()
        eff_ref_lat = float(valid_lats.mean())
        eff_ref_lon = float(valid_lons.mean())
        logger.info(
            f"apply_spatial_tolerance: using centroid reference ({eff_ref_lat:.4f}, {eff_ref_lon:.4f})"
        )

    def _within_radius(row: pd.Series) -> bool:
        if pd.isna(row["_lat_numeric"]) or pd.isna(row["_lon_numeric"]):
            return False
        dist = _haversine_km(row["_lat_numeric"], row["_lon_numeric"], eff_ref_lat, eff_ref_lon) # type: ignore
        return dist <= tolerance_km

    within_mask = processed_df.apply(_within_radius, axis=1)
    cleanup_cols = ["_lat_numeric", "_lon_numeric"]
    accepted = processed_df[within_mask].drop(columns=cleanup_cols, errors="ignore").reset_index(drop=True)
    rejected = processed_df[~within_mask].drop(columns=cleanup_cols, errors="ignore").reset_index(drop=True)

    logger.info(
        f"apply_spatial_tolerance: accepted={len(accepted)}, rejected={len(rejected)} "
        f"(radius {tolerance_km}km from ({eff_ref_lat}, {eff_ref_lon}))"
    )
    return accepted, rejected


def reject_invalid_matches(
    df: pd.DataFrame,
    temporal_tolerance_hours: float = DEFAULT_TEMPORAL_TOLERANCE_HOURS,
    spatial_tolerance_km: float = DEFAULT_SPATIAL_TOLERANCE_KM,
) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """
    Identifies and removes observations that do not satisfy collocation quality
    criteria. Each rejected row is logged with an explicit rejection reason.

    Rejection criteria (applied in order):
    1. Missing required columns (``Station ID``, ``Date``, ``Time``,
       ``Latitude``, ``Longitude``).
    2. Unparseable timestamp (``Date`` / ``Time`` values).
    3. Coordinates outside physical bounds (lat ∉ [−90, 90] or lon ∉ [−180, 180]).
    4. Coordinates outside India bounding box (lat ∉ [6, 38] or lon ∉ [68, 98]).
    5. Duplicate station-time observation (only the first occurrence is kept).
    6. Satellite match distance exceeds spatial tolerance (when column present).
    7. ERA5 match distance exceeds spatial tolerance (when column present).

    Args:
        df: Input DataFrame.
        temporal_tolerance_hours: Not directly applied here but included for
                                  signature parity; downstream callers may pass
                                  the same value used in apply_temporal_tolerance.
        spatial_tolerance_km: Maximum acceptable satellite/ERA5 match distance.

    Returns:
        A tuple ``(valid_df, rejection_log)`` where *valid_df* is the cleaned
        DataFrame and *rejection_log* is a list of dicts describing each
        rejected row.
    """
    logger.info(
        f"reject_invalid_matches: screening {len(df)} rows "
        f"(temporal_tol={temporal_tolerance_hours}h, spatial_tol={spatial_tolerance_km}km)"
    )

    if df.empty:
        logger.warning("reject_invalid_matches: received an empty DataFrame.")
        return df.copy(), []

    processed_df = df.copy().reset_index(drop=True)
    rejection_log: List[Dict[str, Any]] = []
    # Track which rows to keep (by positional index)
    keep_mask = pd.Series(True, index=processed_df.index)

    def _reject(idx: Any, reason: str, log_warning: bool = True) -> None:
        keep_mask[idx] = False
        row_info = _build_rejection_record(processed_df.iloc[idx], reason, row_index=idx)
        rejection_log.append(row_info)
        if log_warning:
            logger.warning(f"reject_invalid_matches: row {idx} rejected — {reason}")

    # ------------------------------------------------------------------ #
    # 1. Missing required columns → reject all rows if column absent     #
    # ------------------------------------------------------------------ #
    for col in COLLOCATION_REQUIRED_COLS:
        if col not in processed_df.columns:
            logger.error(
                f"reject_invalid_matches: required column '{col}' is missing "
                "— all rows will be rejected."
            )
            for idx in processed_df.index:
                _reject(idx, f"Required column '{col}' absent from dataset", log_warning=False)
            valid_df = processed_df[keep_mask].copy().reset_index(drop=True)
            return valid_df, rejection_log

    # ------------------------------------------------------------------ #
    # 2. Unparseable timestamps                                           #
    # ------------------------------------------------------------------ #
    df_tmp = _parse_datetime(processed_df)
    for idx, row in df_tmp.iterrows():
        if not keep_mask[idx]:
            continue
        if pd.isna(row[_COL_DATETIME]):
            _reject(
                idx,
                f"Unparseable timestamp: Date='{row.get(COL_DATE)}', Time='{row.get(COL_TIME)}'"
            )

    # ------------------------------------------------------------------ #
    # 3 & 4. Coordinate validation                                        #
    # ------------------------------------------------------------------ #
    for idx, row in processed_df.iterrows():
        if not keep_mask[idx]:
            continue
        lat_raw = row.get(COL_LATITUDE)
        lon_raw = row.get(COL_LONGITUDE)

        if pd.isna(lat_raw) or pd.isna(lon_raw):
            _reject(idx, f"Missing coordinate: Latitude='{lat_raw}', Longitude='{lon_raw}'")
            continue

        try:
            lat = float(lat_raw)
            lon = float(lon_raw)
        except (ValueError, TypeError):
            _reject(idx, f"Non-numeric coordinate: Latitude='{lat_raw}', Longitude='{lon_raw}'")
            continue

        if not (-90.0 <= lat <= 90.0) or not (-180.0 <= lon <= 180.0):
            _reject(
                idx,
                f"Coordinate outside physical bounds: ({lat}, {lon})"
            )
            continue

        if not (6.0 <= lat <= 38.0) or not (68.0 <= lon <= 98.0):
            _reject(
                idx,
                f"Coordinate outside India bounding box [6–38°N, 68–98°E]: ({lat}, {lon})"
            )

    # ------------------------------------------------------------------ #
    # 5. Duplicate station-time (keep first occurrence)                  #
    # ------------------------------------------------------------------ #
    subset_cols = [COL_STATION_ID, COL_DATE, COL_TIME]
    surviving = processed_df[keep_mask]
    dup_mask_on_surviving = surviving.duplicated(subset=subset_cols, keep="first")
    dup_indices = surviving[dup_mask_on_surviving].index.tolist()
    for idx in dup_indices:
        _reject(
            idx,
            f"Duplicate station-time observation for "
            f"station={processed_df.at[idx, COL_STATION_ID]}, "
            f"date={processed_df.at[idx, COL_DATE]}, time={processed_df.at[idx, COL_TIME]}"
        )

    # ------------------------------------------------------------------ #
    # 6. Satellite match distance > spatial tolerance                     #
    # ------------------------------------------------------------------ #
    if COL_SAT_DIST in processed_df.columns:
        for idx, row in processed_df.iterrows():
            if not keep_mask[idx]:
                continue
            sat_dist = row.get(COL_SAT_DIST)
            if pd.notna(sat_dist):
                try:
                    if float(sat_dist) > spatial_tolerance_km:
                        _reject(
                            idx,
                            f"Satellite match distance {float(sat_dist):.2f}km exceeds "
                            f"tolerance {spatial_tolerance_km}km"
                        )
                except (ValueError, TypeError):
                    pass  # Non-numeric distance is not grounds for rejection here

    # ------------------------------------------------------------------ #
    # 7. ERA5 match distance > spatial tolerance                          #
    # ------------------------------------------------------------------ #
    if COL_ERA5_DIST in processed_df.columns:
        for idx, row in processed_df.iterrows():
            if not keep_mask[idx]:
                continue
            era5_dist = row.get(COL_ERA5_DIST)
            if pd.notna(era5_dist):
                try:
                    if float(era5_dist) > spatial_tolerance_km:
                        _reject(
                            idx,
                            f"ERA5 match distance {float(era5_dist):.2f}km exceeds "
                            f"tolerance {spatial_tolerance_km}km"
                        )
                except (ValueError, TypeError):
                    pass

    valid_df = processed_df[keep_mask].copy().reset_index(drop=True)
    logger.info(
        f"reject_invalid_matches: {len(valid_df)} rows accepted, "
        f"{len(rejection_log)} rows rejected."
    )
    return valid_df, rejection_log


def collocate_dataset(
    file_path: Optional[Union[str, Path]] = None,
    station_ids: Optional[List[str]] = None,
    temporal_tolerance_hours: float = DEFAULT_TEMPORAL_TOLERANCE_HOURS,
    spatial_tolerance_km: float = DEFAULT_SPATIAL_TOLERANCE_KM,
    reference_datetime: Optional[datetime.datetime] = None,
    reference_lat: Optional[float] = None,
    reference_lon: Optional[float] = None,
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Full collocation pipeline: reads the Day 3 merged feature table, applies
    station matching, temporal tolerance, spatial tolerance, and invalid-match
    rejection, then returns the collocated DataFrame alongside a structured
    summary dictionary.

    The pipeline guarantees:
    - Exactly one observation per station-time.
    - No duplicate observations.
    - All retained rows satisfy the coordinate and timestamp validity checks.
    - All rejected rows are logged with an explicit reason.

    Args:
        file_path: Path to the merged feature table CSV. Defaults to
                   ``config.FEATURES_DIR / "merged_feature_table.csv"``.
        station_ids: Optional allow-list of station IDs to include.
        temporal_tolerance_hours: Half-width of the temporal acceptance window
                                  in hours. Default: 1.0 h.
        spatial_tolerance_km: Maximum satellite/ERA5 match distance in km.
                              Also used as the radius for apply_spatial_tolerance
                              when reference coordinates are provided. Default: 50 km.
        reference_datetime: Optional reference datetime for apply_temporal_tolerance.
                            When ``None`` the dataset's median timestamp is used.
        reference_lat: Optional reference latitude for apply_spatial_tolerance.
                       When ``None`` (and reference_lon is also ``None``) the
                       function skips the spatial window filter and relies solely
                       on coordinate bounds checks inside reject_invalid_matches.
        reference_lon: Optional reference longitude for apply_spatial_tolerance.

    Returns:
        A tuple ``(collocated_df, summary)`` where *collocated_df* is the
        validated, deduplicated DataFrame and *summary* is a structured dict
        containing input/output row counts, station counts, rejection counts,
        and configuration metadata.
    """
    actual_file_path = (
        config.FEATURES_DIR / "merged_feature_table.csv"
        if file_path is None
        else Path(file_path)
    )

    logger.info(
        f"collocate_dataset: starting collocation pipeline on '{actual_file_path}' "
        f"(temporal_tol={temporal_tolerance_hours}h, spatial_tol={spatial_tolerance_km}km)"
    )

    summary: Dict[str, Any] = {
        "dataset_path": str(actual_file_path.resolve()),
        "timestamp": datetime.datetime.now().isoformat(),
        "configuration": {
            "temporal_tolerance_hours": temporal_tolerance_hours,
            "spatial_tolerance_km": spatial_tolerance_km,
            "reference_datetime": reference_datetime.isoformat() if reference_datetime else None,
            "reference_lat": reference_lat,
            "reference_lon": reference_lon,
            "station_filter": station_ids,
        },
    }

    # ------------------------------------------------------------------ #
    # Load the merged feature table                                       #
    # ------------------------------------------------------------------ #
    if not actual_file_path.exists():
        msg = f"Merged feature table not found: {actual_file_path}"
        logger.error(msg)
        summary.update({"status": "ERROR", "error": msg, "collocated_rows": 0})
        return pd.DataFrame(), summary

    try:
        df_raw = pd.read_csv(actual_file_path)
    except Exception as exc:  # noqa: BLE001
        msg = f"Failed to read merged feature table: {exc}"
        logger.error(msg)
        summary.update({"status": "ERROR", "error": msg, "collocated_rows": 0})
        return pd.DataFrame(), summary

    input_rows = len(df_raw)
    input_stations = int(df_raw[COL_STATION_ID].nunique()) if COL_STATION_ID in df_raw.columns else 0
    logger.info(f"collocate_dataset: loaded {input_rows} rows from {input_stations} stations.")

    # ------------------------------------------------------------------ #
    # Step 1 — Match station records                                      #
    # ------------------------------------------------------------------ #
    df_stations = match_station_records(df_raw, station_ids=station_ids)
    after_station_filter = len(df_stations)

    # ------------------------------------------------------------------ #
    # Step 2 — Reject invalid matches                                     #
    # ------------------------------------------------------------------ #
    df_valid, rejection_log = reject_invalid_matches(
        df_stations,
        temporal_tolerance_hours=temporal_tolerance_hours,
        spatial_tolerance_km=spatial_tolerance_km,
    )
    after_rejection = len(df_valid)

    # ------------------------------------------------------------------ #
    # Step 3 — Apply temporal tolerance (optional reference window)       #
    # ------------------------------------------------------------------ #
    if reference_datetime is not None:
        df_valid, df_temporal_rejected = apply_temporal_tolerance(
            df_valid,
            reference_datetime=reference_datetime,
            tolerance_hours=temporal_tolerance_hours,
        )
        for row in df_temporal_rejected.to_dict(orient="records"):
            row_info = _build_rejection_record(
                row,
                f"Outside temporal tolerance window ±{temporal_tolerance_hours}h of {reference_datetime.isoformat()}"
            )
            rejection_log.append(row_info)
            logger.warning(
                f"collocate_dataset: temporal rejection — station="
                f"{row.get(COL_STATION_ID)}, date={row.get(COL_DATE)}, time={row.get(COL_TIME)}"
            )
    after_temporal_filter = len(df_valid)

    # ------------------------------------------------------------------ #
    # Step 4 — Apply spatial tolerance (optional reference location)      #
    # ------------------------------------------------------------------ #
    if reference_lat is not None and reference_lon is not None:
        df_valid, df_spatial_rejected = apply_spatial_tolerance(
            df_valid,
            reference_lat=reference_lat,
            reference_lon=reference_lon,
            tolerance_km=spatial_tolerance_km,
        )
        for row in df_spatial_rejected.to_dict(orient="records"):
            row_info = _build_rejection_record(
                row,
                f"Outside spatial tolerance radius {spatial_tolerance_km}km from ({reference_lat}, {reference_lon})"
            )
            rejection_log.append(row_info)
            logger.warning(
                f"collocate_dataset: spatial rejection — station="
                f"{row.get(COL_STATION_ID)}, lat={row.get(COL_LATITUDE)}, lon={row.get(COL_LONGITUDE)}"
            )
    after_spatial_filter = len(df_valid)

    # ------------------------------------------------------------------ #
    # Step 5 — Match nearest timestamp (deduplication guard)              #
    # ------------------------------------------------------------------ #
    df_valid['_temp_idx'] = df_valid.index
    df_collocated = match_nearest_timestamp(
        df_valid,
        reference_times=None,           # self-deduplicate mode
        tolerance_hours=temporal_tolerance_hours,
    )
    
    dropped_mask = ~df_valid['_temp_idx'].isin(df_collocated['_temp_idx'])
    df_dropped_nearest = df_valid[dropped_mask]
    
    for row in df_dropped_nearest.to_dict(orient="records"):
        row_info = _build_rejection_record(
            row,
            "Dropped during deduplication to nearest timestamp",
            row_index=row.get('_temp_idx')
        )
        rejection_log.append(row_info)
        logger.warning(
            f"collocate_dataset: deduplication rejection — station="
            f"{row.get(COL_STATION_ID)}, date={row.get(COL_DATE)}, time={row.get(COL_TIME)}"
        )

    df_collocated = df_collocated.drop(columns=['_temp_idx'], errors='ignore')

    final_rows = len(df_collocated)
    final_stations = (
        int(df_collocated[COL_STATION_ID].nunique())
        if COL_STATION_ID in df_collocated.columns
        else 0
    )

    # ------------------------------------------------------------------ #
    # Build summary                                                       #
    # ------------------------------------------------------------------ #
    summary.update(
        {
            "status": "SUCCESS" if final_rows > 0 else "EMPTY",
            "input_rows": input_rows,
            "input_stations": input_stations,
            "after_station_filter": after_station_filter,
            "after_invalid_rejection": after_rejection,
            "after_temporal_filter": after_temporal_filter,
            "after_spatial_filter": after_spatial_filter,
            "collocated_rows": final_rows,
            "collocated_stations": final_stations,
            "total_rejected": len(rejection_log),
            "rejection_log_sample": rejection_log[:10],
        }
    )

    logger.info(
        f"collocate_dataset: pipeline complete — "
        f"{final_rows} collocated rows, {final_stations} stations, "
        f"{len(rejection_log)} total rejections."
    )
    return df_collocated, summary
