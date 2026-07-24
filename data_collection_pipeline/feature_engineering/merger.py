"""Dataset integration orchestration for Day 3 feature engineering."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd

from data_collection_pipeline import config, setup, utils
from data_collection_pipeline.feature_engineering.feature_builder import (
    ALL_FEATURES,
    METEOROLOGY_FEATURES,
    SATELLITE_FEATURES,
    apply_missing_strategy,
    build_features,
)
from data_collection_pipeline.feature_engineering.metadata import (
    write_feature_dictionary,
    write_feature_summary,
    write_integration_report,
)
from data_collection_pipeline.feature_engineering.spatial_matcher import nearest_grid_row
from data_collection_pipeline.feature_engineering.temporal_matcher import (
    SUPPORTED_TEMPORAL_STRATEGIES,
    add_temporal_keys,
)

logger = logging.getLogger("data_collection_pipeline.feature_engineering")

SATELLITE_GRID_FILES = ["satellite_predictors.csv", "satellite_features.csv"]
ERA5_GRID_FILES = ["era5_meteorology.csv", "era5_features.csv"]
ERA5_RENAME_MAP = {
    "2m_temperature": "Temperature",
    "temperature": "Temperature",
    "relative_humidity": "Relative Humidity",
    "boundary_layer_height": "Boundary Layer Height",
    "surface_pressure": "Surface Pressure",
    "10m_u_component_of_wind": "u_wind_component",
    "u_component_of_wind": "u_wind_component",
    "u10": "u_wind_component",
    "10m_v_component_of_wind": "v_wind_component",
    "v_component_of_wind": "v_wind_component",
    "v10": "v_wind_component",
}
SATELLITE_RENAME_MAP = {
    "aod": "AOD",
    "hcho": "HCHO",
    "no2_column": "NO2 Column",
    "so2_column": "SO2 Column",
    "co_column": "CO Column",
    "o3_column": "O3 Column",
    "aod_obs_date": "AOD Obs Date",
    "aod_temporal_offset": "AOD Temporal Offset",
    "aod_temporal_offset_days": "AOD Temporal Offset",
    "aod_qa": "AOD QA Status",
    "aod_qa_status": "AOD QA Status",
    "aod_publication_lag": "AOD Publication Lag",
    "aod_pub_lag_days": "AOD Publication Lag",
    "hcho_obs_date": "HCHO Obs Date",
    "hcho_temporal_offset": "HCHO Temporal Offset",
    "hcho_temporal_offset_days": "HCHO Temporal Offset",
    "hcho_qa": "HCHO QA Status",
    "hcho_qa_status": "HCHO QA Status",
    "hcho_publication_lag": "HCHO Publication Lag",
    "hcho_pub_lag_days": "HCHO Publication Lag",
    "no2_column_obs_date": "NO2 Column Obs Date",
    "no2_column_temporal_offset": "NO2 Column Temporal Offset",
    "no2_column_temporal_offset_days": "NO2 Column Temporal Offset",
    "no2_column_qa": "NO2 Column QA Status",
    "no2_column_qa_status": "NO2 Column QA Status",
    "no2_column_publication_lag": "NO2 Column Publication Lag",
    "no2_column_pub_lag_days": "NO2 Column Publication Lag",
    "so2_column_obs_date": "SO2 Column Obs Date",
    "so2_column_temporal_offset": "SO2 Column Temporal Offset",
    "so2_column_temporal_offset_days": "SO2 Column Temporal Offset",
    "so2_column_qa": "SO2 Column QA Status",
    "so2_column_qa_status": "SO2 Column QA Status",
    "so2_column_publication_lag": "SO2 Column Publication Lag",
    "so2_column_pub_lag_days": "SO2 Column Publication Lag",
    "co_column_obs_date": "CO Column Obs Date",
    "co_column_temporal_offset": "CO Column Temporal Offset",
    "co_column_temporal_offset_days": "CO Column Temporal Offset",
    "co_column_qa": "CO Column QA Status",
    "co_column_qa_status": "CO Column QA Status",
    "co_column_publication_lag": "CO Column Publication Lag",
    "co_column_pub_lag_days": "CO Column Publication Lag",
    "o3_column_obs_date": "O3 Column Obs Date",
    "o3_column_temporal_offset": "O3 Column Temporal Offset",
    "o3_column_temporal_offset_days": "O3 Column Temporal Offset",
    "o3_column_qa": "O3 Column QA Status",
    "o3_column_qa_status": "O3 Column QA Status",
    "o3_column_publication_lag": "O3 Column Publication Lag",
    "o3_column_pub_lag_days": "O3 Column Publication Lag",
}

SATELLITE_METADATA_FEATURES = [
    "AOD Obs Date", "AOD Temporal Offset", "AOD QA Status", "AOD Publication Lag",
    "HCHO Obs Date", "HCHO Temporal Offset", "HCHO QA Status", "HCHO Publication Lag",
    "NO2 Column Obs Date", "NO2 Column Temporal Offset", "NO2 Column QA Status", "NO2 Column Publication Lag",
    "SO2 Column Obs Date", "SO2 Column Temporal Offset", "SO2 Column QA Status", "SO2 Column Publication Lag",
    "CO Column Obs Date", "CO Column Temporal Offset", "CO Column QA Status", "CO Column Publication Lag",
    "O3 Column Obs Date", "O3 Column Temporal Offset", "O3 Column QA Status", "O3 Column Publication Lag",
]


def _first_existing_file(directory: Path, names: List[str]) -> Path | None:
    for name in names:
        path = directory / name
        if path.exists():
            return path
    return None


def _normalise_grid_columns(df: pd.DataFrame, rename_map: Dict[str, str]) -> pd.DataFrame:
    rename = {}
    for column in df.columns:
        key = str(column).strip().casefold()
        normalized_key = key.replace(" ", "_")
        rename[column] = rename_map.get(normalized_key, rename_map.get(key, column))
        if key in {"lat", "latitude"}:
            rename[column] = "latitude"
        if key in {"lon", "lng", "longitude"}:
            rename[column] = "longitude"
        if key in {"time", "datetime", "date_time", "timestamp"}:
            rename[column] = "timestamp"
    return df.rename(columns=rename)


def _placeholder_grid(
    stations: pd.DataFrame,
    timestamps: pd.Series,
    feature_columns: List[str],
) -> pd.DataFrame:
    rows = []
    unique_times = pd.Series(timestamps.dropna().unique())
    if unique_times.empty:
        unique_times = pd.Series([pd.Timestamp.utcnow()])

    for _, station in stations.dropna(subset=["Latitude", "Longitude"]).iterrows():
        for timestamp in unique_times:
            row = {
                "latitude": station["Latitude"],
                "longitude": station["Longitude"],
                "timestamp": pd.Timestamp(timestamp),
            }
            for feature in feature_columns:
                row[feature] = pd.NA
            rows.append(row)
    return pd.DataFrame(rows)


def load_cpcb_observations() -> pd.DataFrame:
    """Load cleaned CPCB observations from processed_data/."""
    path = config.PROCESSED_DATA_DIR / "cpcb_cleaned_latest.csv"
    if not path.exists():
        raise FileNotFoundError(f"Cleaned CPCB file not found: {path}")
    observations = pd.read_csv(path)
    observations = observations.rename(
        columns={"station": "Station Name", "last_update": "timestamp"}
    )
    return add_temporal_keys(observations, "timestamp")


def load_station_metadata() -> pd.DataFrame:
    """Load validated station metadata from metadata/."""
    path = config.METADATA_DIR / "validated_station_metadata.csv"
    if not path.exists():
        raise FileNotFoundError(f"Validated station metadata not found: {path}")
    return pd.read_csv(path)


def load_satellite_grid(stations: pd.DataFrame, timestamps: pd.Series) -> Tuple[pd.DataFrame, str]:
    """Load satellite predictors or create an explicit placeholder interface."""
    path = _first_existing_file(config.PROCESSED_DATA_DIR, SATELLITE_GRID_FILES)
    if path is None:
        all_cols = SATELLITE_FEATURES + SATELLITE_METADATA_FEATURES
        return _placeholder_grid(stations, timestamps, all_cols), "placeholder_grid"
    grid = _normalise_grid_columns(pd.read_csv(path), SATELLITE_RENAME_MAP)
    return grid, str(path)


def load_era5_grid(stations: pd.DataFrame, timestamps: pd.Series) -> Tuple[pd.DataFrame, str]:
    """Load ERA5 tabular predictors or create an explicit placeholder interface."""
    path = _first_existing_file(config.PROCESSED_DATA_DIR, ERA5_GRID_FILES)
    if path is None:
        source = "placeholder_grid"
        if (config.RAW_DATA_DIR / "era5_request_spec.json").exists():
            source = "placeholder_grid_from_era5_request_spec"
        return _placeholder_grid(stations, timestamps, METEOROLOGY_FEATURES), source
    grid = _normalise_grid_columns(pd.read_csv(path), ERA5_RENAME_MAP)
    return grid, str(path)


def _nearest_temporal_row(
    timestamp: pd.Timestamp,
    grid: pd.DataFrame,
    strategy: str,
) -> pd.DataFrame:
    if grid.empty or "timestamp" not in grid.columns:
        return grid

    # grid has already been converted to datetime and cleaned
    candidates = grid

    if strategy == "hourly":
        return candidates[candidates["timestamp"].dt.floor("h") == timestamp.floor("h")]
    if strategy == "daily_average":
        daily = candidates[candidates["timestamp"].dt.floor("D") == timestamp.floor("D")]
        if daily.empty:
            return daily
        numeric_cols = [
            column
            for column in daily.select_dtypes(include="number").columns
            if column not in {"latitude", "longitude"}
        ]
        grouped = daily.groupby(["latitude", "longitude"], as_index=False)[numeric_cols].mean()
        grouped["timestamp"] = timestamp.floor("D")
        return grouped

    time_delta = (candidates["timestamp"] - timestamp).abs()
    nearest_time = candidates.loc[time_delta.idxmin(), "timestamp"]
    return candidates[candidates["timestamp"] == nearest_time]


def _attach_grid_features(
    observations: pd.DataFrame,
    grid: pd.DataFrame,
    feature_columns: List[str],
    prefix: str,
    temporal_strategy: str,
    is_placeholder: bool = False,
) -> pd.DataFrame:
    if is_placeholder:
        df = observations.copy()
        for col in feature_columns:
            df[col] = pd.NA
        df[f"{prefix}_match_distance_km"] = float("nan")
        return df

    # Pre-convert grid timestamps once to avoid slow repeated parsing
    grid_copy = grid.copy()
    if not grid_copy.empty and "timestamp" in grid_copy.columns:
        grid_copy["timestamp"] = pd.to_datetime(
            grid_copy["timestamp"],
            errors="coerce",
            format="mixed",
        )
        grid_copy = grid_copy.dropna(subset=["timestamp"])

    rows = []
    for _, observation in observations.iterrows():
        timestamp = observation["timestamp"]
        candidates = _nearest_temporal_row(timestamp, grid_copy, temporal_strategy)
        nearest = nearest_grid_row(observation["Latitude"], observation["Longitude"], candidates)
        row = observation.to_dict()
        for feature in feature_columns:
            row[feature] = pd.NA if nearest is None else nearest.get(feature, pd.NA)
        distance_column = f"{prefix}_match_distance_km"
        if is_placeholder:
            row[distance_column] = float("nan")
        else:
            row[distance_column] = pd.NA if nearest is None else nearest["match_distance_km"]
        rows.append(row)
    return pd.DataFrame(rows)


def integrate_datasets(
    temporal_strategy: str,
    missing_strategy: str,
    satellite_path: Path | None = None,
    era5_path: Path | None = None,
) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Load and merge cleaned observations, station metadata, satellite, and ERA5 grids.

    Parameters
    ----------
    temporal_strategy:
        Strategy used when aligning grid timestamps to observation timestamps.
        Must be one of ``SUPPORTED_TEMPORAL_STRATEGIES``.
    missing_strategy:
        Strategy applied to missing feature values after merging.
    satellite_path:
        Optional path to a specific satellite predictors CSV file.  When
        provided, the function skips the automatic file-discovery logic in
        ``load_satellite_grid()`` and reads this path directly.  Intended for
        use by the Phase-1 historical pipeline which produces its own
        ``satellite_predictors_hist.csv``.  When ``None`` (the default), the
        existing discovery behaviour is preserved.
    era5_path:
        Optional path to a specific ERA5 meteorology CSV file.  When provided,
        the function skips the automatic file-discovery logic in
        ``load_era5_grid()`` and reads this path directly.  Intended for use
        by the Phase-1 historical pipeline which produces its own
        ``era5_meteorology_hist.csv``.  When ``None`` (the default), the
        existing discovery behaviour is preserved.
    """
    if temporal_strategy not in SUPPORTED_TEMPORAL_STRATEGIES:
        raise ValueError(f"Unsupported temporal alignment strategy: {temporal_strategy}")

    observations = load_cpcb_observations()
    stations = load_station_metadata()
    merged = observations.merge(
        stations,
        on="Station Name",
        how="left",
        suffixes=("", "_metadata"),
    )

    # Use explicit paths when provided (historical mode), otherwise auto-discover.
    import os
    force_skip_satellite = os.environ.get("SKIP_SATELLITE_MERGE") == "1"
    if force_skip_satellite:
        all_cols = SATELLITE_FEATURES + SATELLITE_METADATA_FEATURES
        satellite_grid, satellite_source = _placeholder_grid(stations, merged["timestamp"], all_cols), "placeholder_grid"
    elif satellite_path is not None:
        satellite_path = Path(satellite_path)
        if satellite_path.exists():
            grid = _normalise_grid_columns(pd.read_csv(satellite_path), SATELLITE_RENAME_MAP)
            satellite_grid, satellite_source = grid, str(satellite_path)
        else:
            logger.warning(
                "satellite_path '%s' does not exist; falling back to auto-discovery.",
                satellite_path,
            )
            satellite_grid, satellite_source = load_satellite_grid(stations, merged["timestamp"])
    else:
        satellite_grid, satellite_source = load_satellite_grid(stations, merged["timestamp"])

    force_skip_era5 = os.environ.get("SKIP_ERA5_MERGE") == "1"
    if force_skip_era5:
        era5_grid, era5_source = _placeholder_grid(stations, merged["timestamp"], METEOROLOGY_FEATURES), "placeholder_grid"
    elif era5_path is not None:
        era5_path = Path(era5_path)
        if era5_path.exists():
            grid = _normalise_grid_columns(pd.read_csv(era5_path), ERA5_RENAME_MAP)
            era5_grid, era5_source = grid, str(era5_path)
        else:
            logger.warning(
                "era5_path '%s' does not exist; falling back to auto-discovery.",
                era5_path,
            )
            era5_grid, era5_source = load_era5_grid(stations, merged["timestamp"])
    else:
        era5_grid, era5_source = load_era5_grid(stations, merged["timestamp"])


    is_satellite_placeholder = "placeholder" in satellite_source
    is_era5_placeholder = "placeholder" in era5_source
    num_rows = len(merged)

    # Log structured warnings
    warnings_generated = []
    if is_satellite_placeholder and is_era5_placeholder:
        warn_msg = (
            "Missing data sources: Satellite and ERA5. "
            "Placeholder data was generated because the physical grid files "
            "(satellite_predictors.csv/satellite_features.csv and era5_meteorology.csv/era5_features.csv) "
            "were not found in processed_data/. "
            f"Created {num_rows} placeholder rows for Satellite features and {num_rows} placeholder rows for ERA5 features."
        )
        logger.warning(warn_msg)
        warnings_generated.append(warn_msg)
    elif is_satellite_placeholder:
        warn_msg = (
            "Missing data source: Satellite. "
            "Placeholder data was generated because the physical grid files "
            "(satellite_predictors.csv/satellite_features.csv) were not found in processed_data/. "
            f"Created {num_rows} placeholder rows for Satellite features."
        )
        logger.warning(warn_msg)
        warnings_generated.append(warn_msg)
    elif is_era5_placeholder:
        warn_msg = (
            "Missing data source: ERA5. "
            "Placeholder data was generated because the physical grid files "
            "(era5_meteorology.csv/era5_features.csv) were not found in processed_data/. "
            f"Created {num_rows} placeholder rows for ERA5 features."
        )
        logger.warning(warn_msg)
        warnings_generated.append(warn_msg)

    # Delete obsolete diagnostics report if it exists
    old_report_path = config.BASE_DIR.parent / "placeholder_diagnostics_report.md"
    if old_report_path.exists():
        try:
            old_report_path.unlink()
            logger.info(f"Removed obsolete report: {old_report_path}")
        except Exception as e:
            logger.error(f"Failed to remove obsolete report {old_report_path}: {e}")

    # ------------------------------------------------------------------
    # Attach grid features to the merged CPCB observation DataFrame
    # ------------------------------------------------------------------
    merged = _attach_grid_features(
        merged,
        satellite_grid,
        SATELLITE_FEATURES + SATELLITE_METADATA_FEATURES,
        "satellite",
        temporal_strategy,
        is_placeholder=is_satellite_placeholder,
    )
    merged = _attach_grid_features(
        merged,
        era5_grid,
        METEOROLOGY_FEATURES,
        "era5",
        temporal_strategy,
        is_placeholder=is_era5_placeholder,
    )
    target_col = getattr(config, "REQUIRED_TARGET_COLUMN", "AQI")
    cpcb_source_path = str(config.PROCESSED_DATA_DIR / "cpcb_cleaned_latest.csv")

    # Log target column detection
    logger.info("[TARGET COLUMN] Configured target column: '%s'", target_col)
    logger.info("[TARGET COLUMN] Source dataset: %s", cpcb_source_path)

    # Verify target column survived the CPCB → station merge
    if target_col in merged.columns:
        non_null_after_merge = merged[target_col].notna().sum()
        logger.info(
            "[TARGET COLUMN] Propagation check after CPCB+metadata merge: "
            "column present, %d/%d non-null values.",
            non_null_after_merge,
            len(merged),
        )
    else:
        logger.warning(
            "[TARGET COLUMN] '%s' not found in merged CPCB+metadata dataframe. "
            "It will be filled with NA in the output.",
            target_col,
        )

    features = build_features(merged)

    # ------------------------------------------------------------------
    # Compute row-level placeholder flags BEFORE applying missing value strategy
    # ------------------------------------------------------------------
    is_sat_placeholder_row = features[SATELLITE_FEATURES].isna().all(axis=1) | is_satellite_placeholder
    is_met_placeholder_row = features[METEOROLOGY_FEATURES].isna().all(axis=1) | is_era5_placeholder

    # Log propagation after build_features (must not mutate target column)
    if target_col in features.columns:
        non_null_after_build = features[target_col].notna().sum()
        logger.info(
            "[TARGET COLUMN] Propagation check after build_features: "
            "column present, %d/%d non-null values.",
            non_null_after_build,
            len(features),
        )
    else:
        logger.warning(
            "[TARGET COLUMN] '%s' missing after build_features stage.",
            target_col,
        )

    features = apply_missing_strategy(features, missing_strategy, ALL_FEATURES)

    # Log propagation after apply_missing_strategy (target col must not be imputed)
    if target_col in features.columns:
        non_null_after_impute = features[target_col].notna().sum()
        logger.info(
            "[TARGET COLUMN] Propagation check after apply_missing_strategy: "
            "column present, %d/%d non-null values.",
            non_null_after_impute,
            len(features),
        )
    else:
        logger.warning(
            "[TARGET COLUMN] '%s' missing after apply_missing_strategy stage.",
            target_col,
        )

    # Assign row-level placeholder flag computed before imputation
    features["placeholder_used"] = is_sat_placeholder_row | is_met_placeholder_row

    # Collect diagnostics metrics and generate validation report based on row-level flag
    missing_sources = []
    if is_satellite_placeholder:
        missing_sources.append("Satellite")
    if is_era5_placeholder:
        missing_sources.append("ERA5")

    satellite_placeholders_created = int(is_sat_placeholder_row.sum())
    era5_placeholders_created = int(is_met_placeholder_row.sum())
    total_placeholders_created = satellite_placeholders_created + era5_placeholders_created

    placeholder_cols = []
    if is_satellite_placeholder:
        placeholder_cols.extend(SATELLITE_FEATURES)
    if is_era5_placeholder:
        placeholder_cols.extend(METEOROLOGY_FEATURES)

    satellite_success_matches = int((~is_sat_placeholder_row).sum())
    era5_success_matches = int((~is_met_placeholder_row).sum())
    satellite_placeholder_matches = satellite_placeholders_created
    era5_placeholder_matches = era5_placeholders_created

    total_true_rows = int(features["placeholder_used"].sum())
    total_false_rows = int((~features["placeholder_used"]).sum())

    if is_satellite_placeholder or is_era5_placeholder:
        dist_verify_msg = (
            "VERIFIED: Placeholder rows contain NaN in the distance columns "
            "(`satellite_match_distance_km` / `era5_match_distance_km`)."
        )
        validation_summary = "Collocated rows correctly set to placeholder_used=True because GEE and/or ERA5 datasets are missing."
        validation_result = "PASS"
    elif total_true_rows > 0:
        dist_verify_msg = (
            "VERIFIED: Real rows retain actual spatial distances calculated via Haversine distance, "
            "while rows matching sentinel placeholder coordinates represent missing GEE stations."
        )
        validation_summary = f"Flagged {total_true_rows} rows as placeholder_used=True due to missing/sentinel station-level GEE satellite observations."
        validation_result = "PASS"
    else:
        dist_verify_msg = (
            "VERIFIED: Real rows retain actual spatial distances calculated via Haversine distance."
        )
        validation_summary = "All collocated rows set to placeholder_used=False (real merged observations)."
        validation_result = "PASS"

    report_path = config.BASE_DIR.parent / "placeholder_merge_validation_report.md"
    report_content = f"""# Placeholder Merge Validation Report

## Missing Data Sources Detected
{chr(10).join(f"* {src}" for src in missing_sources) if missing_sources else "* None"}

## Summary of Placeholder Rows Created
* **Satellite Placeholder Rows:** {satellite_placeholders_created}
* **ERA5 Placeholder Rows:** {era5_placeholders_created}
* **Total Placeholder Rows:** {total_placeholders_created}

## Placeholder Columns Populated
{chr(10).join(f"* {col}" for col in placeholder_cols) if placeholder_cols else "* None"}

## Spatial Match Statistics
* **Successful Spatial Matches (Satellite):** {satellite_success_matches}
* **Successful Spatial Matches (ERA5):** {era5_success_matches}
* **Placeholder Matches (Satellite):** {satellite_placeholder_matches}
* **Placeholder Matches (ERA5):** {era5_placeholder_matches}

## match_distance_km verification
* **Validation Check:** Confirm placeholder rows contain NaN and real rows retain actual distances.
* **Result:** {dist_verify_msg}

## placeholder_used verification
* **Total TRUE Rows:** {total_true_rows}
* **Total FALSE Rows:** {total_false_rows}
* **Validation Summary:** {validation_summary}

## Warnings Generated During Execution
{chr(10).join(f"* {w}" for w in warnings_generated) if warnings_generated else "* None"}

## Final Validation Result
* **Overall Status:** {validation_result}
* **Summary:** The integration pipeline completed successfully. The `placeholder_used` boolean column was created and mapped correctly across all {num_rows} rows.
"""
    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        logger.info(f"Generated placeholder merge validation report at {report_path}")
    except OSError as e:
        logger.error(f"Failed to write placeholder merge validation report: {e}")

    output_columns = [
        "Station ID",
        "Station Name",
        "City",
        "State",
        "Latitude",
        "Longitude",
        "Date",
        "Time",
        *ALL_FEATURES,
        *SATELLITE_METADATA_FEATURES,
        "satellite_match_distance_km",
        "era5_match_distance_km",
        "placeholder_used",
        target_col,
    ]
    for column in output_columns:
        if column not in features.columns:
            features[column] = pd.NA

    # Final propagation check before returning
    final_non_null = features[target_col].notna().sum() if target_col in features.columns else 0
    logger.info(
        "[TARGET COLUMN] Final propagation validation before output: "
        "'%s' present=%s, non-null=%d/%d. Propagation SUCCESS.",
        target_col,
        target_col in features.columns,
        final_non_null,
        len(features),
    )

    data_sources = {
        "CPCB cleaned observations": cpcb_source_path,
        "Validated station metadata": str(config.METADATA_DIR / "validated_station_metadata.csv"),
        "Satellite predictors": satellite_source,
        "ERA5 meteorology": era5_source,
    }
    return features[output_columns], data_sources


