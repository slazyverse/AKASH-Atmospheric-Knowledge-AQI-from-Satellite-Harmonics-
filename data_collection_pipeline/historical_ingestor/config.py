"""Historical-pipeline configuration knobs.

All values are loaded from environment variables and default to safe values
that do not affect the existing real-time pipeline.

This module is intentionally separate from the root ``config.py`` so the
historical knobs are co-located with the historical package.  The same values
are also appended to ``config.py`` (Phase 1 S1-01) for convenience when the
root config is the single import point.
"""

from __future__ import annotations

import os
from pathlib import Path

# Re-import FEATURES_DIR from the root config so HIST_OUTPUT_DIR is consistent.
from data_collection_pipeline.config import (
    FEATURES_DIR,
    PROCESSED_DATA_DIR,
    RAW_DATA_DIR,
)

# ---------------------------------------------------------------------------
# Date window
# ---------------------------------------------------------------------------

#: Start of the historical ingestion window (inclusive). ISO-8601 format.
HIST_START_DATE: str = os.getenv("HIST_START_DATE", "2020-01-01")

#: End of the historical ingestion window (inclusive). ISO-8601 format.
HIST_END_DATE: str = os.getenv("HIST_END_DATE", "2024-12-31")

# ---------------------------------------------------------------------------
# Chunking parameters
# ---------------------------------------------------------------------------

#: Number of days per GEE Sentinel-5P collection request chunk.
#: Keep at ≤ 30 to avoid exceeding GEE compute quotas.
HIST_GEE_CHUNK_DAYS: int = int(os.getenv("HIST_GEE_CHUNK_DAYS", "30"))

#: Number of calendar months per ERA5 CDS API batch request.
#: Keep at 1 to stay well within the 1 000-field CDS per-request limit.
HIST_ERA5_CHUNK_MONTHS: int = int(os.getenv("HIST_ERA5_CHUNK_MONTHS", "1"))

# ---------------------------------------------------------------------------
# Output paths
# ---------------------------------------------------------------------------

#: Directory that receives the historical analysis-ready dataset artifacts.
HIST_OUTPUT_DIR: Path = FEATURES_DIR / "historical"

#: Tag prepended to versioned model artifact filenames.
HIST_MODEL_TAG: str = os.getenv("HIST_MODEL_TAG", "historical")

# ---------------------------------------------------------------------------
# Quality gates
# ---------------------------------------------------------------------------

#: Minimum number of non-null AQI training rows required before model training
#: is attempted.  The pipeline aborts with a clear error if this is not met.
HIST_MIN_TRAINING_ROWS: int = int(os.getenv("HIST_MIN_TRAINING_ROWS", "500"))

# ---------------------------------------------------------------------------
# Derived output file paths (convenience references)
# ---------------------------------------------------------------------------

#: Raw concatenated CPCB historical observations.
HIST_CPCB_RAW: Path = RAW_DATA_DIR / "cpcb_raw_historical.csv"

#: Cleaned historical CPCB observations (after data_cleaning/pipeline.py).
HIST_CPCB_CLEANED: Path = PROCESSED_DATA_DIR / "cpcb_cleaned_historical.csv"

#: Concatenated Sentinel-5P / MODIS satellite predictors for the hist window.
HIST_SATELLITE_CSV: Path = PROCESSED_DATA_DIR / "satellite_predictors_hist.csv"

#: Concatenated ERA5 meteorology for the hist window.
HIST_ERA5_CSV: Path = PROCESSED_DATA_DIR / "era5_meteorology_hist.csv"

#: Final merged feature table (written to features/ then collocated).
HIST_MERGED_FEATURE_TABLE: Path = FEATURES_DIR / "merged_feature_table.csv"

#: Analysis-ready dataset produced by dataset_builder.
HIST_ARI_DATASET: Path = HIST_OUTPUT_DIR / "analysis_ready_dataset.csv"
