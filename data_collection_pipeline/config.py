import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# Base directory of the data collection pipeline
BASE_DIR = Path(__file__).resolve().parent

# Directory Paths
RAW_DATA_DIR = BASE_DIR / "raw_data"
PROCESSED_DATA_DIR = BASE_DIR / "processed_data"
METADATA_DIR = BASE_DIR / "metadata"
LOG_DIR = BASE_DIR / "logs"
DOCUMENTATION_DIR = BASE_DIR / "documentation"
FEATURES_DIR = BASE_DIR / "features"

# API Keys & Credentials
DATA_GOV_API_KEY = os.getenv("DATA_GOV_API_KEY", "")
OPENAQ_API_KEY = os.getenv("OPENAQ_API_KEY", "")

# API Endpoints
# CPCB Real-time Air Quality resource ID on data.gov.in
CPCB_RESOURCE_ID = "3b01bcb8-0b14-4abf-b6f2-c1bfd384ba69"
CPCB_BASE_URL = f"https://api.data.gov.in/resource/{CPCB_RESOURCE_ID}"

# OpenAQ API endpoint (v2 is used for standard country-level measurement fetching)
OPENAQ_BASE_URL = "https://api.openaq.org/v2/measurements"

# ERA5 Meteorological Configurations (bounding box covers India: North, West, South, East)
ERA5_BOUNDING_BOX = [38.0, 68.0, 6.0, 98.0]
ERA5_DEFAULT_VARIABLES = [
    "2m_temperature",
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "total_precipitation",
    "boundary_layer_height",
    "relative_humidity"
]

# Day 3 feature integration defaults
TEMPORAL_ALIGNMENT = os.getenv("TEMPORAL_ALIGNMENT", "nearest")
MISSING_VALUE_STRATEGY = os.getenv("MISSING_VALUE_STRATEGY", "leave_missing")

# Connection & Retry Policy
HTTP_TIMEOUT = 30  # seconds
MAX_RETRIES = 3
BACKOFF_FACTOR = 2.0  # multiplier for exponential backoff

# Logging configuration file path
LOG_FILE_PATH = LOG_DIR / "data_collection.log"
