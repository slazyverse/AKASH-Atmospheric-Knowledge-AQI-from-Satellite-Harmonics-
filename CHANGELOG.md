# Changelog

All notable changes to the AKASH project under Soumyadeb's scientific and AI/ML pipeline scope will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.5.0] - 2026-07-09
### Added
* Random Forest Baseline in [baseline_model.py](file:///Users/soumyadebtripathy/Downloads/StockSphere_Project/Akaash/data_collection_pipeline/model_training/baseline_model.py):
  * Dynamic train/test split supporting temporal/chronological hold-out slicing.
  * Hyperparameter configurations loaded from the central `config.py` module.
  * Evaluation metrics (R², RMSE, MAE, and Mean Bias Error).
  * Post-preprocessor feature importance mapping matching columns output by One-Hot Encoders.
  * joblib serialization exporting fitted pipelines, summaries, metrics, and importances.
* Dedicated unit/integration test suite in [test_random_forest.py](file:///Users/soumyadebtripathy/Downloads/StockSphere_Project/Akaash/data_collection_pipeline/tests/test_random_forest.py).
* Sprint-04B report in `docs/sprints/Sprint-04B.md`.

### Changed
* Refactored [cross_validator.py](file:///Users/soumyadebtripathy/Downloads/StockSphere_Project/Akaash/data_collection_pipeline/model_validation/cross_validator.py) to load Random Forest hyperparameters from `config.py` central parameters to ensure testing parity.

---

## [0.4.0] - 2026-07-09
### Added
* Preprocessing Package in [preprocessing.py](file:///Users/soumyadebtripathy/Downloads/StockSphere_Project/Akaash/data_collection_pipeline/feature_engineering/preprocessing.py):
  * Unified scikit-learn `Pipeline` and `ColumnTransformer` builder separating numerical (scaler + imputer) and categorical (one-hot encoder + imputer) variables.
  * Target AQI preprocessor supporting dynamic CPCB reconstruction from raw pollutant concentration columns.
* Unit and integration test suite in [test_preprocessing.py](file:///Users/soumyadebtripathy/Downloads/StockSphere_Project/Akaash/data_collection_pipeline/tests/test_preprocessing.py).
* Sprint-04A report in `docs/sprints/Sprint-04A.md`.

### Changed
* Refactored [baseline_model.py](file:///Users/soumyadebtripathy/Downloads/StockSphere_Project/Akaash/data_collection_pipeline/model_training/baseline_model.py) and [cross_validator.py](file:///Users/soumyadebtripathy/Downloads/StockSphere_Project/Akaash/data_collection_pipeline/model_validation/cross_validator.py):
  * Removed every instance of `.select_dtypes(include=["number"])`.
  * Routed feature extraction exclusively through `FeatureGroupManager`.
  * Integrated `FeatureValidator` checks at execution entry points to abort on critical errors.
  * Extracted and replaced legacy preprocessing logic with the unified preprocessing pipeline.

---

## [0.3.0] - 2026-07-09
### Added
* Feature Engineering Framework in [data_collection_pipeline/feature_engineering/](file:///Users/soumyadebtripathy/Downloads/StockSphere_Project/Akaash/data_collection_pipeline/feature_engineering/):
  * `schema.py`: Reusable metadata class and global schema constraints for targets, satellite, meteorology, geography, temporal, and metadata features.
  * `groups.py`: Feature group manager mapping and querying features by their category.
  * `validation.py`: Feature validator running out-of-range, null percentage, and type checks on DataFrames.
  * `selection.py`: Selection tools implementing variance thresholding, collinearity pruning, and group-filtering.
* Pytest unit tests in [test_feature_engineering.py](file:///Users/soumyadebtripathy/Downloads/StockSphere_Project/Akaash/data_collection_pipeline/tests/test_feature_engineering.py).
* Sprint-03 report in `docs/sprints/Sprint-03.md`.

---

## [0.2.0] - 2026-07-09
### Added
* Google Earth Engine (GEE) Data Pipeline Package in [earth_engine/](file:///Users/soumyadebtripathy/Downloads/StockSphere_Project/Akaash/data_collection_pipeline/earth_engine/):
  * `config.py`, `initializer.py`, `dataset_catalog.py`, `analysis_grid.py`, `base_loader.py`.
  * Modular loaders for TROPOMI (`tropomi.py`), MODIS AOD (`modis.py`), ERA5 Land (`era5.py`), and VIIRS Active Fire (`viirs.py`).
  * Cloud export stubs and coordinate/geojson helpers.
* Technical documentation in `docs/earth_engine.md`.
* Unit tests in [test_gee_pipeline.py](file:///Users/soumyadebtripathy/Downloads/StockSphere_Project/Akaash/data_collection_pipeline/tests/test_gee_pipeline.py).
* Sprint-02 report in `docs/sprints/Sprint-02.md`.

---

## [0.1.0] - 2026-07-09
### Added
* CPCB AQI Breakpoint Calculation Module in [aqi_calculator.py](file:///Users/soumyadebtripathy/Downloads/StockSphere_Project/Akaash/data_collection_pipeline/aqi_calculator.py).
* Pytest unit tests in [test_aqi_calculator.py](file:///Users/soumyadebtripathy/Downloads/StockSphere_Project/Akaash/data_collection_pipeline/tests/test_aqi_calculator.py).
* Sprint-01 report in `docs/sprints/Sprint-01.md`.
