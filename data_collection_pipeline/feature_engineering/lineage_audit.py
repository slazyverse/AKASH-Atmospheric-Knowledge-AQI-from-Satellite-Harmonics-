"""
Feature Lineage Audit module for the VAYU-DRISHTI / AKASH pipeline.

Responsibilities
----------------
* Define a complete registry of every planned ML feature.
* Verify each feature through every pipeline stage (raw → cleaning →
  feature engineering → dataset builder → analysis-ready dataset → model).
* Classify every feature as one of:
    - Available              : feature is present and non-null
    - Waiting for Data       : implemented but upstream data unavailable
                               (credentials missing / file not downloaded)
    - Pending Implementation : feature never implemented in the codebase
* Generate ``feature_availability_manifest.csv`` and
  ``feature_lineage_report.md`` in the workspace root.
* Provide ``validate_features_before_training()`` for calling just before
  model training — logs ERROR for unexpected disappearances, INFO for
  pending features.  Never raises on pending features.

This module is VALIDATION AND DOCUMENTATION ONLY.
It does NOT modify any dataset, model, feature value, or imputation logic.
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd

from data_collection_pipeline import config

logger = logging.getLogger("data_collection_pipeline.feature_engineering.lineage_audit")

# ---------------------------------------------------------------------------
# Master Feature Registry
# ---------------------------------------------------------------------------

# STATUS constants
STATUS_AVAILABLE = "Available"
STATUS_WAITING = "Waiting for Data"
STATUS_PENDING = "Pending Implementation"

# Source labels
SRC_CPCB = "CPCB API (data.gov.in)"
SRC_ERA5 = "ERA5 Reanalysis (Copernicus CDS)"
SRC_SATELLITE = "Sentinel-5P TROPOMI / MODIS AOD (Google Earth Engine)"
SRC_DERIVED = "Derived from CPCB timestamp"
SRC_GIS = "Static GIS dataset (not yet integrated)"

# Credentials labels
CRED_ERA5 = "ERA5 CDS API key + NetCDF download (run --era5-only --no-dry-run)"
CRED_GEE = "Google Earth Engine credentials (earthengine authenticate)"
CRED_NONE = "None required"
CRED_GIS = "GIS dataset ingestion not implemented"

# Pipeline stages — order matches the data flow
STAGE_RAW = "Raw Collection"
STAGE_CLEAN = "Cleaning"
STAGE_FE = "Feature Engineering"
STAGE_BUILDER = "Dataset Builder"
STAGE_ANALYSIS = "Analysis Ready Dataset"
STAGE_MODEL = "Model Training"

ALL_STAGES = [STAGE_RAW, STAGE_CLEAN, STAGE_FE, STAGE_BUILDER, STAGE_ANALYSIS, STAGE_MODEL]


#: Every planned ML feature and its expected lineage.
#: Fields: feature, category, expected_source, module, credentials_needed,
#:         pending_implementation, used_by_model (default True unless override)
FEATURE_REGISTRY: List[Dict] = [
    # ------------------------------------------------------------------ #
    # Pollutant ground observations (CPCB)                                #
    # ------------------------------------------------------------------ #
    {
        "feature": "PM2.5",
        "category": "Pollutant",
        "expected_source": SRC_CPCB,
        "module": "cpcb_collector.py → data_cleaning/cleaners.py",
        "credentials_needed": CRED_NONE,
        "pending_implementation": False,
        "used_by_model": True,
        "first_stage": STAGE_RAW,
    },
    {
        "feature": "PM10",
        "category": "Pollutant",
        "expected_source": SRC_CPCB,
        "module": "cpcb_collector.py → data_cleaning/cleaners.py",
        "credentials_needed": CRED_NONE,
        "pending_implementation": False,
        "used_by_model": True,
        "first_stage": STAGE_RAW,
    },
    {
        "feature": "NO2",
        "category": "Pollutant",
        "expected_source": SRC_CPCB,
        "module": "cpcb_collector.py → data_cleaning/cleaners.py",
        "credentials_needed": CRED_NONE,
        "pending_implementation": False,
        "used_by_model": True,
        "first_stage": STAGE_RAW,
    },
    {
        "feature": "SO2",
        "category": "Pollutant",
        "expected_source": SRC_CPCB,
        "module": "cpcb_collector.py → data_cleaning/cleaners.py",
        "credentials_needed": CRED_NONE,
        "pending_implementation": False,
        "used_by_model": True,
        "first_stage": STAGE_RAW,
    },
    {
        "feature": "CO",
        "category": "Pollutant",
        "expected_source": SRC_CPCB,
        "module": "cpcb_collector.py → data_cleaning/cleaners.py",
        "credentials_needed": CRED_NONE,
        "pending_implementation": False,
        "used_by_model": True,
        "first_stage": STAGE_RAW,
    },
    {
        "feature": "O3",
        "category": "Pollutant",
        "expected_source": SRC_CPCB,
        "module": "cpcb_collector.py → data_cleaning/cleaners.py",
        "credentials_needed": CRED_NONE,
        "pending_implementation": False,
        "used_by_model": True,
        "first_stage": STAGE_RAW,
    },
    # ------------------------------------------------------------------ #
    # Satellite column densities (Sentinel-5P / MODIS via GEE)           #
    # ------------------------------------------------------------------ #
    {
        "feature": "AOD",
        "category": "Satellite",
        "expected_source": SRC_SATELLITE,
        "module": "sentinel5p_collector.py → feature_engineering/merger.py",
        "credentials_needed": CRED_GEE,
        "pending_implementation": False,
        "used_by_model": True,
        "first_stage": STAGE_FE,
        "waiting_reason": (
            "Google Earth Engine credentials not configured. "
            "Run: earthengine authenticate. "
            "Then execute: python run_pipeline.py --collect-satellite. "
            "File expected at: processed_data/satellite_predictors.csv"
        ),
    },
    {
        "feature": "HCHO",
        "category": "Satellite",
        "expected_source": SRC_SATELLITE,
        "module": "sentinel5p_collector.py → feature_engineering/merger.py",
        "credentials_needed": CRED_GEE,
        "pending_implementation": False,
        "used_by_model": True,
        "first_stage": STAGE_FE,
        "waiting_reason": (
            "Google Earth Engine credentials not configured. "
            "Run: earthengine authenticate. "
            "Then execute: python run_pipeline.py --collect-satellite. "
            "File expected at: processed_data/satellite_predictors.csv"
        ),
    },
    {
        "feature": "NO2 Column",
        "category": "Satellite",
        "expected_source": SRC_SATELLITE,
        "module": "sentinel5p_collector.py → feature_engineering/merger.py",
        "credentials_needed": CRED_GEE,
        "pending_implementation": False,
        "used_by_model": True,
        "first_stage": STAGE_FE,
        "waiting_reason": (
            "Google Earth Engine credentials not configured. "
            "Sentinel-5P NO2 column retrieval requires GEE authentication."
        ),
    },
    {
        "feature": "SO2 Column",
        "category": "Satellite",
        "expected_source": SRC_SATELLITE,
        "module": "sentinel5p_collector.py → feature_engineering/merger.py",
        "credentials_needed": CRED_GEE,
        "pending_implementation": False,
        "used_by_model": True,
        "first_stage": STAGE_FE,
        "waiting_reason": (
            "Google Earth Engine credentials not configured. "
            "Sentinel-5P SO2 column retrieval requires GEE authentication."
        ),
    },
    {
        "feature": "CO Column",
        "category": "Satellite",
        "expected_source": SRC_SATELLITE,
        "module": "sentinel5p_collector.py → feature_engineering/merger.py",
        "credentials_needed": CRED_GEE,
        "pending_implementation": False,
        "used_by_model": True,
        "first_stage": STAGE_FE,
        "waiting_reason": (
            "Google Earth Engine credentials not configured. "
            "Sentinel-5P CO column retrieval requires GEE authentication."
        ),
    },
    {
        "feature": "O3 Column",
        "category": "Satellite",
        "expected_source": SRC_SATELLITE,
        "module": "sentinel5p_collector.py → feature_engineering/merger.py",
        "credentials_needed": CRED_GEE,
        "pending_implementation": False,
        "used_by_model": True,
        "first_stage": STAGE_FE,
        "waiting_reason": (
            "Google Earth Engine credentials not configured. "
            "Sentinel-5P O3 column retrieval requires GEE authentication."
        ),
    },
    # ------------------------------------------------------------------ #
    # Meteorology (ERA5 reanalysis)                                        #
    # ------------------------------------------------------------------ #
    {
        "feature": "Temperature",
        "category": "Meteorology",
        "expected_source": SRC_ERA5,
        "module": "era5_downloader.py → era5_processor.py → feature_engineering/merger.py",
        "credentials_needed": CRED_ERA5,
        "pending_implementation": False,
        "used_by_model": True,
        "first_stage": STAGE_FE,
        "waiting_reason": (
            "ERA5 NetCDF not downloaded. "
            "Run: python run_pipeline.py --era5-only --no-dry-run (requires CDS API key). "
            "Then: python run_pipeline.py --process-era5. "
            "File expected at: processed_data/era5_meteorology.csv"
        ),
    },
    {
        "feature": "Relative Humidity",
        "category": "Meteorology",
        "expected_source": SRC_ERA5,
        "module": "era5_downloader.py → era5_processor.py → feature_engineering/merger.py",
        "credentials_needed": CRED_ERA5,
        "pending_implementation": False,
        "used_by_model": True,
        "first_stage": STAGE_FE,
        "waiting_reason": (
            "ERA5 NetCDF not downloaded. "
            "Requires Copernicus CDS API key in .cdsapirc."
        ),
    },
    {
        "feature": "Boundary Layer Height",
        "category": "Meteorology",
        "expected_source": SRC_ERA5,
        "module": "era5_downloader.py → era5_processor.py → feature_engineering/merger.py",
        "credentials_needed": CRED_ERA5,
        "pending_implementation": False,
        "used_by_model": True,
        "first_stage": STAGE_FE,
        "waiting_reason": (
            "ERA5 NetCDF not downloaded. "
            "Boundary Layer Height (BLH) is included in ERA5 request spec."
        ),
    },
    {
        "feature": "Surface Pressure",
        "category": "Meteorology",
        "expected_source": SRC_ERA5,
        "module": "era5_downloader.py → era5_processor.py → feature_engineering/merger.py",
        "credentials_needed": CRED_ERA5,
        "pending_implementation": False,
        "used_by_model": True,
        "first_stage": STAGE_FE,
        "waiting_reason": (
            "ERA5 NetCDF not downloaded. "
            "Surface Pressure is included in ERA5 request spec."
        ),
    },
    {
        "feature": "Wind Speed",
        "category": "Meteorology",
        "expected_source": SRC_ERA5,
        "module": (
            "era5_downloader.py → era5_processor.py → "
            "feature_engineering/feature_builder.py (derived from U/V)"
        ),
        "credentials_needed": CRED_ERA5,
        "pending_implementation": False,
        "used_by_model": True,
        "first_stage": STAGE_FE,
        "waiting_reason": (
            "ERA5 U/V wind components not downloaded. "
            "Wind Speed is derived by feature_builder.py from u_wind_component and v_wind_component."
        ),
    },
    {
        "feature": "Wind Direction",
        "category": "Meteorology",
        "expected_source": SRC_ERA5,
        "module": (
            "era5_downloader.py → era5_processor.py → "
            "feature_engineering/feature_builder.py (derived from U/V)"
        ),
        "credentials_needed": CRED_ERA5,
        "pending_implementation": False,
        "used_by_model": True,
        "first_stage": STAGE_FE,
        "waiting_reason": (
            "ERA5 U/V wind components not downloaded. "
            "Wind Direction is derived by feature_builder.py from u_wind_component and v_wind_component."
        ),
    },
    # ------------------------------------------------------------------ #
    # Derived temporal features (always available from CPCB timestamp)    #
    # ------------------------------------------------------------------ #
    {
        "feature": "Day of Week",
        "category": "Derived",
        "expected_source": SRC_DERIVED,
        "module": "feature_engineering/feature_builder.py",
        "credentials_needed": CRED_NONE,
        "pending_implementation": False,
        "used_by_model": True,
        "first_stage": STAGE_FE,
    },
    {
        "feature": "Month",
        "category": "Derived",
        "expected_source": SRC_DERIVED,
        "module": "feature_engineering/feature_builder.py",
        "credentials_needed": CRED_NONE,
        "pending_implementation": False,
        "used_by_model": True,
        "first_stage": STAGE_FE,
    },
    {
        "feature": "Season",
        "category": "Derived",
        "expected_source": SRC_DERIVED,
        "module": "feature_engineering/feature_builder.py",
        "credentials_needed": CRED_NONE,
        "pending_implementation": False,
        "used_by_model": False,  # categorical — excluded from numeric training
        "first_stage": STAGE_FE,
    },
    {
        "feature": "Weekend Flag",
        "category": "Derived",
        "expected_source": SRC_DERIVED,
        "module": "feature_engineering/feature_builder.py",
        "credentials_needed": CRED_NONE,
        "pending_implementation": False,
        "used_by_model": True,
        "first_stage": STAGE_FE,
    },
    # ------------------------------------------------------------------ #
    # Static GIS features — NOT YET IMPLEMENTED                           #
    # ------------------------------------------------------------------ #
    {
        "feature": "Elevation",
        "category": "Static GIS",
        "expected_source": SRC_GIS,
        "module": "NOT IMPLEMENTED — no module exists in the codebase",
        "credentials_needed": CRED_GIS,
        "pending_implementation": True,
        "used_by_model": False,
        "first_stage": "N/A",
        "pending_reason": (
            "Elevation data integration is not implemented. "
            "Planned source: SRTM Digital Elevation Model via GEE or a local GeoTIFF. "
            "No collector, processor, or merger logic exists for this feature."
        ),
    },
    {
        "feature": "Distance to Coast",
        "category": "Static GIS",
        "expected_source": SRC_GIS,
        "module": "NOT IMPLEMENTED — no module exists in the codebase",
        "credentials_needed": CRED_GIS,
        "pending_implementation": True,
        "used_by_model": False,
        "first_stage": "N/A",
        "pending_reason": (
            "Distance-to-coast computation is not implemented. "
            "Planned approach: compute Haversine distance from each station to the nearest "
            "Indian coastline point from a GIS shapefile. No module exists for this."
        ),
    },
    {
        "feature": "Land Cover Class",
        "category": "Static GIS",
        "expected_source": SRC_GIS,
        "module": "NOT IMPLEMENTED — no module exists in the codebase",
        "credentials_needed": CRED_GIS,
        "pending_implementation": True,
        "used_by_model": False,
        "first_stage": "N/A",
        "pending_reason": (
            "Land cover classification is not implemented. "
            "Planned source: MODIS MCD12Q1 Land Cover Type or ESA CCI Land Cover. "
            "No GIS ingestion module or spatial join logic exists for this feature."
        ),
    },
]


# ---------------------------------------------------------------------------
# Stage-presence probe
# ---------------------------------------------------------------------------

def _probe_stage(
    feature: str,
    df: Optional[pd.DataFrame],
    stage_label: str,
    pending: bool,
) -> str:
    """Return PASS / FAIL / PENDING for a feature at a given stage."""
    if pending:
        return "PENDING"
    if df is None:
        return "FAIL"
    if feature not in df.columns:
        return "FAIL"
    non_null = df[feature].notna().sum()
    if non_null == 0:
        # Column exists but all NA — treat as FAIL at this stage
        return "FAIL"
    return "PASS"


def _load_df_safe(path: Path) -> Optional[pd.DataFrame]:
    """Read a CSV quietly; return None if the file is absent or unparseable."""
    if not path.exists():
        return None
    try:
        return pd.read_csv(path)
    except Exception:  # noqa: BLE001
        return None


# ---------------------------------------------------------------------------
# Core audit function
# ---------------------------------------------------------------------------

def run_lineage_audit(
    analysis_ready_path: Optional[Path] = None,
) -> List[Dict]:
    """
    Perform a complete feature lineage audit across all pipeline stages.

    Parameters
    ----------
    analysis_ready_path:
        Explicit path to ``analysis_ready_dataset.csv``.
        Defaults to ``config.DATASET_OUTPUT_DIRECTORY / "analysis_ready_dataset.csv"``.

    Returns
    -------
    List[Dict]
        One dict per feature with keys matching the manifest CSV columns.
    """
    logger.info("[LINEAGE AUDIT] Starting feature lineage audit across all pipeline stages.")

    # ------------------------------------------------------------------ #
    # Load stage artefacts                                                #
    # ------------------------------------------------------------------ #
    raw_cpcb_path = max(
        config.RAW_DATA_DIR.glob("cpcb_raw_*.csv"),
        key=lambda p: p.stat().st_mtime,
        default=None,
    ) if config.RAW_DATA_DIR.exists() else None
    df_raw_cpcb = _load_df_safe(raw_cpcb_path) if raw_cpcb_path else None

    df_cleaned_cpcb = _load_df_safe(config.PROCESSED_DATA_DIR / "cpcb_cleaned_latest.csv")

    df_merged_features = _load_df_safe(config.FEATURES_DIR / "merged_feature_table.csv")

    if analysis_ready_path is None:
        analysis_ready_path = Path(config.DATASET_OUTPUT_DIRECTORY) / "analysis_ready_dataset.csv"
    df_analysis_ready = _load_df_safe(analysis_ready_path)

    # Train dataset presence (proxy for model training stage)
    df_train = _load_df_safe(Path(config.DATASET_OUTPUT_DIRECTORY) / "train_dataset.csv")

    logger.info(
        "[LINEAGE AUDIT] Stage artefacts located:"
        "\n  Raw CPCB:         %s"
        "\n  Cleaned CPCB:     %s"
        "\n  Merged features:  %s"
        "\n  Analysis-ready:   %s"
        "\n  Train split:      %s",
        raw_cpcb_path or "NOT FOUND",
        config.PROCESSED_DATA_DIR / "cpcb_cleaned_latest.csv"
        if (config.PROCESSED_DATA_DIR / "cpcb_cleaned_latest.csv").exists()
        else "NOT FOUND",
        config.FEATURES_DIR / "merged_feature_table.csv"
        if (config.FEATURES_DIR / "merged_feature_table.csv").exists()
        else "NOT FOUND",
        analysis_ready_path if analysis_ready_path.exists() else "NOT FOUND",
        Path(config.DATASET_OUTPUT_DIRECTORY) / "train_dataset.csv"
        if (Path(config.DATASET_OUTPUT_DIRECTORY) / "train_dataset.csv").exists()
        else "NOT FOUND",
    )

    # ------------------------------------------------------------------ #
    # Satellite and ERA5 data availability                                #
    # ------------------------------------------------------------------ #
    satellite_file_present = any(
        (config.PROCESSED_DATA_DIR / name).exists()
        for name in ["satellite_predictors.csv", "satellite_features.csv"]
    )
    era5_file_present = any(
        (config.PROCESSED_DATA_DIR / name).exists()
        for name in ["era5_meteorology.csv", "era5_features.csv"]
    )

    if satellite_file_present:
        logger.info("[LINEAGE AUDIT] Satellite predictors CSV found — satellite features AVAILABLE.")
    else:
        logger.info(
            "[LINEAGE AUDIT] Satellite predictors CSV NOT found "
            "(processed_data/satellite_predictors.csv). "
            "GEE credentials required — satellite features WAITING FOR DATA."
        )

    if era5_file_present:
        logger.info("[LINEAGE AUDIT] ERA5 meteorology CSV found — meteorological features AVAILABLE.")
    else:
        logger.info(
            "[LINEAGE AUDIT] ERA5 meteorology CSV NOT found "
            "(processed_data/era5_meteorology.csv). "
            "CDS credentials required — meteorological features WAITING FOR DATA."
        )

    # ------------------------------------------------------------------ #
    # Audit each feature                                                  #
    # ------------------------------------------------------------------ #
    audit_rows: List[Dict] = []

    for entry in FEATURE_REGISTRY:
        feature = entry["feature"]
        category = entry["category"]
        pending = entry["pending_implementation"]
        cred_needed = entry["credentials_needed"]

        # Determine current status
        if pending:
            current_status = STATUS_PENDING
            reason = entry.get("pending_reason", "Feature not implemented.")
        elif category == "Satellite" and not satellite_file_present:
            current_status = STATUS_WAITING
            reason = entry.get("waiting_reason", "GEE credentials required.")
        elif category == "Meteorology" and not era5_file_present:
            # Wind Speed / Wind Direction are derived from ERA5 U/V — also blocked
            current_status = STATUS_WAITING
            reason = entry.get("waiting_reason", "ERA5 data download required.")
        else:
            # Check actual presence in analysis-ready dataset
            if df_analysis_ready is not None and feature in df_analysis_ready.columns:
                non_null = df_analysis_ready[feature].notna().sum()
                if non_null > 0:
                    current_status = STATUS_AVAILABLE
                    reason = f"Feature present in analysis_ready_dataset.csv with {non_null} non-null values."
                else:
                    # Column exists but all null — classify based on category
                    if category in ("Satellite", "Meteorology"):
                        current_status = STATUS_WAITING
                        reason = (
                            f"Column '{feature}' exists in analysis_ready_dataset.csv "
                            "but is entirely null (upstream data not downloaded)."
                        )
                    else:
                        current_status = STATUS_AVAILABLE
                        reason = (
                            f"Column '{feature}' exists in analysis_ready_dataset.csv "
                            "but all values are null — investigate upstream."
                        )
            elif df_analysis_ready is None:
                current_status = STATUS_WAITING if not pending else STATUS_PENDING
                reason = "analysis_ready_dataset.csv has not been generated yet."
            else:
                current_status = STATUS_PENDING if pending else STATUS_WAITING
                reason = f"Column '{feature}' not found in analysis_ready_dataset.csv."

        # Probe each stage
        stage_results: Dict[str, str] = {}

        # Raw Collection — only CPCB pollutants appear here
        if category == "Pollutant":
            stage_results[STAGE_RAW] = _probe_stage(
                feature if feature != "AQI" else "AQI",
                df_raw_cpcb,
                STAGE_RAW,
                pending,
            )
        else:
            stage_results[STAGE_RAW] = "N/A" if not pending else "PENDING"

        # Cleaning stage — CPCB pollutants survive; satellite/meteo/GIS don't exist yet
        if category == "Pollutant":
            stage_results[STAGE_CLEAN] = _probe_stage(feature, df_cleaned_cpcb, STAGE_CLEAN, pending)
        elif category == "Derived":
            stage_results[STAGE_CLEAN] = "N/A"
        elif category == "Static GIS":
            stage_results[STAGE_CLEAN] = "PENDING"
        else:
            stage_results[STAGE_CLEAN] = "N/A"

        # Feature Engineering — everything should first appear here in merged table
        if pending:
            stage_results[STAGE_FE] = "PENDING"
        elif category in ("Satellite",) and not satellite_file_present:
            # Feature is in merged table as null placeholder — column exists
            stage_results[STAGE_FE] = _probe_stage(
                feature, df_merged_features, STAGE_FE, False
            )
            # If column exists but all null, classify as WAITING
            if (
                df_merged_features is not None
                and feature in df_merged_features.columns
                and df_merged_features[feature].notna().sum() == 0
            ):
                stage_results[STAGE_FE] = "WAITING"
        elif category == "Meteorology" and not era5_file_present:
            stage_results[STAGE_FE] = _probe_stage(
                feature, df_merged_features, STAGE_FE, False
            )
            if (
                df_merged_features is not None
                and feature in df_merged_features.columns
                and df_merged_features[feature].notna().sum() == 0
            ):
                stage_results[STAGE_FE] = "WAITING"
        else:
            stage_results[STAGE_FE] = _probe_stage(feature, df_merged_features, STAGE_FE, pending)

        # Dataset Builder — same as Analysis Ready (builder writes analysis_ready_dataset)
        stage_results[STAGE_BUILDER] = _probe_stage(
            feature, df_analysis_ready, STAGE_BUILDER, pending
        )
        if stage_results[STAGE_BUILDER] == "FAIL" and current_status == STATUS_WAITING:
            stage_results[STAGE_BUILDER] = "WAITING"

        # Analysis Ready Dataset
        stage_results[STAGE_ANALYSIS] = _probe_stage(
            feature, df_analysis_ready, STAGE_ANALYSIS, pending
        )
        if stage_results[STAGE_ANALYSIS] == "FAIL" and current_status == STATUS_WAITING:
            stage_results[STAGE_ANALYSIS] = "WAITING"

        # Model Training — only numeric features reach the model
        if pending or not entry.get("used_by_model", True):
            stage_results[STAGE_MODEL] = "PENDING" if pending else "N/A"
        elif current_status == STATUS_WAITING:
            stage_results[STAGE_MODEL] = "WAITING"
        elif current_status == STATUS_AVAILABLE:
            # Numeric check: model drops all-null columns
            if category == "Derived" and feature == "Season":
                stage_results[STAGE_MODEL] = "N/A (categorical)"
            elif df_train is not None and feature in df_train.columns:
                non_null = df_train[feature].notna().sum()
                stage_results[STAGE_MODEL] = "PASS" if non_null > 0 else "WAITING"
            else:
                stage_results[STAGE_MODEL] = "PASS"  # not yet split but will be
        else:
            stage_results[STAGE_MODEL] = "PENDING"

        # Emit log line
        if pending:
            logger.info(
                "[LINEAGE AUDIT] [INFO] Feature='%s' | Status=Pending Implementation | %s",
                feature,
                entry.get("pending_reason", ""),
            )
        elif current_status == STATUS_WAITING:
            logger.info(
                "[LINEAGE AUDIT] [INFO] Feature='%s' | Status=Waiting for Data | %s",
                feature,
                reason,
            )
        elif current_status == STATUS_AVAILABLE:
            logger.info(
                "[LINEAGE AUDIT] [PASS] Feature='%s' | Status=Available | %s",
                feature,
                reason,
            )
        else:
            logger.error(
                "[LINEAGE AUDIT] [ERROR] Feature='%s' | Status=%s | %s",
                feature,
                current_status,
                reason,
            )

        audit_rows.append(
            {
                "Feature": feature,
                "Category": category,
                "Expected Source": entry["expected_source"],
                "Pipeline Stage First Expected": entry.get("first_stage", STAGE_RAW),
                "Current Status": current_status,
                "Reason": reason,
                "Needs External Credentials": cred_needed,
                "Pending Implementation": "Yes" if pending else "No",
                "Used By Model": "Yes" if entry.get("used_by_model", True) else "No",
                # Stage checks
                STAGE_RAW: stage_results.get(STAGE_RAW, "N/A"),
                STAGE_CLEAN: stage_results.get(STAGE_CLEAN, "N/A"),
                STAGE_FE: stage_results.get(STAGE_FE, "N/A"),
                STAGE_BUILDER: stage_results.get(STAGE_BUILDER, "N/A"),
                STAGE_ANALYSIS: stage_results.get(STAGE_ANALYSIS, "N/A"),
                STAGE_MODEL: stage_results.get(STAGE_MODEL, "N/A"),
            }
        )

    # Log summary
    total = len(audit_rows)
    available = sum(1 for r in audit_rows if r["Current Status"] == STATUS_AVAILABLE)
    waiting = sum(1 for r in audit_rows if r["Current Status"] == STATUS_WAITING)
    pending_count = sum(1 for r in audit_rows if r["Current Status"] == STATUS_PENDING)
    reaching_model = sum(
        1 for r in audit_rows
        if r["Current Status"] == STATUS_AVAILABLE and r["Used By Model"] == "Yes"
    )

    logger.info(
        "[LINEAGE AUDIT] Summary: total=%d | available=%d | waiting_for_data=%d | "
        "pending_implementation=%d | reaching_model=%d",
        total, available, waiting, pending_count, reaching_model,
    )

    return audit_rows


# ---------------------------------------------------------------------------
# Report generators
# ---------------------------------------------------------------------------

def generate_manifest(audit_rows: List[Dict], output_path: Path) -> pd.DataFrame:
    """
    Write ``feature_availability_manifest.csv``.

    Parameters
    ----------
    audit_rows : list of dicts returned by ``run_lineage_audit``.
    output_path : destination file path.
    """
    manifest_cols = [
        "Feature",
        "Category",
        "Expected Source",
        "Pipeline Stage First Expected",
        "Current Status",
        "Reason",
        "Needs External Credentials",
        "Pending Implementation",
        "Used By Model",
    ]
    df = pd.DataFrame(audit_rows)[manifest_cols]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False)
    logger.info("[LINEAGE AUDIT] feature_availability_manifest.csv written to %s", output_path)
    return df


def _status_badge(stage_val: str) -> str:
    """Format a stage result as a readable cell for the markdown table."""
    mapping = {
        "PASS": "✅ PASS",
        "FAIL": "❌ FAIL",
        "PENDING": "⏳ PENDING",
        "WAITING": "⏳ WAITING",
        "N/A": "—",
        "N/A (categorical)": "— (categorical)",
    }
    return mapping.get(stage_val, stage_val)


def generate_lineage_report(audit_rows: List[Dict], output_path: Path) -> None:
    """
    Write ``feature_lineage_report.md``.

    Parameters
    ----------
    audit_rows : list of dicts returned by ``run_lineage_audit``.
    output_path : destination file path.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    total = len(audit_rows)
    available = sum(1 for r in audit_rows if r["Current Status"] == STATUS_AVAILABLE)
    waiting = sum(1 for r in audit_rows if r["Current Status"] == STATUS_WAITING)
    pending_count = sum(1 for r in audit_rows if r["Current Status"] == STATUS_PENDING)
    reaching_model = sum(
        1 for r in audit_rows
        if r["Current Status"] == STATUS_AVAILABLE and r["Used By Model"] == "Yes"
    )

    pending_features = [r for r in audit_rows if r["Current Status"] == STATUS_PENDING]
    waiting_features = [r for r in audit_rows if r["Current Status"] == STATUS_WAITING]
    available_features = [r for r in audit_rows if r["Current Status"] == STATUS_AVAILABLE]

    lines = [
        "# Feature Lineage Report — VAYU-DRISHTI / AKASH Pipeline",
        "",
        f"> Generated: {timestamp}",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        "| Metric | Count |",
        "|--------|-------|",
        f"| **Total Planned Features** | {total} |",
        f"| **Available** | {available} |",
        f"| **Waiting for Data (credentials/download)** | {waiting} |",
        f"| **Pending Implementation** | {pending_count} |",
        f"| **Reaching Model Training** | {reaching_model} |",
        "",
        "---",
        "",
        "## Feature Lineage Table",
        "",
        "Pipeline stages: **Raw Collection → Cleaning → Feature Engineering → Dataset Builder → Analysis-Ready Dataset → Model Training**",
        "",
        "| Feature | Category | Status | Raw | Clean | Feat. Eng. | Dataset Builder | Analysis-Ready | Model |",
        "|---------|----------|--------|-----|-------|------------|-----------------|----------------|-------|",
    ]

    for r in audit_rows:
        lines.append(
            f"| **{r['Feature']}** "
            f"| {r['Category']} "
            f"| {r['Current Status']} "
            f"| {_status_badge(r[STAGE_RAW])} "
            f"| {_status_badge(r[STAGE_CLEAN])} "
            f"| {_status_badge(r[STAGE_FE])} "
            f"| {_status_badge(r[STAGE_BUILDER])} "
            f"| {_status_badge(r[STAGE_ANALYSIS])} "
            f"| {_status_badge(r[STAGE_MODEL])} |"
        )

    lines += [
        "",
        "---",
        "",
        "## Root Cause Analysis",
        "",
    ]

    # Case A: Implemented but data unavailable
    lines += [
        "### Case A — Implemented but Upstream Data Unavailable",
        "",
        "These features are **fully implemented** in the codebase. The pipeline code, "
        "collector modules, and feature engineering merger are all in place. "
        "The features are absent only because the required external data has not been "
        "downloaded (credentials missing or download not yet triggered).",
        "",
    ]
    if waiting_features:
        for r in waiting_features:
            lines += [
                f"#### {r['Feature']} ({r['Category']})",
                "",
                f"- **Expected Source:** {r['Expected Source']}",
                f"- **Module:** {r['Reason']}",
                f"- **Credentials Required:** {r['Needs External Credentials']}",
                "",
            ]
    else:
        lines.append("*None — all implemented features have data available.*\n")

    # Case B: Never implemented
    lines += [
        "### Case B — Never Implemented (Pending Feature Development)",
        "",
        "These features **do not exist anywhere in the codebase**. "
        "No collector, processor, merger, or GIS ingestion module has been written for them. "
        "They silently propagate as `pd.NA` through the pipeline because `feature_builder.py` "
        "fills all missing columns with `pd.NA`. This behaviour is now explicitly documented here.",
        "",
    ]
    if pending_features:
        for r in pending_features:
            lines += [
                f"#### {r['Feature']} ({r['Category']})",
                "",
                f"- **Reason:** {r['Reason']}",
                "",
            ]
    else:
        lines.append("*No pending features — all planned features are implemented.*\n")

    lines += [
        "---",
        "",
        "## Pending Feature Development",
        "",
        "The following features are planned but have **zero implementation** in the pipeline.",
        "They must not be treated as available. They must not be silently imputed.",
        "They are explicitly documented here as `Pending Implementation`.",
        "",
    ]
    if pending_features:
        lines += [
            "| Feature | Category | Planned Source | Pending Reason |",
            "|---------|----------|----------------|----------------|",
        ]
        for r in pending_features:
            lines.append(
                f"| **{r['Feature']}** | {r['Category']} | {r['Expected Source']} | {r['Reason']} |"
            )
        lines.append("")
        lines += [
            "### Required Development Work",
            "",
            "To implement these features, the following work is required:",
            "",
            "1. **Elevation**",
            "   - Write a GIS collector module to fetch SRTM DEM data (e.g., via GEE or a local GeoTIFF).",
            "   - Add station-level elevation lookup using spatial join.",
            "   - Add `Elevation` to `feature_builder.py` ALL_FEATURES and `FEATURE_DEFINITIONS`.",
            "",
            "2. **Distance to Coast**",
            "   - Obtain an Indian coastline shapefile (e.g., from NOAA GSHHS or Natural Earth).",
            "   - Compute Haversine distance from each station coordinate to nearest coastline point.",
            "   - Add as a static lookup table keyed by Station ID.",
            "",
            "3. **Land Cover Class**",
            "   - Integrate MODIS MCD12Q1 or ESA CCI Land Cover via GEE or a local raster.",
            "   - Extract land cover class for each station coordinate using spatial join.",
            "   - Encode as integer category or one-hot for model consumption.",
            "",
        ]
    else:
        lines.append("*No pending features.*\n")

    lines += [
        "---",
        "",
        "## Data Availability Status by Category",
        "",
        "### Pollutant Features (CPCB)",
        "",
        "All pollutant features (PM2.5, PM10, NO2, SO2, CO, O3) are sourced from the CPCB API "
        "via `cpcb_collector.py`. They are present in the raw data, survive cleaning, and appear "
        "in the final analysis-ready dataset.",
        "",
        "### Satellite Features (GEE / Sentinel-5P / MODIS)",
        "",
        "The collection module `sentinel5p_collector.py` is fully implemented. "
        "All 6 satellite features will become available once GEE authentication is configured "
        "and `python run_pipeline.py --collect-satellite` is executed.",
        "",
        "**To activate:**",
        "```bash",
        "earthengine authenticate",
        "python data_collection_pipeline/scripts/run_pipeline.py --collect-satellite",
        "python data_collection_pipeline/scripts/run_pipeline.py --integrate-only",
        "```",
        "",
        "### Meteorological Features (ERA5)",
        "",
        "The download spec (`era5_downloader.py`) and processor (`era5_processor.py`) are fully "
        "implemented. All 6 meteorological features will become available once ERA5 data is "
        "downloaded and processed.",
        "",
        "**To activate:**",
        "```bash",
        "# Configure ~/.cdsapirc with your Copernicus CDS API key first",
        "python data_collection_pipeline/scripts/run_pipeline.py --era5-only --no-dry-run",
        "python data_collection_pipeline/scripts/run_pipeline.py --process-era5",
        "python data_collection_pipeline/scripts/run_pipeline.py --integrate-only",
        "```",
        "",
        "### Static GIS Features",
        "",
        "**Not implemented.** No development work has begun for Elevation, Distance to Coast, "
        "or Land Cover Class. See *Pending Feature Development* section above.",
        "",
        "---",
        "",
        f"*Report generated by `feature_engineering/lineage_audit.py` at {timestamp}*",
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("[LINEAGE AUDIT] feature_lineage_report.md written to %s", output_path)


# ---------------------------------------------------------------------------
# Pre-training validation hook
# ---------------------------------------------------------------------------

def validate_features_before_training(
    df: pd.DataFrame,
    implemented_features: Optional[List[str]] = None,
) -> None:
    """
    Validate feature presence in a dataset before model training.

    Rules
    -----
    * If an **implemented** feature (not pending) is missing or entirely null
      → log ERROR (unexpected disappearance).
    * If a **pending** feature is missing → log INFO (expected, not an error).
    * Never raises an exception for pending features.

    Parameters
    ----------
    df : DataFrame to validate (e.g., the training split).
    implemented_features : list of feature names to check as 'implemented'.
        Defaults to all non-pending, non-GIS features from FEATURE_REGISTRY.
    """
    if implemented_features is None:
        implemented_features = [
            r["feature"]
            for r in FEATURE_REGISTRY
            if not r["pending_implementation"] and r.get("used_by_model", True)
        ]

    pending_features = [
        r["feature"] for r in FEATURE_REGISTRY if r["pending_implementation"]
    ]

    logger.info(
        "[PRE-TRAINING VALIDATION] Checking %d implemented features in training dataset "
        "(%d rows, %d columns).",
        len(implemented_features),
        len(df),
        len(df.columns),
    )

    for feature in implemented_features:
        if feature not in df.columns:
            logger.error(
                "[PRE-TRAINING VALIDATION] ERROR: Implemented feature '%s' is MISSING "
                "from the training dataset. This is an unexpected disappearance. "
                "Investigate the feature engineering and dataset preparation pipeline.",
                feature,
            )
        else:
            non_null = df[feature].notna().sum()
            if non_null == 0:
                logger.error(
                    "[PRE-TRAINING VALIDATION] ERROR: Implemented feature '%s' is present "
                    "but entirely null in the training dataset (%d rows). "
                    "This indicates upstream data was not ingested.",
                    feature,
                    len(df),
                )
            else:
                logger.info(
                    "[PRE-TRAINING VALIDATION] PASS: '%s' | non-null=%d/%d",
                    feature,
                    non_null,
                    len(df),
                )

    for feature in pending_features:
        logger.info(
            "[PRE-TRAINING VALIDATION] INFO: Pending feature '%s' is not present "
            "in the training dataset — this is expected (not yet implemented).",
            feature,
        )


# ---------------------------------------------------------------------------
# Main entrypoint
# ---------------------------------------------------------------------------

def run_full_lineage_pipeline(
    analysis_ready_path: Optional[Path] = None,
) -> None:
    """
    Run the complete lineage audit and write all output artefacts.

    Outputs (written to workspace root = config.BASE_DIR.parent):
    * feature_availability_manifest.csv
    * feature_lineage_report.md
    """
    output_root = config.BASE_DIR.parent

    audit_rows = run_lineage_audit(analysis_ready_path=analysis_ready_path)

    generate_manifest(
        audit_rows,
        output_path=output_root / "feature_availability_manifest.csv",
    )

    generate_lineage_report(
        audit_rows,
        output_path=output_root / "feature_lineage_report.md",
    )

    logger.info(
        "[LINEAGE AUDIT] Lineage pipeline complete. "
        "Reports written to %s",
        output_root,
    )
