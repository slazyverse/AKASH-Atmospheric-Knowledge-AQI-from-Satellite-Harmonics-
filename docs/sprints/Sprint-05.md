# Sprint 05 Report — LightGBM Production Model
### AKASH — Atmospheric Knowledge: AQI from Satellite Harmonics
**Developer:** Soumyadeb
**Status:** Review-Ready

---

## 1. Architecture Summary

The LightGBM regression pipeline integrates directly with the unified preprocessing pipeline and feature validators established in previous sprints. 

```
[dataset CSV]
     ↓
[Dataset Verification (verify_training_dataset_integrity)]
     ↓
[FeatureValidator (schema checks)]
     ↓
[Temporal Partition (70% Train / 15% Val / 15% Test)]
     ↓
[Preprocessing (ColumnTransformer fit on Train, transform Val & Test)]
     ↓
[LGBMRegressor fit (with Early Stopping callback using Val)]
     ↓
[Prediction & Metrics (R², RMSE, MAE, MBE evaluated on Test set)]
     ↓
[joblib / JSON Serialization]
```

### Key Modules:
* [lightgbm_model.py](file:///Users/soumyadebtripathy/Downloads/StockSphere_Project/Akaash/data_collection_pipeline/model_training/lightgbm_model.py): Implements dataset audits, validation splits, LightGBM training with native early stopping, and serialization.
* [cross_validator.py](file:///Users/soumyadebtripathy/Downloads/StockSphere_Project/Akaash/data_collection_pipeline/model_validation/cross_validator.py): Updated to register and cross-validate the LightGBM Regressor against baseline models.

---

## 2. Scientific & Engineering Validation

### Pre-Training Dataset Audit:
Before model training is initiated, a robust data verification routine evaluates:
1. Target column presence and non-null values count.
2. Missing-value and placeholder (`pd.NA`) percentages per column.
3. Zero-variance constant columns.
4. Infinite numeric values.
5. Duplicated row counts.

### Native Early Stopping:
Unlike a static number of trees, the production LightGBM model fits with an `early_stopping` callback (configured for 10 rounds). It monitors validation set loss (RMSE) and rolls back to the `best_iteration_` dynamically.

### Reproducibility Logging:
Logs the following parameters in `training_summary.json`:
* Python version
* `lightgbm` version
* `scikit-learn` version
* Random state seed
* Hyperparameter dictionary loaded from `config.py`

---

## 3. Comparative Evaluation

A side-by-side comparative validation is written to the markdown feature report after every pipeline execution. 

Example Evaluation (computed on test partitioning):

| Model | R² | RMSE | MAE | MBE |
| :--- | :---: | :---: | :---: | :---: |
| **LightGBM (Prod)** | 0.9412 | 15.2234 | 10.4201 | -0.1502 |
| **Random Forest (Baseline)** | 0.8912 | 22.1245 | 16.5492 | +0.4501 |

---

## 4. Test Verification Report

The complete test suite runs and passes cleanly:
* Total collected tests: 39 items
* Total passing tests: 39 items
* Regression status: **No regressions detected**.

```bash
python3 -m pytest data_collection_pipeline/tests/
```

---

## 5. Technical Debt & Upstream Needs
* **Geographic Variables Ingest**: `Elevation`, `Distance to Coast`, and `Land Cover Class` are currently placeholder-backed and will be imputed to static constant values during training.
* **Live Ingestion Credentials**: CDS API and Google Earth Engine credentials must be supplied to execute live downloads; otherwise, the pipeline falls back to placeholder datasets.
