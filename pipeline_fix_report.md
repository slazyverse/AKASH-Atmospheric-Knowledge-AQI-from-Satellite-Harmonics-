# Historical ARD Pipeline V2 ? Critical Defect Resolution Report

## 1. Executive Summary

This report documents the resolution of the two critical data integrity defects identified during the validation of the Analysis Ready Dataset (ARD) Pipeline V2. By enforcing rigorous join cardinality rules and establishing a robust coordinate resolution protocol, the pipeline successfully eliminated 33,240 duplicate records and 510 stations with invalid/missing geospatial coordinates.

**Final Dataset Metrics:**
- Total Rows: 3,333
- Total Columns: 53
- Duplicate Primary Keys: 0
- Invalid Coordinates: 0
- Pipeline Status: **PASS**

---

## 2. Issue 1: Duplicate Primary Keys (Cartesian Product)

### Root Cause
The validation harness revealed exactly 33,240 duplicate records grouped by `(station_id, timestamp_utc)`. Investigation determined that `pandas.merge` defaulted to many-to-many joins. Because the underlying right-hand datasets (ERA5 Meteorology, Sentinel-5P, MODIS MAIAC) had not been strictly deduplicated or aggregated down to the primary temporal grain (`date` or `timestamp_utc`) prior to joining, the merge caused an exponential Cartesian product expansion of rows.

### Resolution
1. **Pre-aggregation and Deduplication**: A tracking function (`prepare_right_df`) was introduced to monitor the rows entering every join. If duplicates exist in the secondary dataset, they are collapsed using `.groupby().mean(numeric_only=True)`.
2. **Cardinality Enforcement**: All spatial and meteorological merges in `build_ard_v2.py` were hardened using Pandas' strict `validate` assertions:
   - `ERA5`: `validate='1:1'` (Hourly grain matching base dataset)
   - `Sentinel-5P` & `MODIS`: `validate='m:1'` (Daily grain broadcasted to hourly base dataset)
   - `Static Features`: `validate='m:1'` (Static metadata broadcasted to base dataset)
   
> [!TIP]
> The deduplication logs are now written to `d:\AKASH\duplicate_key_report.csv` as an audit trail for future dataset ingestion runs.

---

## 3. Issue 2: Invalid Coordinate Quarantining

### Root Cause
The `build_station_registry.py` script was defaulting unresolvable coordinates (and `pd.NA` values) to `0.0, 0.0` mathematically, masking missing data as valid points off the coast of Africa. These points subsequently poisoned spatial features, land cover codes, and geospatial distance metrics.

### Resolution
1. **Strict Spatial Bounds Filtering**: The Metadata Builder was updated to strictly validate that `latitude` falls between `[8.0, 38.0]` and `longitude` falls between `[68.0, 98.0]`. 
2. **Quarantine Logic**: Coordinates failing the boundary check or defaulting to exactly `0.0` are tagged with `coordinate_status = 'MISSING'` rather than 'VALID'.
3. **ARD Upstream Rejection**: `build_ard_v2.py` now specifically identifies the quarantined stations using `meta_df` and filters out their historical ground observations *prior* to joining any satellite/meteorological data.

> [!NOTE]
> Out of 1031 scraped locations, 510 OpenAQ stations missing standard coordinate structures were gracefully quarantined, dropping the invalid geometry while saving a log to `d:\AKASH\coordinate_resolution_report.csv`.

---

## 4. Verification

1. A full end-to-end execution of `build_station_registry.py` and `build_ard_v2.py` succeeded.
2. The `validate_ard_v2.py` harness reported **0 Duplicate Primary Keys** and **0 Zero/Invalid Coordinates**.
3. A separate standalone unit test suite (`d:\AKASH\tests\test_validation_fixes.py`) confirmed data integrity mathematically.
