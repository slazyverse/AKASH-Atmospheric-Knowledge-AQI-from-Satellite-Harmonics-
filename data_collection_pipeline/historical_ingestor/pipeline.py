"""Historical Training Pipeline orchestrator.

``run_historical_pipeline`` is the single entry point for Phase 1.  It
wires together all existing and new modules in the correct order to produce
a reproducible ``analysis_ready_dataset.csv`` from historical data and then
train a versioned baseline model on it.

Workflow
--------
1. ``HistoricalCPCBLoader.load()``            — raw historical observations
2. ``run_cleaning_pipeline(source_file=...)`` — cleaning + station validation
3. ``HistoricalSatelliteCollector.collect()`` — Sentinel-5P / MODIS (optional)
4. ``HistoricalERA5Collector.collect()``      — ERA5 meteorology (optional)
5. ``integrate_datasets(satellite_path=..., era5_path=...)`` — feature merge
6. ``build_analysis_dataset()``              — collocation + target validation
7. ``run_training_pipeline()``               — baseline RandomForest training

All downstream modules are called through their existing public APIs with
optional kwargs that default-to-None when the historical overrides are not
needed (i.e. the real-time pipeline remains unaffected).
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import Optional

from data_collection_pipeline import config as root_config, setup, utils
from data_collection_pipeline.data_cleaning.pipeline import run_cleaning_pipeline
from data_collection_pipeline.dataset_preparation.dataset_builder import (
    build_analysis_dataset,
)
from data_collection_pipeline.feature_engineering.merger import run_integration_pipeline
from data_collection_pipeline.historical_ingestor import config as hist_config
from data_collection_pipeline.historical_ingestor.cpcb_loader import HistoricalCPCBLoader
from data_collection_pipeline.historical_ingestor.era5_collector import HistoricalERA5Collector
from data_collection_pipeline.historical_ingestor.satellite_collector import HistoricalSatelliteCollector
from data_collection_pipeline.model_training.baseline_model import run_training_pipeline

logger = logging.getLogger("data_collection_pipeline.historical_ingestor.pipeline")


def run_historical_pipeline(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    skip_satellite: bool = False,
    skip_era5: bool = False,
    csv_folder: Optional[str] = None,
    use_openaq: bool = True,
) -> bool:
    """Run the full historical ingestion and baseline-model training pipeline.

    Parameters
    ----------
    start_date:
        ISO-8601 start date (``YYYY-MM-DD``).  Defaults to
        ``hist_config.HIST_START_DATE`` (env: ``HIST_START_DATE``).
    end_date:
        ISO-8601 end date (``YYYY-MM-DD``).  Defaults to
        ``hist_config.HIST_END_DATE`` (env: ``HIST_END_DATE``).
    skip_satellite:
        When ``True``, skip GEE Sentinel-5P / MODIS collection.  The merger
        will fall back to placeholder satellite data.  Useful when GEE
        credentials are unavailable.
    skip_era5:
        When ``True``, skip ERA5 CDS API collection.  The merger will fall
        back to placeholder meteorological data.  Useful when CDS API
        credentials are unavailable.
    csv_folder:
        Path to a directory containing local CPCB annual/monthly CSV exports.
        When ``None``, defaults to ``raw_data/historical/cpcb/``.
    use_openaq:
        When ``True`` (the default), the OpenAQ API is also queried for the
        requested date range in addition to any local CSV files.

    Returns
    -------
    bool
        ``True`` if the pipeline completed successfully (model artifact
        written); ``False`` on any fatal error.
    """
    setup.init_workspace()
    utils.setup_logging()
    
    import os
    if skip_satellite:
        os.environ["SKIP_SATELLITE_MERGE"] = "1"
    else:
        os.environ.pop("SKIP_SATELLITE_MERGE", None)
        
    if skip_era5:
        os.environ["SKIP_ERA5_MERGE"] = "1"
    else:
        os.environ.pop("SKIP_ERA5_MERGE", None)

    start_date = start_date or hist_config.HIST_START_DATE
    end_date = end_date or hist_config.HIST_END_DATE

    logger.info("=" * 55)
    logger.info("AKASH Phase 1 — Historical Training Pipeline")
    logger.info("=" * 55)
    logger.info("Date range : %s → %s", start_date, end_date)
    logger.info("skip_satellite: %s | skip_era5: %s", skip_satellite, skip_era5)
    logger.info("use_openaq   : %s | csv_folder: %s", use_openaq, csv_folder or "<default>")

    # ------------------------------------------------------------------
    # Step 1: Load raw historical CPCB / OpenAQ observations
    # ------------------------------------------------------------------
    logger.info("[Step 1/7] Loading historical CPCB/OpenAQ observations...")
    try:
        loader = HistoricalCPCBLoader(
            csv_folder=Path(csv_folder) if csv_folder else None,
            use_openaq=use_openaq,
        )
        loader.load(start_date=start_date, end_date=end_date)
    except RuntimeError as exc:
        logger.error("[Step 1/7] FAILED: %s", exc)
        return False

    # ------------------------------------------------------------------
    # Step 2: Clean observations + validate stations
    # ------------------------------------------------------------------
    logger.info("[Step 2/7] Running data cleaning pipeline (historical mode)...")
    clean_ok = run_cleaning_pipeline(source_file=str(hist_config.HIST_CPCB_RAW))
    if not clean_ok:
        logger.warning(
            "[Step 2/7] Cleaning pipeline reported errors; continuing with "
            "whatever was produced."
        )

    # Swap the CPCB observations loader to read cpcb_cleaned_historical.csv.
    # We do this by temporarily overriding the CPCB cleaned file path expected
    # by merger.load_cpcb_observations() via a lightweight monkey-patch approach:
    # create a symlink-equivalent by copying to cpcb_cleaned_latest.csv only
    # if no real-time file is present, otherwise keep them separate and use
    # the path-override in integrate_datasets().
    # The cleanest approach: we override merger.load_cpcb_observations to load
    # from the historical cleaned file.  We achieve this by updating
    # the processed_data/ symlink-file so that merger.py picks it up.
    _swap_cpcb_cleaned_for_historical()

    # ------------------------------------------------------------------
    # Step 3: Collect Sentinel-5P / MODIS satellite data
    # ------------------------------------------------------------------
    satellite_path: Optional[Path] = None
    if not skip_satellite:
        logger.info("[Step 3/7] Collecting historical satellite data...")
        try:
            sat_collector = HistoricalSatelliteCollector()
            sat_df = sat_collector.collect(start_date=start_date, end_date=end_date)
            if not sat_df.empty:
                satellite_path = hist_config.HIST_SATELLITE_CSV
                logger.info(
                    "[Step 3/7] Satellite collection complete (%d rows).", len(sat_df)
                )
            else:
                logger.warning(
                    "[Step 3/7] Satellite collection returned no data; "
                    "merger will use placeholder satellite features."
                )
        except Exception as exc:  # noqa: BLE001
            logger.error("[Step 3/7] Satellite collection failed: %s", exc)
            logger.warning("Continuing without satellite data (placeholder mode).")
    else:
        logger.info("[Step 3/7] Satellite collection SKIPPED (--skip-satellite).")

    # ------------------------------------------------------------------
    # Step 4: Collect ERA5 meteorological data
    # ------------------------------------------------------------------
    era5_path: Optional[Path] = None
    if not skip_era5:
        logger.info("[Step 4/7] Collecting historical ERA5 meteorological data...")
        try:
            era5_collector = HistoricalERA5Collector()
            era5_df = era5_collector.collect(start_date=start_date, end_date=end_date)
            if not era5_df.empty:
                era5_path = hist_config.HIST_ERA5_CSV
                logger.info(
                    "[Step 4/7] ERA5 collection complete (%d rows).", len(era5_df)
                )
            else:
                logger.warning(
                    "[Step 4/7] ERA5 collection returned no data; "
                    "merger will use placeholder meteorological features."
                )
        except Exception as exc:  # noqa: BLE001
            logger.error("[Step 4/7] ERA5 collection failed: %s", exc)
            logger.warning("Continuing without ERA5 data (placeholder mode).")
    else:
        logger.info("[Step 4/7] ERA5 collection SKIPPED (--skip-era5).")

    # ------------------------------------------------------------------
    # Step 5: Feature engineering — merge satellite + ERA5 into features
    # ------------------------------------------------------------------
    logger.info("[Step 5/7] Running feature engineering integration pipeline...")
    temporal_strategy = root_config.TEMPORAL_ALIGNMENT
    missing_strategy = root_config.MISSING_VALUE_STRATEGY

    try:
        from data_collection_pipeline.feature_engineering.merger import integrate_datasets
        import data_collection_pipeline.feature_engineering.merger as _merger_mod

        merged_features, data_sources = integrate_datasets(
            temporal_strategy=temporal_strategy,
            missing_strategy=missing_strategy,
            satellite_path=satellite_path,
            era5_path=era5_path,
        )
        output_path = root_config.FEATURES_DIR / "merged_feature_table.csv"
        root_config.FEATURES_DIR.mkdir(parents=True, exist_ok=True)
        merged_features.to_csv(output_path, index=False)
        logger.info(
            "[Step 5/7] Merged feature table written: %s (%d rows, %d cols).",
            output_path, len(merged_features), len(merged_features.columns),
        )
    except (FileNotFoundError, ValueError, OSError) as exc:
        logger.error("[Step 5/7] Feature integration failed: %s", exc)
        return False

    # ------------------------------------------------------------------
    # Step 6: Build analysis-ready dataset
    # ------------------------------------------------------------------
    logger.info("[Step 6/7] Building analysis-ready dataset...")
    hist_config.HIST_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    try:
        collocated_df, X, y = build_analysis_dataset(
            file_path=root_config.FEATURES_DIR / "merged_feature_table.csv"
        )
        ari_path = hist_config.HIST_ARI_DATASET
        collocated_df.to_csv(ari_path, index=False)
        logger.info(
            "[Step 6/7] Analysis-ready dataset written: %s (%d rows).",
            ari_path, len(collocated_df),
        )
    except (FileNotFoundError, ValueError) as exc:
        logger.error("[Step 6/7] Dataset build failed: %s", exc)
        return False

    # Guard: ensure we have enough data to train meaningfully.
    non_null_target = y.notna().sum()
    min_rows = hist_config.HIST_MIN_TRAINING_ROWS
    if non_null_target < min_rows:
        logger.error(
            "[Step 6/7] Insufficient training data: %d non-null target rows "
            "(minimum required: %d).  Aborting model training.",
            non_null_target, min_rows,
        )
        return False
    logger.info(
        "[Step 6/7] Training data guard passed: %d non-null target rows.", non_null_target
    )

    # ------------------------------------------------------------------
    # Step 7: Train baseline model on historical data
    # ------------------------------------------------------------------
    logger.info("[Step 7/7] Training baseline model on historical dataset...")
    date_tag = datetime.datetime.now().strftime("%Y%m%d")
    model_tag = hist_config.HIST_MODEL_TAG
    output_dir = hist_config.HIST_OUTPUT_DIR

    try:
        model_pipeline = run_training_pipeline(
            data_path=ari_path,
            output_dir=output_dir,
        )

        # Rename the generic baseline_model.joblib to a versioned filename
        # so it does not overwrite the real-time production model.
        generic_model = output_dir / "baseline_model.joblib"
        versioned_model = output_dir / f"{model_tag}_baseline_{date_tag}.joblib"
        if generic_model.exists():
            if versioned_model.exists():
                versioned_model.unlink()
            generic_model.rename(versioned_model)
            logger.info(
                "[Step 7/7] Model saved as versioned artifact: %s", versioned_model
            )
        else:
            logger.warning(
                "[Step 7/7] Expected model file %s not found after training.",
                generic_model,
            )

    except Exception as exc:  # noqa: BLE001
        logger.error("[Step 7/7] Model training failed: %s", exc)
        return False

    logger.info("=" * 55)
    logger.info("Phase 1 Historical Training Pipeline COMPLETE")
    logger.info("=" * 55)
    logger.info("Output dataset : %s", hist_config.HIST_ARI_DATASET)
    logger.info("Model artifact : %s/%s_baseline_%s.joblib", output_dir, model_tag, date_tag)
    return True


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _swap_cpcb_cleaned_for_historical() -> None:
    """Copy cpcb_cleaned_historical.csv → cpcb_cleaned_latest.csv if the
    historical file exists and is newer than (or replacing) the latest file.

    This allows ``merger.load_cpcb_observations()`` — which reads
    ``cpcb_cleaned_latest.csv`` — to transparently pick up historical data
    without any code changes in the merger.

    The original ``cpcb_cleaned_latest.csv`` (real-time data) is backed up
    as ``cpcb_cleaned_latest_realtime_backup.csv`` so it can be restored.
    """
    hist_cleaned = hist_config.HIST_CPCB_CLEANED
    latest_cleaned = root_config.PROCESSED_DATA_DIR / "cpcb_cleaned_latest.csv"
    backup_cleaned = root_config.PROCESSED_DATA_DIR / "cpcb_cleaned_latest_realtime_backup.csv"

    if not hist_cleaned.exists():
        logger.warning(
            "Historical cleaned file '%s' not found; merger will use "
            "the existing real-time cpcb_cleaned_latest.csv.",
            hist_cleaned,
        )
        return

    import shutil

    # Backup existing real-time file before overwriting.
    if latest_cleaned.exists() and not backup_cleaned.exists():
        shutil.copy2(str(latest_cleaned), str(backup_cleaned))
        logger.info(
            "Real-time cleaned file backed up to %s.", backup_cleaned.name
        )

    shutil.copy2(str(hist_cleaned), str(latest_cleaned))
    logger.info(
        "Historical cleaned data (%d rows) installed as cpcb_cleaned_latest.csv "
        "for the feature engineering merger.",
        len(open(str(hist_cleaned)).readlines()) - 1,  # quick row count
    )
