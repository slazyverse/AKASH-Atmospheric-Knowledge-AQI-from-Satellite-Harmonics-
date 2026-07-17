# LightGBM Feature Validation & Comparison Report

## Dataset Audit
* **Total Rows:** 502
* **Total Columns:** 58
* **Duplicate Rows:** 0
* **Audit Status:** PASS

## Columns Summary
* **Feature Count:** 18
* **Constant Columns:** ['Date', 'Time', 'Day of Week', 'Month', 'Season', 'Weekend Flag', 'AOD Publication Lag', 'HCHO Publication Lag', 'NO2 Column Publication Lag', 'SO2 Column Publication Lag', 'CO Column QA Status', 'CO Column Publication Lag', 'O3 Column Publication Lag', 'placeholder_used']
* **Infinite Value Columns:** {}

## Model Comparison
| Model | R² | RMSE | MAE | MBE |
| :--- | :---: | :---: | :---: | :---: |
| **LightGBM (Prod)** | -0.0729 | 75.5807 | 51.8897 | -25.2884 |
| **Random Forest (Baseline)** | N/A | N/A | N/A | N/A |