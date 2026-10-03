# Sprint-04B: Random Forest Baseline

## Objective
Implement a production-grade, scientifically validated Random Forest baseline model using scikit-learn Pipelines, supporting metrics computations (RMSE, MAE, R², MBE) and feature importance analysis.

## Work Completed
* Integrated `config.py` central hyperparameter loading into `baseline_model.py` and `cross_validator.py` to prevent hardcoded settings.
* Implemented dataset splitting supporting chronological/temporal slicing when date columns are present.
* Integrated evaluation metrics:
  * $R^2$: Coefficient of Determination
  * $RMSE$: Root Mean Squared Error
  * $MAE$: Mean Absolute Error
  * $MBE$: Mean Bias Error (measures systematic under- or over-estimation)
* Implemented post-processing mapping feature importances correctly to their transformed column names (post-One-Hot-Encoding).
* Structured output serialization to export:
  * `baseline_model.joblib`: The fitted Pipeline containing preprocessing and estimator.
  * `training_summary.json`: Training and validation metadata.
  * `evaluation_metrics.json`: Performance metrics.
  * `feature_importances.json`: Sorted feature importances.
  * `data_validation_report.json`: FeatureValidator compliance log.
* Created a dedicated test file `test_random_forest.py` checking predictions, metrics, and serialization.

## Technical Decisions
* **Pipelines over raw features**: By packaging preprocess steps and estimator together, we ensure test predictions automatically pass through the correct scaler/encoder, preventing training-serving skew.
* **Deterministic Seeds**: Enforced deterministic training across all models using a fixed seed (`config.RANDOM_STATE = 42`).

## Scientific Decisions
* **Temporal Hold-Out Split**: Splitting is done temporally (by sorting target dates) instead of randomly by default when temporal fields exist, providing a better simulation of real-world forecast performance.
* **Mean Bias Error (MBE)**: Added MBE to track structural model over-prediction or under-prediction trends.

## Files Changed
* `data_collection_pipeline/config.py` [MODIFIED]
* `data_collection_pipeline/model_training/baseline_model.py` [MODIFIED]
* `data_collection_pipeline/model_validation/cross_validator.py` [MODIFIED]
* `data_collection_pipeline/tests/test_random_forest.py` [NEW]
* `docs/sprints/Sprint-04B.md` [NEW]

## Validation Performed
* Run complete test suite covering all 33 test cases.
* Result: 33/33 tests passed successfully.

## Known Limitations
* Imputation defaults to standard column means, which may oversimplify complex temporal profiles.

## Next Sprint Goals
* Execute Sprint 05: Implement the production LightGBM model with quantile regression uncertainty limits.
