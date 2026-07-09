# Sprint-03: Feature Engineering Framework

## Objective
Implement a reusable, highly modular Feature Engineering and Selection Framework defining schemas, groups, value-range validations, and collinearity pruning utilities.

## Work Completed
* Defined a comprehensive `FeatureSchema` grouping 29 distinct satellite, meteorology, geography, temporal, and metadata variables.
* Implemented `FeatureGroupManager` supporting group categorization and dynamic list queries.
* Built `FeatureValidator` providing range verification, null tracking, and data-type verification.
* Built `FeatureSelector` implementing subset group selection, low-variance threshold filtering, and multicollinear feature pruning.
* Created a test suite with 6 pytest unit tests verifying validations, bounds, and selection logic.

## Technical Decisions
* **Decoupled Validation**: Separated range checks and column validation into a `FeatureValidator` that generates a detailed dictionary audit report, rather than raising immediate exceptions, preventing silent failures.
* **Collinearity Tie-Breaker**: Designed a Pearson correlation filter that resolves redundant feature pairs by keeping the feature with higher absolute correlation to the target variable, maximizing predictive capacity.

## Scientific Decisions
* **Physical Bound Constraints**: Mapped range limits matching physical constraints of the atmospheric/geographic models:
  * Near-surface temperature: $200$ K to $330$ K.
  * Relative Humidity: $0\%$ to $100\%$.
  * AOD: $0.0$ to $5.0$.
  * Boundary Layer Height: $0$ m to $6000$ m.
  * Elevation: $-100$ m to $9000$ m.

## Files Changed
* `data_collection_pipeline/feature_engineering/schema.py` [NEW]
* `data_collection_pipeline/feature_engineering/groups.py` [NEW]
* `data_collection_pipeline/feature_engineering/validation.py` [NEW]
* `data_collection_pipeline/feature_engineering/selection.py` [NEW]
* `data_collection_pipeline/feature_engineering/__init__.py` [MODIFIED]
* `data_collection_pipeline/tests/test_feature_engineering.py` [NEW]

## Validation Performed
* Pytest unit tests running 6 verification checks of validators and selection algorithms.
* Result: 6/6 tests passed successfully.

## Known Limitations
* Pearson correlation checks assume linear relationships between variables; non-linear feature redundancies are not checked.

## Next Sprint Goals
* Implementation of the baseline Random Forest model pipeline (sprint-04).
