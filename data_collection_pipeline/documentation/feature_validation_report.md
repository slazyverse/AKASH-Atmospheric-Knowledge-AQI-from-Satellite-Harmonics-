# AQI Pipeline — Feature Validation Report

*Generated: 2026-07-13 13:01 UTC*

## Executive Summary

| Status | Meaning | Count |
|--------|---------|-------|
| ✅ PASS | Meets all expectations | 50 |
| ℹ️ WARNING (expected) | Expected operational limitation (no action required) | 7 |
| ⚠️ WARNING (investigate) | Unexpected condition (requires investigation) | 0 |
| ❌ FAIL | Hard failure (must fix) | 0 |
| — SKIP | Not in pipeline yet | 3 |
| **Total** | | **60** |

### Configured Temporal Offset Window

| Parameter | Value |
|-----------|-------|
| `TEMPORAL_WINDOW_DAYS` | 3 days |
| `MAX_ADAPTIVE_LOOKBACK_DAYS` | 14 days |
| **Valid offset range** | **[−14, +3] days** |

> [!NOTE]
> Temporal offsets within the configured window are **PASS**.
> Offsets outside the window are **WARNING (investigate)** (the contributing
> observation falls outside the adaptive collection window).


### Scientific Terminology & Validation Context

The data collection pipeline explicitly distinguishes between satellite products to apply accurate QA filtering context:

**Sentinel-5P Products (NO2, SO2, HCHO, CO, O3):**
- **Processing**: Level-2 retrieval to Level-3 gridding.
- **Quality Metric**: Standard `qa_value` constraints.
- **Validation References**: Sentinel-5P ATBDs and Product Readmes.
- **Context**: Google Earth Engine ingests Level-3 Sentinel-5P data, with standard `qa_value` masking pre-applied. The pipeline subsequently applies a secondary cloud fraction filter.

**MODIS MAIAC Products (AOD):**
- **Processing**: Level-2 (MCD19A2).
- **Quality Metric**: MAIAC `AOD_QA` bits and quality flags.
- **Validation References**: MODIS MAIAC ATBD and User Guide.
- **Context**: AOD relies on complex surface reflectance and cloud masking specific to MAIAC, inherently distinct from UV/DOAS logic.

## Feature Status Overview

| Feature | Group | Unit | Overall | Collector | Merger | Dataset Builder | merged<br>feature<br>table.csv | analysis<br>ready<br>dataset.csv | train<br>dataset.csv | FeatureGroupManager |
|---------|-------|------|---------|---|---|---|---|---|---|---|
| PM2.5 | target | µg/m³ | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| PM10 | target | µg/m³ | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| NO2 | target | µg/m³ | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| SO2 | target | µg/m³ | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| CO | target | mg/m³ | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| O3 | target | µg/m³ | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| AQI | target | index | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| AOD | satellite | unitless (physical AOD, scale factor 0.001 applied) | ℹ️ WARNING (expected) | ℹ️ | ℹ️ | ℹ️ | ℹ️ | ℹ️ | ℹ️ | ✅ |
| HCHO | satellite | mol/m2 | ℹ️ WARNING (expected) | ℹ️ | ℹ️ | ℹ️ | ℹ️ | ℹ️ | ℹ️ | ✅ |
| NO2 Column | satellite | mol/m2 | ℹ️ WARNING (expected) | ℹ️ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| SO2 Column | satellite | mol/m2 | ℹ️ WARNING (expected) | ℹ️ | ℹ️ | ℹ️ | ℹ️ | ℹ️ | ℹ️ | ✅ |
| CO Column | satellite | mol/m2 | ℹ️ WARNING (expected) | ℹ️ | ℹ️ | ℹ️ | ℹ️ | ℹ️ | ℹ️ | ✅ |
| O3 Column | satellite | mol/m2 | ℹ️ WARNING (expected) | ℹ️ | ℹ️ | ℹ️ | ℹ️ | ℹ️ | ℹ️ | ✅ |
| Temperature | meteorology | K | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Relative Humidity | meteorology | % | ℹ️ WARNING (expected) | ℹ️ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Boundary Layer Height | meteorology | m | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Wind Speed | meteorology | m/s | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Wind Direction | meteorology | degrees | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Surface Pressure | meteorology | Pa | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Latitude | geography | degrees | ✅ PASS | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Longitude | geography | degrees | ✅ PASS | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Elevation | geography | m | — SKIP | — | — | — | — | — | — | — |
| Distance to Coast | geography | km | — SKIP | — | — | — | — | — | — | — |
| Land Cover Class | geography | class index | — SKIP | — | — | — | — | — | — | — |
| Day of Week | temporal | index (0=Monday) | ✅ PASS | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Month | temporal | index (1–12) | ✅ PASS | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Season | temporal | category | ✅ PASS | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| Weekend Flag | temporal | bool | ✅ PASS | — | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| AOD Obs Date | provenance | date (YYYY-MM-DD) | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| HCHO Obs Date | provenance | date (YYYY-MM-DD) | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| NO2 Column Obs Date | provenance | date (YYYY-MM-DD) | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| SO2 Column Obs Date | provenance | date (YYYY-MM-DD) | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| CO Column Obs Date | provenance | date (YYYY-MM-DD) | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| O3 Column Obs Date | provenance | date (YYYY-MM-DD) | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| AOD Temporal Offset | provenance | days | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| HCHO Temporal Offset | provenance | days | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| NO2 Column Temporal Offset | provenance | days | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| SO2 Column Temporal Offset | provenance | days | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| CO Column Temporal Offset | provenance | days | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| O3 Column Temporal Offset | provenance | days | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| AOD Publication Lag | provenance | days | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| HCHO Publication Lag | provenance | days | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| NO2 Column Publication Lag | provenance | days | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| SO2 Column Publication Lag | provenance | days | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| CO Column Publication Lag | provenance | days | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| O3 Column Publication Lag | provenance | days | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| AOD QA Status | provenance | qa_value | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| HCHO QA Status | provenance | qa_value | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| NO2 Column QA Status | provenance | qa_value | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| SO2 Column QA Status | provenance | qa_value | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| CO Column QA Status | provenance | qa_value | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| O3 Column QA Status | provenance | qa_value | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| placeholder_used | provenance | bool | ✅ PASS | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| requested_date | provenance | date (YYYY-MM-DD) | ✅ PASS | ✅ | — | — | — | — | — | — |
| satellite_match_distance_km | provenance | km | ✅ PASS | — | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| era5_match_distance_km | provenance | km | ✅ PASS | — | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| Station ID | metadata | id | ✅ PASS | — | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| Station Name | metadata | name | ✅ PASS | — | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| Date | metadata | date (YYYY-MM-DD) | ✅ PASS | — | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| Time | metadata | time (HH:MM:SS) | ✅ PASS | — | ✅ | ✅ | ✅ | ✅ | ✅ | — |

## ℹ️ WARN_EXPECTED (expected operational limitations — no action required)

> [!NOTE]
> These conditions are scientifically expected and consistent with
> the pipeline configuration. No code change is required.

### `AOD`
- **[Collector / null_rate]** Missingness is consistent with MAIAC cloud masking.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 6.8 days).
    - Missingness is consistent with MAIAC cloud masking.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: MODIS MAIAC MCD19A2 ATBD, MODIS Land Quality Assurance guides, and Copernicus/GEE MODIS dataset documentation
    Supporting Diagnostic: null_pct = 91.3%
- **[Merger / null_rate]** Missingness is consistent with MAIAC cloud masking.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    Scientific Interpretation:
    - Missingness is consistent with daily orbit overpass gaps (locations fell outside daily orbit swath).
    - Missingness is consistent with MAIAC cloud masking.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: MODIS MAIAC MCD19A2 ATBD, MODIS Land Quality Assurance guides, and Copernicus/GEE MODIS dataset documentation
    Supporting Diagnostic: null_pct = 100.0%
- **[Dataset Builder / null_rate]** Missingness is consistent with MAIAC cloud masking.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    Scientific Interpretation:
    - Missingness is consistent with daily orbit overpass gaps (locations fell outside daily orbit swath).
    - Missingness is consistent with MAIAC cloud masking.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: MODIS MAIAC MCD19A2 ATBD, MODIS Land Quality Assurance guides, and Copernicus/GEE MODIS dataset documentation
    Supporting Diagnostic: null_pct = 100.0%
- **[merged_feature_table.csv / null_rate]** Missingness is consistent with MAIAC cloud masking.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    Scientific Interpretation:
    - Missingness is consistent with daily orbit overpass gaps (locations fell outside daily orbit swath).
    - Missingness is consistent with MAIAC cloud masking.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: MODIS MAIAC MCD19A2 ATBD, MODIS Land Quality Assurance guides, and Copernicus/GEE MODIS dataset documentation
    Supporting Diagnostic: null_pct = 100.0%
- **[analysis_ready_dataset.csv / null_rate]** Missingness is consistent with MAIAC cloud masking.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    Scientific Interpretation:
    - Missingness is consistent with daily orbit overpass gaps (locations fell outside daily orbit swath).
    - Missingness is consistent with MAIAC cloud masking.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: MODIS MAIAC MCD19A2 ATBD, MODIS Land Quality Assurance guides, and Copernicus/GEE MODIS dataset documentation
    Supporting Diagnostic: null_pct = 100.0%
- **[train_dataset.csv / null_rate]** Missingness is consistent with MAIAC cloud masking.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    Scientific Interpretation:
    - Missingness is consistent with daily orbit overpass gaps (locations fell outside daily orbit swath).
    - Missingness is consistent with MAIAC cloud masking.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: MODIS MAIAC MCD19A2 ATBD, MODIS Land Quality Assurance guides, and Copernicus/GEE MODIS dataset documentation
    Supporting Diagnostic: null_pct = 100.0%

