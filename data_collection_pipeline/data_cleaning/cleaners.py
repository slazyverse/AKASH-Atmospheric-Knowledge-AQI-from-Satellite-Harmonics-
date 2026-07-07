"""Reusable dataset cleaning utilities for CPCB and OpenAQ records."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pandas as pd

POLLUTANT_RENAME_MAP = {
    "pm25": "PM2.5",
    "pm2_5": "PM2.5",
    "pm2.5": "PM2.5",
    "pm 2.5": "PM2.5",
    "PM25": "PM2.5",
    "PM2_5": "PM2.5",
    "PM2.5": "PM2.5",
    "pm10": "PM10",
    "PM10": "PM10",
    "no2": "NO2",
    "NO2": "NO2",
    "so2": "SO2",
    "SO2": "SO2",
    "co": "CO",
    "CO": "CO",
    "o3": "O3",
    "O3": "O3",
    "ozone": "O3",
    "OZONE": "O3",
    "aqi": "AQI",
    "AQI": "AQI",
}

POLLUTANT_COLUMNS = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "AQI"]
POLLUTANT_UNITS = {
    "PM2.5": "ug/m3",
    "PM10": "ug/m3",
    "NO2": "ug/m3",
    "SO2": "ug/m3",
    "CO": "mg/m3",
    "O3": "ug/m3",
    "AQI": "index",
}


@dataclass
class CleaningMetrics:
    """Metrics emitted into metadata/data_quality_report.csv."""

    dataset: str
    source_file: str
    rows_before: int = 0
    rows_after: int = 0
    missing_values: int = 0
    duplicates_removed: int = 0
    duplicate_timestamps_removed: int = 0
    negative_pollutant_values: int = 0
    outlier_count: int = 0
    invalid_coordinates: int = 0
    station_metadata_mismatches: int = 0
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


def log_operation(
    logger: logging.Logger,
    dataset: str,
    operation: str,
    rows_affected: int,
    started_at: float,
    warnings: Optional[Iterable[str]] = None,
    errors: Optional[Iterable[str]] = None,
) -> None:
    """Log a standardized cleaning operation audit line."""
    elapsed = time.perf_counter() - started_at
    warning_text = "; ".join(warnings or []) or "none"
    error_text = "; ".join(errors or []) or "none"
    logger.info(
        "Dataset=%s | Operation=%s | Rows affected=%s | Warnings=%s | "
        "Errors=%s | Execution time=%.3fs",
        dataset,
        operation,
        rows_affected,
        warning_text,
        error_text,
        elapsed,
    )


def read_csv(path: Path) -> pd.DataFrame:
    """Read a CSV without mutating raw input files."""
    return pd.read_csv(path)


def standardize_pollutant_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Normalize pollutant column names while preserving non-pollutant columns."""
    return df.rename(columns={col: POLLUTANT_RENAME_MAP.get(col, col) for col in df.columns})


def normalize_datetime_column(df: pd.DataFrame, datetime_column: str) -> pd.DataFrame:
    """Normalize datetime strings without stripping timezone offsets."""
    if datetime_column not in df.columns:
        return df

    cleaned = df.copy()

    def parse_datetime(value: object) -> object:
        if pd.isna(value) or str(value).strip() == "":
            return pd.NA
        parsed = pd.to_datetime(value, errors="coerce", format="mixed")
        if pd.isna(parsed):
            return pd.NA
        return parsed.isoformat()

    cleaned[datetime_column] = cleaned[datetime_column].map(parse_datetime)
    return cleaned


def get_source_columns(dataset: str) -> Tuple[str, str]:
    """Return station and datetime columns for a supported dataset."""
    dataset_key = dataset.lower()
    if dataset_key == "cpcb":
        return "station", "last_update"
    if dataset_key == "openaq":
        return "location", "utc_time"
    raise ValueError(f"Unsupported dataset for cleaning: {dataset}")


def remove_negative_pollutants(
    df: pd.DataFrame,
    pollutant_columns: Iterable[str],
) -> Tuple[pd.DataFrame, int]:
    """Remove rows containing impossible negative pollutant concentrations."""
    available_columns = [col for col in pollutant_columns if col in df.columns]
    if not available_columns:
        return df, 0

    numeric = df[available_columns].apply(pd.to_numeric, errors="coerce")
    negative_mask = numeric.lt(0).any(axis=1)
    return df.loc[~negative_mask].copy(), int(negative_mask.sum())


