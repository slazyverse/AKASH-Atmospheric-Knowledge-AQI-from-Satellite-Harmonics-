"""Station metadata validation helpers."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

from data_collection_pipeline.data_cleaning.cleaners import log_operation

REQUIRED_COLUMNS = ["Station ID", "Station Name", "City", "State", "Latitude", "Longitude"]
OFFICIAL_LIST_CANDIDATES = [
    "official_cpcb_station_list.csv",
    "cpcb_station_list.csv",
    "cpcb_stations_official.csv",
]


def _normalise_text(value: object) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip().casefold()


def find_official_station_list(metadata_dir: Path) -> Optional[Path]:
    """Find an official CPCB station list if one has been provided."""
    for filename in OFFICIAL_LIST_CANDIDATES:
        path = metadata_dir / filename
        if path.exists():
            return path
    return None


def _canonical_columns(df: pd.DataFrame) -> pd.DataFrame:
    aliases = {
        "station_id": "Station ID",
        "station id": "Station ID",
        "id": "Station ID",
        "station_name": "Station Name",
        "station name": "Station Name",
        "station": "Station Name",
        "name": "Station Name",
        "city": "City",
        "state": "State",
        "latitude": "Latitude",
        "lat": "Latitude",
        "longitude": "Longitude",
        "lon": "Longitude",
        "lng": "Longitude",
    }
    rename_map: Dict[str, str] = {}
    for column in df.columns:
        rename_map[column] = aliases.get(str(column).strip().casefold(), column)
    return df.rename(columns=rename_map)


def _build_official_lookup(official_df: pd.DataFrame) -> Dict[str, pd.Series]:
    official = _canonical_columns(official_df)
    lookup: Dict[str, pd.Series] = {}
    if "Station ID" in official.columns:
        for _, row in official.iterrows():
            station_id = _normalise_text(row.get("Station ID"))
            if station_id:
                lookup[f"id:{station_id}"] = row
    if "Station Name" in official.columns:
        for _, row in official.iterrows():
            station_name = _normalise_text(row.get("Station Name"))
            city = _normalise_text(row.get("City"))
            if station_name:
                lookup[f"name:{station_name}|city:{city}"] = row
    return lookup


def _coordinate_mismatch(left: object, right: object, tolerance: float = 0.01) -> bool:
    left_value = pd.to_numeric(pd.Series([left]), errors="coerce").iloc[0]
    right_value = pd.to_numeric(pd.Series([right]), errors="coerce").iloc[0]
    if pd.isna(left_value) or pd.isna(right_value):
        return False
    return abs(float(left_value) - float(right_value)) > tolerance


def _compare_with_official(row: pd.Series, official_row: pd.Series) -> List[str]:
    mismatches: List[str] = []
    text_fields = ["Station ID", "Station Name", "City", "State"]
    for field in text_fields:
        if field in official_row.index and _normalise_text(row.get(field)) != _normalise_text(
            official_row.get(field)
        ):
            mismatches.append(field)

    for field in ["Latitude", "Longitude"]:
        if field in official_row.index and _coordinate_mismatch(row.get(field), official_row.get(field)):
            mismatches.append(field)

    return mismatches


def _validate_required_fields(row: pd.Series, duplicate_station: bool) -> List[str]:
    warnings: List[str] = []
    if not _normalise_text(row.get("Latitude")):
        warnings.append("missing_latitude")
    if not _normalise_text(row.get("Longitude")):
        warnings.append("missing_longitude")
    if not _normalise_text(row.get("City")):
        warnings.append("missing_city")
    if not _normalise_text(row.get("State")):
        warnings.append("missing_state")
    if duplicate_station:
        warnings.append("duplicate_station")

    lat = pd.to_numeric(pd.Series([row.get("Latitude")]), errors="coerce").iloc[0]
    lon = pd.to_numeric(pd.Series([row.get("Longitude")]), errors="coerce").iloc[0]
    if pd.notna(lat) and (lat < -90 or lat > 90):
        warnings.append("invalid_latitude_range")
    if pd.notna(lon) and (lon < -180 or lon > 180):
        warnings.append("invalid_longitude_range")

    return warnings


def _lookup_official_row(
    row: pd.Series,
    official_lookup: Dict[str, pd.Series],
) -> Optional[pd.Series]:
    station_id = _normalise_text(row.get("Station ID"))
    station_name = _normalise_text(row.get("Station Name"))
    city = _normalise_text(row.get("City"))
    matched_by_id = official_lookup.get(f"id:{station_id}")
    if matched_by_id is not None:
        return matched_by_id
    return official_lookup.get(f"name:{station_name}|city:{city}")


def validate_station_metadata(
    station_metadata_path: Path,
    output_path: Path,
    metadata_dir: Path,
    logger: logging.Logger,
) -> Tuple[pd.DataFrame, int, int]:
    """Validate station metadata and emit a warning-annotated CSV."""
    started = time.perf_counter()
    warnings: List[str] = []

    if not station_metadata_path.exists():
        empty = pd.DataFrame(columns=REQUIRED_COLUMNS + ["Validation Warnings"])
        empty.to_csv(output_path, index=False)
        log_operation(
            logger,
            "Station Metadata",
            "validate_station_metadata",
            0,
            started,
            errors=[f"Missing station metadata file: {station_metadata_path}"],
        )
        return empty, 0, 0

    df = _canonical_columns(pd.read_csv(station_metadata_path))
    for column in REQUIRED_COLUMNS:
        if column not in df.columns:
            df[column] = pd.NA
            warnings.append(f"missing_required_column:{column}")

    official_path = find_official_station_list(metadata_dir)
    official_lookup: Dict[str, pd.Series] = {}
    if official_path:
        official_lookup = _build_official_lookup(pd.read_csv(official_path))
    else:
        warnings.append("official_cpcb_station_list_not_available")

    duplicate_mask = df.duplicated(subset=["Station Name", "City", "State"], keep=False)
    validation_warnings: List[str] = []
    mismatch_fields: List[str] = []
    mismatch_count = 0

    for index, row in df.iterrows():
        row_warnings = _validate_required_fields(row, bool(duplicate_mask.iloc[index]))
        official_row = _lookup_official_row(row, official_lookup) if official_lookup else None

        if official_row is not None:
            mismatches = _compare_with_official(row, official_row)
            if mismatches:
                mismatch_count += 1
                mismatch_fields.append("|".join(mismatches))
                row_warnings.append(f"official_metadata_mismatch:{'|'.join(mismatches)}")
            else:
                mismatch_fields.append("")
        else:
            mismatch_fields.append("")
            if official_lookup:
                row_warnings.append("official_station_not_matched")

        validation_warnings.append("; ".join(row_warnings))

    validated = df.copy()
    validated["Validation Warnings"] = validation_warnings
    validated["Official Mismatch Fields"] = mismatch_fields
    output_path.parent.mkdir(parents=True, exist_ok=True)
    validated.to_csv(output_path, index=False)

    invalid_coordinate_count = sum(
        warning.find("invalid_latitude_range") >= 0 or warning.find("invalid_longitude_range") >= 0
        for warning in validation_warnings
    )
    rows_with_warnings = sum(bool(warning) for warning in validation_warnings)
    log_operation(
        logger,
        "Station Metadata",
        "validate_station_metadata",
        rows_with_warnings,
        started,
        warnings=warnings,
    )
    return validated, int(invalid_coordinate_count), mismatch_count


def count_warning_rows(warnings: Iterable[str]) -> int:
    """Count non-empty warning entries."""
    return sum(bool(warning) for warning in warnings)
