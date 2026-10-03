# Sprint-01: CPCB AQI Calculator

## Objective
Implement a scientifically accurate, CPCB-compliant Air Quality Index (AQI) sub-index and overall AQI calculation engine.

## Work Completed
* Implemented the segmented linear interpolation formula for the eight criteria pollutants ($PM_{2.5}$, $PM_{10}$, $NO_2$, $SO_2$, $CO$, $O_3$, $NH_3$, and $Pb$).
* Developed the overall AQI aggregator with deterministic lexicographical tie-breaking for identifying the dominant pollutant.
* Built the CPCB minimum data validator (checking if at least 3 pollutants are present, with at least one being $PM_{2.5}$ or $PM_{10}$).
* Created a test suite with 9 pytest unit tests verifying exact boundaries, mid-interval interpolation, and edge cases.

## Technical Decisions
* **Pre-Truncation**: Applied sensory concentration truncation before breakpoint matching ($CO$ and $Pb$ to $1$ decimal place; others to integers) to align with CPCB's official segmented ranges.
* **Separation of Concerns**: Decoupled the calculator, the aggregator, and the requirement validator into separate, testable functions instead of combining them into a single monolithic loop.

## Scientific Decisions
* Capped sub-indices at $500$ when concentrations exceed the highest severe breakpoint ($BP_{max}$) to match regulatory reporting bounds.

## Files Changed
* `data_collection_pipeline/aqi_calculator.py` [NEW]
* `data_collection_pipeline/tests/test_aqi_calculator.py` [NEW]

## Validation Performed
* Run pytest unit tests verifying lower, upper, and mid-interval concentrations (e.g. $PM_{2.5} = 45 \to 75$, $NO_2 = 50 \to 62$).
* Result: 9/9 tests passed successfully.

## Known Limitations
* The calculator returns `None` for overall AQI if CPCB validation checks fail (requires at least 3 pollutants), unless bypassed using `enforce_requirements=False`.

## Next Sprint Goals
* Google Earth Engine initialization, authentication, and dataset loading pipeline.
