import time
import logging
import csv
import datetime
from pathlib import Path
import requests
from typing import Optional, Dict, Tuple
from data_collection_pipeline import config

def setup_logging() -> logging.Logger:
    """
    Sets up a logger that logs to both the console and a file defined in config.py.
    """
    logger = logging.getLogger("data_collection_pipeline")
    
    # Avoid duplicate handlers if already configured
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.INFO)
    
    # Formatter for logs
    formatter = logging.Formatter(
        "[%(asctime)s] %(levelname)s [%(name)s:%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Ensure log directory exists (fail-safe)
    try:
        config.LOG_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(config.LOG_FILE_PATH, encoding="utf-8")
        file_handler.setLevel(logging.INFO)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError as e:
        print(f"Warning: Could not create log file handler: {e}")
    
    logger.addHandler(console_handler)
    return logger

logger = setup_logging()

# Default headers used by every outbound request.
# data.gov.in and several other Indian government APIs return HTTP 502 when
# they see the default Python/requests User-Agent string.  Using a generic
# browser-style User-Agent resolves this transparently.
_DEFAULT_HEADERS: Dict[str, str] = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json",
}

# Reusable global requests session
_SESSION = requests.Session()
_SESSION.headers.update(_DEFAULT_HEADERS)


def safe_request(
    url: str,
    params: Optional[Dict] = None,
    headers: Optional[Dict] = None
) -> Optional[requests.Response]:
    """
    Executes an HTTP GET request with retry logic and exponential backoff.
    Catches specific requests exceptions.

    A reusable ``requests.Session`` is used so that default browser-like headers are
    sent with every request.  This avoids HTTP 502 responses from APIs (such
    as data.gov.in) that block the default Python/requests User-Agent.

    Caller-supplied *headers* are merged on top of the session defaults, so
    any value provided by the caller always takes precedence.
    """
    retries = 0
    backoff = config.BACKOFF_FACTOR

    # Build merged headers: defaults first, then caller overrides.
    merged_headers: Dict[str, str] = {**_DEFAULT_HEADERS, **(headers or {})}

    while retries < config.MAX_RETRIES:
        try:
            logger.info(f"Executing GET request to {url} (Attempt {retries + 1}/{config.MAX_RETRIES})")
            response = _SESSION.get(
                url,
                params=params,
                headers=merged_headers,
                timeout=config.HTTP_TIMEOUT
            )

            # Raise exception for 4xx or 5xx status codes
            response.raise_for_status()
            return response

        except requests.exceptions.HTTPError as e:
            retries += 1
            logger.warning(f"HTTP error occurred: {e}. Retry {retries}/{config.MAX_RETRIES}...")
        except requests.exceptions.ConnectionError as e:
            retries += 1
            logger.warning(f"Connection error occurred: {e}. Retry {retries}/{config.MAX_RETRIES}...")
        except requests.exceptions.Timeout as e:
            retries += 1
            logger.warning(f"Request timeout occurred: {e}. Retry {retries}/{config.MAX_RETRIES}...")
        except requests.exceptions.RequestException as e:
            retries += 1
            logger.warning(f"Request exception occurred: {e}. Retry {retries}/{config.MAX_RETRIES}...")

        if retries < config.MAX_RETRIES:
            sleep_time = backoff ** retries
            logger.info(f"Sleeping for {sleep_time} seconds before retrying...")
            time.sleep(sleep_time)

    logger.error(f"Failed to fetch data from {url} after {config.MAX_RETRIES} attempts.")
    return None

def append_to_source_manifest(
    dataset: str,
    url: str,
    rows: int,
    status: str
) -> None:
    """
    Appends a download record to metadata/source_manifest.csv.
    Creates the manifest with correct headers if it does not exist.
    """
    manifest_path = config.METADATA_DIR / "source_manifest.csv"
    headers = ["Dataset", "Source URL", "Downloaded Timestamp", "Rows Downloaded", "Download Status"]
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    row = [dataset, url, timestamp, rows, status]
    
    # Ensure metadata directory exists
    try:
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Failed to create metadata directory for source manifest: {e}")
        return

    file_exists = manifest_path.exists()
    
    try:
        with open(manifest_path, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(headers)
            writer.writerow(row)
        logger.info(f"Source manifest updated: {dataset} -> {status} ({rows} rows)")
    except OSError as e:
        logger.error(f"Failed to write to source manifest at {manifest_path}: {e}")

# Geographic coordinate mapping for major Indian cities to enrich CPCB station metadata
CITY_COORDINATES_LOOKUP: Dict[str, Tuple[float, float]] = {
    "delhi": (28.6139, 77.2090),
    "new delhi": (28.6139, 77.2090),
    "mumbai": (19.0760, 72.8777),
    "bengaluru": (12.9716, 77.5946),
    "bangalore": (12.9716, 77.5946),
    "kolkata": (22.5726, 88.3639),
    "calcutta": (22.5726, 88.3639),
    "chennai": (13.0827, 80.2707),
    "madras": (13.0827, 80.2707),
    "hyderabad": (17.3850, 78.4867),
    "ahmedabad": (23.0225, 72.5714),
    "pune": (18.5204, 73.8567),
    "surat": (21.1702, 72.8311),
    "jaipur": (26.9124, 75.7873),
    "lucknow": (26.8467, 80.9462),
    "kanpur": (26.4499, 80.3319),
    "nagpur": (21.1458, 79.0882),
    "indore": (22.7196, 75.8577),
    "thane": (19.2183, 72.9781),
    "bhopal": (23.2599, 77.4126),
    "visakhapatnam": (17.6868, 83.2185),
    "patna": (25.5941, 85.1376),
    "vadodara": (22.3072, 73.1812),
    "ghaziabad": (28.6692, 77.4538),
    "ludhiana": (30.9010, 75.8573),
    "agra": (27.1767, 78.0081),
    "nashik": (19.9975, 73.7898),
    "faridabad": (28.4089, 77.3178),
    "meerut": (28.9845, 77.7064),
    "rajkot": (22.3039, 70.8022),
    "varanasi": (25.3176, 82.9739),
    "srinagar": (34.0837, 74.7973),
    "chandigarh": (30.7333, 76.7794),
    "guwahati": (26.1445, 91.7362),
    "coimbatore": (11.0168, 76.9558),
    "vijayawada": (16.5062, 80.6480),
    "kochi": (9.9312, 76.2673),
    "trivandrum": (8.5241, 76.9366),
    "thiruvananthapuram": (8.5241, 76.9366),
    "bhubaneswar": (20.3040, 85.8189),
    "ranchi": (23.3441, 85.3096),
    "raipur": (21.2514, 81.6296),
    "dehradun": (30.3165, 78.0322),
    "shimla": (31.1048, 77.1734),
    "panaji": (15.4909, 73.8278),
    "imphal": (24.8170, 93.9368),
    "shillong": (25.5788, 91.8831),
    "aizawl": (23.7271, 92.7176),
    "kohima": (25.6751, 94.1086),
    "itanagar": (27.0844, 93.6053),
    "gangtok": (27.3314, 88.6138),
    "agartala": (23.8315, 91.2868),
}

def get_coordinates_for_city(city: str) -> Tuple[Optional[float], Optional[float]]:
    """
    Returns latitude and longitude for a city name, or (None, None) if not found.
    """
    if not city:
        return None, None
    city_clean = str(city).strip().lower()
    return CITY_COORDINATES_LOOKUP.get(city_clean, (None, None))
