# Sprint-02: Google Earth Engine Data Pipeline

## Objective
Implement a modular, scalable Google Earth Engine (GEE) dataset loader and initialization framework for satellite, meteorological, and fire datasets.

## Work Completed
* Created the `earth_engine/` package with dedicated config, initializer, and catalog structures.
* Built modular loaders for Sentinel-5P TROPOMI, MODIS MAIAC, ERA5 Land, and VIIRS Active Fire.
* Implemented the 5 km common analysis grid generator supporting both local Python coordinates and GEE FeatureCollections.
* Added stubs for exporting images to Drive, Cloud Assets, and GCS.
* Created a test suite containing 9 offline-capable unit tests mocking GEE objects.

## Technical Decisions
* **Sensor Decoupling**: Split loaders into dataset-specific files rather than a single monolithic loaders module to ease maintenance and extension.
* **Offline Pytest Mocks**: Inserted a mocked `ee` module into `sys.modules` during testing to verify parameters, filters, and ranges without executing live Google Cloud calls.
* **Flexible Geometries**: Accepted arbitrary bounding box arrays and GeoJSON geometries rather than hardcoding coordinates, allowing regional sub-cropping.

## Scientific Decisions
* **TROPOMI Quality Filter**: Filtered pixels dynamically using `qa_value >= 0.5`.
* **MODIS AOD Quality Filter**: Implemented bitwise checks on the `AOD_QA` band to verify clear conditions (bits 0-2 = 1) and best quality (bits 8-11 = 0).
* **ERA5 Temporal Aggregation**: Added hourly-to-daily downsampling methods to aggregate weather parameters.
* **VIIRS Confidence Filter**: Excluded low-confidence hotspots by filtering the active fire anomaly bands.

## Files Changed
* `data_collection_pipeline/requirements.txt` [MODIFIED]
* `data_collection_pipeline/earth_engine/` [NEW]
* `data_collection_pipeline/tests/test_gee_pipeline.py` [NEW]
* `docs/earth_engine.md` [NEW]

## Validation Performed
* Pytest GEE suite running and passing 9 mock filtering, geometry, and catalog checks.
* Result: 9/9 tests passed successfully.

## Known Limitations
* Requires active GEE authentication or service account key environment variables for live remote data downloads.

## Next Sprint Goals
* Feature Engineering Framework, schema validation, and collinearity filters.
