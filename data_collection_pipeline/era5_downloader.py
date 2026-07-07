import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional
from data_collection_pipeline import config

logger = logging.getLogger("data_collection_pipeline.era5")

def get_era5_request_dict(
    year: str = "2026",
    month: str = "07",
    day: str = "01",
    variables: Optional[List[str]] = None
) -> Dict:
    """
    Formulates the API request dictionary for ERA5 reanalysis single levels data.
    Filters by the bounding box of India.
    """
    if variables is None:
        variables = config.ERA5_DEFAULT_VARIABLES
        
    return {
        "product_type": "reanalysis",
        "format": "netcdf",
        "variable": variables,
        "year": year,
        "month": month,
        "day": day,
        "time": [
            "00:00", "01:00", "02:00",
            "03:00", "04:00", "05:00",
            "06:00", "07:00", "08:00",
            "09:00", "10:00", "11:00",
            "12:00", "13:00", "14:00",
            "15:00", "16:00", "17:00",
            "18:00", "19:00", "20:00",
            "21:00", "22:00", "23:00"
        ],
        "area": config.ERA5_BOUNDING_BOX,  # North, West, South, East [38.0, 68.0, 6.0, 98.0]
    }

def prepare_era5_download(
    year: str = "2026",
    month: str = "07",
    day: str = "01",
    variables: Optional[List[str]] = None,
    output_filename: str = "era5_meteorological_india.nc",
    dry_run: bool = True
) -> bool:
    """
    Prepares the request for ERA5 meteorological data.
    If dry_run is True, it saves the API request dictionary and a sample download script
    to raw_data/ without executing the API download.
    If dry_run is False, it attempts to download the file using the cdsapi library.
    """
    logger.info("Initializing ERA5 meteorological data preparation...")
    request_dict = get_era5_request_dict(year, month, day, variables)
    
    raw_dir = config.RAW_DATA_DIR
    spec_path = raw_dir / "era5_request_spec.json"
    script_path = raw_dir / "download_era5_script.py"
    target_nc_path = raw_dir / output_filename
    
    # Save the request JSON specification
    try:
        with open(spec_path, "w", encoding="utf-8") as f:
            json.dump(request_dict, f, indent=4)
        logger.info(f"Saved ERA5 query specification to {spec_path}")
    except OSError as e:
        logger.error(f"OS/IO error writing ERA5 specification file: {e}")
        return False
        
    # Save the sample download python script
    script_content = f"""# Auto-generated script to download ERA5 data for India
# To run this, install cdsapi: pip install cdsapi
# And configure your ~/.cdsapirc file with your URL and key details.

import cdsapi

client = cdsapi.Client()

dataset = 'reanalysis-era5-single-levels'
request = {json.dumps(request_dict, indent=4)}

target = '{target_nc_path.name}'

print(f"Downloading ERA5 data to {{target}}...")
client.retrieve(dataset, request, target)
print("Download complete!")
"""
    try:
        with open(script_path, "w", encoding="utf-8") as f:
            f.write(script_content)
        logger.info(f"Saved standalone ERA5 download script to {script_path}")
    except OSError as e:
        logger.error(f"OS/IO error writing ERA5 download script: {e}")
        return False
        
    if dry_run:
        logger.info("[Dry Run] Skipping actual ERA5 download to prevent downloading large datasets automatically.")
        logger.info(f"To download manually, you can execute: python {script_path}")
        return True
        
    # Actual download execution
    logger.info("Executing actual ERA5 download via cdsapi...")
    
    # Check for credentials
    cdsapirc_path = Path.home() / ".cdsapirc"
    if not cdsapirc_path.exists() and "CDSAPI_KEY" not in os.environ:
        logger.error(
            "CDS API credentials not found. Please create ~/.cdsapirc or set CDSAPI_KEY. "
            "Reverting to dry run."
        )
        return False
        
    try:
        import cdsapi
        client = cdsapi.Client()
        logger.info(f"Retrieving 'reanalysis-era5-single-levels' into {target_nc_path}...")
        client.retrieve("reanalysis-era5-single-levels", request_dict, str(target_nc_path))
        logger.info(f"Successfully downloaded ERA5 dataset to {target_nc_path}")
        return True
    except ImportError as e:
        logger.error(
            f"The 'cdsapi' Python package could not be imported: {e}. "
            "Please run: pip install cdsapi"
        )
        return False
    except Exception as e:
        # We catch client exceptions dynamically as cdsapi might throw custom package exceptions
        logger.error(f"An unexpected error occurred during ERA5 download: {e}")
        return False
