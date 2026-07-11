# Earth Engine Verification & Duplicate Analysis Report
### AKASH — Atmospheric Knowledge: AQI from Satellite Harmonics
**Team RAPTORS | Lead Data Engineer**
**Date:** 2026-07-09 | **Status:** READ-ONLY VERIFICATION COMPLETE

---

## 1. Existence Check & Branch Comparison

We performed a thorough check of the repository for the reported `earth_engine` package, `era5.py`, `modis.py`, `tropomi.py`, and any other GEE ingestion packages.

### 1.1 Local Branch (`main`)
* **`data_collection_pipeline/earth_engine/`**: Does not exist.
* **`data_collection_pipeline/era5_processor.py`**: Exists (processes local NetCDF files).
* **`data_collection_pipeline/sentinel5p_collector.py`**: Exists (orchestrates GEE queries and exports tabular CSV).

### 1.2 Remote Tracking Branch (`origin/main`)
* **`data_collection_pipeline/earth_engine/`**: **Exists** (tracked by Git, merged in PR #2, commit `852a563`).
  - `earth_engine/__init__.py`
  - `earth_engine/analysis_grid.py`
  - `earth_engine/base_loader.py`
  - `earth_engine/config.py`
  - `earth_engine/dataset_catalog.py`
  - `earth_engine/era5.py`
  - `earth_engine/export.py`
  - `earth_engine/initializer.py`
  - `earth_engine/modis.py`
  - `earth_engine/tropomi.py`
  - `earth_engine/utils.py`
  - `earth_engine/viirs.py`
* **`data_collection_pipeline/tests/test_gee_pipeline.py`**: **Exists**.
* **`docs/earth_engine.md`**: **Exists**.

---

## 2. Functionality & Architecture Comparison

Below is the comparison between our local P0 implementations and the classes defined in `origin/main`:

| Domain | Local Implementation (`main`) | Remote Package (`origin/main:earth_engine/`) |
| :--- | :--- | :--- |
| **ERA5 Data Source** | **Copernicus CDS API** (downloads physical `.nc` file via `cdsapi` and flattens it to CSV locally). | **Google Earth Engine** (loads `ECMWF/ERA5_LAND/HOURLY` image collections directly in-memory). |
| **Satellite Data Source** | **Google Earth Engine** (queries Sentinel-5P + MODIS 3km AOD, samples grid in-memory, writes CSV). | **Google Earth Engine** (defines `TROPOMILoader` and `MODISAODLoader` with QA bitmasks, but lacks export/sampling code). |
| **Ingestion Output** | `processed_data/era5_meteorology.csv`<br>`processed_data/satellite_predictors.csv` | Abstract export stubs to GCS/Assets/Drive only; does not generate the tabular files required by the feature merger. |
| **Integration** | Fully wired into `scripts/run_pipeline.py`. | Declared as sprint assets, but not integrated into `main.py` or the CLI. |

---

## 3. Duplication & Complementary Analysis

### 3.1 ERA5 Modules
* **Verdict:** **Different Implementations / Complementary**.
* **Analysis:** Local `era5_processor.py` processes NetCDF single-levels reanalysis downloaded via CDS API, whereas `earth_engine/era5.py` loads hourly ERA5 Land reanalysis in GEE. The target formats and download paths are different.

### 3.2 Satellite Ingestion Modules
* **Verdict:** **Overlapping & Complementary**.
* **Analysis:**
  - **Overlapping:** Both query the same GEE Sentinel-5P L3 collections for HCHO, NO2, SO2, CO, and O3.
  - **Different MODIS AOD:** Local uses `MODIS/061/MOD04_3K` (3 km resolution), while remote uses `MODIS/061/MCD19A2_GRANULES` (1 km resolution).
  - **Missing Remote Logic:** The remote `earth_engine` package is a library of abstract loaders. It lacks the orchestration logic to perform spatial coordinate sampling over India's bounding box and write the resulting table to `processed_data/satellite_predictors.csv`.

---

## 4. Recommended Integration Architecture

Per instructions, **no refactoring has been performed** to preserve pipeline stability and prevent breaking working components. When integration is performed in the next sprint, we recommend the following unified structure:

```
[scripts/run_pipeline.py]
         ↓
[sentinel5p_collector.py (Runner)]
         ↓ imports and uses
[earth_engine.tropomi / earth_engine.modis (Loaders)]
         ↓
  [GEE ImageCollection]
         ↓ sampled on
[earth_engine.AnalysisGrid (Grid system)]
         ↓
[processed_data/satellite_predictors.csv]
```

### Integration Details:
1. **GEE Initialization:** Settle on `earth_engine/initializer.py` as the single GEE initialization entrypoint.
2. **Collection Queries:** Replace GEE queries in `sentinel5p_collector.py` with `TROPOMILoader` and `MODISAODLoader` to leverage their built-in QA cloud masking.
3. **Grid Alignment:** Use `AnalysisGrid` from the `earth_engine` package to standardize coordinates rather than simple degrees rounding.

---

## 5. Refactoring Requirements Summary

* **Is refactoring required right now?** **NO**. No refactoring is required in this step. The local pipeline runs correctly and does not collide since the `earth_engine` package is currently isolated on `origin/main` and not pulled or invoked in the active path.
* **Compatibility:** All active CLI interfaces and files are preserved as-is.
