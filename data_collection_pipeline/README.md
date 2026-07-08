# ISRO Bharatiya Antariksh Hackathon 2026: Data Collection Module

This directory contains the improved, production-grade **Data Collection** module for the project **"Development of Surface AQI & Identification of HCHO Hotspots over India using Satellite Data."**

This module handles programmatic data ingestion from multiple APIs (CPCB via `data.gov.in`, OpenAQ, and ERA5) with automated logging, retry policies, robust failure handling, custom data validations, directory initialization, and automated audit manifests.

---

## 📁 Directory Layout

```text
data_collection_pipeline/
├── config.py                 # Central configurations, path and variable definitions
├── setup.py                  # Workspace folder initialization and dotenv loading
├── utils.py                  # HTTP client, exponential retries, logging, manifest writing
├── cpcb_collector.py         # CPCB Real-time Air Quality data API client
├── openaq_collector.py       # OpenAQ API data connector (handles null values safely)
├── era5_downloader.py        # ERA5 Copernicus Climate Data Store preparation
├── main.py                   # Data collection orchestrator
├── requirements.txt          # Python package dependencies
├── README.md                 # Usage documentation (This file)
├── documentation/
│   └── data_collection_architecture.md   # System and data flow diagrams
├── scripts/
│   └── run_pipeline.py       # CLI launcher for the pipeline
├── raw_data/                 # Raw API response CSVs and ERA5 spec downloads
├── processed_data/           # (Placeholder) Ingested tables ready for downstream QA
├── metadata/
│   ├── station_metadata.csv  # Consolidated station metadata (GPS & source mapping)
│   └── source_manifest.csv   # Automatically generated audit trail manifest
└── logs/
    └── data_collection.log   # Active pipeline logs
```

---

## ⚙️ Configuration & Environment Setup

This pipeline is built for **Python 3.11** and is fully PEP8 compliant.

### 1. Install Dependencies
Install all required libraries from the pipeline root:
```bash
pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a file named `.env` in the root of the `data_collection_pipeline/` directory (or workspace root) and specify the following keys:
```env
# data.gov.in API Key (obtain from https://data.gov.in/dashboard)
DATA_GOV_API_KEY=your_datagov_api_key_here

# OpenAQ API Key (obtain from https://explore.openaq.org/)
OPENAQ_API_KEY=your_openaq_api_key_here
```

*Note: If no API keys are provided or network calls fail, the pipeline will log a warning and fall back to producing realistic mock datasets, enabling full end-to-end dry-run tests without keys.*

### 3. Initialize Folders
To initialize the folder structure separately without running the pipeline:
```bash
python setup.py
```

---

## 🚀 Running the Pipeline

You can run the full collection pipeline using the orchestrator:

### 1. Default (Dry Run Mode)
Runs CPCB and OpenAQ queries, saves their raw datasets, compiles `station_metadata.csv`, writes the ERA5 request specifications/standalone download scripts *without* triggering the massive ERA5 download:
```bash
python scripts/run_pipeline.py
```

### 2. Live Download Mode
Runs CPCB and OpenAQ queries and executes the live CDS API download call for ERA5 (requires configured credentials):
```bash
python scripts/run_pipeline.py --no-dry-run
```

### 3. Running Modules Individually
You can run any collector in isolation using CLI flags:
```bash
# Run CPCB data collection only
python scripts/run_pipeline.py --cpcb-only

# Run OpenAQ connector only
python scripts/run_pipeline.py --openaq-only