### `HCHO`
- **[Collector / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 6.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P HCHO ATBD (S5P-L2-HCHO-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-HCHO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 14.9%
- **[Merger / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P HCHO ATBD (S5P-L2-HCHO-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-HCHO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 25.0%
- **[Dataset Builder / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P HCHO ATBD (S5P-L2-HCHO-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-HCHO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 25.0%
- **[merged_feature_table.csv / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P HCHO ATBD (S5P-L2-HCHO-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-HCHO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 25.0%
- **[analysis_ready_dataset.csv / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P HCHO ATBD (S5P-L2-HCHO-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-HCHO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 25.0%
- **[train_dataset.csv / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P HCHO ATBD (S5P-L2-HCHO-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-HCHO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 25.9%

### `NO2 Column`
- **[Collector / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with publication lag of 5 days (adaptive lookback applied).
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 6.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P NO2 Column ATBD (S5P-L2-NO2-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-NO2), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 5.6%

### `SO2 Column`
- **[Collector / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 6.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P SO2 Column ATBD (S5P-L2-SO2-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-SO2), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 29.8%
- **[Merger / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P SO2 Column ATBD (S5P-L2-SO2-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-SO2), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 41.7%
- **[Dataset Builder / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P SO2 Column ATBD (S5P-L2-SO2-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-SO2), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 41.7%
- **[merged_feature_table.csv / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P SO2 Column ATBD (S5P-L2-SO2-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-SO2), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 41.7%
- **[analysis_ready_dataset.csv / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P SO2 Column ATBD (S5P-L2-SO2-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-SO2), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 41.7%
- **[train_dataset.csv / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P SO2 Column ATBD (S5P-L2-SO2-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-SO2), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 41.4%

### `CO Column`
- **[Collector / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 6.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P CO Column ATBD (S5P-L2-CO-ATBD), Product Readme File (S5P-MPC-SRON-PRF-CO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 6.2%
- **[Merger / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P CO Column ATBD (S5P-L2-CO-ATBD), Product Readme File (S5P-MPC-SRON-PRF-CO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 16.7%
- **[Dataset Builder / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P CO Column ATBD (S5P-L2-CO-ATBD), Product Readme File (S5P-MPC-SRON-PRF-CO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 16.7%
- **[merged_feature_table.csv / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P CO Column ATBD (S5P-L2-CO-ATBD), Product Readme File (S5P-MPC-SRON-PRF-CO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 16.7%
- **[analysis_ready_dataset.csv / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P CO Column ATBD (S5P-L2-CO-ATBD), Product Readme File (S5P-MPC-SRON-PRF-CO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 16.7%
- **[train_dataset.csv / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P CO Column ATBD (S5P-L2-CO-ATBD), Product Readme File (S5P-MPC-SRON-PRF-CO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 17.2%

### `O3 Column`
- **[Collector / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 6.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P O3 Column ATBD (S5P-L2-O3-ATBD), Product Readme File (S5P-MPC-DLR-PRF-O3), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 19.9%
- **[Merger / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P O3 Column ATBD (S5P-L2-O3-ATBD), Product Readme File (S5P-MPC-DLR-PRF-O3), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 25.0%
- **[Dataset Builder / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P O3 Column ATBD (S5P-L2-O3-ATBD), Product Readme File (S5P-MPC-DLR-PRF-O3), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 25.0%
- **[merged_feature_table.csv / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P O3 Column ATBD (S5P-L2-O3-ATBD), Product Readme File (S5P-MPC-DLR-PRF-O3), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 25.0%
- **[analysis_ready_dataset.csv / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P O3 Column ATBD (S5P-L2-O3-ATBD), Product Readme File (S5P-MPC-DLR-PRF-O3), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 25.0%
- **[train_dataset.csv / null_rate]** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P O3 Column ATBD (S5P-L2-O3-ATBD), Product Readme File (S5P-MPC-DLR-PRF-O3), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 25.9%

### `Relative Humidity`
- **[Collector / scientific_validation]** 453 values between 100.0–100.5% (ERA5 spectral truncation artefact; expected, documented, not a bug). observed max=100%

## Detailed Validation Results

### Group: `geography`

#### ✅ `Latitude` (PASS)

- **Unit:** degrees
- **Source:** Station registry
- **In ML model:** Yes
- **Valid range:** (5.0, 40.0)
- **Description:** Station latitude (India: ~6–38°N)

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Merger | ✅ PASS | degrees | — | PASS | 84/84 | 0.0% | 0.0% | 12.92 | 20.81 | 28.65 | 5.736 | 12 | 14.3% | 32.9 | 0.2761 | 28.65, 28.61, 19.06 |
| Dataset Builder | ✅ PASS | degrees | — | PASS | 84/84 | 0.0% | 0.0% | 12.92 | 20.81 | 28.65 | 5.736 | 12 | 14.3% | 32.9 | 0.2761 | 25.6, 28.65, 28.61 |
| merged_feature_table.csv | ✅ PASS | degrees | — | PASS | 84/84 | 0.0% | 0.0% | 12.92 | 20.81 | 28.65 | 5.736 | 12 | 14.3% | 32.9 | 0.2761 | 28.65, 28.61, 19.06 |
| analysis_ready_dataset.csv | ✅ PASS | degrees | — | PASS | 84/84 | 0.0% | 0.0% | 12.92 | 20.81 | 28.65 | 5.736 | 12 | 14.3% | 32.9 | 0.2761 | 25.6, 28.65, 28.61 |
| train_dataset.csv | ✅ PASS | degrees | — | PASS | 58/58 | 0.0% | 0.0% | 12.92 | 20.81 | 28.65 | 5.662 | 12 | 20.7% | 32.06 | 0.2726 | 25.6, 12.97, 17.46 |
| FeatureGroupManager | ✅ PASS | degrees | — | PASS | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

#### ✅ `Longitude` (PASS)

- **Unit:** degrees
- **Source:** Station registry
- **In ML model:** Yes
- **Valid range:** (65.0, 100.0)
- **Description:** Station longitude (India: ~65–100°E)

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Merger | ✅ PASS | degrees | — | PASS | 84/84 | 0.0% | 0.0% | 72.86 | 78.03 | 88.36 | 4.999 | 12 | 14.3% | 24.99 | 0.06269 | 77.32, 77.21, 72.86 |
| Dataset Builder | ✅ PASS | degrees | — | PASS | 84/84 | 0.0% | 0.0% | 72.86 | 78.03 | 88.36 | 4.999 | 12 | 14.3% | 24.99 | 0.06269 | 85.11, 77.32, 77.21 |
| merged_feature_table.csv | ✅ PASS | degrees | — | PASS | 84/84 | 0.0% | 0.0% | 72.86 | 78.03 | 88.36 | 4.999 | 12 | 14.3% | 24.99 | 0.06269 | 77.32, 77.21, 72.86 |
| analysis_ready_dataset.csv | ✅ PASS | degrees | — | PASS | 84/84 | 0.0% | 0.0% | 72.86 | 78.03 | 88.36 | 4.999 | 12 | 14.3% | 24.99 | 0.06269 | 85.11, 77.32, 77.21 |
| train_dataset.csv | ✅ PASS | degrees | — | PASS | 58/58 | 0.0% | 0.0% | 72.86 | 78.44 | 88.36 | 5.08 | 12 | 20.7% | 25.81 | 0.06364 | 85.11, 77.59, 78.44 |
| FeatureGroupManager | ✅ PASS | degrees | — | PASS | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

#### — `Elevation` (SKIP)

- **Unit:** m
- **Source:** DEM
- **In ML model:** No
- **Valid range:** (-100.0, 9000.0)
- **Description:** Altitude above sea level

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Merger | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Dataset Builder | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| merged_feature_table.csv | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| analysis_ready_dataset.csv | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| train_dataset.csv | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

#### — `Distance to Coast` (SKIP)

- **Unit:** km
- **Source:** GIS
- **In ML model:** No
- **Valid range:** (0.0, 2000.0)
- **Description:** Distance to nearest shoreline

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Merger | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Dataset Builder | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| merged_feature_table.csv | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| analysis_ready_dataset.csv | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| train_dataset.csv | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

#### — `Land Cover Class` (SKIP)

- **Unit:** class index
- **Source:** MODIS
- **In ML model:** No
- **Valid range:** N/A
- **Description:** Dominant land cover type index

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Merger | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Dataset Builder | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| merged_feature_table.csv | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| analysis_ready_dataset.csv | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| train_dataset.csv | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

### Group: `metadata`

#### ✅ `Station ID` (PASS)

- **Unit:** id
- **Source:** CPCB station registry
- **In ML model:** No
- **Valid range:** N/A
- **Description:** Unique CPCB monitoring station code (e.g. DL_01)

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Merger | ✅ PASS | id | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | STN_001, STN_004, STN_002 |
| Dataset Builder | ✅ PASS | id | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | STN_008, STN_001, STN_004 |
| merged_feature_table.csv | ✅ PASS | id | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | STN_001, STN_004, STN_002 |
| analysis_ready_dataset.csv | ✅ PASS | id | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | STN_008, STN_001, STN_004 |
| train_dataset.csv | ✅ PASS | id | — | PASS | 58/58 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | STN_008, STN_007, STN_009 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

#### ✅ `Station Name` (PASS)

- **Unit:** name
- **Source:** CPCB station registry
- **In ML model:** No
- **Valid range:** N/A
- **Description:** Human-readable name of the monitoring station

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Merger | ✅ PASS | name | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | Anand Vihar, Delhi -, Dwarka-Sector 8, Del, Bandra Kurla Complex |
| Dataset Builder | ✅ PASS | name | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | Rajbansi Nagar, Patn, Anand Vihar, Delhi -, Dwarka-Sector 8, Del |
| merged_feature_table.csv | ✅ PASS | name | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | Anand Vihar, Delhi -, Dwarka-Sector 8, Del, Bandra Kurla Complex |
| analysis_ready_dataset.csv | ✅ PASS | name | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | Rajbansi Nagar, Patn, Anand Vihar, Delhi -, Dwarka-Sector 8, Del |
| train_dataset.csv | ✅ PASS | name | — | PASS | 58/58 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | Rajbansi Nagar, Patn, Peenya, Bengaluru - , Sanathnagar, Hyderab |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

#### ✅ `Date` (PASS)

- **Unit:** date (YYYY-MM-DD)
- **Source:** Pipeline
- **In ML model:** No
- **Valid range:** N/A
- **Description:** Observation date string

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Merger | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-12, 2026-07-12, 2026-07-12 |
| Dataset Builder | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-06, 2026-07-06, 2026-07-06 |
| merged_feature_table.csv | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-12, 2026-07-12, 2026-07-12 |
| analysis_ready_dataset.csv | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-06, 2026-07-06, 2026-07-06 |
| train_dataset.csv | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 58/58 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-06, 2026-07-06, 2026-07-06 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

#### ✅ `Time` (PASS)

- **Unit:** time (HH:MM:SS)
- **Source:** Pipeline
- **In ML model:** No
- **Valid range:** N/A
- **Description:** Observation time string

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Merger | ✅ PASS | time (HH:MM:SS) | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | 12:00:00, 12:00:00, 12:00:00 |
| Dataset Builder | ✅ PASS | time (HH:MM:SS) | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | 12:00:00, 12:00:00, 12:00:00 |
| merged_feature_table.csv | ✅ PASS | time (HH:MM:SS) | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | 12:00:00, 12:00:00, 12:00:00 |
| analysis_ready_dataset.csv | ✅ PASS | time (HH:MM:SS) | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | 12:00:00, 12:00:00, 12:00:00 |
| train_dataset.csv | ✅ PASS | time (HH:MM:SS) | — | PASS | 58/58 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | 12:00:00, 12:00:00, 12:00:00 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

### Group: `meteorology`

#### ✅ `Temperature` (PASS)

- **Unit:** K
- **Source:** ERA5
- **In ML model:** Yes
- **Valid range:** (200.0, 330.0)
- **Description:** 2 m air temperature. Stored in Kelvin throughout the pipeline (ERA5 native). Valid range 200–330 K covers terrestrial surface temperatures for India. If a Kelvin → Celsius conversion is added downstream, add a StageSpec with unit='°C' and valid_range=(-50.0, 60.0) for the converted stages.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | K | K | PASS | 374616/374616 | 0.0% | 0.0% | 255.2 | 300.8 | 317.4 | 9.486 | 98039 | 26.2% | 89.99 | 0.03193 | 296.5, 294.3, 295.6 |
| Merger | ✅ PASS | K | K | PASS | 84/84 | 0.0% | 0.0% | 295 | 300.2 | 302.7 | 2.512 | 10 | 11.9% | 6.312 | 0.008386 | 300.9, 301.3, 300.2 |
| Dataset Builder | ✅ PASS | K | K | PASS | 84/84 | 0.0% | 0.0% | 295 | 300.2 | 302.7 | 2.512 | 10 | 11.9% | 6.312 | 0.008386 | 302.5, 300.9, 301.3 |
| merged_feature_table.csv | ✅ PASS | K | K | PASS | 84/84 | 0.0% | 0.0% | 295 | 300.2 | 302.7 | 2.512 | 10 | 11.9% | 6.312 | 0.008386 | 300.9, 301.3, 300.2 |
| analysis_ready_dataset.csv | ✅ PASS | K | K | PASS | 84/84 | 0.0% | 0.0% | 295 | 300.2 | 302.7 | 2.512 | 10 | 11.9% | 6.312 | 0.008386 | 302.5, 300.9, 301.3 |
| train_dataset.csv | ✅ PASS | K | K | PASS | 58/58 | 0.0% | 0.0% | 295 | 300.2 | 302.7 | 2.481 | 10 | 17.2% | 6.157 | 0.008282 | 302.5, 295, 296.9 |
| FeatureGroupManager | ✅ PASS | K | — | PASS | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 0.0% null
  - ✅ **Collector/scientific_validation:** Temperature within valid Kelvin scientific bounds (200–330 K)

  - ✅ **Merger/null_rate:** 0.0% null
  - ✅ **Merger/scientific_validation:** Temperature within valid Kelvin scientific bounds (200–330 K)

  - ✅ **Dataset Builder/null_rate:** 0.0% null
  - ✅ **Dataset Builder/scientific_validation:** Temperature within valid Kelvin scientific bounds (200–330 K)

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null
  - ✅ **merged_feature_table.csv/scientific_validation:** Temperature within valid Kelvin scientific bounds (200–330 K)

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null
  - ✅ **analysis_ready_dataset.csv/scientific_validation:** Temperature within valid Kelvin scientific bounds (200–330 K)

  - ✅ **train_dataset.csv/null_rate:** 0.0% null
  - ✅ **train_dataset.csv/scientific_validation:** Temperature within valid Kelvin scientific bounds (200–330 K)

#### ℹ️ `Relative Humidity` (WARNING (expected))

- **Unit:** %
- **Source:** ERA5
- **In ML model:** Yes
- **Valid range:** (0.0, 100.5)
- **Description:** Relative humidity. Physical range strictly 0–100%. ERA5 may occasionally produce values marginally above 100% due to spectral truncation artefacts in the ECMWF model (values up to ~100.5% are documented in ECMWF validation reports and are not a pipeline bug). valid_range is set to (0.0, 100.5) to prevent false FAIL for these known artefacts; the scientific_validation check (Check 12) distinguishes: values in [100.0, 100.5] → WARN_EXPECTED (ERA5 artefact, documented); values above 100.5 → FAIL (genuine out-of-range). This is the ONLY accepted expansion beyond physical range and is explicitly documented here — do NOT expand further without scientific justification.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ℹ️ WARNING (expected) | % | — | PASS | 374616/374616 | 0.0% | 0.0% | 6.606 | 80.88 | 100 | 19.53 | 362338 | 96.7% | 381.4 | 0.2643 | 33.9, 43.82, 43.67 |
| Merger | ✅ PASS | % | % | PASS | 84/84 | 0.0% | 0.0% | 66.14 | 91.29 | 95.8 | 7.947 | 10 | 11.9% | 63.15 | 0.08858 | 94.94, 95.25, 90.21 |
| Dataset Builder | ✅ PASS | % | — | PASS | 84/84 | 0.0% | 0.0% | 66.14 | 91.29 | 95.8 | 7.947 | 10 | 11.9% | 63.15 | 0.08858 | 84.67, 94.94, 95.25 |
| merged_feature_table.csv | ✅ PASS | % | % | PASS | 84/84 | 0.0% | 0.0% | 66.14 | 91.29 | 95.8 | 7.947 | 10 | 11.9% | 63.15 | 0.08858 | 94.94, 95.25, 90.21 |
| analysis_ready_dataset.csv | ✅ PASS | % | — | PASS | 84/84 | 0.0% | 0.0% | 66.14 | 91.29 | 95.8 | 7.947 | 10 | 11.9% | 63.15 | 0.08858 | 84.67, 94.94, 95.25 |
| train_dataset.csv | ✅ PASS | % | — | PASS | 58/58 | 0.0% | 0.0% | 66.14 | 91.29 | 95.8 | 8.074 | 10 | 17.2% | 65.19 | 0.09009 | 84.67, 89.45, 87.75 |
| FeatureGroupManager | ✅ PASS | % | — | PASS | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 0.0% null
  - ℹ️ **Collector/scientific_validation:** 453 values between 100.0–100.5% (ERA5 spectral truncation artefact; expected, documented, not a bug). observed max=100%

  - ✅ **Merger/null_rate:** 0.0% null
  - ✅ **Merger/scientific_validation:** Relative Humidity within physical bounds (0–100%)

  - ✅ **Dataset Builder/null_rate:** 0.0% null
  - ✅ **Dataset Builder/scientific_validation:** Relative Humidity within physical bounds (0–100%)

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null
  - ✅ **merged_feature_table.csv/scientific_validation:** Relative Humidity within physical bounds (0–100%)

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null
  - ✅ **analysis_ready_dataset.csv/scientific_validation:** Relative Humidity within physical bounds (0–100%)

  - ✅ **train_dataset.csv/null_rate:** 0.0% null
  - ✅ **train_dataset.csv/scientific_validation:** Relative Humidity within physical bounds (0–100%)

#### ✅ `Boundary Layer Height` (PASS)

- **Unit:** m
- **Source:** ERA5
- **In ML model:** Yes
- **Valid range:** (0.0, 6000.0)
- **Description:** Planetary boundary layer height

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | m | — | PASS | 374616/374616 | 0.0% | 0.0% | 9.563 | 683.2 | 4615 | 559.8 | 198914 | 53.1% | 3.134e+05 | 0.783 | 29, 26.75, 17.88 |
| Merger | ✅ PASS | m | m | PASS | 84/84 | 0.0% | 0.0% | 88.84 | 511.3 | 819.6 | 264.1 | 10 | 11.9% | 6.977e+04 | 0.5795 | 145.5, 88.84, 563 |
| Dataset Builder | ✅ PASS | m | — | PASS | 84/84 | 0.0% | 0.0% | 88.84 | 511.3 | 819.6 | 264.1 | 10 | 11.9% | 6.977e+04 | 0.5795 | 558.6, 145.5, 88.84 |
| merged_feature_table.csv | ✅ PASS | m | m | PASS | 84/84 | 0.0% | 0.0% | 88.84 | 511.3 | 819.6 | 264.1 | 10 | 11.9% | 6.977e+04 | 0.5795 | 145.5, 88.84, 563 |
| analysis_ready_dataset.csv | ✅ PASS | m | — | PASS | 84/84 | 0.0% | 0.0% | 88.84 | 511.3 | 819.6 | 264.1 | 10 | 11.9% | 6.977e+04 | 0.5795 | 558.6, 145.5, 88.84 |
| train_dataset.csv | ✅ PASS | m | — | PASS | 58/58 | 0.0% | 0.0% | 88.84 | 511.3 | 819.6 | 263.4 | 10 | 17.2% | 6.937e+04 | 0.5775 | 558.6, 749.1, 819.6 |
| FeatureGroupManager | ✅ PASS | m | — | PASS | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 0.0% null

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

#### ✅ `Wind Speed` (PASS)

- **Unit:** m/s
- **Source:** ERA5 (derived)
- **In ML model:** Yes
- **Valid range:** (0.0, 100.0)
- **Description:** Wind speed derived from U/V components

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | m/s | — | PASS | 374616/374616 | 0.0% | 0.0% | 0.004299 | 3.691 | 13.45 | 3.311 | 372116 | 99.3% | 10.96 | 0.7133 | 1.398, 1.429, 0.987 |
| Merger | ✅ PASS | m/s | m/s | PASS | 84/84 | 0.0% | 0.0% | 0.9595 | 3.689 | 5.875 | 1.633 | 10 | 11.9% | 2.667 | 0.4674 | 1.601, 0.9595, 5.632 |
| Dataset Builder | ✅ PASS | m/s | — | PASS | 84/84 | 0.0% | 0.0% | 0.9595 | 3.689 | 5.875 | 1.633 | 10 | 11.9% | 2.667 | 0.4674 | 3.657, 1.601, 0.9595 |
| merged_feature_table.csv | ✅ PASS | m/s | m/s | PASS | 84/84 | 0.0% | 0.0% | 0.9595 | 3.689 | 5.875 | 1.633 | 10 | 11.9% | 2.667 | 0.4674 | 1.601, 0.9595, 5.632 |
| analysis_ready_dataset.csv | ✅ PASS | m/s | — | PASS | 84/84 | 0.0% | 0.0% | 0.9595 | 3.689 | 5.875 | 1.633 | 10 | 11.9% | 2.667 | 0.4674 | 3.657, 1.601, 0.9595 |
| train_dataset.csv | ✅ PASS | m/s | — | PASS | 58/58 | 0.0% | 0.0% | 0.9595 | 3.689 | 5.875 | 1.637 | 10 | 17.2% | 2.679 | 0.4672 | 3.657, 4.831, 5.875 |
| FeatureGroupManager | ✅ PASS | m/s | — | PASS | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 0.0% null

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

#### ✅ `Wind Direction` (PASS)

- **Unit:** degrees
- **Source:** ERA5 (derived)
- **In ML model:** Yes
- **Valid range:** (0.0, 360.0)
- **Description:** Wind direction (meteorological convention). Range strictly 0–360°.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | degrees | — | PASS | 374616/374616 | 0.0% | 0.0% | 0.001959 | 76.16 | 360 | 105.7 | 371424 | 99.1% | 1.117e+04 | 0.8 | 341.8, 341.6, 305.5 |
| Merger | ✅ PASS | degrees | degrees | PASS | 84/84 | 0.0% | 0.0% | 33.79 | 176.5 | 294.7 | 110.4 | 10 | 11.9% | 1.22e+04 | 0.6404 | 271.4, 283, 45.02 |
| Dataset Builder | ✅ PASS | degrees | — | PASS | 84/84 | 0.0% | 0.0% | 33.79 | 176.5 | 294.7 | 110.4 | 10 | 11.9% | 1.22e+04 | 0.6404 | 274.5, 271.4, 283 |
| merged_feature_table.csv | ✅ PASS | degrees | degrees | PASS | 84/84 | 0.0% | 0.0% | 33.79 | 176.5 | 294.7 | 110.4 | 10 | 11.9% | 1.22e+04 | 0.6404 | 271.4, 283, 45.02 |
| analysis_ready_dataset.csv | ✅ PASS | degrees | — | PASS | 84/84 | 0.0% | 0.0% | 33.79 | 176.5 | 294.7 | 110.4 | 10 | 11.9% | 1.22e+04 | 0.6404 | 274.5, 271.4, 283 |
| train_dataset.csv | ✅ PASS | degrees | — | PASS | 58/58 | 0.0% | 0.0% | 33.79 | 176.5 | 294.7 | 111 | 10 | 17.2% | 1.233e+04 | 0.6435 | 274.5, 69.38, 83.97 |
| FeatureGroupManager | ✅ PASS | degrees | — | PASS | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 0.0% null
  - ✅ **Collector/scientific_validation:** Wind Direction within valid scientific bounds (0–360°)

  - ✅ **Merger/null_rate:** 0.0% null
  - ✅ **Merger/scientific_validation:** Wind Direction within valid scientific bounds (0–360°)

  - ✅ **Dataset Builder/null_rate:** 0.0% null
  - ✅ **Dataset Builder/scientific_validation:** Wind Direction within valid scientific bounds (0–360°)

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null
  - ✅ **merged_feature_table.csv/scientific_validation:** Wind Direction within valid scientific bounds (0–360°)

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null
  - ✅ **analysis_ready_dataset.csv/scientific_validation:** Wind Direction within valid scientific bounds (0–360°)

  - ✅ **train_dataset.csv/null_rate:** 0.0% null
  - ✅ **train_dataset.csv/scientific_validation:** Wind Direction within valid scientific bounds (0–360°)

#### ✅ `Surface Pressure` (PASS)

- **Unit:** Pa
- **Source:** ERA5
- **In ML model:** Yes
- **Valid range:** (45000.0, 110000.0)
- **Description:** Surface atmospheric pressure

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | Pa | — | PASS | 374616/374616 | 0.0% | 0.0% | 4.999e+04 | 9.786e+04 | 1.015e+05 | 1.684e+04 | 198225 | 52.9% | 2.835e+08 | 0.1894 | 9.22e+04, 8.956e+04, 9.109e+04 |
| Merger | ✅ PASS | Pa | Pa | PASS | 84/84 | 0.0% | 0.0% | 9.124e+04 | 9.889e+04 | 1.004e+05 | 3283 | 10 | 11.9% | 1.078e+07 | 0.03368 | 9.747e+04, 9.747e+04, 1.002e+05 |
| Dataset Builder | ✅ PASS | Pa | — | PASS | 84/84 | 0.0% | 0.0% | 9.124e+04 | 9.889e+04 | 1.004e+05 | 3283 | 10 | 11.9% | 1.078e+07 | 0.03368 | 9.926e+04, 9.747e+04, 9.747e+04 |
| merged_feature_table.csv | ✅ PASS | Pa | Pa | PASS | 84/84 | 0.0% | 0.0% | 9.124e+04 | 9.889e+04 | 1.004e+05 | 3283 | 10 | 11.9% | 1.078e+07 | 0.03368 | 9.747e+04, 9.747e+04, 1.002e+05 |
| analysis_ready_dataset.csv | ✅ PASS | Pa | — | PASS | 84/84 | 0.0% | 0.0% | 9.124e+04 | 9.889e+04 | 1.004e+05 | 3283 | 10 | 11.9% | 1.078e+07 | 0.03368 | 9.926e+04, 9.747e+04, 9.747e+04 |
| train_dataset.csv | ✅ PASS | Pa | — | PASS | 58/58 | 0.0% | 0.0% | 9.124e+04 | 9.926e+04 | 1.004e+05 | 3243 | 10 | 17.2% | 1.052e+07 | 0.03323 | 9.926e+04, 9.124e+04, 9.416e+04 |
| FeatureGroupManager | ✅ PASS | Pa | — | PASS | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 0.0% null

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

### Group: `provenance`

#### ✅ `AOD Obs Date` (PASS)

- **Unit:** date (YYYY-MM-DD)
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** N/A
- **Description:** Actual acquisition date of the AOD observation used. Null when the science feature is null (cloud cover / QA masking).

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 14/161 | 91.3% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-05, 2026-07-05, 2026-07-06 |
| Merger | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 0/84 | 100.0% | 0.0% | — | — | — | — | — | — | — | — | — |
| Dataset Builder | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 0/84 | 100.0% | 0.0% | — | — | — | — | — | — | — | — | — |
| merged_feature_table.csv | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 0/84 | 100.0% | 0.0% | — | — | — | — | — | — | — | — | — |
| analysis_ready_dataset.csv | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 0/84 | 100.0% | 0.0% | — | — | — | — | — | — | — | — | — |
| train_dataset.csv | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 0/58 | 100.0% | 0.0% | — | — | — | — | — | — | — | — | — |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 91.3% null (provenance coupling check below)

  - ✅ **Merger/null_rate:** 100.0% null (provenance coupling check below)

  - ✅ **Dataset Builder/null_rate:** 100.0% null (provenance coupling check below)

  - ✅ **merged_feature_table.csv/null_rate:** 100.0% null (provenance coupling check below)

  - ✅ **analysis_ready_dataset.csv/null_rate:** 100.0% null (provenance coupling check below)

  - ✅ **train_dataset.csv/null_rate:** 100.0% null (provenance coupling check below)

#### ✅ `HCHO Obs Date` (PASS)

- **Unit:** date (YYYY-MM-DD)
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** N/A
- **Description:** Actual acquisition date of the HCHO observation used. Null when the science feature is null (cloud cover / QA masking).

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 137/161 | 14.9% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-07, 2026-07-07, 2026-07-01 |
| Merger | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 63/84 | 25.0% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-06, 2026-07-06, 2026-07-05 |
| Dataset Builder | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 63/84 | 25.0% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-06, 2026-07-06, 2026-07-06 |
| merged_feature_table.csv | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 63/84 | 25.0% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-06, 2026-07-06, 2026-07-05 |
| analysis_ready_dataset.csv | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 63/84 | 25.0% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-06, 2026-07-06, 2026-07-06 |
| train_dataset.csv | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 43/58 | 25.9% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-06, 2026-07-05, 2026-07-06 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 14.9% null (provenance coupling check below)

  - ✅ **Merger/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **Dataset Builder/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **merged_feature_table.csv/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **analysis_ready_dataset.csv/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **train_dataset.csv/null_rate:** 25.9% null (provenance coupling check below)

#### ✅ `NO2 Column Obs Date` (PASS)

- **Unit:** date (YYYY-MM-DD)
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** N/A
- **Description:** Actual acquisition date of the NO2 Column observation used. Null when the science feature is null (cloud cover / QA masking).

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 152/161 | 5.6% | 0.0% | — | — | — | — | — | — | — | — | 2026-06-26, 2026-06-30, 2026-06-29 |
| Merger | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | 2026-06-29, 2026-06-29, 2026-06-27 |
| Dataset Builder | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | 2026-06-28, 2026-06-29, 2026-06-29 |
| merged_feature_table.csv | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | 2026-06-29, 2026-06-29, 2026-06-27 |
| analysis_ready_dataset.csv | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | 2026-06-28, 2026-06-29, 2026-06-29 |
| train_dataset.csv | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 58/58 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | 2026-06-28, 2026-06-28, 2026-06-28 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 5.6% null (provenance coupling check below)

  - ✅ **Merger/null_rate:** 0.0% null (provenance coupling check below)

  - ✅ **Dataset Builder/null_rate:** 0.0% null (provenance coupling check below)

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null (provenance coupling check below)

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null (provenance coupling check below)

  - ✅ **train_dataset.csv/null_rate:** 0.0% null (provenance coupling check below)

#### ✅ `SO2 Column Obs Date` (PASS)

- **Unit:** date (YYYY-MM-DD)
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** N/A
- **Description:** Actual acquisition date of the SO2 Column observation used. Null when the science feature is null (cloud cover / QA masking).

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 113/161 | 29.8% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-07, 2026-07-07, 2026-06-30 |
| Merger | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 49/84 | 41.7% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-06, 2026-07-06, 2026-07-03 |
| Dataset Builder | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 49/84 | 41.7% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-04, 2026-07-06, 2026-07-06 |
| merged_feature_table.csv | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 49/84 | 41.7% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-06, 2026-07-06, 2026-07-03 |
| analysis_ready_dataset.csv | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 49/84 | 41.7% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-04, 2026-07-06, 2026-07-06 |
| train_dataset.csv | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 34/58 | 41.4% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-04, 2026-07-08, 2026-07-03 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 29.8% null (provenance coupling check below)

  - ✅ **Merger/null_rate:** 41.7% null (provenance coupling check below)

  - ✅ **Dataset Builder/null_rate:** 41.7% null (provenance coupling check below)

  - ✅ **merged_feature_table.csv/null_rate:** 41.7% null (provenance coupling check below)

  - ✅ **analysis_ready_dataset.csv/null_rate:** 41.7% null (provenance coupling check below)

  - ✅ **train_dataset.csv/null_rate:** 41.4% null (provenance coupling check below)

#### ✅ `CO Column Obs Date` (PASS)

- **Unit:** date (YYYY-MM-DD)
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** N/A
- **Description:** Actual acquisition date of the CO Column observation used. Null when the science feature is null (cloud cover / QA masking).

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 151/161 | 6.2% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-07, 2026-07-07, 2026-07-06 |
| Merger | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 70/84 | 16.7% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-06, 2026-07-06, 2026-07-07 |
| Dataset Builder | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 70/84 | 16.7% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-06, 2026-07-06, 2026-07-06 |
| merged_feature_table.csv | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 70/84 | 16.7% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-06, 2026-07-06, 2026-07-07 |
| analysis_ready_dataset.csv | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 70/84 | 16.7% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-06, 2026-07-06, 2026-07-06 |
| train_dataset.csv | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 48/58 | 17.2% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-06, 2026-07-07, 2026-07-06 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 6.2% null (provenance coupling check below)

  - ✅ **Merger/null_rate:** 16.7% null (provenance coupling check below)

  - ✅ **Dataset Builder/null_rate:** 16.7% null (provenance coupling check below)

  - ✅ **merged_feature_table.csv/null_rate:** 16.7% null (provenance coupling check below)

  - ✅ **analysis_ready_dataset.csv/null_rate:** 16.7% null (provenance coupling check below)

  - ✅ **train_dataset.csv/null_rate:** 17.2% null (provenance coupling check below)

#### ✅ `O3 Column Obs Date` (PASS)

- **Unit:** date (YYYY-MM-DD)
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** N/A
- **Description:** Actual acquisition date of the O3 Column observation used. Null when the science feature is null (cloud cover / QA masking).

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 129/161 | 19.9% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-07, 2026-07-07, 2026-07-01 |
| Merger | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 63/84 | 25.0% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-06, 2026-07-06, 2026-07-05 |
| Dataset Builder | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 63/84 | 25.0% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-04, 2026-07-06, 2026-07-06 |
| merged_feature_table.csv | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 63/84 | 25.0% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-06, 2026-07-06, 2026-07-05 |
| analysis_ready_dataset.csv | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 63/84 | 25.0% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-04, 2026-07-06, 2026-07-06 |
| train_dataset.csv | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 43/58 | 25.9% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-04, 2026-07-05, 2026-07-06 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 19.9% null (provenance coupling check below)

  - ✅ **Merger/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **Dataset Builder/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **merged_feature_table.csv/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **analysis_ready_dataset.csv/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **train_dataset.csv/null_rate:** 25.9% null (provenance coupling check below)

#### ✅ `AOD Temporal Offset` (PASS)

- **Unit:** days
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** (-14.0, 3.0)
- **Description:** Temporal offset of the AOD observation from the effective target date (negative = earlier, positive = later). Expected range: [-14, +3] days, where 14 = MAX_ADAPTIVE_LOOKBACK_DAYS and 3 = TEMPORAL_WINDOW_DAYS. Values outside this range are flagged WARN_INVESTIGATE. Null when the science feature is null.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | days | — | PASS | 14/161 | 91.3% | 0.0% | -6.816 | -1.203 | 1.399 | 2.507 | 10 | 71.4% | 6.286 | 1.346 | -1.819, -1.819, -0.5868 |
| Merger | ✅ PASS | days | — | PASS | 0/84 | 100.0% | 0.0% | — | — | — | 0 | 0 | 0.0% | 0 | 0 | — |
| Dataset Builder | ✅ PASS | days | — | PASS | 0/84 | 100.0% | 0.0% | — | — | — | 0 | 0 | 0.0% | 0 | 0 | — |
| merged_feature_table.csv | ✅ PASS | days | — | PASS | 0/84 | 100.0% | 0.0% | — | — | — | 0 | 0 | 0.0% | 0 | 0 | — |
| analysis_ready_dataset.csv | ✅ PASS | days | — | PASS | 0/84 | 100.0% | 0.0% | — | — | — | 0 | 0 | 0.0% | 0 | 0 | — |
| train_dataset.csv | ✅ PASS | days | — | PASS | 0/58 | 100.0% | 0.0% | — | — | — | 0 | 0 | 0.0% | 0 | 0 | — |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 91.3% null (provenance coupling check below)

  - ✅ **Merger/null_rate:** 100.0% null (provenance coupling check below)

  - ✅ **Dataset Builder/null_rate:** 100.0% null (provenance coupling check below)

  - ✅ **merged_feature_table.csv/null_rate:** 100.0% null (provenance coupling check below)

  - ✅ **analysis_ready_dataset.csv/null_rate:** 100.0% null (provenance coupling check below)

  - ✅ **train_dataset.csv/null_rate:** 100.0% null (provenance coupling check below)

#### ✅ `HCHO Temporal Offset` (PASS)

- **Unit:** days
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** (-14.0, 3.0)
- **Description:** Temporal offset of the HCHO observation from the effective target date (negative = earlier, positive = later). Expected range: [-14, +3] days, where 14 = MAX_ADAPTIVE_LOOKBACK_DAYS and 3 = TEMPORAL_WINDOW_DAYS. Values outside this range are flagged WARN_INVESTIGATE. Null when the science feature is null.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | days | — | PASS | 137/161 | 14.9% | 0.0% | -6.703 | -0.7114 | 1.333 | 1.747 | 14 | 10.2% | 3.052 | 1.513 | 0.2754, 0.2754, -5.645 |
| Merger | ✅ PASS | days | — | PASS | 63/84 | 25.0% | 0.0% | -3.672 | -1.698 | -0.7114 | 1.308 | 3 | 4.8% | 1.71 | 0.682 | -0.7114, -0.7114, -1.698 |
| Dataset Builder | ✅ PASS | days | — | PASS | 63/84 | 25.0% | 0.0% | -3.672 | -1.698 | -0.7114 | 1.308 | 3 | 4.8% | 1.71 | 0.682 | -0.7114, -0.7114, -0.7114 |
| merged_feature_table.csv | ✅ PASS | days | — | PASS | 63/84 | 25.0% | 0.0% | -3.672 | -1.698 | -0.7114 | 1.308 | 3 | 4.8% | 1.71 | 0.682 | -0.7114, -0.7114, -1.698 |
| analysis_ready_dataset.csv | ✅ PASS | days | — | PASS | 63/84 | 25.0% | 0.0% | -3.672 | -1.698 | -0.7114 | 1.308 | 3 | 4.8% | 1.71 | 0.682 | -0.7114, -0.7114, -0.7114 |
| train_dataset.csv | ✅ PASS | days | — | PASS | 43/58 | 25.9% | 0.0% | -3.672 | -1.698 | -0.7114 | 1.329 | 3 | 7.0% | 1.766 | 0.6813 | -0.7114, -1.698, -0.7114 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 14.9% null (provenance coupling check below)

  - ✅ **Merger/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **Dataset Builder/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **merged_feature_table.csv/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **analysis_ready_dataset.csv/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **train_dataset.csv/null_rate:** 25.9% null (provenance coupling check below)

#### ✅ `NO2 Column Temporal Offset` (PASS)

- **Unit:** days
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** (-14.0, 3.0)
- **Description:** Temporal offset of the NO2 Column observation from the effective target date (negative = earlier, positive = later). Expected range: [-14, +3] days, where 14 = MAX_ADAPTIVE_LOOKBACK_DAYS and 3 = TEMPORAL_WINDOW_DAYS. Values outside this range are flagged WARN_INVESTIGATE. Null when the science feature is null.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | days | — | PASS | 152/161 | 5.6% | 0.0% | -6.707 | -2.689 | 0.3415 | 2 | 14 | 9.2% | 3.998 | 0.8275 | -5.65, -1.703, -2.689 |
| Merger | ✅ PASS | days | — | PASS | 84/84 | 0.0% | 0.0% | -4.663 | -2.689 | 0.271 | 1.541 | 4 | 4.8% | 2.375 | 0.556 | -2.689, -2.689, -4.663 |
| Dataset Builder | ✅ PASS | days | — | PASS | 84/84 | 0.0% | 0.0% | -4.663 | -2.689 | 0.271 | 1.541 | 4 | 4.8% | 2.375 | 0.556 | -3.676, -2.689, -2.689 |
| merged_feature_table.csv | ✅ PASS | days | — | PASS | 84/84 | 0.0% | 0.0% | -4.663 | -2.689 | 0.271 | 1.541 | 4 | 4.8% | 2.375 | 0.556 | -2.689, -2.689, -4.663 |
| analysis_ready_dataset.csv | ✅ PASS | days | — | PASS | 84/84 | 0.0% | 0.0% | -4.663 | -2.689 | 0.271 | 1.541 | 4 | 4.8% | 2.375 | 0.556 | -3.676, -2.689, -2.689 |
| train_dataset.csv | ✅ PASS | days | — | PASS | 58/58 | 0.0% | 0.0% | -4.663 | -2.689 | 0.271 | 1.567 | 4 | 6.9% | 2.455 | 0.5683 | -3.676, -3.676, -3.676 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 5.6% null (provenance coupling check below)

  - ✅ **Merger/null_rate:** 0.0% null (provenance coupling check below)

  - ✅ **Dataset Builder/null_rate:** 0.0% null (provenance coupling check below)

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null (provenance coupling check below)

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null (provenance coupling check below)

  - ✅ **train_dataset.csv/null_rate:** 0.0% null (provenance coupling check below)

#### ✅ `SO2 Column Temporal Offset` (PASS)

- **Unit:** days
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** (-14.0, 3.0)
- **Description:** Temporal offset of the SO2 Column observation from the effective target date (negative = earlier, positive = later). Expected range: [-14, +3] days, where 14 = MAX_ADAPTIVE_LOOKBACK_DAYS and 3 = TEMPORAL_WINDOW_DAYS. Values outside this range are flagged WARN_INVESTIGATE. Null when the science feature is null.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | days | — | PASS | 113/161 | 29.8% | 0.0% | -6.703 | -0.7114 | 1.333 | 1.849 | 15 | 13.3% | 3.419 | 1.446 | 0.2754, 0.2754, -6.703 |
| Merger | ✅ PASS | days | — | PASS | 49/84 | 41.7% | 0.0% | -3.672 | -1.698 | 1.333 | 1.703 | 5 | 10.2% | 2.902 | 1.009 | -0.7114, -0.7114, -3.672 |
| Dataset Builder | ✅ PASS | days | — | PASS | 49/84 | 41.7% | 0.0% | -3.672 | -1.698 | 1.333 | 1.703 | 5 | 10.2% | 2.902 | 1.009 | -2.685, -0.7114, -0.7114 |
| merged_feature_table.csv | ✅ PASS | days | — | PASS | 49/84 | 41.7% | 0.0% | -3.672 | -1.698 | 1.333 | 1.703 | 5 | 10.2% | 2.902 | 1.009 | -0.7114, -0.7114, -3.672 |
| analysis_ready_dataset.csv | ✅ PASS | days | — | PASS | 49/84 | 41.7% | 0.0% | -3.672 | -1.698 | 1.333 | 1.703 | 5 | 10.2% | 2.902 | 1.009 | -2.685, -0.7114, -0.7114 |
| train_dataset.csv | ✅ PASS | days | — | PASS | 34/58 | 41.4% | 0.0% | -3.672 | -1.698 | 1.333 | 1.728 | 5 | 14.7% | 2.985 | 1.006 | -2.685, 1.333, -3.672 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 29.8% null (provenance coupling check below)

  - ✅ **Merger/null_rate:** 41.7% null (provenance coupling check below)

  - ✅ **Dataset Builder/null_rate:** 41.7% null (provenance coupling check below)

  - ✅ **merged_feature_table.csv/null_rate:** 41.7% null (provenance coupling check below)

  - ✅ **analysis_ready_dataset.csv/null_rate:** 41.7% null (provenance coupling check below)

  - ✅ **train_dataset.csv/null_rate:** 41.4% null (provenance coupling check below)

#### ✅ `CO Column Temporal Offset` (PASS)

- **Unit:** days
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** (-14.0, 3.0)
- **Description:** Temporal offset of the CO Column observation from the effective target date (negative = earlier, positive = later). Expected range: [-14, +3] days, where 14 = MAX_ADAPTIVE_LOOKBACK_DAYS and 3 = TEMPORAL_WINDOW_DAYS. Values outside this range are flagged WARN_INVESTIGATE. Null when the science feature is null.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | days | — | PASS | 151/161 | 6.2% | 0.0% | -6.703 | -0.7114 | 1.333 | 1.502 | 12 | 7.9% | 2.257 | 2.14 | 0.3459, 0.3459, -0.7114 |
| Merger | ✅ PASS | days | — | PASS | 70/84 | 16.7% | 0.0% | -3.672 | -0.6761 | 1.333 | 1.317 | 6 | 8.6% | 1.734 | 2.28 | -0.7114, -0.7114, 0.3459 |
| Dataset Builder | ✅ PASS | days | — | PASS | 70/84 | 16.7% | 0.0% | -3.672 | -0.6761 | 1.333 | 1.317 | 6 | 8.6% | 1.734 | 2.28 | -0.7114, -0.7114, -0.7114 |
| merged_feature_table.csv | ✅ PASS | days | — | PASS | 70/84 | 16.7% | 0.0% | -3.672 | -0.6761 | 1.333 | 1.317 | 6 | 8.6% | 1.734 | 2.28 | -0.7114, -0.7114, 0.3459 |
| analysis_ready_dataset.csv | ✅ PASS | days | — | PASS | 70/84 | 16.7% | 0.0% | -3.672 | -0.6761 | 1.333 | 1.317 | 6 | 8.6% | 1.734 | 2.28 | -0.7114, -0.7114, -0.7114 |
| train_dataset.csv | ✅ PASS | days | — | PASS | 48/58 | 17.2% | 0.0% | -3.672 | -0.6761 | 1.333 | 1.342 | 6 | 12.5% | 1.8 | 2.259 | -0.7114, 0.3459, -0.6409 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 6.2% null (provenance coupling check below)

  - ✅ **Merger/null_rate:** 16.7% null (provenance coupling check below)

  - ✅ **Dataset Builder/null_rate:** 16.7% null (provenance coupling check below)

  - ✅ **merged_feature_table.csv/null_rate:** 16.7% null (provenance coupling check below)

  - ✅ **analysis_ready_dataset.csv/null_rate:** 16.7% null (provenance coupling check below)

  - ✅ **train_dataset.csv/null_rate:** 17.2% null (provenance coupling check below)

#### ✅ `O3 Column Temporal Offset` (PASS)

- **Unit:** days
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** (-14.0, 3.0)
- **Description:** Temporal offset of the O3 Column observation from the effective target date (negative = earlier, positive = later). Expected range: [-14, +3] days, where 14 = MAX_ADAPTIVE_LOOKBACK_DAYS and 3 = TEMPORAL_WINDOW_DAYS. Values outside this range are flagged WARN_INVESTIGATE. Null when the science feature is null.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | days | — | PASS | 129/161 | 19.9% | 0.0% | -6.703 | -0.7114 | 1.333 | 1.798 | 12 | 9.3% | 3.234 | 1.536 | 0.2754, 0.2754, -5.645 |
| Merger | ✅ PASS | days | — | PASS | 63/84 | 25.0% | 0.0% | -3.672 | -1.698 | -0.7114 | 1.25 | 4 | 6.3% | 1.564 | 0.5852 | -0.7114, -0.7114, -1.698 |
| Dataset Builder | ✅ PASS | days | — | PASS | 63/84 | 25.0% | 0.0% | -3.672 | -1.698 | -0.7114 | 1.25 | 4 | 6.3% | 1.564 | 0.5852 | -2.685, -0.7114, -0.7114 |
| merged_feature_table.csv | ✅ PASS | days | — | PASS | 63/84 | 25.0% | 0.0% | -3.672 | -1.698 | -0.7114 | 1.25 | 4 | 6.3% | 1.564 | 0.5852 | -0.7114, -0.7114, -1.698 |
| analysis_ready_dataset.csv | ✅ PASS | days | — | PASS | 63/84 | 25.0% | 0.0% | -3.672 | -1.698 | -0.7114 | 1.25 | 4 | 6.3% | 1.564 | 0.5852 | -2.685, -0.7114, -0.7114 |
| train_dataset.csv | ✅ PASS | days | — | PASS | 43/58 | 25.9% | 0.0% | -3.672 | -1.698 | -0.7114 | 1.262 | 4 | 9.3% | 1.594 | 0.5791 | -2.685, -1.698, -0.7114 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 19.9% null (provenance coupling check below)

  - ✅ **Merger/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **Dataset Builder/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **merged_feature_table.csv/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **analysis_ready_dataset.csv/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **train_dataset.csv/null_rate:** 25.9% null (provenance coupling check below)

#### ✅ `AOD Publication Lag` (PASS)

- **Unit:** days
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** (0.0, 30.0)
- **Description:** Publication lag of the AOD collection relative to the requested date (0 = available on time, N = N days behind). Must be non-negative. Null when the science feature is null.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | days | — | PASS | 14/161 | 91.3% | 0.0% | 0 | 0 | 0 | 0 | 1 | 7.1% | 0 | 0 | 0, 0, 0 |
| Merger | ✅ PASS | days | — | PASS | 0/84 | 100.0% | 0.0% | — | — | — | 0 | 0 | 0.0% | 0 | 0 | — |
| Dataset Builder | ✅ PASS | days | — | PASS | 0/84 | 100.0% | 0.0% | — | — | — | 0 | 0 | 0.0% | 0 | 0 | — |
| merged_feature_table.csv | ✅ PASS | days | — | PASS | 0/84 | 100.0% | 0.0% | — | — | — | 0 | 0 | 0.0% | 0 | 0 | — |
| analysis_ready_dataset.csv | ✅ PASS | days | — | PASS | 0/84 | 100.0% | 0.0% | — | — | — | 0 | 0 | 0.0% | 0 | 0 | — |
| train_dataset.csv | ✅ PASS | days | — | PASS | 0/58 | 100.0% | 0.0% | — | — | — | 0 | 0 | 0.0% | 0 | 0 | — |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 91.3% null (provenance coupling check below)
  - ✅ **Collector/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **Collector/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

  - ✅ **Merger/null_rate:** 100.0% null (provenance coupling check below)

  - ✅ **Dataset Builder/null_rate:** 100.0% null (provenance coupling check below)

  - ✅ **merged_feature_table.csv/null_rate:** 100.0% null (provenance coupling check below)

  - ✅ **analysis_ready_dataset.csv/null_rate:** 100.0% null (provenance coupling check below)

  - ✅ **train_dataset.csv/null_rate:** 100.0% null (provenance coupling check below)

#### ✅ `HCHO Publication Lag` (PASS)

- **Unit:** days
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** (0.0, 30.0)
- **Description:** Publication lag of the HCHO collection relative to the requested date (0 = available on time, N = N days behind). Must be non-negative. Null when the science feature is null.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | days | — | PASS | 137/161 | 14.9% | 0.0% | 0 | 0 | 0 | 0 | 1 | 0.7% | 0 | 0 | 0, 0, 0 |
| Merger | ✅ PASS | days | — | PASS | 63/84 | 25.0% | 0.0% | 0 | 0 | 0 | 0 | 1 | 1.6% | 0 | 0 | 0, 0, 0 |
| Dataset Builder | ✅ PASS | days | — | PASS | 63/84 | 25.0% | 0.0% | 0 | 0 | 0 | 0 | 1 | 1.6% | 0 | 0 | 0, 0, 0 |
| merged_feature_table.csv | ✅ PASS | days | — | PASS | 63/84 | 25.0% | 0.0% | 0 | 0 | 0 | 0 | 1 | 1.6% | 0 | 0 | 0, 0, 0 |
| analysis_ready_dataset.csv | ✅ PASS | days | — | PASS | 63/84 | 25.0% | 0.0% | 0 | 0 | 0 | 0 | 1 | 1.6% | 0 | 0 | 0, 0, 0 |
| train_dataset.csv | ✅ PASS | days | — | PASS | 43/58 | 25.9% | 0.0% | 0 | 0 | 0 | 0 | 1 | 2.3% | 0 | 0 | 0, 0, 0 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 14.9% null (provenance coupling check below)
  - ✅ **Collector/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **Collector/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

  - ✅ **Merger/null_rate:** 25.0% null (provenance coupling check below)
  - ✅ **Merger/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **Merger/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

  - ✅ **Dataset Builder/null_rate:** 25.0% null (provenance coupling check below)
  - ✅ **Dataset Builder/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **Dataset Builder/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

  - ✅ **merged_feature_table.csv/null_rate:** 25.0% null (provenance coupling check below)
  - ✅ **merged_feature_table.csv/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **merged_feature_table.csv/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

  - ✅ **analysis_ready_dataset.csv/null_rate:** 25.0% null (provenance coupling check below)
  - ✅ **analysis_ready_dataset.csv/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **analysis_ready_dataset.csv/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

  - ✅ **train_dataset.csv/null_rate:** 25.9% null (provenance coupling check below)
  - ✅ **train_dataset.csv/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **train_dataset.csv/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

#### ✅ `NO2 Column Publication Lag` (PASS)

- **Unit:** days
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** (0.0, 30.0)
- **Description:** Publication lag of the NO2 Column collection relative to the requested date (0 = available on time, N = N days behind). Must be non-negative. Null when the science feature is null.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | days | — | PASS | 152/161 | 5.6% | 0.0% | 5 | 5 | 5 | 0 | 1 | 0.7% | 0 | 0 | 5, 5, 5 |
| Merger | ✅ PASS | days | — | PASS | 84/84 | 0.0% | 0.0% | 5 | 5 | 5 | 0 | 1 | 1.2% | 0 | 0 | 5, 5, 5 |
| Dataset Builder | ✅ PASS | days | — | PASS | 84/84 | 0.0% | 0.0% | 5 | 5 | 5 | 0 | 1 | 1.2% | 0 | 0 | 5, 5, 5 |
| merged_feature_table.csv | ✅ PASS | days | — | PASS | 84/84 | 0.0% | 0.0% | 5 | 5 | 5 | 0 | 1 | 1.2% | 0 | 0 | 5, 5, 5 |
| analysis_ready_dataset.csv | ✅ PASS | days | — | PASS | 84/84 | 0.0% | 0.0% | 5 | 5 | 5 | 0 | 1 | 1.2% | 0 | 0 | 5, 5, 5 |
| train_dataset.csv | ✅ PASS | days | — | PASS | 58/58 | 0.0% | 0.0% | 5 | 5 | 5 | 0 | 1 | 1.7% | 0 | 0 | 5, 5, 5 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 5.6% null (provenance coupling check below)
  - ✅ **Collector/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **Collector/low_variance_check:** Info: Publication Lag is constant in this dataset (value=5.0).

  - ✅ **Merger/null_rate:** 0.0% null (provenance coupling check below)
  - ✅ **Merger/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **Merger/low_variance_check:** Info: Publication Lag is constant in this dataset (value=5.0).

  - ✅ **Dataset Builder/null_rate:** 0.0% null (provenance coupling check below)
  - ✅ **Dataset Builder/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **Dataset Builder/low_variance_check:** Info: Publication Lag is constant in this dataset (value=5.0).

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null (provenance coupling check below)
  - ✅ **merged_feature_table.csv/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **merged_feature_table.csv/low_variance_check:** Info: Publication Lag is constant in this dataset (value=5.0).

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null (provenance coupling check below)
  - ✅ **analysis_ready_dataset.csv/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **analysis_ready_dataset.csv/low_variance_check:** Info: Publication Lag is constant in this dataset (value=5.0).

  - ✅ **train_dataset.csv/null_rate:** 0.0% null (provenance coupling check below)
  - ✅ **train_dataset.csv/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **train_dataset.csv/low_variance_check:** Info: Publication Lag is constant in this dataset (value=5.0).

#### ✅ `SO2 Column Publication Lag` (PASS)

- **Unit:** days
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** (0.0, 30.0)
- **Description:** Publication lag of the SO2 Column collection relative to the requested date (0 = available on time, N = N days behind). Must be non-negative. Null when the science feature is null.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | days | — | PASS | 113/161 | 29.8% | 0.0% | 0 | 0 | 0 | 0 | 1 | 0.9% | 0 | 0 | 0, 0, 0 |
| Merger | ✅ PASS | days | — | PASS | 49/84 | 41.7% | 0.0% | 0 | 0 | 0 | 0 | 1 | 2.0% | 0 | 0 | 0, 0, 0 |
| Dataset Builder | ✅ PASS | days | — | PASS | 49/84 | 41.7% | 0.0% | 0 | 0 | 0 | 0 | 1 | 2.0% | 0 | 0 | 0, 0, 0 |
| merged_feature_table.csv | ✅ PASS | days | — | PASS | 49/84 | 41.7% | 0.0% | 0 | 0 | 0 | 0 | 1 | 2.0% | 0 | 0 | 0, 0, 0 |
| analysis_ready_dataset.csv | ✅ PASS | days | — | PASS | 49/84 | 41.7% | 0.0% | 0 | 0 | 0 | 0 | 1 | 2.0% | 0 | 0 | 0, 0, 0 |
| train_dataset.csv | ✅ PASS | days | — | PASS | 34/58 | 41.4% | 0.0% | 0 | 0 | 0 | 0 | 1 | 2.9% | 0 | 0 | 0, 0, 0 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 29.8% null (provenance coupling check below)
  - ✅ **Collector/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **Collector/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

  - ✅ **Merger/null_rate:** 41.7% null (provenance coupling check below)
  - ✅ **Merger/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **Merger/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

  - ✅ **Dataset Builder/null_rate:** 41.7% null (provenance coupling check below)
  - ✅ **Dataset Builder/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **Dataset Builder/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

  - ✅ **merged_feature_table.csv/null_rate:** 41.7% null (provenance coupling check below)
  - ✅ **merged_feature_table.csv/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **merged_feature_table.csv/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

  - ✅ **analysis_ready_dataset.csv/null_rate:** 41.7% null (provenance coupling check below)
  - ✅ **analysis_ready_dataset.csv/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **analysis_ready_dataset.csv/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

  - ✅ **train_dataset.csv/null_rate:** 41.4% null (provenance coupling check below)
  - ✅ **train_dataset.csv/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **train_dataset.csv/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

#### ✅ `CO Column Publication Lag` (PASS)

- **Unit:** days
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** (0.0, 30.0)
- **Description:** Publication lag of the CO Column collection relative to the requested date (0 = available on time, N = N days behind). Must be non-negative. Null when the science feature is null.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | days | — | PASS | 151/161 | 6.2% | 0.0% | 0 | 0 | 0 | 0 | 1 | 0.7% | 0 | 0 | 0, 0, 0 |
| Merger | ✅ PASS | days | — | PASS | 70/84 | 16.7% | 0.0% | 0 | 0 | 0 | 0 | 1 | 1.4% | 0 | 0 | 0, 0, 0 |
| Dataset Builder | ✅ PASS | days | — | PASS | 70/84 | 16.7% | 0.0% | 0 | 0 | 0 | 0 | 1 | 1.4% | 0 | 0 | 0, 0, 0 |
| merged_feature_table.csv | ✅ PASS | days | — | PASS | 70/84 | 16.7% | 0.0% | 0 | 0 | 0 | 0 | 1 | 1.4% | 0 | 0 | 0, 0, 0 |
| analysis_ready_dataset.csv | ✅ PASS | days | — | PASS | 70/84 | 16.7% | 0.0% | 0 | 0 | 0 | 0 | 1 | 1.4% | 0 | 0 | 0, 0, 0 |
| train_dataset.csv | ✅ PASS | days | — | PASS | 48/58 | 17.2% | 0.0% | 0 | 0 | 0 | 0 | 1 | 2.1% | 0 | 0 | 0, 0, 0 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 6.2% null (provenance coupling check below)
  - ✅ **Collector/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **Collector/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

  - ✅ **Merger/null_rate:** 16.7% null (provenance coupling check below)
  - ✅ **Merger/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **Merger/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

  - ✅ **Dataset Builder/null_rate:** 16.7% null (provenance coupling check below)
  - ✅ **Dataset Builder/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **Dataset Builder/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

  - ✅ **merged_feature_table.csv/null_rate:** 16.7% null (provenance coupling check below)
  - ✅ **merged_feature_table.csv/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **merged_feature_table.csv/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

  - ✅ **analysis_ready_dataset.csv/null_rate:** 16.7% null (provenance coupling check below)
  - ✅ **analysis_ready_dataset.csv/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **analysis_ready_dataset.csv/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

  - ✅ **train_dataset.csv/null_rate:** 17.2% null (provenance coupling check below)
  - ✅ **train_dataset.csv/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **train_dataset.csv/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

#### ✅ `O3 Column Publication Lag` (PASS)

- **Unit:** days
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** (0.0, 30.0)
- **Description:** Publication lag of the O3 Column collection relative to the requested date (0 = available on time, N = N days behind). Must be non-negative. Null when the science feature is null.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | days | — | PASS | 129/161 | 19.9% | 0.0% | 0 | 0 | 0 | 0 | 1 | 0.8% | 0 | 0 | 0, 0, 0 |
| Merger | ✅ PASS | days | — | PASS | 63/84 | 25.0% | 0.0% | 0 | 0 | 0 | 0 | 1 | 1.6% | 0 | 0 | 0, 0, 0 |
| Dataset Builder | ✅ PASS | days | — | PASS | 63/84 | 25.0% | 0.0% | 0 | 0 | 0 | 0 | 1 | 1.6% | 0 | 0 | 0, 0, 0 |
| merged_feature_table.csv | ✅ PASS | days | — | PASS | 63/84 | 25.0% | 0.0% | 0 | 0 | 0 | 0 | 1 | 1.6% | 0 | 0 | 0, 0, 0 |
| analysis_ready_dataset.csv | ✅ PASS | days | — | PASS | 63/84 | 25.0% | 0.0% | 0 | 0 | 0 | 0 | 1 | 1.6% | 0 | 0 | 0, 0, 0 |
| train_dataset.csv | ✅ PASS | days | — | PASS | 43/58 | 25.9% | 0.0% | 0 | 0 | 0 | 0 | 1 | 2.3% | 0 | 0 | 0, 0, 0 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 19.9% null (provenance coupling check below)
  - ✅ **Collector/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **Collector/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

  - ✅ **Merger/null_rate:** 25.0% null (provenance coupling check below)
  - ✅ **Merger/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **Merger/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

  - ✅ **Dataset Builder/null_rate:** 25.0% null (provenance coupling check below)
  - ✅ **Dataset Builder/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **Dataset Builder/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

  - ✅ **merged_feature_table.csv/null_rate:** 25.0% null (provenance coupling check below)
  - ✅ **merged_feature_table.csv/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **merged_feature_table.csv/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

  - ✅ **analysis_ready_dataset.csv/null_rate:** 25.0% null (provenance coupling check below)
  - ✅ **analysis_ready_dataset.csv/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **analysis_ready_dataset.csv/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

  - ✅ **train_dataset.csv/null_rate:** 25.9% null (provenance coupling check below)
  - ✅ **train_dataset.csv/scientific_validation:** Publication Lag within valid scientific bounds (>=0)
  - ✅ **train_dataset.csv/low_variance_check:** Info: Publication Lag is constant in this dataset (value=0.0).

#### ✅ `AOD QA Status` (PASS)

- **Unit:** qa_value
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** (-1.0, 32767.0)
- **Description:** QA value for AOD. Sentinel-5P cloud fraction: 0–1 (threshold <0.5). MODIS MAIAC AOD: AOD_QA bitmask integer (non-negative). CO Column has no native QA band; sentinel value -1 is used. Null when the science feature is null.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | qa_value | — | PASS | 14/161 | 91.3% | 0.0% | 1 | 1 | 8193 | 3488 | 2 | 14.3% | 1.217e+07 | 1.986 | 1, 1, 8193 |
| Merger | ✅ PASS | qa_value | — | PASS | 0/84 | 100.0% | 0.0% | — | — | — | 0 | 0 | 0.0% | 0 | 0 | — |
| Dataset Builder | ✅ PASS | qa_value | — | PASS | 0/84 | 100.0% | 0.0% | — | — | — | 0 | 0 | 0.0% | 0 | 0 | — |
| merged_feature_table.csv | ✅ PASS | qa_value | — | PASS | 0/84 | 100.0% | 0.0% | — | — | — | 0 | 0 | 0.0% | 0 | 0 | — |
| analysis_ready_dataset.csv | ✅ PASS | qa_value | — | PASS | 0/84 | 100.0% | 0.0% | — | — | — | 0 | 0 | 0.0% | 0 | 0 | — |
| train_dataset.csv | ✅ PASS | qa_value | — | PASS | 0/58 | 100.0% | 0.0% | — | — | — | 0 | 0 | 0.0% | 0 | 0 | — |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 91.3% null (provenance coupling check below)

  - ✅ **Merger/null_rate:** 100.0% null (provenance coupling check below)

  - ✅ **Dataset Builder/null_rate:** 100.0% null (provenance coupling check below)

  - ✅ **merged_feature_table.csv/null_rate:** 100.0% null (provenance coupling check below)

  - ✅ **analysis_ready_dataset.csv/null_rate:** 100.0% null (provenance coupling check below)

  - ✅ **train_dataset.csv/null_rate:** 100.0% null (provenance coupling check below)

#### ✅ `HCHO QA Status` (PASS)

- **Unit:** qa_value
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** (-1.0, 32767.0)
- **Description:** QA value for HCHO. Sentinel-5P cloud fraction: 0–1 (threshold <0.5). MODIS MAIAC AOD: AOD_QA bitmask integer (non-negative). CO Column has no native QA band; sentinel value -1 is used. Null when the science feature is null.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | qa_value | — | PASS | 137/161 | 14.9% | 0.0% | 0 | 0.3113 | 0.4978 | 0.1452 | 129 | 94.2% | 0.02108 | 0.4855 | 0.3032, 0.2577, 0.4978 |
| Merger | ✅ PASS | qa_value | — | PASS | 63/84 | 25.0% | 0.0% | 0.1441 | 0.3732 | 0.4796 | 0.1163 | 9 | 14.3% | 0.01353 | 0.3308 | 0.1591, 0.1441, 0.4796 |
| Dataset Builder | ✅ PASS | qa_value | — | PASS | 63/84 | 25.0% | 0.0% | 0.1441 | 0.3732 | 0.4796 | 0.1163 | 9 | 14.3% | 0.01353 | 0.3308 | 0.4505, 0.1591, 0.1441 |
| merged_feature_table.csv | ✅ PASS | qa_value | — | PASS | 63/84 | 25.0% | 0.0% | 0.1441 | 0.3732 | 0.4796 | 0.1163 | 9 | 14.3% | 0.01353 | 0.3308 | 0.1591, 0.1441, 0.4796 |
| analysis_ready_dataset.csv | ✅ PASS | qa_value | — | PASS | 63/84 | 25.0% | 0.0% | 0.1441 | 0.3732 | 0.4796 | 0.1163 | 9 | 14.3% | 0.01353 | 0.3308 | 0.4505, 0.1591, 0.1441 |
| train_dataset.csv | ✅ PASS | qa_value | — | PASS | 43/58 | 25.9% | 0.0% | 0.1441 | 0.3732 | 0.4796 | 0.1146 | 9 | 20.9% | 0.01313 | 0.324 | 0.4505, 0.4529, 0.4034 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 14.9% null (provenance coupling check below)

  - ✅ **Merger/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **Dataset Builder/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **merged_feature_table.csv/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **analysis_ready_dataset.csv/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **train_dataset.csv/null_rate:** 25.9% null (provenance coupling check below)

#### ✅ `NO2 Column QA Status` (PASS)

- **Unit:** qa_value
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** (-1.0, 32767.0)
- **Description:** QA value for NO2 Column. Sentinel-5P cloud fraction: 0–1 (threshold <0.5). MODIS MAIAC AOD: AOD_QA bitmask integer (non-negative). CO Column has no native QA band; sentinel value -1 is used. Null when the science feature is null.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | qa_value | — | PASS | 152/161 | 5.6% | 0.0% | 1.247e-07 | 0.2586 | 0.4987 | 0.1352 | 148 | 97.4% | 0.01829 | 0.525 | 0.3832, 0.263, 0.2239 |
| Merger | ✅ PASS | qa_value | — | PASS | 84/84 | 0.0% | 0.0% | 0.1502 | 0.2822 | 0.4923 | 0.1192 | 11 | 13.1% | 0.01422 | 0.3974 | 0.2983, 0.2661, 0.4923 |
| Dataset Builder | ✅ PASS | qa_value | — | PASS | 84/84 | 0.0% | 0.0% | 0.1502 | 0.2822 | 0.4923 | 0.1192 | 11 | 13.1% | 0.01422 | 0.3974 | 0.1932, 0.2983, 0.2661 |
| merged_feature_table.csv | ✅ PASS | qa_value | — | PASS | 84/84 | 0.0% | 0.0% | 0.1502 | 0.2822 | 0.4923 | 0.1192 | 11 | 13.1% | 0.01422 | 0.3974 | 0.2983, 0.2661, 0.4923 |
| analysis_ready_dataset.csv | ✅ PASS | qa_value | — | PASS | 84/84 | 0.0% | 0.0% | 0.1502 | 0.2822 | 0.4923 | 0.1192 | 11 | 13.1% | 0.01422 | 0.3974 | 0.1932, 0.2983, 0.2661 |
| train_dataset.csv | ✅ PASS | qa_value | — | PASS | 58/58 | 0.0% | 0.0% | 0.1502 | 0.2822 | 0.4923 | 0.1211 | 11 | 19.0% | 0.01466 | 0.4014 | 0.1932, 0.213, 0.3915 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 5.6% null (provenance coupling check below)

  - ✅ **Merger/null_rate:** 0.0% null (provenance coupling check below)

  - ✅ **Dataset Builder/null_rate:** 0.0% null (provenance coupling check below)

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null (provenance coupling check below)

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null (provenance coupling check below)

  - ✅ **train_dataset.csv/null_rate:** 0.0% null (provenance coupling check below)

#### ✅ `SO2 Column QA Status` (PASS)

- **Unit:** qa_value
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** (-1.0, 32767.0)
- **Description:** QA value for SO2 Column. Sentinel-5P cloud fraction: 0–1 (threshold <0.5). MODIS MAIAC AOD: AOD_QA bitmask integer (non-negative). CO Column has no native QA band; sentinel value -1 is used. Null when the science feature is null.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | qa_value | — | PASS | 113/161 | 29.8% | 0.0% | 0 | 0.1908 | 0.2958 | 0.08475 | 103 | 91.2% | 0.007183 | 0.4739 | 0.2474, 0.254, 0.2424 |
| Merger | ✅ PASS | qa_value | — | PASS | 49/84 | 41.7% | 0.0% | 0.1441 | 0.2085 | 0.2886 | 0.05034 | 7 | 14.3% | 0.002534 | 0.2331 | 0.1591, 0.1441, 0.2886 |
| Dataset Builder | ✅ PASS | qa_value | — | PASS | 49/84 | 41.7% | 0.0% | 0.1441 | 0.2085 | 0.2886 | 0.05034 | 7 | 14.3% | 0.002534 | 0.2331 | 0.2085, 0.1591, 0.1441 |
| merged_feature_table.csv | ✅ PASS | qa_value | — | PASS | 49/84 | 41.7% | 0.0% | 0.1441 | 0.2085 | 0.2886 | 0.05034 | 7 | 14.3% | 0.002534 | 0.2331 | 0.1591, 0.1441, 0.2886 |
| analysis_ready_dataset.csv | ✅ PASS | qa_value | — | PASS | 49/84 | 41.7% | 0.0% | 0.1441 | 0.2085 | 0.2886 | 0.05034 | 7 | 14.3% | 0.002534 | 0.2331 | 0.2085, 0.1591, 0.1441 |
| train_dataset.csv | ✅ PASS | qa_value | — | PASS | 34/58 | 41.4% | 0.0% | 0.1441 | 0.2085 | 0.2886 | 0.05031 | 7 | 20.6% | 0.002532 | 0.2312 | 0.2085, 0.2064, 0.2886 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 29.8% null (provenance coupling check below)

  - ✅ **Merger/null_rate:** 41.7% null (provenance coupling check below)

  - ✅ **Dataset Builder/null_rate:** 41.7% null (provenance coupling check below)

  - ✅ **merged_feature_table.csv/null_rate:** 41.7% null (provenance coupling check below)

  - ✅ **analysis_ready_dataset.csv/null_rate:** 41.7% null (provenance coupling check below)

  - ✅ **train_dataset.csv/null_rate:** 41.4% null (provenance coupling check below)

#### ✅ `CO Column QA Status` (PASS)

- **Unit:** qa_value
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** (-1.0, 32767.0)
- **Description:** QA value for CO Column. Sentinel-5P cloud fraction: 0–1 (threshold <0.5). MODIS MAIAC AOD: AOD_QA bitmask integer (non-negative). CO Column has no native QA band; sentinel value -1 is used. Null when the science feature is null.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | qa_value | — | PASS | 151/161 | 6.2% | 0.0% | -1 | -1 | -1 | 0 | 1 | 0.7% | 0 | 0 | -1, -1, -1 |
| Merger | ✅ PASS | qa_value | — | PASS | 70/84 | 16.7% | 0.0% | -1 | -1 | -1 | 0 | 1 | 1.4% | 0 | 0 | -1, -1, -1 |
| Dataset Builder | ✅ PASS | qa_value | — | PASS | 70/84 | 16.7% | 0.0% | -1 | -1 | -1 | 0 | 1 | 1.4% | 0 | 0 | -1, -1, -1 |
| merged_feature_table.csv | ✅ PASS | qa_value | — | PASS | 70/84 | 16.7% | 0.0% | -1 | -1 | -1 | 0 | 1 | 1.4% | 0 | 0 | -1, -1, -1 |
| analysis_ready_dataset.csv | ✅ PASS | qa_value | — | PASS | 70/84 | 16.7% | 0.0% | -1 | -1 | -1 | 0 | 1 | 1.4% | 0 | 0 | -1, -1, -1 |
| train_dataset.csv | ✅ PASS | qa_value | — | PASS | 48/58 | 17.2% | 0.0% | -1 | -1 | -1 | 0 | 1 | 2.1% | 0 | 0 | -1, -1, -1 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 6.2% null (provenance coupling check below)

  - ✅ **Merger/null_rate:** 16.7% null (provenance coupling check below)

  - ✅ **Dataset Builder/null_rate:** 16.7% null (provenance coupling check below)

  - ✅ **merged_feature_table.csv/null_rate:** 16.7% null (provenance coupling check below)

  - ✅ **analysis_ready_dataset.csv/null_rate:** 16.7% null (provenance coupling check below)

  - ✅ **train_dataset.csv/null_rate:** 17.2% null (provenance coupling check below)

#### ✅ `O3 Column QA Status` (PASS)

- **Unit:** qa_value
- **Source:** GEE / satellite collector
- **In ML model:** No
- **Valid range:** (-1.0, 32767.0)
- **Description:** QA value for O3 Column. Sentinel-5P cloud fraction: 0–1 (threshold <0.5). MODIS MAIAC AOD: AOD_QA bitmask integer (non-negative). CO Column has no native QA band; sentinel value -1 is used. Null when the science feature is null.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | qa_value | — | PASS | 129/161 | 19.9% | 0.0% | 0 | 0.3032 | 0.495 | 0.1464 | 121 | 93.8% | 0.02144 | 0.5077 | 0.3032, 0.2577, 0.4192 |
| Merger | ✅ PASS | qa_value | — | PASS | 63/84 | 25.0% | 0.0% | 0.1441 | 0.3593 | 0.4796 | 0.1112 | 9 | 14.3% | 0.01236 | 0.3307 | 0.1591, 0.1441, 0.4796 |
| Dataset Builder | ✅ PASS | qa_value | — | PASS | 63/84 | 25.0% | 0.0% | 0.1441 | 0.3593 | 0.4796 | 0.1112 | 9 | 14.3% | 0.01236 | 0.3307 | 0.3121, 0.1591, 0.1441 |
| merged_feature_table.csv | ✅ PASS | qa_value | — | PASS | 63/84 | 25.0% | 0.0% | 0.1441 | 0.3593 | 0.4796 | 0.1112 | 9 | 14.3% | 0.01236 | 0.3307 | 0.1591, 0.1441, 0.4796 |
| analysis_ready_dataset.csv | ✅ PASS | qa_value | — | PASS | 63/84 | 25.0% | 0.0% | 0.1441 | 0.3593 | 0.4796 | 0.1112 | 9 | 14.3% | 0.01236 | 0.3307 | 0.3121, 0.1591, 0.1441 |
| train_dataset.csv | ✅ PASS | qa_value | — | PASS | 43/58 | 25.9% | 0.0% | 0.1441 | 0.3593 | 0.4796 | 0.1094 | 9 | 20.9% | 0.01196 | 0.3239 | 0.3121, 0.4529, 0.4034 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 19.9% null (provenance coupling check below)

  - ✅ **Merger/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **Dataset Builder/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **merged_feature_table.csv/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **analysis_ready_dataset.csv/null_rate:** 25.0% null (provenance coupling check below)

  - ✅ **train_dataset.csv/null_rate:** 25.9% null (provenance coupling check below)

#### ✅ `placeholder_used` (PASS)

- **Unit:** bool
- **Source:** sentinel5p_collector / merger
- **In ML model:** No
- **Valid range:** N/A
- **Description:** True when this row is a NaN sentinel inserted because the station returned no data from any GEE product. Rows where placeholder_used=True must have all satellite features null; rows where placeholder_used=False and satellite features are null indicate cloud/QA masking (expected).

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | bool | — | PASS | 161/161 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | False, False, False |
| Merger | ✅ PASS | bool | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | False, False, False |
| Dataset Builder | ✅ PASS | bool | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | False, False, False |
| merged_feature_table.csv | ✅ PASS | bool | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | False, False, False |
| analysis_ready_dataset.csv | ✅ PASS | bool | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | False, False, False |
| train_dataset.csv | ✅ PASS | bool | — | PASS | 58/58 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | False, False, False |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 0.0% null

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

#### ✅ `requested_date` (PASS)

- **Unit:** date (YYYY-MM-DD)
- **Source:** sentinel5p_collector
- **In ML model:** No
- **Valid range:** N/A
- **Description:** The originally requested satellite acquisition date before adaptive shifting

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | date (YYYY-MM-DD) | — | PASS | 161/161 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | 2026-07-07, 2026-07-07, 2026-07-07 |
| Merger | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Dataset Builder | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| merged_feature_table.csv | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| analysis_ready_dataset.csv | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| train_dataset.csv | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 0.0% null

#### ✅ `satellite_match_distance_km` (PASS)

- **Unit:** km
- **Source:** feature_engineering merger
- **In ML model:** No
- **Valid range:** (0.0, 50.0)
- **Description:** Distance between CPCB station and nearest satellite grid point

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Merger | ✅ PASS | km | — | PASS | 84/84 | 0.0% | 0.0% | 1.157 | 4.175 | 8.024 | 2.172 | 12 | 14.3% | 4.716 | 0.4915 | 5.513, 1.778, 5.787 |
| Dataset Builder | ✅ PASS | km | — | PASS | 84/84 | 0.0% | 0.0% | 1.157 | 4.175 | 8.024 | 2.172 | 12 | 14.3% | 4.716 | 0.4915 | 1.157, 5.513, 1.778 |
| merged_feature_table.csv | ✅ PASS | km | — | PASS | 84/84 | 0.0% | 0.0% | 1.157 | 4.175 | 8.024 | 2.172 | 12 | 14.3% | 4.716 | 0.4915 | 5.513, 1.778, 5.787 |
| analysis_ready_dataset.csv | ✅ PASS | km | — | PASS | 84/84 | 0.0% | 0.0% | 1.157 | 4.175 | 8.024 | 2.172 | 12 | 14.3% | 4.716 | 0.4915 | 1.157, 5.513, 1.778 |
| train_dataset.csv | ✅ PASS | km | — | PASS | 58/58 | 0.0% | 0.0% | 1.157 | 4.175 | 8.024 | 2.204 | 12 | 20.7% | 4.859 | 0.4986 | 1.157, 3.212, 6.323 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

#### ✅ `era5_match_distance_km` (PASS)

- **Unit:** km
- **Source:** feature_engineering merger
- **In ML model:** No
- **Valid range:** (0.0, 50.0)
- **Description:** Distance between CPCB station and nearest ERA5 grid point

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Merger | ✅ PASS | km | — | PASS | 84/84 | 0.0% | 0.0% | 3.744 | 13.18 | 16.17 | 3.487 | 12 | 14.3% | 12.16 | 0.2836 | 13.07, 13.28, 13.65 |
| Dataset Builder | ✅ PASS | km | — | PASS | 84/84 | 0.0% | 0.0% | 3.744 | 13.18 | 16.17 | 3.487 | 12 | 14.3% | 12.16 | 0.2836 | 15.95, 13.07, 13.28 |
| merged_feature_table.csv | ✅ PASS | km | — | PASS | 84/84 | 0.0% | 0.0% | 3.744 | 13.18 | 16.17 | 3.487 | 12 | 14.3% | 12.16 | 0.2836 | 13.07, 13.28, 13.65 |
| analysis_ready_dataset.csv | ✅ PASS | km | — | PASS | 84/84 | 0.0% | 0.0% | 3.744 | 13.18 | 16.17 | 3.487 | 12 | 14.3% | 12.16 | 0.2836 | 15.95, 13.07, 13.28 |
| train_dataset.csv | ✅ PASS | km | — | PASS | 58/58 | 0.0% | 0.0% | 3.744 | 13.28 | 16.17 | 3.549 | 12 | 20.7% | 12.59 | 0.2883 | 15.95, 10.73, 7.732 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

### Group: `satellite`

#### ℹ️ `AOD` (WARNING (expected))

- **Unit:** unitless (physical AOD, scale factor 0.001 applied)
- **Source:** MODIS MAIAC
- **In ML model:** Yes
- **Valid range:** (0.0, 5.0)
- **Description:** Aerosol Optical Depth at 550 nm. Physical range 0-5. MODIS stores as integer * 0.001; scale factor is applied in the collector. Null rate >50% during Indian monsoon (June-September) is expected due to cloud cover masking - classified WARN_EXPECTED, not a data-quality failure.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ℹ️ WARNING (expected) | unitless (physical AOD, scale factor 0.001 applied) | — | PASS | 14/161 | 91.3% | 0.0% | 0.217 | 0.5685 | 1.023 | 0.1952 | 14 | 100.0% | 0.03811 | 0.3493 | 0.639, 1.023, 0.648 |
| Merger | ℹ️ WARNING (expected) | unitless (physical AOD, scale factor 0.001 applied) | unitless | PASS | 0/84 | 100.0% | 0.0% | — | — | — | 0 | 0 | 0.0% | 0 | 0 | — |
| Dataset Builder | ℹ️ WARNING (expected) | unitless (physical AOD, scale factor 0.001 applied) | — | PASS | 0/84 | 100.0% | 0.0% | — | — | — | 0 | 0 | 0.0% | 0 | 0 | — |
| merged_feature_table.csv | ℹ️ WARNING (expected) | unitless (physical AOD, scale factor 0.001 applied) | unitless | PASS | 0/84 | 100.0% | 0.0% | — | — | — | 0 | 0 | 0.0% | 0 | 0 | — |
| analysis_ready_dataset.csv | ℹ️ WARNING (expected) | unitless (physical AOD, scale factor 0.001 applied) | — | PASS | 0/84 | 100.0% | 0.0% | — | — | — | 0 | 0 | 0.0% | 0 | 0 | — |
| train_dataset.csv | ℹ️ WARNING (expected) | unitless (physical AOD, scale factor 0.001 applied) | — | PASS | 0/58 | 100.0% | 0.0% | — | — | — | 0 | 0 | 0.0% | 0 | 0 | — |
| FeatureGroupManager | ✅ PASS | unitless (physical AOD, scale factor 0.001 applied) | — | PASS | — | — | — | — | — | — | — | — | — | — | — | — |

  - ℹ️ **Collector/null_rate:** Missingness is consistent with MAIAC cloud masking.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 6.8 days).
    - Missingness is consistent with MAIAC cloud masking.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: MODIS MAIAC MCD19A2 ATBD, MODIS Land Quality Assurance guides, and Copernicus/GEE MODIS dataset documentation
    Supporting Diagnostic: null_pct = 91.3%
  - ✅ **Collector/scientific_validation:** AOD within valid physical range (0.0–5.0)

  - ℹ️ **Merger/null_rate:** Missingness is consistent with MAIAC cloud masking.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    Scientific Interpretation:
    - Missingness is consistent with daily orbit overpass gaps (locations fell outside daily orbit swath).
    - Missingness is consistent with MAIAC cloud masking.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: MODIS MAIAC MCD19A2 ATBD, MODIS Land Quality Assurance guides, and Copernicus/GEE MODIS dataset documentation
    Supporting Diagnostic: null_pct = 100.0%

  - ℹ️ **Dataset Builder/null_rate:** Missingness is consistent with MAIAC cloud masking.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    Scientific Interpretation:
    - Missingness is consistent with daily orbit overpass gaps (locations fell outside daily orbit swath).
    - Missingness is consistent with MAIAC cloud masking.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: MODIS MAIAC MCD19A2 ATBD, MODIS Land Quality Assurance guides, and Copernicus/GEE MODIS dataset documentation
    Supporting Diagnostic: null_pct = 100.0%

  - ℹ️ **merged_feature_table.csv/null_rate:** Missingness is consistent with MAIAC cloud masking.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    Scientific Interpretation:
    - Missingness is consistent with daily orbit overpass gaps (locations fell outside daily orbit swath).
    - Missingness is consistent with MAIAC cloud masking.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: MODIS MAIAC MCD19A2 ATBD, MODIS Land Quality Assurance guides, and Copernicus/GEE MODIS dataset documentation
    Supporting Diagnostic: null_pct = 100.0%

  - ℹ️ **analysis_ready_dataset.csv/null_rate:** Missingness is consistent with MAIAC cloud masking.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    Scientific Interpretation:
    - Missingness is consistent with daily orbit overpass gaps (locations fell outside daily orbit swath).
    - Missingness is consistent with MAIAC cloud masking.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: MODIS MAIAC MCD19A2 ATBD, MODIS Land Quality Assurance guides, and Copernicus/GEE MODIS dataset documentation
    Supporting Diagnostic: null_pct = 100.0%

  - ℹ️ **train_dataset.csv/null_rate:** Missingness is consistent with MAIAC cloud masking.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    Scientific Interpretation:
    - Missingness is consistent with daily orbit overpass gaps (locations fell outside daily orbit swath).
    - Missingness is consistent with MAIAC cloud masking.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: MODIS MAIAC MCD19A2 ATBD, MODIS Land Quality Assurance guides, and Copernicus/GEE MODIS dataset documentation
    Supporting Diagnostic: null_pct = 100.0%

#### ℹ️ `HCHO` (WARNING (expected))

- **Unit:** mol/m2
- **Source:** TROPOMI S5P OFFL L3_HCHO
- **In ML model:** Yes
- **Valid range:** (-0.001, 0.01)
- **Description:** Formaldehyde (HCHO) tropospheric vertical column density. Small negative values (to ~-0.001 mol/m2) are physically valid in clean-air scenes due to TROPOMI retrieval noise; KNMI specification retains them.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ℹ️ WARNING (expected) | mol/m2 | — | PASS | 137/161 | 14.9% | 0.0% | -0.0001406 | 0.0001692 | 0.0005831 | 0.0001155 | 133 | 97.1% | 1.333e-08 | 0.6591 | -5.372e-05, 9.04e-05, -6.709e-05 |
| Merger | ℹ️ WARNING (expected) | mol/m2 | mol/m2 | PASS | 63/84 | 25.0% | 0.0% | 5.93e-06 | 0.0001955 | 0.0003103 | 8.705e-05 | 9 | 14.3% | 7.578e-09 | 0.508 | 0.0001955, 0.0002581, 0.0001191 |
| Dataset Builder | ℹ️ WARNING (expected) | mol/m2 | — | PASS | 63/84 | 25.0% | 0.0% | 5.93e-06 | 0.0001955 | 0.0003103 | 8.705e-05 | 9 | 14.3% | 7.578e-09 | 0.508 | 0.0002065, 0.0001955, 0.0002581 |
| merged_feature_table.csv | ℹ️ WARNING (expected) | mol/m2 | mol/m2 | PASS | 63/84 | 25.0% | 0.0% | 5.93e-06 | 0.0001955 | 0.0003103 | 8.705e-05 | 9 | 14.3% | 7.578e-09 | 0.508 | 0.0001955, 0.0002581, 0.0001191 |
| analysis_ready_dataset.csv | ℹ️ WARNING (expected) | mol/m2 | — | PASS | 63/84 | 25.0% | 0.0% | 5.93e-06 | 0.0001955 | 0.0003103 | 8.705e-05 | 9 | 14.3% | 7.578e-09 | 0.508 | 0.0002065, 0.0001955, 0.0002581 |
| train_dataset.csv | ℹ️ WARNING (expected) | mol/m2 | — | PASS | 43/58 | 25.9% | 0.0% | 5.93e-06 | 0.0001955 | 0.0003103 | 8.552e-05 | 9 | 20.9% | 7.314e-09 | 0.4897 | 0.0002065, 5.93e-06, 0.0003103 |
| FeatureGroupManager | ✅ PASS | mol/m2 | — | PASS | — | — | — | — | — | — | — | — | — | — | — | — |

  - ℹ️ **Collector/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 6.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P HCHO ATBD (S5P-L2-HCHO-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-HCHO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 14.9%

  - ℹ️ **Merger/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P HCHO ATBD (S5P-L2-HCHO-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-HCHO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 25.0%

  - ℹ️ **Dataset Builder/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P HCHO ATBD (S5P-L2-HCHO-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-HCHO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 25.0%

  - ℹ️ **merged_feature_table.csv/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P HCHO ATBD (S5P-L2-HCHO-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-HCHO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 25.0%

  - ℹ️ **analysis_ready_dataset.csv/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P HCHO ATBD (S5P-L2-HCHO-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-HCHO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 25.0%

  - ℹ️ **train_dataset.csv/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P HCHO ATBD (S5P-L2-HCHO-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-HCHO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 25.9%

#### ℹ️ `NO2 Column` (WARNING (expected))

- **Unit:** mol/m2
- **Source:** TROPOMI S5P OFFL L3_NO2
- **In ML model:** Yes
- **Valid range:** (0.0, 0.01)
- **Description:** Tropospheric NO2 vertical column number density

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ℹ️ WARNING (expected) | mol/m2 | — | PASS | 152/161 | 5.6% | 0.0% | 1.915e-06 | 4.537e-05 | 0.000203 | 3.645e-05 | 148 | 97.4% | 1.329e-09 | 0.6637 | 8.287e-05, 3.924e-05, 7.712e-06 |
| Merger | ✅ PASS | mol/m2 | mol/m2 | PASS | 84/84 | 0.0% | 0.0% | 3.171e-05 | 6.807e-05 | 0.0001235 | 2.876e-05 | 11 | 13.1% | 8.273e-10 | 0.4171 | 0.0001235, 0.0001101, 7.558e-05 |
| Dataset Builder | ✅ PASS | mol/m2 | — | PASS | 84/84 | 0.0% | 0.0% | 3.171e-05 | 6.807e-05 | 0.0001235 | 2.876e-05 | 11 | 13.1% | 8.273e-10 | 0.4171 | 9.075e-05, 0.0001235, 0.0001101 |
| merged_feature_table.csv | ✅ PASS | mol/m2 | mol/m2 | PASS | 84/84 | 0.0% | 0.0% | 3.171e-05 | 6.807e-05 | 0.0001235 | 2.876e-05 | 11 | 13.1% | 8.273e-10 | 0.4171 | 0.0001235, 0.0001101, 7.558e-05 |
| analysis_ready_dataset.csv | ✅ PASS | mol/m2 | — | PASS | 84/84 | 0.0% | 0.0% | 3.171e-05 | 6.807e-05 | 0.0001235 | 2.876e-05 | 11 | 13.1% | 8.273e-10 | 0.4171 | 9.075e-05, 0.0001235, 0.0001101 |
| train_dataset.csv | ✅ PASS | mol/m2 | — | PASS | 58/58 | 0.0% | 0.0% | 3.171e-05 | 6.807e-05 | 0.0001235 | 2.8e-05 | 11 | 19.0% | 7.839e-10 | 0.4078 | 9.075e-05, 3.171e-05, 5.626e-05 |
| FeatureGroupManager | ✅ PASS | mol/m2 | — | PASS | — | — | — | — | — | — | — | — | — | — | — | — |

  - ℹ️ **Collector/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with publication lag of 5 days (adaptive lookback applied).
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 6.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P NO2 Column ATBD (S5P-L2-NO2-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-NO2), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 5.6%

  - ✅ **Merger/null_rate:** Feature completely present.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - No unexplained missingness or retrieval limitations detected.
    Supporting Diagnostic: null_pct = 0.0%

  - ✅ **Dataset Builder/null_rate:** Feature completely present.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - No unexplained missingness or retrieval limitations detected.
    Supporting Diagnostic: null_pct = 0.0%

  - ✅ **merged_feature_table.csv/null_rate:** Feature completely present.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - No unexplained missingness or retrieval limitations detected.
    Supporting Diagnostic: null_pct = 0.0%

  - ✅ **analysis_ready_dataset.csv/null_rate:** Feature completely present.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - No unexplained missingness or retrieval limitations detected.
    Supporting Diagnostic: null_pct = 0.0%

  - ✅ **train_dataset.csv/null_rate:** Feature completely present.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - No unexplained missingness or retrieval limitations detected.
    Supporting Diagnostic: null_pct = 0.0%

#### ℹ️ `SO2 Column` (WARNING (expected))

- **Unit:** mol/m2
- **Source:** TROPOMI S5P OFFL L3_SO2
- **In ML model:** Yes
- **Valid range:** (-0.001, 0.05)
- **Description:** SO2 total vertical column density. Negative values (to ~-0.001 mol/m2) are physically valid in very-low-SO2 scenes; TROPOMI SO2 retrieval is an incremental measurement relative to a reference spectrum.

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ℹ️ WARNING (expected) | mol/m2 | — | PASS | 113/161 | 29.8% | 0.0% | -0.0003259 | 1.258e-05 | 0.0005876 | 0.0001792 | 109 | 96.5% | 3.212e-08 | 5.047 | 8.609e-05, -0.0001729, -7.171e-06 |
| Merger | ℹ️ WARNING (expected) | mol/m2 | mol/m2 | PASS | 49/84 | 41.7% | 0.0% | -0.0001404 | 1.257e-05 | 0.0002826 | 0.000126 | 7 | 14.3% | 1.587e-08 | 2.58 | -0.0001404, -2.869e-05, 0.0002826 |
| Dataset Builder | ℹ️ WARNING (expected) | mol/m2 | — | PASS | 49/84 | 41.7% | 0.0% | -0.0001404 | 1.257e-05 | 0.0002826 | 0.000126 | 7 | 14.3% | 1.587e-08 | 2.58 | -7.073e-06, -0.0001404, -2.869e-05 |
| merged_feature_table.csv | ℹ️ WARNING (expected) | mol/m2 | mol/m2 | PASS | 49/84 | 41.7% | 0.0% | -0.0001404 | 1.257e-05 | 0.0002826 | 0.000126 | 7 | 14.3% | 1.587e-08 | 2.58 | -0.0001404, -2.869e-05, 0.0002826 |
| analysis_ready_dataset.csv | ℹ️ WARNING (expected) | mol/m2 | — | PASS | 49/84 | 41.7% | 0.0% | -0.0001404 | 1.257e-05 | 0.0002826 | 0.000126 | 7 | 14.3% | 1.587e-08 | 2.58 | -7.073e-06, -0.0001404, -2.869e-05 |
| train_dataset.csv | ℹ️ WARNING (expected) | mol/m2 | — | PASS | 34/58 | 41.4% | 0.0% | -0.0001404 | 1.257e-05 | 0.0002826 | 0.000124 | 7 | 20.6% | 1.537e-08 | 2.279 | -7.073e-06, 1.257e-05, 0.0002826 |
| FeatureGroupManager | ✅ PASS | mol/m2 | — | PASS | — | — | — | — | — | — | — | — | — | — | — | — |

  - ℹ️ **Collector/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 6.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P SO2 Column ATBD (S5P-L2-SO2-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-SO2), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 29.8%

  - ℹ️ **Merger/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P SO2 Column ATBD (S5P-L2-SO2-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-SO2), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 41.7%

  - ℹ️ **Dataset Builder/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P SO2 Column ATBD (S5P-L2-SO2-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-SO2), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 41.7%

  - ℹ️ **merged_feature_table.csv/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P SO2 Column ATBD (S5P-L2-SO2-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-SO2), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 41.7%

  - ℹ️ **analysis_ready_dataset.csv/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P SO2 Column ATBD (S5P-L2-SO2-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-SO2), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 41.7%

  - ℹ️ **train_dataset.csv/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P SO2 Column ATBD (S5P-L2-SO2-ATBD), Product Readme File (S5P-MPC-KNMI-PRF-SO2), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 41.4%

#### ℹ️ `CO Column` (WARNING (expected))

- **Unit:** mol/m2
- **Source:** TROPOMI S5P OFFL L3_CO
- **In ML model:** Yes
- **Valid range:** (0.0, 0.5)
- **Description:** CO total column number density

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ℹ️ WARNING (expected) | mol/m2 | — | PASS | 151/161 | 6.2% | 0.0% | 0.01813 | 0.03266 | 0.04318 | 0.005562 | 147 | 97.4% | 3.094e-05 | 0.168 | 0.0283, 0.02927, 0.02987 |
| Merger | ℹ️ WARNING (expected) | mol/m2 | mol/m2 | PASS | 70/84 | 16.7% | 0.0% | 0.02534 | 0.03203 | 0.04289 | 0.005783 | 10 | 14.3% | 3.345e-05 | 0.1764 | 0.04289, 0.03937, 0.02538 |
| Dataset Builder | ℹ️ WARNING (expected) | mol/m2 | — | PASS | 70/84 | 16.7% | 0.0% | 0.02534 | 0.03203 | 0.04289 | 0.005783 | 10 | 14.3% | 3.345e-05 | 0.1764 | 0.03653, 0.04289, 0.03937 |
| merged_feature_table.csv | ℹ️ WARNING (expected) | mol/m2 | mol/m2 | PASS | 70/84 | 16.7% | 0.0% | 0.02534 | 0.03203 | 0.04289 | 0.005783 | 10 | 14.3% | 3.345e-05 | 0.1764 | 0.04289, 0.03937, 0.02538 |
| analysis_ready_dataset.csv | ℹ️ WARNING (expected) | mol/m2 | — | PASS | 70/84 | 16.7% | 0.0% | 0.02534 | 0.03203 | 0.04289 | 0.005783 | 10 | 14.3% | 3.345e-05 | 0.1764 | 0.03653, 0.04289, 0.03937 |
| train_dataset.csv | ℹ️ WARNING (expected) | mol/m2 | — | PASS | 48/58 | 17.2% | 0.0% | 0.02534 | 0.03203 | 0.04289 | 0.005632 | 10 | 20.8% | 3.172e-05 | 0.1721 | 0.03653, 0.02534, 0.02742 |
| FeatureGroupManager | ✅ PASS | mol/m2 | — | PASS | — | — | — | — | — | — | — | — | — | — | — | — |

  - ℹ️ **Collector/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 6.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P CO Column ATBD (S5P-L2-CO-ATBD), Product Readme File (S5P-MPC-SRON-PRF-CO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 6.2%

  - ℹ️ **Merger/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P CO Column ATBD (S5P-L2-CO-ATBD), Product Readme File (S5P-MPC-SRON-PRF-CO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 16.7%

  - ℹ️ **Dataset Builder/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P CO Column ATBD (S5P-L2-CO-ATBD), Product Readme File (S5P-MPC-SRON-PRF-CO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 16.7%

  - ℹ️ **merged_feature_table.csv/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P CO Column ATBD (S5P-L2-CO-ATBD), Product Readme File (S5P-MPC-SRON-PRF-CO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 16.7%

  - ℹ️ **analysis_ready_dataset.csv/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P CO Column ATBD (S5P-L2-CO-ATBD), Product Readme File (S5P-MPC-SRON-PRF-CO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 16.7%

  - ℹ️ **train_dataset.csv/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P CO Column ATBD (S5P-L2-CO-ATBD), Product Readme File (S5P-MPC-SRON-PRF-CO), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 17.2%

#### ℹ️ `O3 Column` (WARNING (expected))

- **Unit:** mol/m2
- **Source:** TROPOMI S5P OFFL L3_O3
- **In ML model:** Yes
- **Valid range:** (0.0, 0.5)
- **Description:** O3 total vertical column density

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ℹ️ WARNING (expected) | mol/m2 | — | PASS | 129/161 | 19.9% | 0.0% | 0.1235 | 0.1289 | 0.1342 | 0.002233 | 125 | 96.9% | 4.984e-06 | 0.0173 | 0.1285, 0.1287, 0.1253 |
| Merger | ℹ️ WARNING (expected) | mol/m2 | mol/m2 | PASS | 63/84 | 25.0% | 0.0% | 0.1256 | 0.1277 | 0.1329 | 0.002366 | 9 | 14.3% | 5.596e-06 | 0.01845 | 0.1279, 0.1277, 0.1259 |
| Dataset Builder | ℹ️ WARNING (expected) | mol/m2 | — | PASS | 63/84 | 25.0% | 0.0% | 0.1256 | 0.1277 | 0.1329 | 0.002366 | 9 | 14.3% | 5.596e-06 | 0.01845 | 0.1329, 0.1279, 0.1277 |
| merged_feature_table.csv | ℹ️ WARNING (expected) | mol/m2 | mol/m2 | PASS | 63/84 | 25.0% | 0.0% | 0.1256 | 0.1277 | 0.1329 | 0.002366 | 9 | 14.3% | 5.596e-06 | 0.01845 | 0.1279, 0.1277, 0.1259 |
| analysis_ready_dataset.csv | ℹ️ WARNING (expected) | mol/m2 | — | PASS | 63/84 | 25.0% | 0.0% | 0.1256 | 0.1277 | 0.1329 | 0.002366 | 9 | 14.3% | 5.596e-06 | 0.01845 | 0.1329, 0.1279, 0.1277 |
| train_dataset.csv | ℹ️ WARNING (expected) | mol/m2 | — | PASS | 43/58 | 25.9% | 0.0% | 0.1256 | 0.1277 | 0.1329 | 0.002405 | 9 | 20.9% | 5.783e-06 | 0.01875 | 0.1329, 0.126, 0.1256 |
| FeatureGroupManager | ✅ PASS | mol/m2 | — | PASS | — | — | — | — | — | — | — | — | — | — | — | — |

  - ℹ️ **Collector/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 6.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P O3 Column ATBD (S5P-L2-O3-ATBD), Product Readme File (S5P-MPC-DLR-PRF-O3), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 19.9%

  - ℹ️ **Merger/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P O3 Column ATBD (S5P-L2-O3-ATBD), Product Readme File (S5P-MPC-DLR-PRF-O3), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 25.0%

  - ℹ️ **Dataset Builder/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P O3 Column ATBD (S5P-L2-O3-ATBD), Product Readme File (S5P-MPC-DLR-PRF-O3), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 25.0%

  - ℹ️ **merged_feature_table.csv/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P O3 Column ATBD (S5P-L2-O3-ATBD), Product Readme File (S5P-MPC-DLR-PRF-O3), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 25.0%

  - ℹ️ **analysis_ready_dataset.csv/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P O3 Column ATBD (S5P-L2-O3-ATBD), Product Readme File (S5P-MPC-DLR-PRF-O3), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 25.0%

  - ℹ️ **train_dataset.csv/null_rate:** Missingness is consistent with Sentinel-5P retrieval limitations.
    Runtime Evidence:
    - Collector executed successfully
    - Image collection successfully queried
    - Placeholder not used
    - QA metadata verified
    Scientific Interpretation:
    - Missingness is consistent with documented QA filtering.
    - Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to 3.7 days).
    - Missingness is consistent with Sentinel-5P retrieval limitations.
    - Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).
    Official References: Sentinel-5P O3 Column ATBD (S5P-L2-O3-ATBD), Product Readme File (S5P-MPC-DLR-PRF-O3), Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides
    Supporting Diagnostic: null_pct = 25.9%

### Group: `target`

#### ✅ `PM2.5` (PASS)

- **Unit:** µg/m³
- **Source:** CPCB
- **In ML model:** No
- **Valid range:** (0.0, 1000.0)
- **Description:** Fine particulate matter (PM2.5) ground concentration

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | µg/m³ | ug/m3 | PASS | 84/84 | 0.0% | 0.0% | 24 | 186 | 401 | 86.09 | 72 | 85.7% | 7411 | 0.4768 | 259, 206, 237 |
| Merger | ✅ PASS | µg/m³ | ug/m3 | PASS | 84/84 | 0.0% | 0.0% | 24 | 186 | 401 | 86.09 | 72 | 85.7% | 7411 | 0.4768 | 259, 206, 237 |
| Dataset Builder | ✅ PASS | µg/m³ | — | PASS | 84/84 | 0.0% | 0.0% | 24 | 186 | 401 | 86.09 | 72 | 85.7% | 7411 | 0.4768 | 81, 220, 130 |
| merged_feature_table.csv | ✅ PASS | µg/m³ | ug/m3 | PASS | 84/84 | 0.0% | 0.0% | 24 | 186 | 401 | 86.09 | 72 | 85.7% | 7411 | 0.4768 | 259, 206, 237 |
| analysis_ready_dataset.csv | ✅ PASS | µg/m³ | — | PASS | 84/84 | 0.0% | 0.0% | 24 | 186 | 401 | 86.09 | 72 | 85.7% | 7411 | 0.4768 | 81, 220, 130 |
| train_dataset.csv | ✅ PASS | µg/m³ | — | PASS | 58/58 | 0.0% | 0.0% | 24 | 181 | 401 | 90.55 | 55 | 94.8% | 8199 | 0.5127 | 81, 63, 155 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 0.0% null

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

#### ✅ `PM10` (PASS)

- **Unit:** µg/m³
- **Source:** CPCB
- **In ML model:** No
- **Valid range:** (0.0, 1500.0)
- **Description:** Coarse particulate matter (PM10) ground concentration

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | µg/m³ | ug/m3 | PASS | 84/84 | 0.0% | 0.0% | 61 | 373.5 | 750 | 176 | 82 | 97.6% | 3.099e+04 | 0.476 | 543, 504, 420 |
| Merger | ✅ PASS | µg/m³ | ug/m3 | PASS | 84/84 | 0.0% | 0.0% | 61 | 373.5 | 750 | 176 | 82 | 97.6% | 3.099e+04 | 0.476 | 543, 504, 420 |
| Dataset Builder | ✅ PASS | µg/m³ | — | PASS | 84/84 | 0.0% | 0.0% | 61 | 373.5 | 750 | 176 | 82 | 97.6% | 3.099e+04 | 0.476 | 207, 440, 378 |
| merged_feature_table.csv | ✅ PASS | µg/m³ | ug/m3 | PASS | 84/84 | 0.0% | 0.0% | 61 | 373.5 | 750 | 176 | 82 | 97.6% | 3.099e+04 | 0.476 | 543, 504, 420 |
| analysis_ready_dataset.csv | ✅ PASS | µg/m³ | — | PASS | 84/84 | 0.0% | 0.0% | 61 | 373.5 | 750 | 176 | 82 | 97.6% | 3.099e+04 | 0.476 | 207, 440, 378 |
| train_dataset.csv | ✅ PASS | µg/m³ | — | PASS | 58/58 | 0.0% | 0.0% | 61 | 371.5 | 687 | 178.7 | 57 | 98.3% | 3.192e+04 | 0.4943 | 207, 161, 243 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 0.0% null

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

#### ✅ `NO2` (PASS)

- **Unit:** µg/m³
- **Source:** CPCB
- **In ML model:** No
- **Valid range:** (0.0, 1000.0)
- **Description:** NO2 ground concentration

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | µg/m³ | ug/m3 | PASS | 84/84 | 0.0% | 0.0% | 6 | 56.5 | 116 | 28.37 | 56 | 66.7% | 805.1 | 0.5105 | 90, 57, 64 |
| Merger | ✅ PASS | µg/m³ | ug/m3 | PASS | 84/84 | 0.0% | 0.0% | 6 | 56.5 | 116 | 28.37 | 56 | 66.7% | 805.1 | 0.5105 | 90, 57, 64 |
| Dataset Builder | ✅ PASS | µg/m³ | — | PASS | 84/84 | 0.0% | 0.0% | 6 | 56.5 | 116 | 28.37 | 56 | 66.7% | 805.1 | 0.5105 | 32, 72, 50 |
| merged_feature_table.csv | ✅ PASS | µg/m³ | ug/m3 | PASS | 84/84 | 0.0% | 0.0% | 6 | 56.5 | 116 | 28.37 | 56 | 66.7% | 805.1 | 0.5105 | 90, 57, 64 |
| analysis_ready_dataset.csv | ✅ PASS | µg/m³ | — | PASS | 84/84 | 0.0% | 0.0% | 6 | 56.5 | 116 | 28.37 | 56 | 66.7% | 805.1 | 0.5105 | 32, 72, 50 |
| train_dataset.csv | ✅ PASS | µg/m³ | — | PASS | 58/58 | 0.0% | 0.0% | 6 | 56.5 | 116 | 29.63 | 45 | 77.6% | 878 | 0.5319 | 32, 19, 44 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 0.0% null

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

#### ✅ `SO2` (PASS)

- **Unit:** µg/m³
- **Source:** CPCB
- **In ML model:** No
- **Valid range:** (0.0, 2000.0)
- **Description:** SO2 ground concentration

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | µg/m³ | ug/m3 | PASS | 84/84 | 0.0% | 0.0% | 4 | 24.5 | 63 | 14.55 | 41 | 48.8% | 211.8 | 0.5759 | 17, 26, 39 |
| Merger | ✅ PASS | µg/m³ | ug/m3 | PASS | 84/84 | 0.0% | 0.0% | 4 | 24.5 | 63 | 14.55 | 41 | 48.8% | 211.8 | 0.5759 | 17, 26, 39 |
| Dataset Builder | ✅ PASS | µg/m³ | — | PASS | 84/84 | 0.0% | 0.0% | 4 | 24.5 | 63 | 14.55 | 41 | 48.8% | 211.8 | 0.5759 | 7, 28, 18 |
| merged_feature_table.csv | ✅ PASS | µg/m³ | ug/m3 | PASS | 84/84 | 0.0% | 0.0% | 4 | 24.5 | 63 | 14.55 | 41 | 48.8% | 211.8 | 0.5759 | 17, 26, 39 |
| analysis_ready_dataset.csv | ✅ PASS | µg/m³ | — | PASS | 84/84 | 0.0% | 0.0% | 4 | 24.5 | 63 | 14.55 | 41 | 48.8% | 211.8 | 0.5759 | 7, 28, 18 |
| train_dataset.csv | ✅ PASS | µg/m³ | — | PASS | 58/58 | 0.0% | 0.0% | 4 | 24.5 | 63 | 14.61 | 34 | 58.6% | 213.6 | 0.583 | 7, 12, 25 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 0.0% null

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

#### ✅ `CO` (PASS)

- **Unit:** mg/m³
- **Source:** CPCB
- **In ML model:** No
- **Valid range:** (0.0, 100.0)
- **Description:** CO ground concentration

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | mg/m³ | mg/m3 | PASS | 84/84 | 0.0% | 0.0% | 0.4 | 2.38 | 5.61 | 1.291 | 79 | 94.0% | 1.667 | 0.5211 | 3.88, 3.77, 3.67 |
| Merger | ✅ PASS | mg/m³ | mg/m3 | PASS | 84/84 | 0.0% | 0.0% | 0.4 | 2.38 | 5.61 | 1.291 | 79 | 94.0% | 1.667 | 0.5211 | 3.88, 3.77, 3.67 |
| Dataset Builder | ✅ PASS | mg/m³ | — | PASS | 84/84 | 0.0% | 0.0% | 0.4 | 2.38 | 5.61 | 1.291 | 79 | 94.0% | 1.667 | 0.5211 | 0.9, 1.42, 1.81 |
| merged_feature_table.csv | ✅ PASS | mg/m³ | mg/m3 | PASS | 84/84 | 0.0% | 0.0% | 0.4 | 2.38 | 5.61 | 1.291 | 79 | 94.0% | 1.667 | 0.5211 | 3.88, 3.77, 3.67 |
| analysis_ready_dataset.csv | ✅ PASS | mg/m³ | — | PASS | 84/84 | 0.0% | 0.0% | 0.4 | 2.38 | 5.61 | 1.291 | 79 | 94.0% | 1.667 | 0.5211 | 0.9, 1.42, 1.81 |
| train_dataset.csv | ✅ PASS | mg/m³ | — | PASS | 58/58 | 0.0% | 0.0% | 0.4 | 2.455 | 5.61 | 1.363 | 57 | 98.3% | 1.857 | 0.5475 | 0.9, 1.31, 1.28 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 0.0% null

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

#### ✅ `O3` (PASS)

- **Unit:** µg/m³
- **Source:** CPCB
- **In ML model:** No
- **Valid range:** (0.0, 1000.0)
- **Description:** Ozone ground concentration

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | µg/m³ | ug/m3 | PASS | 84/84 | 0.0% | 0.0% | 9 | 72 | 170 | 37.2 | 58 | 69.0% | 1384 | 0.4983 | 116, 107, 93 |
| Merger | ✅ PASS | µg/m³ | ug/m3 | PASS | 84/84 | 0.0% | 0.0% | 9 | 72 | 170 | 37.2 | 58 | 69.0% | 1384 | 0.4983 | 116, 107, 93 |
| Dataset Builder | ✅ PASS | µg/m³ | — | PASS | 84/84 | 0.0% | 0.0% | 9 | 72 | 170 | 37.2 | 58 | 69.0% | 1384 | 0.4983 | 29, 90, 79 |
| merged_feature_table.csv | ✅ PASS | µg/m³ | ug/m3 | PASS | 84/84 | 0.0% | 0.0% | 9 | 72 | 170 | 37.2 | 58 | 69.0% | 1384 | 0.4983 | 116, 107, 93 |
| analysis_ready_dataset.csv | ✅ PASS | µg/m³ | — | PASS | 84/84 | 0.0% | 0.0% | 9 | 72 | 170 | 37.2 | 58 | 69.0% | 1384 | 0.4983 | 29, 90, 79 |
| train_dataset.csv | ✅ PASS | µg/m³ | — | PASS | 58/58 | 0.0% | 0.0% | 9 | 71.5 | 170 | 37.67 | 45 | 77.6% | 1419 | 0.5109 | 29, 31, 58 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 0.0% null

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

#### ✅ `AQI` (PASS)

- **Unit:** index
- **Source:** CPCB
- **In ML model:** No
- **Valid range:** (0.0, 500.0)
- **Description:** Air Quality Index (0–500 scale)

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | ✅ PASS | index | index | PASS | 84/84 | 0.0% | 0.0% | 41 | 258.5 | 448 | 110.2 | 77 | 91.7% | 1.214e+04 | 0.446 | 331, 337, 276 |
| Merger | ✅ PASS | index | — | PASS | 84/84 | 0.0% | 0.0% | 41 | 258.5 | 448 | 110.2 | 77 | 91.7% | 1.214e+04 | 0.446 | 331, 337, 276 |
| Dataset Builder | ✅ PASS | index | — | PASS | 84/84 | 0.0% | 0.0% | 41 | 258.5 | 448 | 110.2 | 77 | 91.7% | 1.214e+04 | 0.446 | 127, 257, 212 |
| merged_feature_table.csv | ✅ PASS | index | — | PASS | 84/84 | 0.0% | 0.0% | 41 | 258.5 | 448 | 110.2 | 77 | 91.7% | 1.214e+04 | 0.446 | 331, 337, 276 |
| analysis_ready_dataset.csv | ✅ PASS | index | — | PASS | 84/84 | 0.0% | 0.0% | 41 | 258.5 | 448 | 110.2 | 77 | 91.7% | 1.214e+04 | 0.446 | 127, 257, 212 |
| train_dataset.csv | ✅ PASS | index | — | PASS | 58/58 | 0.0% | 0.0% | 41 | 243 | 448 | 115.7 | 57 | 98.3% | 1.338e+04 | 0.4751 | 127, 102, 202 |
| FeatureGroupManager | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Collector/null_rate:** 0.0% null

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

### Group: `temporal`

#### ✅ `Day of Week` (PASS)

- **Unit:** index (0=Monday)
- **Source:** Derived from timestamp
- **In ML model:** Yes
- **Valid range:** (0.0, 6.0)
- **Description:** Day of week (0=Monday, 6=Sunday)

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Merger | ✅ PASS | index (0=Monday) | index | PASS | 84/84 | 0.0% | 0.0% | 0 | 3 | 6 | 2.012 | 7 | 8.3% | 4.048 | 0.6707 | 6, 6, 6 |
| Dataset Builder | ✅ PASS | index (0=Monday) | — | PASS | 84/84 | 0.0% | 0.0% | 0 | 3 | 6 | 2.012 | 7 | 8.3% | 4.048 | 0.6707 | 0, 0, 0 |
| merged_feature_table.csv | ✅ PASS | index (0=Monday) | index | PASS | 84/84 | 0.0% | 0.0% | 0 | 3 | 6 | 2.012 | 7 | 8.3% | 4.048 | 0.6707 | 6, 6, 6 |
| analysis_ready_dataset.csv | ✅ PASS | index (0=Monday) | — | PASS | 84/84 | 0.0% | 0.0% | 0 | 3 | 6 | 2.012 | 7 | 8.3% | 4.048 | 0.6707 | 0, 0, 0 |
| train_dataset.csv | ✅ PASS | index (0=Monday) | — | PASS | 58/58 | 0.0% | 0.0% | 0 | 2 | 4 | 1.4 | 5 | 8.6% | 1.96 | 0.725 | 0, 0, 0 |
| FeatureGroupManager | ✅ PASS | index (0=Monday) | — | PASS | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

#### ✅ `Month` (PASS)

- **Unit:** index (1–12)
- **Source:** Derived from timestamp
- **In ML model:** Yes
- **Valid range:** (1.0, 12.0)
- **Description:** Calendar month (1–12)

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Merger | ✅ PASS | index (1–12) | index | PASS | 84/84 | 0.0% | 0.0% | 7 | 7 | 7 | 0 | 1 | 1.2% | 0 | 0 | 7, 7, 7 |
| Dataset Builder | ✅ PASS | index (1–12) | — | PASS | 84/84 | 0.0% | 0.0% | 7 | 7 | 7 | 0 | 1 | 1.2% | 0 | 0 | 7, 7, 7 |
| merged_feature_table.csv | ✅ PASS | index (1–12) | index | PASS | 84/84 | 0.0% | 0.0% | 7 | 7 | 7 | 0 | 1 | 1.2% | 0 | 0 | 7, 7, 7 |
| analysis_ready_dataset.csv | ✅ PASS | index (1–12) | — | PASS | 84/84 | 0.0% | 0.0% | 7 | 7 | 7 | 0 | 1 | 1.2% | 0 | 0 | 7, 7, 7 |
| train_dataset.csv | ✅ PASS | index (1–12) | — | PASS | 58/58 | 0.0% | 0.0% | 7 | 7 | 7 | 0 | 1 | 1.7% | 0 | 0 | 7, 7, 7 |
| FeatureGroupManager | ✅ PASS | index (1–12) | — | PASS | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

#### ✅ `Season` (PASS)

- **Unit:** category
- **Source:** Derived from Month
- **In ML model:** Yes
- **Valid range:** N/A
- **Description:** India meteorological season: Winter, Pre-Monsoon, Monsoon, Post-Monsoon

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Merger | ✅ PASS | category | category | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | Monsoon, Monsoon, Monsoon |
| Dataset Builder | ✅ PASS | category | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | Monsoon, Monsoon, Monsoon |
| merged_feature_table.csv | ✅ PASS | category | category | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | Monsoon, Monsoon, Monsoon |
| analysis_ready_dataset.csv | ✅ PASS | category | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | Monsoon, Monsoon, Monsoon |
| train_dataset.csv | ✅ PASS | category | — | PASS | 58/58 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | Monsoon, Monsoon, Monsoon |
| FeatureGroupManager | ✅ PASS | category | — | PASS | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

#### ✅ `Weekend Flag` (PASS)

- **Unit:** bool
- **Source:** Derived from Day of Week
- **In ML model:** Yes
- **Valid range:** N/A
- **Description:** True if Saturday or Sunday

| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |
|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|
| Collector | — — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |
| Merger | ✅ PASS | bool | boolean | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | True, True, True |
| Dataset Builder | ✅ PASS | bool | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | False, False, False |
| merged_feature_table.csv | ✅ PASS | bool | boolean | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | True, True, True |
| analysis_ready_dataset.csv | ✅ PASS | bool | — | PASS | 84/84 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | False, False, False |
| train_dataset.csv | ✅ PASS | bool | — | PASS | 58/58 | 0.0% | 0.0% | — | — | — | — | — | — | — | — | False, False, False |
| FeatureGroupManager | ✅ PASS | bool | — | PASS | — | — | — | — | — | — | — | — | — | — | — | — |

  - ✅ **Merger/null_rate:** 0.0% null

  - ✅ **Dataset Builder/null_rate:** 0.0% null

  - ✅ **merged_feature_table.csv/null_rate:** 0.0% null

  - ✅ **analysis_ready_dataset.csv/null_rate:** 0.0% null

  - ✅ **train_dataset.csv/null_rate:** 0.0% null

## Appendix: Pipeline Stage File Locations

| Stage | File / Source |
|-------|------|
| `Collector` | CPCB / ERA5 / MODIS / TROPOMI raw outputs |
| `Merger` | `data_collection_pipeline/features/merged_feature_table.csv` |
| `Dataset Builder` | `analysis_ready_dataset.csv` |
| `merged_feature_table.csv` | `data_collection_pipeline/features/merged_feature_table.csv` |
| `analysis_ready_dataset.csv` | `analysis_ready_dataset.csv` |
| `train_dataset.csv` | `train_dataset.csv` |
| `FeatureGroupManager` | `FeatureGroupManager` model features registry |

## Appendix: Unit Key

| Abbreviation | Meaning |
|-------------|---------|
| µg/m³ | micrograms per cubic metre |
| mg/m³ | milligrams per cubic metre |
| mol/m² | moles per square metre |
| K | Kelvin |
| °C | Celsius |
| Pa | Pascals |
| m/s | metres per second |

## Appendix: Validation Status Definitions

| Status | Symbol | Meaning |
|--------|--------|---------|
| PASS | ✅ | Feature meets all schema expectations |
| WARN_EXPECTED | ℹ️ | Expected operational limitation (e.g. AOD null during monsoon, provenance null when science feature is null due to cloud cover, Relative Humidity 100.0–100.5% from ERA5 spectral artefacts). No code change required. |
| WARN_INVESTIGATE | ⚠️ | Unexpected condition that should be investigated (e.g. temporal offset outside configured lookback window [−14, +3] days, provenance null when science feature is present, unexpectedly high null rate without documented cause). |
| FAIL | ❌ | Hard failure: feature missing, 100% null, values outside physical range. Must be fixed before production use. |
| SKIP | — | Feature not expected in this pipeline stage. |

*Report generated by `data_collection_pipeline.validation`.*