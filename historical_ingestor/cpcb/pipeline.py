import os
import glob
import logging
import pandas as pd
from typing import List, Dict, Tuple
from historical_ingestor.cpcb.parser import parse_cpcb_file
from historical_ingestor.cpcb.merger import merge_datasets, export_to_parquet

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("cpcb_ingestion.log")
    ]
)
logger = logging.getLogger("CPCB_Pipeline")

def run_pipeline(raw_data_dir: str, output_parquet_dir: str, openaq_csv_path: str = None):
    """
    Main orchestration function for the CPCB pipeline.
    """
    logger.info("Starting CPCB Historical Ground Data Ingestion Pipeline...")
    
    # 1. Discover files
    csv_files = glob.glob(os.path.join(raw_data_dir, "cpcb_raw_*.csv"))
    if not csv_files:
        logger.warning(f"No CPCB raw data files found in {raw_data_dir}.")
        return
        
    all_observations = []
    all_metadata = []
    
    # 2. Parse, Clean, Validate, and Extract Metadata
    for filepath in csv_files:
        logger.info(f"Processing file: {filepath}")
        try:
            obs, meta = parse_cpcb_file(filepath)
            all_observations.extend(obs)
            all_metadata.extend(meta)
            logger.info(f"Extracted {len(obs)} observations and {len(meta)} metadata records from {os.path.basename(filepath)}")
        except Exception as e:
            logger.error(f"Failed to process {filepath}: {str(e)}")
            
    if not all_observations:
        logger.warning("No observations extracted from any file. Exiting.")
        return
        
    # 3. Load OpenAQ data if provided
    openaq_df = None
    if openaq_csv_path and os.path.exists(openaq_csv_path):
        logger.info(f"Loading existing OpenAQ dataset from {openaq_csv_path}")
        try:
            openaq_df = pd.read_csv(openaq_csv_path)
            # Ensure OpenAQ schema matches expected common schema columns
        except Exception as e:
            logger.error(f"Failed to load OpenAQ data: {str(e)}")
            
    # 4. Merge datasets
    logger.info("Merging datasets (CPCB + OpenAQ)...")
    merged_df = merge_datasets(all_observations, openaq_df)
    logger.info(f"Merged dataset contains {len(merged_df)} total records.")
    
    # 5. Export to Parquet
    logger.info(f"Exporting to partitioned Parquet structure at {output_parquet_dir}...")
    try:
        export_to_parquet(merged_df, output_parquet_dir)
        logger.info("Export completed successfully.")
    except Exception as e:
        logger.error(f"Failed to export to Parquet: {str(e)}")
        
    logger.info("Pipeline execution finished.")

if __name__ == "__main__":
    # Example execution
    raw_dir = os.path.join("d:\\AKASH", "data_collection_pipeline", "raw_data")
    output_dir = os.path.join("d:\\AKASH", "historical_data", "unified_parquet")
    openaq_path = os.path.join("d:\\AKASH", "historical_data", "openaq", "2025", "station_8039.csv")
    
    run_pipeline(raw_dir, output_dir, openaq_path)