# Prepare ERA5 specifications only
python scripts/run_pipeline.py --era5-only
```

---

## 📊 Pipeline Outputs

### 1. Raw Air Quality Data
Stored in `raw_data/` as timestamped CSVs (e.g. `cpcb_raw_20260707_120000.csv` and `openaq_raw_20260707_120000.csv`).

### 2. ERA5 Query Specs
Stored in `raw_data/era5_request_spec.json` and `raw_data/download_era5_script.py` which can be executed separately to download the NetCDF file.

### 3. Station Metadata (`metadata/station_metadata.csv`)
Enriches the station registry with geographic coordinates, assigns sequential unique Station IDs (`STN_001`, `STN_002`...), and identifies data availability across sources:
- `Station ID`: Sequentially mapped unique identifier (e.g. `STN_001`, `STN_002`...)
- `Station Name`: Unique name of the monitoring station
- `City`: City location
- `State`: State location (if CPCB)
- `Latitude` / `Longitude`: Coordinates resolved from OpenAQ or lookup table
- `Source`: Origin database (`CPCB`, `OpenAQ`, or `CPCB, OpenAQ` if present in both)
- `Last Updated`: Timestamp of last ingest

### 4. Source Audit Trail (`metadata/source_manifest.csv`)
Automatically generated and appended to during every execution. Tracks data lineage and ingestion auditing:
- `Dataset`: Name of the collected dataset (e.g. CPCB Real-time Air Quality)
- `Source URL`: Remote endpoint accessed
- `Downloaded Timestamp`: Date and time of download execution
- `Rows Downloaded`: Number of rows successfully written
- `Download Status`: Ingestion result status (`SUCCESS`, `FALLBACK_MOCK`, `DRY_RUN`, or `FAILED`)

---

## Data Cleaning & Validation Workflow

Run the Day 2 cleaning pipeline after raw CPCB/OpenAQ files and `metadata/station_metadata.csv` exist:

```bash
python scripts/run_pipeline.py --clean-only
```

The cleaning command does not modify raw datasets. It reads the latest `cpcb_raw_*.csv` and `openaq_raw_*.csv` snapshots from `raw_data/`, then writes cleaned copies to:

- `processed_data/cpcb_cleaned_latest.csv`
- `processed_data/openaq_cleaned_latest.csv`

Cleaning operations include duplicate row removal, duplicate station/timestamp removal, datetime normalization, timezone-preserving timestamp formatting, pollutant name standardization, negative concentration removal, standard unit annotation where possible, and statistical outlier flagging. Outliers are retained and marked with `<pollutant>_outlier` boolean columns.

## Station Validation Workflow

Station validation reads `metadata/station_metadata.csv` and writes `metadata/validated_station_metadata.csv`.

Validation checks include missing latitude, missing longitude, missing city, missing state, duplicate stations, invalid coordinate ranges, and comparison against an official CPCB station list when one is available in `metadata/` as one of:

- `official_cpcb_station_list.csv`
- `cpcb_station_list.csv`
- `cpcb_stations_official.csv`

Mismatched station values are not modified automatically. They are reported in `Validation Warnings` and `Official Mismatch Fields`.

## Data Quality Report

The cleaning pipeline writes `metadata/data_quality_report.csv` with rows before cleaning, rows after cleaning, missing values, duplicates removed, duplicate timestamps removed, negative pollutant values, outlier count, invalid coordinates, station metadata mismatches, cleaning timestamp, warnings, and errors.

Cleaning and validation operations use the existing logger and append to `logs/data_collection.log`. Each operation logs the dataset, operation name, rows affected, warnings, errors, and execution time.

---

## Day 3 Feature Engineering & Dataset Integration

Run the Day 3 integration workflow after Day 2 cleaning has generated
`processed_data/cpcb_cleaned_latest.csv` and
`metadata/validated_station_metadata.csv`:

```bash
python scripts/run_pipeline.py --integrate-only
```

The integration pipeline preserves raw and cleaned datasets. It loads cleaned
CPCB observations, validated station metadata, satellite predictor grids when
available, and ERA5 meteorology grids when available. If satellite or ERA5
tabular grids are not present, it creates explicit placeholder interfaces so
the ML-ready schema remains stable while missing percentages are documented.

### Pipeline Flow

```text
processed_data/cpcb_cleaned_latest.csv
        +
metadata/validated_station_metadata.csv
        +
processed_data/satellite_predictors.csv (optional placeholder-backed input)
        +
processed_data/era5_meteorology.csv (optional placeholder-backed input)
        |
        v
nearest-neighbour spatial matching
        |
configurable temporal alignment: nearest, hourly, daily_average
        |
missing handling: interpolation, forward_fill, station_median, leave_missing
        |
