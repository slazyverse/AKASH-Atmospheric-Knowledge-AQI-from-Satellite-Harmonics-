import argparse
import sys
from pathlib import Path

# Resolve path to include the workspace root directory in sys.path
workspace_root = Path(__file__).resolve().parent.parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

try:
    from data_collection_pipeline import (
        config,
        cpcb_collector,
        era5_downloader,
        era5_processor,
        sentinel5p_collector,
        main,
        openaq_collector,
        setup,
        utils,
    )
    from data_collection_pipeline.data_cleaning import run_cleaning_pipeline
    from data_collection_pipeline.feature_engineering import run_integration_pipeline
except ImportError as e:
    print(f"ImportError: {e}")
    print("Ensure you are running the script with correct paths or within the workspace.")
    sys.exit(1)

def main_cli():
    # Setup directories before any pipeline actions
    try:
        setup.init_workspace()
    except OSError as e:
        print(f"Failed to initialize workspace directories: {e}")
        sys.exit(1)
        
    parser = argparse.ArgumentParser(
        description="ISRO Bharatiya Antariksh Hackathon 2026: Data Collection Module"
    )
    
    # Execution mode flags
    parser.add_argument(
        "--no-dry-run",
        action="store_true",
        help="Disable dry-run mode and trigger actual downloads (e.g. ERA5 via cdsapi, if configured)."
    )
    
    # Module specific selectors
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--cpcb-only",
        action="store_true",
        help="Execute only the CPCB Air Quality data collector."
    )
    group.add_argument(
        "--openaq-only",
        action="store_true",
        help="Execute only the OpenAQ API connector."
    )
    group.add_argument(
        "--era5-only",
        action="store_true",
        help="Execute only the ERA5 meteorological downloader preparation."
    )
    group.add_argument(
        "--clean-only",
        action="store_true",
        help="Execute only the data cleaning and station validation pipeline."
    )
    group.add_argument(
        "--integrate-only",
        action="store_true",
        help="Execute only the Day 3 feature engineering and dataset integration pipeline."
    )
    group.add_argument(
        "--prepare-dataset",
        action="store_true",
        help="Execute the Day 4A dataset preparation pipeline."
    )
    group.add_argument(
        "--run-ml-pipeline",
        action="store_true",
        help="Execute the Day 4B ML pipeline (Preparation, Split, Training, Evaluation)."
    )
    group.add_argument(
        "--process-era5",
        action="store_true",
        help=(
            "Convert a downloaded ERA5 NetCDF file "
            "(raw_data/era5_meteorological_india.nc) to "
            "processed_data/era5_meteorology.csv for feature engineering."
        ),
    )
    group.add_argument(
        "--collect-satellite",
        action="store_true",
        help=(
            "Collect Sentinel-5P TROPOMI and MODIS AOD data via Google Earth Engine "
            "and write processed_data/satellite_predictors.csv."
        ),
    )
    group.add_argument(
        "--historical",
        action="store_true",
        help=(
            "Run the Phase 1 historical training pipeline: ingest multi-year "
            "CPCB/OpenAQ/Sentinel-5P/ERA5 data, build the analysis-ready dataset, "
            "and train a versioned baseline model. "
            "Control the date range with --hist-start and --hist-end."
        ),
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="Target date for satellite collection (used with --collect-satellite).",
    )
    parser.add_argument(
        "--cpcb-window-days",
        type=int,
        default=1,
        help="Number of days of CPCB air quality history to collect (mock mode only).",
    )
    parser.add_argument(
        "--satellite-window-days",
        type=int,
        default=1,
        help="Temporal averaging/search window in days around target date (default 1).",
    )
    parser.add_argument(
        "--satellite-lookback-days",
        type=int,
        default=7,
        help="Number of days to search backwards if imagery is unavailable (default 7).",
    )

    # --- Phase 1: Historical pipeline arguments ---
    parser.add_argument(
        "--hist-start",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help=(
            "Start date for the historical training pipeline (used with --historical). "
            "Defaults to HIST_START_DATE env var (2020-01-01)."
        ),
    )
    parser.add_argument(
        "--hist-end",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help=(
            "End date for the historical training pipeline (used with --historical). "
            "Defaults to HIST_END_DATE env var (2024-12-31)."
        ),
    )
    parser.add_argument(
        "--skip-satellite",
        action="store_true",
        help="Skip GEE satellite collection when running --historical (uses placeholder data).",
    )
    parser.add_argument(
        "--skip-era5",
        action="store_true",
        help="Skip ERA5 collection when running --historical (uses placeholder data).",
    )
    parser.add_argument(
        "--csv-folder",
        type=str,
        default=None,
        metavar="PATH",
        help=(
            "Path to a directory containing CPCB annual/monthly CSV exports "
            "(used with --historical). Defaults to raw_data/historical/cpcb/."
        ),
    )
    parser.add_argument(
        "--no-openaq",
        action="store_true",
        help="Disable OpenAQ API querying when running --historical.",
    )
    
    args = parser.parse_args()
    
    # Initialize logger
    logger = utils.setup_logging()
    logger.info("Initializing Data Collection Pipeline CLI Runner...")
    
    dry_run = not args.no_dry_run
    if dry_run:
        logger.info("Running in DRY RUN mode (Meteorological dataset downloads are prepared, but not fetched).")
    else:
        logger.info("Running in LIVE mode.")

    # Execute specific module or run full pipeline
    if args.cpcb_only:
        logger.info("Running CPCB Air Quality data collector only...")
        df_cpcb = cpcb_collector.collect_cpcb_data(window_days=args.cpcb_window_days)
        cpcb_file = config.RAW_DATA_DIR / "cpcb_raw_manual.csv"
        df_cpcb.to_csv(cpcb_file, index=False)
        logger.info(f"CPCB execution complete. Output saved to {cpcb_file}")
        
    elif args.openaq_only:
        logger.info("Running OpenAQ API connector only...")
        df_openaq = openaq_collector.collect_openaq_data()
        openaq_file = config.RAW_DATA_DIR / "openaq_raw_manual.csv"
        df_openaq.to_csv(openaq_file, index=False)
        logger.info(f"OpenAQ execution complete. Output saved to {openaq_file}")
        
    elif args.era5_only:
        import time
        start_time = time.time()
        logger.info("Running ERA5 preparation and ingestion pipeline...")
        
        # 1. Check credentials
        from data_collection_pipeline.era5_downloader import diagnose_credentials
        credential_info = diagnose_credentials()
        
        # Resolve dry_run: if credentials exist, automatically run live (dry_run=False)
        resolved_dry_run = dry_run
        if not args.no_dry_run and credential_info["overall"]:
            resolved_dry_run = False
            logger.info("CDS API credentials detected. Automatically resolving to live download/processing mode.")
        
        # 2. Download
        download_success = era5_downloader.prepare_era5_download(dry_run=resolved_dry_run)
        
        # 3. Process CSV if downloaded
        processing_success = False
        if download_success and not resolved_dry_run and credential_info["overall"]:
            logger.info("Download successful. Automatically initiating NetCDF → CSV processing...")
            processing_success = era5_processor.process_era5_netcdf()
            
        # 4. Validate and write report
        from data_collection_pipeline.era5_validator import run_era5_pipeline_validation
        runtime = time.time() - start_time
        val_result = run_era5_pipeline_validation(
            download_success=download_success,
            processing_success=processing_success,
            dry_run=resolved_dry_run,
            credential_info=credential_info,
            runtime_seconds=runtime,
        )
        
        if val_result["passed"]:
            logger.info("ERA5 pipeline execution completed successfully.")
        else:
            logger.error("ERA5 pipeline execution failed or was skipped due to missing credentials.")

    elif args.clean_only:
        logger.info("Running Data Cleaning & Validation pipeline only...")
        success = run_cleaning_pipeline()
        if success:
            logger.info("Data Cleaning & Validation execution completed successfully.")
            sys.exit(0)
        logger.error("Data Cleaning & Validation execution encountered errors.")
        sys.exit(1)

    elif args.integrate_only:
        logger.info("Running Feature Engineering & Dataset Integration pipeline only...")
        success = run_integration_pipeline()
        if success:
            logger.info("Feature Engineering & Dataset Integration completed successfully.")
            sys.exit(0)
        logger.error("Feature Engineering & Dataset Integration encountered errors.")
        sys.exit(1)

    elif args.process_era5:
        logger.info("Running ERA5 NetCDF → CSV processor ...")
        success = era5_processor.process_era5_netcdf()
        if success:
            logger.info(
                "ERA5 processing complete.  "
                "processed_data/era5_meteorology.csv is ready for feature engineering."
            )
            sys.exit(0)
        logger.error(
            "ERA5 processing failed.  "
            "Verify that raw_data/era5_meteorological_india.nc exists "
            "(run --era5-only --no-dry-run first)."
        )
        sys.exit(1)

    elif args.collect_satellite:
        logger.info("Running Sentinel-5P / MODIS satellite data collector ...")
        from data_collection_pipeline.sentinel5p_collector import diagnose_credentials
        
        credential_info = diagnose_credentials()
        if not credential_info["overall"]:
            logger.warning(
                "Satellite data collection skipped due to missing credentials or dependencies. "
                "The pipeline will continue with placeholder satellite data."
            )
            # Exit with 0 so downstream tasks can run if executed in a chain.
            sys.exit(0)

        success = sentinel5p_collector.collect_satellite_data(
            date_str=getattr(args, "date", None),
            temporal_window_days=args.satellite_window_days,
            lookback_days=args.satellite_lookback_days,
        )
        if success:
            logger.info(
                "Satellite collection complete.  "
                "processed_data/satellite_predictors.csv is ready for feature engineering."
            )
            sys.exit(0)
        logger.error(
            "Satellite data collection failed during execution.  "
            "Ensure GEE quotas are not exceeded and network is available."
        )
        sys.exit(1)

    elif args.prepare_dataset:
        logger.info("Running Day 4A Dataset Preparation pipeline...")
        from data_collection_pipeline.dataset_preparation import dataset_validator, dataset_builder, reporting
        import json
        
        # 1. Dataset Validation
        logger.info("Step 1/4: Dataset Validation")
        val_summary = dataset_validator.validate_merged_table()
        if val_summary.get("validation_status") == "FAILED":
            logger.error("Dataset validation failed. Halting dataset preparation.")
            sys.exit(1)
            
        # 2. Feature-Target Collocation & 3. Dataset Builder
        logger.info("Step 2/4 and 3/4: Feature-Target Collocation & Dataset Builder")
        df, X, y = dataset_builder.build_analysis_dataset()
        
        # Pre-save: verify target column is present and non-null in final df
        target_col = getattr(config, "REQUIRED_TARGET_COLUMN", "AQI")
        logger.info(
            "[TARGET COLUMN] Pre-save check before writing analysis_ready_dataset.csv: "
            "column='%s'", target_col
        )
        if target_col not in df.columns:
            logger.error(
                "[TARGET COLUMN] '%s' is missing from the final dataset. "
                "Cannot write analysis_ready_dataset.csv.", target_col
            )
            raise ValueError(
                f"Target column '{target_col}' is missing from the analysis-ready "
                "dataset. Verify the complete pipeline from CPCB cleaning through "
                "feature engineering to collocation."
            )
        null_count = int(df[target_col].isna().sum())
        non_null = len(df) - null_count
        if non_null == 0:
            logger.error(
                "[TARGET COLUMN] '%s' is present but entirely null (%d records). "
                "Cannot write analysis_ready_dataset.csv.", target_col, len(df)
            )
            raise ValueError(
                f"Target column '{target_col}' contains only null values in the "
                "analysis-ready dataset. Check CPCB source data."
            )
        logger.info(
            "[TARGET COLUMN] Pre-save validation PASSED: '%s' present, "
            "non-null=%d/%d. Writing analysis_ready_dataset.csv.",
            target_col, non_null, len(df)
        )
        
        # 4. Reporting
        logger.info("Step 4/4: Reporting")
        output_dir = Path(config.DATASET_OUTPUT_DIRECTORY)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        df.to_csv(output_dir / "analysis_ready_dataset.csv", index=False)
        logger.info(
            "Generated analysis_ready_dataset.csv (%d rows, %d columns, "
            "target column '%s' included).",
            len(df), len(df.columns), target_col
        )
        
        summary = reporting.generate_dataset_summary(df, X, y)
        with open(output_dir / "dataset_summary.json", "w") as f:
            json.dump(summary, f, indent=4)
        logger.info("Generated dataset_summary.json")
            
        stats_df = reporting.generate_feature_statistics(X)
        stats_df.to_csv(output_dir / "feature_statistics.csv")
        logger.info("Generated feature_statistics.csv")
        
        report_md = reporting.generate_quality_report(summary, stats_df)
        with open(output_dir / "dataset_quality_report.md", "w") as f:
            f.write(report_md)
        logger.info("Generated dataset_quality_report.md")
        
        logger.info("Dataset Preparation execution completed successfully.")
        sys.exit(0)
        
    elif args.run_ml_pipeline:
        logger.info("Running Day 4B ML Pipeline Integration...")
        from data_collection_pipeline.dataset_preparation import dataset_validator, dataset_builder, reporting
        from data_collection_pipeline.model_preparation import dataset_splitter
        from data_collection_pipeline.model_training import baseline_model
        from data_collection_pipeline.model_evaluation import evaluator
        import json
        
        output_dir = Path(config.DATASET_OUTPUT_DIRECTORY)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. Dataset Preparation
        logger.info("--- Stage 1: Dataset Preparation ---")
        val_summary = dataset_validator.validate_merged_table()
        if val_summary.get("validation_status") == "FAILED":
            logger.error("Dataset validation failed. Halting ML pipeline.")
            sys.exit(1)
            
        try:
            df, X, y = dataset_builder.build_analysis_dataset()
            dataset_path = output_dir / "analysis_ready_dataset.csv"

            # Pre-save: verify target column is present and non-null
            target_col_ml = getattr(config, "REQUIRED_TARGET_COLUMN", "AQI")
            logger.info(
                "[TARGET COLUMN] Pre-save check before writing analysis_ready_dataset.csv: "
                "column='%s'", target_col_ml
            )
            if target_col_ml not in df.columns:
                raise ValueError(
                    f"Target column '{target_col_ml}' is missing from the analysis-ready "
                    "dataset. Verify the complete pipeline from CPCB cleaning through "
                    "feature engineering to collocation."
                )
            null_count_ml = int(df[target_col_ml].isna().sum())
            non_null_ml = len(df) - null_count_ml
            if non_null_ml == 0:
                raise ValueError(
                    f"Target column '{target_col_ml}' contains only null values in the "
                    "analysis-ready dataset. Check CPCB source data."
                )
            logger.info(
                "[TARGET COLUMN] Pre-save validation PASSED: '%s' present, "
                "non-null=%d/%d. Writing analysis_ready_dataset.csv.",
                target_col_ml, non_null_ml, len(df)
            )

            df.to_csv(dataset_path, index=False)
            logger.info(
                "Generated analysis_ready_dataset.csv (%d rows, %d columns, "
                "target column '%s' included).",
                len(df), len(df.columns), target_col_ml
            )
            
            summary = reporting.generate_dataset_summary(df, X, y)
            with open(output_dir / "dataset_summary.json", "w") as f:
                json.dump(summary, f, indent=4)
                
            stats_df = reporting.generate_feature_statistics(X)
            stats_df.to_csv(output_dir / "feature_statistics.csv")
            
            report_md = reporting.generate_quality_report(summary, stats_df)
            with open(output_dir / "dataset_quality_report.md", "w") as f:
                f.write(report_md)
        except Exception as e:
            logger.error(f"Dataset preparation failed: {e}")
            sys.exit(1)
            
        # 2. Chronological Dataset Split
        logger.info("--- Stage 2: Chronological Dataset Split ---")
        try:
            df_loaded = dataset_splitter.load_analysis_dataset(dataset_path)
            target_col = baseline_model.select_target_column(df_loaded)
            target = dataset_splitter.identify_target_column(df_loaded, target_name=target_col)
            df_clean = dataset_splitter.remove_invalid_rows(df_loaded, target)
            features = dataset_splitter.identify_feature_columns(df_clean, target)
            train_df, val_df, test_df, split_summary = dataset_splitter.chronological_split(
                df_clean, 
                train_ratio=config.TRAIN_RATIO, 
                val_ratio=config.VALIDATION_RATIO, 
                test_ratio=config.TEST_RATIO
            )
            dataset_splitter.export_datasets(train_df, val_df, test_df, split_summary, config.DATASET_OUTPUT_DIRECTORY)
        except Exception as e:
            logger.error(f"Chronological split failed: {e}")
            sys.exit(1)

        # Pre-training: feature lineage validation
        logger.info("--- Pre-Training: Feature Lineage Validation ---")
        try:
            from data_collection_pipeline.feature_engineering.lineage_audit import (
                validate_features_before_training,
            )
            train_file_for_validation = output_dir / "train_dataset.csv"
            if train_file_for_validation.exists():
                import pandas as _pd
                _df_train_check = _pd.read_csv(train_file_for_validation)
                validate_features_before_training(_df_train_check)
            else:
                logger.warning(
                    "[PRE-TRAINING VALIDATION] train_dataset.csv not found — "
                    "skipping feature lineage validation."
                )
        except Exception as lineage_exc:
            logger.warning(
                "Feature lineage validation encountered a non-fatal error: %s", lineage_exc
            )

        # 3. Baseline Model Training
        logger.info("--- Stage 3: Baseline Model Training ---")
        try:
            train_file = output_dir / "train_dataset.csv"
            df_train = baseline_model.load_training_data(train_file)
            target_col = baseline_model.select_target_column(df_train)
            X_train, y_train, feature_cols = baseline_model.prepare_training_features(df_train, target_col)
            model = baseline_model.train_baseline_model(X_train, y_train, feature_cols)
            importances = baseline_model.get_feature_importances(model)
            training_summary = {
                "dataset_size": len(X_train),
                "feature_count": len(feature_cols),
                "target_column": target_col,
                "status": "completed"
            }
            baseline_model.save_trained_model(model, training_summary, {}, importances, config.MODEL_OUTPUT_PATH)
        except Exception as e:
            logger.error(f"Model training failed: {e}")
            sys.exit(1)
            
        # 4. Model Evaluation
        logger.info("--- Stage 4: Model Evaluation ---")
        try:
            val_file = output_dir / "validation_dataset.csv"
            df_val = evaluator.load_validation_dataset(val_file)
            target_col = baseline_model.select_target_column(df_val)
            X_val, y_val, feature_cols = baseline_model.prepare_training_features(df_val, target_col)
            
            model_file = Path(config.MODEL_OUTPUT_PATH) / "baseline_model.joblib"
            loaded_model = evaluator.load_trained_model(model_file)
            
            y_pred = evaluator.generate_predictions(loaded_model, X_val)
            metrics = evaluator.calculate_regression_metrics(y_val, y_pred)
            importance_df = evaluator.calculate_feature_importance(loaded_model, feature_cols)
            
            evaluator.generate_evaluation_report(metrics, importance_df, config.EVALUATION_OUTPUT_PATH)
        except Exception as e:
            logger.error(f"Model evaluation failed: {e}")
            sys.exit(1)
            
        logger.info("ML Pipeline Integration completed successfully.")
        sys.exit(0)
            
    elif args.historical:
        logger.info("Running Phase 1 Historical Training Pipeline...")
        try:
            from data_collection_pipeline.historical_ingestor.pipeline import (
                run_historical_pipeline,
            )
        except ImportError as imp_err:
            logger.error(
                "historical_ingestor package not found: %s", imp_err
            )
            sys.exit(1)

        success = run_historical_pipeline(
            start_date=args.hist_start,
            end_date=args.hist_end,
            skip_satellite=args.skip_satellite,
            skip_era5=args.skip_era5,
            csv_folder=args.csv_folder,
            use_openaq=not args.no_openaq,
        )
        if success:
            logger.info("Historical pipeline completed successfully.")
            sys.exit(0)
        else:
            logger.error("Historical pipeline encountered errors.")
            sys.exit(1)

    else:
        # Run entire pipeline
        success = main.run_collection_pipeline(dry_run=dry_run)
        if success:
            logger.info("Full Data Collection pipeline execution completed successfully.")
            sys.exit(0)
        else:
            logger.error("Data Collection pipeline execution encountered errors.")
            sys.exit(1)

if __name__ == "__main__":
    main_cli()
