"""
Earth Engine Configuration Module.

Maintains settings, paths, bounding coordinates, and environment variables
for the Google Earth Engine data pipeline.
"""

import os
from pathlib import Path

# Base directories
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent

# Credentials configuration
EE_SA_KEY_PATH = os.getenv("EE_SA_KEY_PATH", "")
EE_PROJECT = os.getenv("EE_PROJECT", os.getenv("GCP_PROJECT", "akaash-aqi"))

# Default Bounding Box for India: [West Longitude, South Latitude, East Longitude, North Latitude]
INDIA_BBOX = [68.1, 6.7, 97.4, 35.5]

# Default Temporal Settings
DEFAULT_START_DATE = "2026-01-01"
DEFAULT_END_DATE = "2026-12-31"