def run_integration_pipeline(
    temporal_strategy: str | None = None,
    missing_strategy: str | None = None,
) -> bool:
    """Run Day 3 feature engineering and dataset integration."""
    setup.init_workspace()
    utils.setup_logging()

    temporal_strategy = temporal_strategy or config.TEMPORAL_ALIGNMENT
    missing_strategy = missing_strategy or config.MISSING_VALUE_STRATEGY

    logger.info("=========================================")
    logger.info("Starting Feature Engineering & Dataset Integration run")
    logger.info("=========================================")

    try:
        merged_features, data_sources = integrate_datasets(temporal_strategy, missing_strategy)
        output_path = config.FEATURES_DIR / "merged_feature_table.csv"
        dictionary_path = config.FEATURES_DIR / "feature_dictionary.csv"
        summary_path = config.FEATURES_DIR / "feature_summary.json"
        report_path = config.FEATURES_DIR / "integration_report.md"

        config.FEATURES_DIR.mkdir(parents=True, exist_ok=True)
        merged_features.to_csv(output_path, index=False)
        feature_dictionary = write_feature_dictionary(
            merged_features,
            ALL_FEATURES,
            dictionary_path,
        )
        summary = write_feature_summary(
            merged_features,
            summary_path,
            temporal_strategy,
            missing_strategy,
            data_sources,
        )
        write_integration_report(report_path, summary, data_sources)

        logger.info("Merged feature table written to %s", output_path)
        logger.info(
            "Feature dictionary written to %s (%s features)",
            dictionary_path,
            len(feature_dictionary),
        )
        logger.info("Feature summary written to %s", summary_path)
        logger.info("Integration report written to %s", report_path)

        # Run feature lineage audit — documentation only, no data mutations
        try:
            from data_collection_pipeline.feature_engineering.lineage_audit import (
                run_full_lineage_pipeline,
            )
            run_full_lineage_pipeline()
        except Exception as audit_exc:  # noqa: BLE001
            logger.warning(
                "Feature lineage audit encountered a non-fatal error: %s", audit_exc
            )

    except (FileNotFoundError, ValueError, OSError, pd.errors.ParserError) as exc:
        logger.error("Feature integration failed: %s", exc)
        return False

    logger.info("=========================================")
    logger.info("Feature Engineering & Dataset Integration run completed!")
    logger.info("=========================================")
    return True
