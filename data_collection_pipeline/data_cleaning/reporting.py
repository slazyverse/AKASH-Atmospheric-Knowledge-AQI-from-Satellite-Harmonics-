"""Data quality report generation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import pandas as pd

from data_collection_pipeline.data_cleaning.cleaners import CleaningMetrics


def write_data_quality_report(metrics: Iterable[CleaningMetrics], output_path: Path) -> pd.DataFrame:
    """Write metadata/data_quality_report.csv from cleaning metrics."""
    cleaning_timestamp = datetime.now(timezone.utc).isoformat()
    rows = []

    for metric in metrics:
        rows.append(
            {
                "Dataset": metric.dataset,
                "Source File": metric.source_file,
                "Rows before cleaning": metric.rows_before,
                "Rows after cleaning": metric.rows_after,
                "Missing values": metric.missing_values,
                "Duplicates removed": metric.duplicates_removed,
                "Duplicate timestamps removed": metric.duplicate_timestamps_removed,
                "Negative pollutant values": metric.negative_pollutant_values,
                "Outlier count": metric.outlier_count,
                "Invalid coordinates": metric.invalid_coordinates,
                "Station metadata mismatches": metric.station_metadata_mismatches,
                "Cleaning timestamp": cleaning_timestamp,
                "Warnings": "; ".join(metric.warnings),
                "Errors": "; ".join(metric.errors),
            }
        )

    report = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(output_path, index=False)
    return report
