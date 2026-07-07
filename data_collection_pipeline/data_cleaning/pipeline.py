"""Cleaning pipeline orchestration for collected air-quality datasets."""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import List, Optional

import pandas as pd

from data_collection_pipeline import config, setup, utils
from data_collection_pipeline.data_cleaning.cleaners import (
    CleaningMetrics,
    clean_dataset,
    find_latest_raw_file,
    log_operation,
    read_csv,
)
from data_collection_pipeline.data_cleaning.reporting import write_data_quality_report
from data_collection_pipeline.data_cleaning.station_validation import (
    find_official_station_list,
    validate_station_metadata,
)

logger = logging.getLogger("data_collection_pipeline.data_cleaning")


def _clean_if_available(
    dataset: str,
    raw_file: Optional[Path],
    output_path: Path,
) -> CleaningMetrics:
    started = time.perf_counter()
    if raw_file is None:
        metric = CleaningMetrics(
            dataset=dataset.upper(),
            source_file="",
            warnings=[f"No raw {dataset.upper()} file found"],
        )
        log_operation(
            logger,
            dataset.upper(),
            "load_raw_dataset",
            0,
            started,
            warnings=metric.warnings,
        )
        return metric

    try:
        df = read_csv(raw_file)
        log_operation(logger, dataset.upper(), "load_raw_dataset", len(df), started)
        cleaned, metric = clean_dataset(df, dataset, raw_file, logger)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        cleaned.to_csv(output_path, index=False)
        log_operation(
            logger,
            dataset.upper(),
            "write_cleaned_dataset",
            len(cleaned),
            time.perf_counter(),
        )
        return metric
    except (OSError, IOError, ValueError, pd.errors.ParserError) as exc:
        metric = CleaningMetrics(
            dataset=dataset.upper(),
            source_file=str(raw_file),
            errors=[str(exc)],
        )
        log_operation(
            logger,
            dataset.upper(),
            "clean_dataset",
            0,
            started,
            errors=metric.errors,
        )
        return metric


def run_cleaning_pipeline() -> bool:
    """Run dataset cleaning, station validation, and quality reporting."""
    setup.init_workspace()
    utils.setup_logging()

    logger.info("=========================================")
    logger.info("Starting Data Cleaning & Validation Pipeline run")
    logger.info("=========================================")

    cpcb_raw = find_latest_raw_file(config.RAW_DATA_DIR, "cpcb_raw_*.csv")
    openaq_raw = find_latest_raw_file(config.RAW_DATA_DIR, "openaq_raw_*.csv")

    metrics: List[CleaningMetrics] = [
        _clean_if_available(
            "cpcb",
            cpcb_raw,
            config.PROCESSED_DATA_DIR / "cpcb_cleaned_latest.csv",
        ),
        _clean_if_available(
            "openaq",
            openaq_raw,
            config.PROCESSED_DATA_DIR / "openaq_cleaned_latest.csv",
        ),
    ]

    validated_path = config.METADATA_DIR / "validated_station_metadata.csv"
    validated_df, invalid_coordinates, station_mismatches = validate_station_metadata(
        station_metadata_path=config.METADATA_DIR / "station_metadata.csv",
        output_path=validated_path,
        metadata_dir=config.METADATA_DIR,
        logger=logger,
    )

    station_warnings = []
    if find_official_station_list(config.METADATA_DIR) is None:
        station_warnings.append("official_cpcb_station_list_not_available")

    station_metric = CleaningMetrics(
        dataset="Station Metadata",
        source_file=str(config.METADATA_DIR / "station_metadata.csv"),
        rows_before=len(validated_df),
        rows_after=len(validated_df),
        invalid_coordinates=invalid_coordinates,
        station_metadata_mismatches=station_mismatches,
        warnings=station_warnings,
    )
    metrics.append(station_metric)

    report_path = config.METADATA_DIR / "data_quality_report.csv"
    write_data_quality_report(metrics, report_path)
    logger.info("Data quality report written to %s", report_path)
    logger.info("Validated station metadata written to %s", validated_path)
    logger.info("=========================================")
    logger.info("Data Cleaning & Validation Pipeline run completed!")
    logger.info("=========================================")

    return not any(metric.errors for metric in metrics)


