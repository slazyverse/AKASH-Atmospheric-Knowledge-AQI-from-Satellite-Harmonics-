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
