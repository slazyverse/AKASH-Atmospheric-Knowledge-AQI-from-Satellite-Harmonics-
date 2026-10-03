# P0 Verification & Integration Report
### AKASH — Atmospheric Knowledge: AQI from Satellite Harmonics
**Team RAPTORS | Lead Data Engineer**
**Date:** 2026-07-09 | **Status:** FINALIZED

---

## 1. Previous Audit Findings & Reference

From the initial `feature_pipeline_audit_report.md`:

| ID | Finding | Severity | Stage | Status |
|----|---------|----------|-------|--------|
| **A1** | `era5_downloader.py` runs in `dry_run` mode by default — ERA5 NetCDF never downloaded. | P0 Critical | Raw Data | **RESOLVED** (Infrastructure ready) |
| **A2** | No satellite data collection module exists — satellite features are all null. | P0 Critical | Raw Data | **RESOLVED** (Infrastructure ready) |
| **A3** | `merger.py` silently falls back to `_placeholder_grid` when grid files are absent. | P0 High | Feature Engineering | **RESOLVED** (Infrastructure ready) |
| **A4** | `match_distance_km = 0.0` for placeholder rows — falsely signals spatial match. | P2 Medium | Feature Engineering | **P2 BACKLOG** |
| **A5** | `baseline_model.py` double-fillna silently converts all-null features to constant zeros. | P1 High | Model Training | **P1 BACKLOG** |
| **A6** | `AQI` (target) missing from merged table — triggers silent fallback to `PM2.5`. | P2 Medium | Dataset Preparation | **P2 BACKLOG** |

---

## 2. Earth Engine & Ingestion Module Duplicate Analysis

Per review requirements, we conducted a thorough workspace-wide scan (case-insensitive search for `earth_engine`, `gee`, `sentinel`, and `tropomi`) to check if any pre-existing modules or packages duplicated the new functionality:

* **Scan Result:** **No `earth_engine` package or equivalent ingestion module exists in the codebase.**
* **Reference Findings:**
  - Files under the `dashboard` and `backend` packages make thematic references to Sentinel-5P TROPOMI column densities (e.g., [`gis_interfaces.py`](file:///D:/AKASH/dashboard/core/gis_interfaces.py#L138) and [`hcho_service.py`](file:///D:/AKASH/dashboard/services/hcho_service.py)), but these are for visualization and API serving of predicted outputs.
  - No active ingestion pipeline or data collector for raw Sentinel-5P or ERA5 datasets was present in the repository prior to this implementation.
* **Duplication Status:** **0% Duplication.** The newly implemented `era5_processor.py` and `sentinel5p_collector.py` represent the unique and only ingestion paths for meteorological and satellite data in this pipeline.

---

## 3. Final P0 Implementation Summary

The P0 infrastructure was implemented under the `data_collection_pipeline` package:

### 3.1 Upgraded ERA5 Downloader
* **File:** [`era5_downloader.py`](file:///D:/AKASH/data_collection_pipeline/era5_downloader.py)
* **Status:** **Completed & Integrated**
* **Details:** Added automatic credential detection. If `~/.cdsapirc` or `CDSAPI_KEY` is present, `dry_run` defaults to `False`. Otherwise, it falls back gracefully to `True` (spec-only mode) with informative warnings, maintaining backward compatibility. Structured error handling was added to classify API response statuses (401/403/quota/timeout).

### 3.2 New ERA5 NetCDF to CSV Processor
* **File:** [`era5_processor.py`](file:///D:/AKASH/data_collection_pipeline/era5_processor.py)
* **Status:** **Completed & Integrated**
* **Details:** Reads the 3-D NetCDF file (`era5_meteorological_india.nc`), flattens it to a tidy long-format DataFrame, renames parameters to match the merger's expectation, calculates derived features (`Wind Speed` and `Wind Direction`), logs null-rates, and outputs `processed_data/era5_meteorology.csv`.

### 3.3 New Sentinel-5P / MODIS Satellite Data Collector
* **File:** [`sentinel5p_collector.py`](file:///D:/AKASH/data_collection_pipeline/sentinel5p_collector.py)
* **Status:** **Completed & Integrated**
* **Details:** Uses GEE Python API (`earthengine-api`) to extract daily Sentinel-5P TROPOMI (NO2, SO2, CO, O3, HCHO) and MODIS AOD over India. Supports OAuth (`~/.config/earthengine/credentials`) and Service Account JSON key configurations. Outputs `processed_data/satellite_predictors.csv` at 0.1° resolution.

---

## 4. Single-Workflow Pipeline Integration

The pipeline CLI entrypoint [`run_pipeline.py`](file:///D:/AKASH/data_collection_pipeline/scripts/run_pipeline.py) has been updated with dedicated flags to execute the new workflows seamlessly:

```bash
# 1. Download raw meteorological NetCDF file from CDS API
python scripts/run_pipeline.py --era5-only --no-dry-run

# 2. Process NetCDF into tidy tabular CSV
python scripts/run_pipeline.py --process-era5

# 3. Collect raw satellite columns from Earth Engine for a specific date
python scripts/run_pipeline.py --collect-satellite --date 2026-07-07

# 4. Integrate all datasets (CPCB, OpenAQ, ERA5, and Satellite)
python scripts/run_pipeline.py --integrate-only
```

Once step 4 completes, the merger reads the processed grid CSVs instead of fallback placeholders, injecting real features into `merged_feature_table.csv` and all downstream ML splits.

---

## 5. External Credentials & Blockers

Although the pipeline infrastructure is fully written and verified, execution of the live download modules requires external keys. Until credentials are configured, the pipeline falls back to writing spec JSON files and utilizing placeholder tables:

| Pipeline Stage | Blocker | Credential Setup |
|---|---|---|
| **ERA5 Retrieval** | CDS API Credentials | Create `~/.cdsapirc` containing: <br>`url: https://cds.climate.copernicus.eu/api/v2`<br>`key: <UID>:<API-KEY>` or set `CDSAPI_KEY`. |
| **Satellite Collection** | GEE Credentials | Run `earthengine authenticate` or configure service account credentials (`GEE_SERVICE_ACCOUNT` + JSON key file or env var). |

---

## 6. Remaining P1/P2 Downstream Improvements

These items are documented for the P1/P2 backlog since they fall outside the P0 ingestion scope and must not be modified in this cycle:

* **P1 (Model Training):** In [`baseline_model.py`](file:///D:/AKASH/data_collection_pipeline/model_training/baseline_model.py#L49), replace `X.fillna(X.mean()).fillna(0.0)` with code that detects and drops all-null columns, preventing silent zero-imputation when files are missing.
* **P2 (Feature Engineering):** In [`merger.py`](file:///D:/AKASH/data_collection_pipeline/feature_engineering/merger.py), set `match_distance_km = NaN` instead of `0.0` when returning a placeholder grid to avoid masking missing matches.
* **P2 (Dataset Preparation):** In [`feature_builder.py`](file:///D:/AKASH/data_collection_pipeline/feature_engineering/feature_builder.py#L28), add `AQI` to `ALL_FEATURES` to ensure the configured target column is preserved through the merge step.