def flag_outliers(
    df: pd.DataFrame,
    pollutant_columns: Iterable[str],
) -> Tuple[pd.DataFrame, int]:
    """Flag statistical outliers using the IQR rule without removing them."""
    flagged = df.copy()
    total_outliers = 0

    for column in pollutant_columns:
        if column not in flagged.columns:
            continue

        numeric = pd.to_numeric(flagged[column], errors="coerce")
        q1 = numeric.quantile(0.25)
        q3 = numeric.quantile(0.75)
        iqr = q3 - q1
        outlier_column = f"{column}_outlier"

        if pd.isna(iqr) or iqr == 0:
            flagged[outlier_column] = False
            continue

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        mask = numeric.lt(lower_bound) | numeric.gt(upper_bound)
        flagged[outlier_column] = mask.fillna(False)
        total_outliers += int(mask.sum())

    return flagged, total_outliers


def add_standard_units(df: pd.DataFrame) -> pd.DataFrame:
    """Attach standard unit columns for pollutants present in wide-format data."""
    enriched = df.copy()
    for pollutant, unit in POLLUTANT_UNITS.items():
        if pollutant in enriched.columns:
            enriched[f"{pollutant}_unit"] = unit
    return enriched


def count_invalid_coordinates(df: pd.DataFrame) -> int:
    """Count rows with latitude/longitude outside valid geographic ranges."""
    if "latitude" not in df.columns or "longitude" not in df.columns:
        return 0

    lat = pd.to_numeric(df["latitude"], errors="coerce")
    lon = pd.to_numeric(df["longitude"], errors="coerce")
    invalid = lat.lt(-90) | lat.gt(90) | lon.lt(-180) | lon.gt(180)
    return int(invalid.fillna(False).sum())


def clean_dataset(
    df: pd.DataFrame,
    dataset: str,
    source_file: Path,
    logger: logging.Logger,
) -> Tuple[pd.DataFrame, CleaningMetrics]:
    """Clean a CPCB or OpenAQ dataset and return a copy plus metrics."""
    station_column, datetime_column = get_source_columns(dataset)
    metrics = CleaningMetrics(
        dataset=dataset.upper(),
        source_file=str(source_file),
        rows_before=len(df),
        missing_values=int(df.isna().sum().sum()),
    )

    started = time.perf_counter()
    cleaned = standardize_pollutant_columns(df.copy())
    log_operation(logger, metrics.dataset, "standardize_pollutant_names", 0, started)

    started = time.perf_counter()
    cleaned = normalize_datetime_column(cleaned, datetime_column)
    log_operation(logger, metrics.dataset, "normalize_datetime", len(cleaned), started)

    started = time.perf_counter()
    before = len(cleaned)
    cleaned = cleaned.drop_duplicates().copy()
    metrics.duplicates_removed = before - len(cleaned)
    log_operation(
        logger,
        metrics.dataset,
        "remove_duplicate_rows",
        metrics.duplicates_removed,
        started,
    )

    started = time.perf_counter()
    if station_column in cleaned.columns and datetime_column in cleaned.columns:
        before = len(cleaned)
        cleaned = cleaned.drop_duplicates(
            subset=[station_column, datetime_column],
            keep="first",
        ).copy()
        metrics.duplicate_timestamps_removed = before - len(cleaned)
    else:
        metrics.warnings.append(
            f"Missing station/timestamp columns: {station_column}, {datetime_column}"
        )
    log_operation(
        logger,
        metrics.dataset,
        "remove_duplicate_station_timestamps",
        metrics.duplicate_timestamps_removed,
        started,
        warnings=metrics.warnings,
    )

    started = time.perf_counter()
    cleaned, metrics.negative_pollutant_values = remove_negative_pollutants(
        cleaned,
        POLLUTANT_COLUMNS,
    )
    log_operation(
        logger,
        metrics.dataset,
        "remove_negative_pollutant_values",
        metrics.negative_pollutant_values,
        started,
    )

    started = time.perf_counter()
    cleaned, metrics.outlier_count = flag_outliers(cleaned, POLLUTANT_COLUMNS)
    log_operation(
        logger,
        metrics.dataset,
        "flag_statistical_outliers",
        metrics.outlier_count,
        started,
    )

    started = time.perf_counter()
    cleaned = add_standard_units(cleaned)
    log_operation(logger, metrics.dataset, "standardize_units", 0, started)

    metrics.invalid_coordinates = count_invalid_coordinates(cleaned)
    metrics.rows_after = len(cleaned)
    return cleaned, metrics


def find_latest_raw_file(raw_data_dir: Path, pattern: str) -> Optional[Path]:
    """Return the most recently modified raw file matching a glob pattern."""
    files = sorted(raw_data_dir.glob(pattern), key=lambda path: path.stat().st_mtime)
    return files[-1] if files else None