features/merged_feature_table.csv
```

### Day 3 Outputs

- `features/merged_feature_table.csv`
- `features/feature_dictionary.csv`
- `features/feature_summary.json`
- `features/integration_report.md`

The merged feature table includes station keys, coordinates, date/time keys,
pollutant features, meteorology features, satellite features, and derived
calendar features. No ML models, AQI prediction, train/test split, scaling,
feature selection, dashboard, or visualization is performed in Day 3.

### Configuration

Temporal alignment defaults to `nearest` and can be configured with:

```env
TEMPORAL_ALIGNMENT=nearest
```

Supported values are `nearest`, `hourly`, and `daily_average`.

Missing-value handling defaults to `leave_missing` and can be configured with:

```env
MISSING_VALUE_STRATEGY=leave_missing
```

Supported values are `interpolation`, `forward_fill`, `station_median`, and
`leave_missing`. Rows are not silently removed by missing-data handling.

---

## Day 4A Dataset Preparation Workflow

Run the Day 4A Dataset Preparation workflow after Day 3 integration has generated the `features/merged_feature_table.csv`:

```bash
python scripts/run_pipeline.py --prepare-dataset
```

The dataset preparation pipeline executes the following stages in order:
1. **Dataset Validation**: Validates schema, timestamps, missing values, duplicates, and physical limits.
2. **Feature-Target Collocation**: Applies spatial and temporal tolerances to align predictors with the target.
3. **Dataset Builder**: Extracts and formats the final Feature Matrix and Target Vector.
4. **Reporting**: Generates the final output files and descriptive statistics.

### Day 4A Outputs

- `analysis_ready_dataset.csv` - The final, validated, collocated dataset.
- `dataset_summary.json` - High-level summary of the dataset.
- `feature_statistics.csv` - Detailed descriptive statistics for features.
- `dataset_quality_report.md` - A formatted markdown summary of data quality.

These output files are saved to the folder defined by `DATASET_OUTPUT_DIRECTORY` (defaults to the workspace root).

### Configuration

You can configure Day 4A behavior by setting the following environment variables:

- `DATASET_OUTPUT_DIRECTORY`: Directory for final outputs.
- `REQUIRED_TARGET_COLUMN`: The name of the target column (default: `AQI`).
- `REQUIRED_FEATURE_COLUMNS`: Comma-separated list of required features.
- `TEMPORAL_TOLERANCE_HOURS`: Tolerance for time matching (default: `1.0`).
- `SPATIAL_TOLERANCE_KM`: Tolerance for spatial matching (default: `50.0`).

---

## Day 4B ML Pipeline Integration Workflow

Run the Day 4B Machine Learning Pipeline Integration workflow to execute the full end-to-end ML process:

```bash
python scripts/run_pipeline.py --run-ml-pipeline
```

The ML pipeline executes the following stages in sequential order, halting immediately if any stage fails:
1. **Dataset Preparation**: Generates `analysis_ready_dataset.csv` and summary reports.
2. **Chronological Dataset Split**: Splits the dataset sequentially into training, validation, and testing sets.
3. **Baseline Model Training**: Trains a `RandomForestRegressor` on the training data and saves the model.
4. **Model Evaluation**: Evaluates the model against the validation set and generates performance metrics.

### Day 4B Outputs

- `train_dataset.csv`, `validation_dataset.csv`, `test_dataset.csv`
- `dataset_split_summary.json`
- `baseline_model.joblib`
- `model_training_summary.json`
- `evaluation_metrics.json`
- `feature_importance.csv`
- `evaluation_report.md`

These output files are saved to the folders defined by `DATASET_OUTPUT_DIRECTORY`, `MODEL_OUTPUT_PATH`, and `EVALUATION_OUTPUT_PATH` (defaulting to the workspace root).

### Configuration

You can configure Day 4B behavior by setting the following environment variables:

- `TRAIN_RATIO`: Ratio of data used for training (default: `0.70`).
- `VALIDATION_RATIO`: Ratio of data used for validation (default: `0.15`).
- `TEST_RATIO`: Ratio of data used for testing (default: `0.15`).
- `RANDOM_STATE`: Random state for reproducible operations (default: `42`).
- `MODEL_OUTPUT_PATH`: Directory for saving trained models.
- `EVALUATION_OUTPUT_PATH`: Directory for evaluation reports.
