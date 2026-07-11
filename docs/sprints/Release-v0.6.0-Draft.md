# Release Notes — v0.6.0 (DRAFT)
### AKASH — Atmospheric Knowledge: AQI from Satellite Harmonics

This release adds the **LightGBM Production Model** to the AKASH machine learning pipeline, completing the Sprint 05 milestone.

---

## 1. Scientific Additions
* **Dataset Auditing**: Implements a scientific validation scanner to check for duplicated entries, infinite numbers, constant values, and missing percentages before training.
* **Early Stopping**: Wires native early stopping on a validation set partition (using temporal ordering) to prevent overfitting.
* **Feature Pruning**: Automated drop of all-null columns to guarantee a zero-variance threshold.

## 2. Engineering Additions
* **Expanded Hyperparameters**: Adds full configuration definitions (`num_leaves`, `min_child_samples`, etc.) to the central `config.py` module.
* **Serialization Integrity**: Consistent joblib and JSON serialization for model objects, feature validation summaries, parameter configurations, and reproducibility logs.
* **Evaluation Framework**: Adds `LightGBM Regressor` into the cross-validation models suite.

## 3. Validation Summary
All 39 unit and integration tests successfully pass:
* `test_lightgbm.py`: Verifies audits, partitions, fitting, metrics, and saving.
* `test_preprocessing.py`: Verifies cross-validation of all models including LightGBM Regressor.

## 4. Upgrade Notes & Known Limitations
* **earthengine-api Required**: The `earthengine-api` package must be installed to run satellite collections.
* **Geographic Variables**: Elevation, Land Cover Class, and Distance to Coast features default to constant imputed values due to missing upstream loader files.
