# Sprint-04A: Random Forest Infrastructure Refactor

## Objective
Refactor the machine learning training and validation infrastructure to consume the newly built Feature Engineering schema, validation, and AQI calculator modules.

## Work Completed
* Removed all legacy code occurrences of `.select_dtypes(include=["number"])` from the training and validation modules.
* Created the reusable `preprocessing.py` module inside `feature_engineering/` defining:
  * `build_preprocessing_pipeline()`: Automates scikit-learn `Pipeline` and `ColumnTransformer` generation mapping inputs to scaling, categorical one-hot encoding, and imputation preprocessors based on `FeatureSchema` metadata.
  * `preprocess_target()`: Dynamically extracts target AQI or automatically reconstructs it using `aqi_calculator.py` if missing but concentrations are present.
* Integrated `FeatureValidator` checks at both training and cross-validation entry points to abort execution on critical anomalies.
* Deduplicated model pre-processing scripts by routing both training and validation scripts to the unified preprocessing helper.
* Created comprehensive integration tests verifying end-to-end model pipeline fits and cross-validation runs.

## Technical Decisions
* **Unified sklearn Pipelines**: Wrapped both preprocessing transformers and regressors within a single `Pipeline` object. This guarantees that model training and model validation (cross-validation folds) do not suffer from data leakage, and ensures model checkpoints (`baseline_model.joblib`) are fully self-contained.
* **Fallback Avoidance**: Replaced the hardcoded `"PM2.5"` target fallback with CPCB target reconstruction, adhering to scientific regulation specifications.

## Scientific Decisions
* Supported both raw target extraction and sub-index reconstruction matching official segmented equations prior to preparing splits.

## Files Changed
* `data_collection_pipeline/feature_engineering/preprocessing.py` [NEW]
* `data_collection_pipeline/feature_engineering/__init__.py` [MODIFIED]
* `data_collection_pipeline/model_training/baseline_model.py` [MODIFIED]
* `data_collection_pipeline/model_validation/cross_validator.py` [MODIFIED]
* `data_collection_pipeline/tests/test_preprocessing.py` [NEW]

## Validation Performed
* Added 5 unit/integration tests running complete pipeline compilations.
* Result: 29/29 total tests passed successfully.

## Known Limitations
* Preprocessing imputer defaults to column mean imputation for baselines.

## Next Sprint Goals
* Execute Sprint 04B: Train the baseline Random Forest model, optimize hyperparameters, and evaluate performance.
