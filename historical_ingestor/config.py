import os
from dotenv import load_dotenv

# Load environment variables from .env if present
load_dotenv()

START_YEAR = int(os.getenv("OPENAQ_START_YEAR", 2020))
END_YEAR = int(os.getenv("OPENAQ_END_YEAR", 2024))
COUNTRY = os.getenv("OPENAQ_COUNTRY", "IN")
OUTPUT_DIRECTORY = os.getenv("OPENAQ_OUTPUT_DIRECTORY", "historical_data/openaq")
LOG_DIRECTORY = os.getenv("OPENAQ_LOG_DIRECTORY", "historical_data/logs")
MAX_RETRIES = int(os.getenv("OPENAQ_MAX_RETRIES", 5))
REQUEST_TIMEOUT = int(os.getenv("OPENAQ_REQUEST_TIMEOUT", 30))
SLEEP_INTERVAL = float(os.getenv("OPENAQ_SLEEP_INTERVAL", 1.5))
API_KEY = os.getenv("OPENAQ_API_KEY", None)

# Base URL for OpenAQ v3 API (v2 is retired)
BASE_URL = "https://api.openaq.org/v3"

# Pollutant list exactly as requested
POLLUTANTS = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]

# OpenAQ API v3 parameter mapping
POLLUTANT_MAP = {
    "PM2.5": "pm25",
    "PM10": "pm10",
    "NO2": "no2",
    "SO2": "so2",
    "CO": "co",
    "O3": "o3"
}

