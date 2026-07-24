# Placeholder Flag Audit Report

**Project:** AKASH — Atmospheric Knowledge AQI from Satellite Harmonics  
**Date:** 2026-07-12  
**Scope:** Audit of `placeholder_used` boolean flag across feature engineering and dataset preparation.

---

## 1. Executive Summary

During the pipeline audit, it was observed that in `analysis_ready_dataset.csv`, rows corresponding to stations with missing Google Earth Engine (GEE) satellite data (e.g. Mumbai BKC, Mumbai Colaba, and Patna Rajbansi Nagar) were either dropped, matched incorrectly to distant cities, or flagged as `placeholder_used = False` even when they were sentinel placeholder rows. 

This report traces the origin, behavior, and resolution of this issue. By moving the evaluation of the row-level placeholder flags to **before** the missing value strategies (imputation) are applied, the pipeline now correctly and permanently records `placeholder_used = True` for all stations that fall back to GEE sentinel placeholder rows, regardless of subsequent downstream imputation.

---

## 2. Implementation Trace

The `placeholder_used` column flows through the following stages:

1. **Origin (Collection):** If a station has no valid GEE satellite imagery due to monsoon cloud cover or orbital gaps, `sentinel5p_collector.py` inserts a sentinel row at that station's registry coordinates with all satellite band columns set to `float("nan")`.
2. **Matching (Feature Integration):** In `merger.py` (`integrate_datasets()`), the CPCB observations are joined with the satellite predictors using `nearest_grid_row()`. For stations with no GEE imagery, they match their own 0 km distance sentinel row, propagating `NaN` values for all satellite features.
3. **Imputation (Missing Value Strategy):** `apply_missing_strategy()` is called to impute `NaN` values using interpolation, forward-filling, or station-median values.
4. **Flag Creation:** The boolean series `is_sat_placeholder_row` and `is_met_placeholder_row` check if all satellite or meteorology features in a row are NaN, or if a global dataset placeholder is active:
   ```python
   is_sat_placeholder_row = features[SATELLITE_FEATURES].isna().all(axis=1) | is_satellite_placeholder
   is_met_placeholder_row = features[METEOROLOGY_FEATURES].isna().all(axis=1) | is_era5_placeholder
   features["placeholder_used"] = is_sat_placeholder_row | is_met_placeholder_row
   ```
5. **Output (Dataset Preparation):** The final `analysis_ready_dataset.csv` preserves the column, which is exported directly.

---

## 3. Current Semantics (Judgment Call)

There were no explicit tests checking `placeholder_used` behavior, but comments in `merger.py` provide clear evidence of the flag's intended meaning:
* `validation_summary = f"Flagged {total_true_rows} rows as placeholder_used=True due to missing/sentinel station-level GEE satellite observations."`

Based on this evidence, we established the following semantic standard:
* **`placeholder_used = True`** represents that a row's satellite or ERA5 features were generated from a placeholder (global fallback grid or station-level sentinel row) because physical GEE/ERA5 observations were missing.
* **`placeholder_used = False`** represents that a row matched real, physical satellite and ERA5 observations.

---

## 4. Observed Behavior & Root Cause

### Observed Behavior (Before Fix)
* In original runs (without sentinel rows), `placeholder_used` was `False` for every row, but Mumbai BKC and Patna observations matched distant stations (Pune and Bhagalpur) and were subsequently rejected by collocation.
* When sentinel rows were introduced to preserve observations, `placeholder_used` evaluated to `False` for any sentinel rows that were successfully imputed by `apply_missing_strategy()`.

### Root Cause
Because the `placeholder_used` flag was calculated **after** `apply_missing_strategy()`, any row that originally matched a sentinel row (all-NaN satellite features) but was subsequently filled with numeric values (e.g. via station medians) lost its NaN values. As a result, `isna().all(axis=1)` evaluated to `False`, resetting the flag to `False` and masking the fact that the original GEE imagery was missing.

---

## 5. Applied Fix

The evaluation of the row-level placeholder flags was moved **before** the missing value strategy is applied in `merger.py`:

```diff
     features = build_features(merged)
 
+    # ------------------------------------------------------------------
+    # Compute row-level placeholder flags BEFORE applying missing value strategy
+    # ------------------------------------------------------------------
+    is_sat_placeholder_row = features[SATELLITE_FEATURES].isna().all(axis=1) | is_satellite_placeholder
+    is_met_placeholder_row = features[METEOROLOGY_FEATURES].isna().all(axis=1) | is_era5_placeholder
+
     # Log propagation after build_features (must not mutate target column)
     if target_col in features.columns:
         non_null_after_build = features[target_col].notna().sum()
@@ -343,11 +343,7 @@
             target_col,
         )
 
-    # ------------------------------------------------------------------
-    # Compute row-level placeholder_used column
-    # ------------------------------------------------------------------
-    is_sat_placeholder_row = features[SATELLITE_FEATURES].isna().all(axis=1) | is_satellite_placeholder
-    is_met_placeholder_row = features[METEOROLOGY_FEATURES].isna().all(axis=1) | is_era5_placeholder
+    # Assign row-level placeholder flag computed before imputation
     features["placeholder_used"] = is_sat_placeholder_row | is_met_placeholder_row
```

This guarantees that if a row matches a sentinel row, it is permanently marked as `placeholder_used = True`, regardless of whether the NaNs are later imputed by the missing strategy.

---

## 6. Before / After Examples

### Before Fix (Imputed Sentinel Row)
* **Station:** Bandra Kurla Complex, Mumbai
* **AOD:** `450.0` (Imputed from station median)
* **CO Column:** `0.025` (Imputed from station median)
* **`placeholder_used`:** `False` ❌ (Omission of GEE imagery is masked)

### After Fix (Imputed Sentinel Row)
* **Station:** Bandra Kurla Complex, Mumbai
* **AOD:** `450.0` (Imputed from station median)
* **CO Column:** `0.025` (Imputed from station median)
* **`placeholder_used`:** `True` ✅ (Correctly flags that the underlying satellite data was missing)

---

## 7. Maintenance Recommendations

1. **Keep Imputation and Flagging Decoupled:** Any future feature engineering step or missing strategy (e.g. forward-fill, interpolation) should always be applied *after* the `placeholder_used` flag is computed.
2. **Add Unit Test Coverage:** A unit test should be added to `test_feature_engineering.py` that mocks a merged table with some all-NaN GEE features and asserts that `placeholder_used` is set to `True` even when a median-imputation strategy is active.
