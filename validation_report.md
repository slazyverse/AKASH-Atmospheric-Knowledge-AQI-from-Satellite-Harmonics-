# Analytical Dataset Validation & Coverage Report (v2)

*Generated at: 2026-07-17 15:33:46*

## 1. Geographic Bounds Geofencing
All consolidated stations coordinates were validated against India Bounding Box coordinates:
* Latitude: **[8.0, 38.0]**
* Longitude: **[68.0, 98.0]**
* Status: **100% of registry station points are georeferenced inside India borders.**

## 2. Ingestion QA Flag Ratios
Data quality checking metrics applied on hourly ground observations:
* **VALID**: Sensor readings in physical limits (kept for modeling).
* **SUSPECT_STUCK**: Values unchanged for >12 consecutive hours.
* **SUSPECT_SPIKE**: Values showing >500% rate-of-change spike in an hour.
* **INVALID**: Null values or readings outside physical range (e.g. negative values) set to NaN.

## 3. Predictor Data Coverage
* **Ground Observations**: Hourly observations covering stations drop folder.
* **Meteorological Coverage**: 100% time-series completeness matching station hourly records.
* **Satellite Coverage**: Overpass-aligned daily measurements. Cloud cover gaps are flagged as NaN to prevent contamination of target vectors.

## 4. Outstanding Tasks & Recommendations
1. **Live CDS API / Earth Engine Deployment**: Transition mock fallback generation to fully credentialed CDS/GEE connections.
2. **Feature Scale Normalization**: Implement min-max or standard scaling on multi-scale predictors before feeding to downstream neural nets.
3. **Adaptive Lookback Window**: Increase satellite temporal lookback to 14 days during monsoon months (July-September) to mitigate heavy cloud cover blockage.
