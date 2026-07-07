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
        main,
        openaq_collector,
        setup,
        utils,
    )
    from data_collection_pipeline.data_cleaning import run_cleaning_pipeline
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
        df_cpcb = cpcb_collector.collect_cpcb_data()
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
        logger.info("Running ERA5 preparation only...")
        success = era5_downloader.prepare_era5_download(dry_run=dry_run)
        if success:
            logger.info("ERA5 preparation execution complete.")
        else:
            logger.error("ERA5 preparation execution failed.")

    elif args.clean_only:
        logger.info("Running Data Cleaning & Validation pipeline only...")
        success = run_cleaning_pipeline()
        if success:
            logger.info("Data Cleaning & Validation execution completed successfully.")
            sys.exit(0)
        logger.error("Data Cleaning & Validation execution encountered errors.")
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
