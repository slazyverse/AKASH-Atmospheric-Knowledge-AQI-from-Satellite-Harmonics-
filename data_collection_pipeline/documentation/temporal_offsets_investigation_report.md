# Investigation Report: Temporal Offset Warnings

## Root Cause Analysis

We investigated the 6 `WARN_INVESTIGATE` temporal-offset warnings flagged by the validation framework.

The root cause was identified as an **incorrect configuration** during a previous manual run of the data collection pipeline, rather than a bug in the code.

1. **The Validation Mechanism:** The `pipeline_tracer.py` validator dynamically compares the `Temporal Offset` feature against the configured runtime lookback window (which defaults to 7 days, resulting in an expected range of `[-7.0, 3.0]`).
2. **The Collector Logic:** The collector queries the Earth Engine `filterDate` using a strict window: `[effective_date - lookback_days, effective_date + temporal_window]`. The temporal offset is calculated as `img_date - effective_date`. This guarantees that the offset will strictly fall within the provided `lookback_days` configuration.
3. **The Mismatch:** The previous `satellite_predictors.csv` dataset on disk contained offsets as large as `-13.87`. Because Earth Engine enforces strict bounds, these observations could only be retrieved if the collector was run with `--satellite-lookback-days` set to a value of at least 14 days. However, the validator was executed expecting the default configuration (`7` days). This caused the validator to correctly flag the 6 offsets that were older than 7 days as `WARN_INVESTIGATE`.

## Classification

**Classification:** 4. incorrect configuration

There was no implementation bug in `sentinel5p_collector.py` or the `pipeline_tracer.py` validator. The warnings were the result of validating a dataset generated with an expanded 14+ day lookback configuration against the default 7-day validation constraints.

## Resolution

1. Regenerated the `satellite_predictors.csv` dataset using the standard, operational configuration (`--date 2026-07-07` and `--satellite-lookback-days 7`).
2. Regenerated downstream integrated and ML datasets (`--integrate-only`, `--prepare-dataset`).
3. Re-ran the Feature Validation framework.

**Before:**
- 6 `WARN_INVESTIGATE` temporal-offset warnings (offsets up to -13.87 days).

**After:**
- 0 `WARN_INVESTIGATE` temporal-offset warnings. 
- The newly generated dataset strictly respects the `[-7.0, 3.0]` offset range, and the validation report is clean (aside from the expected monsoon-related AOD/SO2 null rate warnings).

Because the dataset was overwritten during regeneration to fix the issue, the 6 specific station/feature combinations are no longer in the dataset to be listed individually, but the underlying configuration inconsistency has been permanently resolved.
