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

# Day 4 Dataset Preparation defaults
DATASET_OUTPUT_DIRECTORY = Path(os.getenv("DATASET_OUTPUT_DIRECTORY", str(BASE_DIR.parent)))
REQUIRED_TARGET_COLUMN = os.getenv("REQUIRED_TARGET_COLUMN", "AQI")
REQUIRED_FEATURE_COLUMNS = os.getenv("REQUIRED_FEATURE_COLUMNS", "").split(",") if os.getenv("REQUIRED_FEATURE_COLUMNS") else []
TEMPORAL_TOLERANCE_HOURS = float(os.getenv("TEMPORAL_TOLERANCE_HOURS", "1.0"))
SPATIAL_TOLERANCE_KM = float(os.getenv("SPATIAL_TOLERANCE_KM", "50.0"))

# Day 4B Machine Learning Pipeline defaults
TRAIN_RATIO = float(os.getenv("TRAIN_RATIO", "0.70"))
VALIDATION_RATIO = float(os.getenv("VALIDATION_RATIO", "0.15"))
TEST_RATIO = float(os.getenv("TEST_RATIO", "0.15"))
RANDOM_STATE = int(os.getenv("RANDOM_STATE", "42"))
MODEL_OUTPUT_PATH = Path(os.getenv("MODEL_OUTPUT_PATH", str(BASE_DIR.parent)))
EVALUATION_OUTPUT_PATH = Path(os.getenv("EVALUATION_OUTPUT_PATH", str(BASE_DIR.parent)))

# Random Forest Hyperparameters
RANDOM_FOREST_PARAMS = {
    "n_estimators": int(os.getenv("RF_N_ESTIMATORS", "100")),
    "max_depth": int(os.getenv("RF_MAX_DEPTH", "15")) if os.getenv("RF_MAX_DEPTH") else None,
    "min_samples_split": int(os.getenv("RF_MIN_SAMPLES_SPLIT", "2")),
    "min_samples_leaf": int(os.getenv("RF_MIN_SAMPLES_LEAF", "1")),
    "max_features": os.getenv("RF_MAX_FEATURES", "sqrt"),
    "random_state": RANDOM_STATE,
    "n_jobs": -1
}

# LightGBM Hyperparameters
LIGHTGBM_PARAMS = {
    "n_estimators": int(os.getenv("LGBM_N_ESTIMATORS", "100")),
    "max_depth": int(os.getenv("LGBM_MAX_DEPTH", "-1")),
    "learning_rate": float(os.getenv("LGBM_LEARNING_RATE", "0.1")),
    "num_leaves": int(os.getenv("LGBM_NUM_LEAVES", "31")),
    "min_child_samples": int(os.getenv("LGBM_MIN_CHILD_SAMPLES", "20")),
    "feature_fraction": float(os.getenv("LGBM_FEATURE_FRACTION", "1.0")),
    "bagging_fraction": float(os.getenv("LGBM_BAGGING_FRACTION", "1.0")),
    "bagging_freq": int(os.getenv("LGBM_BAGGING_FREQ", "0")),
    "reg_alpha": float(os.getenv("LGBM_REG_ALPHA", "0.0")),
    "reg_lambda": float(os.getenv("LGBM_REG_LAMBDA", "0.0")),
    "objective": os.getenv("LGBM_OBJECTIVE", "regression"),
    "metric": os.getenv("LGBM_METRIC", "rmse"),
    "verbosity": int(os.getenv("LGBM_VERBOSITY", "-1")),
    "random_state": RANDOM_STATE,
    "n_jobs": -1
}


