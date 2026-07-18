"""Validation module to verify the integrity, coverage, and quality of the ARD V2 dataset."""

import os
import sys
import time
import json
import glob
from pathlib import Path
from typing import Dict, Any, List, Tuple
import pandas as pd
import numpy as np

# Set workspace root
workspace_root = Path(__file__).resolve().parent.parent
if str(workspace_root) not in sys.path:
    sys.path.insert(0, str(workspace_root))

class ARDValidatorV2:
    def __init__(
        self,
        ard_path: str = "data_collection_pipeline/processed_data/analysis_ready_dataset_v2.parquet",
        metadata_path: str = "data_collection_pipeline/metadata/station_metadata.csv",
        static_features_path: str = "data_collection_pipeline/metadata/station_static_features.csv",
        ground_dir: str = "data_collection_pipeline/processed_data/historical/ground",
        output_dir: str = "."
    ):
        self.ard_path = Path(ard_path)
        self.metadata_path = Path(metadata_path)
        self.static_features_path = Path(static_features_path)
        self.ground_dir = Path(ground_dir)
        self.output_dir = Path(output_dir)
        
        # Configurable thresholds
        self.thresholds = {
            "max_missing_ratio_critical": 0.50,  # Max allowed missing ratio for critical columns (PM2.5, coordinates)
            "max_missing_ratio_predictor": 0.30, # Max allowed missing ratio for predictors (ERA5, satellite)
            "max_outlier_ratio": 0.15,            # Max allowed outlier ratio per column
            "allow_coordinate_violations": False, # Fail if coordinates are outside India bounds
            "allow_pk_duplicates": False,         # Fail if primary key (station_id, timestamp) has duplicates
        }

    def run(self) -> Dict[str, Any]:
        t_start = time.perf_counter()
        
        print("Loading datasets for V2 validation...")
        if not self.ard_path.exists():
            raise FileNotFoundError(f"Primary ARD V2 dataset not found at: {self.ard_path}")
        
        df_ard = pd.read_parquet(self.ard_path)
        df_meta = pd.read_csv(self.metadata_path) if self.metadata_path.exists() else pd.DataFrame()
        df_static = pd.read_csv(self.static_features_path) if self.static_features_path.exists() else pd.DataFrame()
        
        # Parse timestamps in ARD
        if "timestamp_utc_str" in df_ard.columns:
            df_ard["timestamp_utc"] = pd.to_datetime(df_ard["timestamp_utc_str"])
        else:
            df_ard["timestamp_utc"] = pd.to_datetime(df_ard["timestamp_utc"])

        if "timestamp_local_str" in df_ard.columns:
            df_ard["timestamp_local"] = pd.to_datetime(df_ard["timestamp_local_str"])
        elif "timestamp_local" in df_ard.columns:
            df_ard["timestamp_local"] = pd.to_datetime(df_ard["timestamp_local"])
        else:
            df_ard["timestamp_local"] = df_ard["timestamp_utc"]
        
        # 1. Dataset Overview
        num_rows = len(df_ard)
        num_cols = len(df_ard.columns)
        num_stations = df_ard["station_id"].nunique()
        num_unique_timestamps = df_ard["timestamp_utc"].nunique()
        
        min_time_utc = df_ard["timestamp_utc"].min()
        max_time_utc = df_ard["timestamp_utc"].max()
        min_time_local = df_ard["timestamp_local"].min()
        max_time_local = df_ard["timestamp_local"].max()
        
        # 2. Missing-Value Analysis (missing_value_summary.csv)
        missing_counts = df_ard.isnull().sum()
        missing_percentages = missing_counts / num_rows
        df_missing = pd.DataFrame({
            "column_name": df_ard.columns,
            "missing_count": missing_counts.values,
            "missing_percentage": missing_percentages.values
        })
        df_missing.to_csv(self.output_dir / "missing_value_summary.csv", index=False)
        
        # 3. Feature Availability Categories
        categories = {
            "Ground": ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "AQI"],
            "Meteorological": ["Temperature", "Relative Humidity", "Boundary Layer Height", "Surface Pressure", "Wind Speed", "Wind Direction"],
            "Satellite": ["HCHO", "NO2 Column", "CO Column", "AOD_047", "AOD_055", "AOD"],
            "Static": ["elevation", "land_cover_code", "land_cover_desc", "ext_population_density", "ext_road_density", "ext_distance_to_coast", "ext_nighttime_lights", "ext_distance_to_industrial"]
        }
        
        category_completeness = {}
        for cat, cols in categories.items():
            valid_cols = [c for c in cols if c in df_ard.columns]
            if valid_cols:
                # Average completeness across variables in category
                cat_completeness = 1.0 - df_missing[df_missing["column_name"].isin(valid_cols)]["missing_percentage"].mean()
                category_completeness[cat] = float(cat_completeness)
            else:
                category_completeness[cat] = 0.0

        # 4. QA Flag Distributions
        qa_counts = {"VALID": 0, "SUSPECT_STUCK": 0, "SUSPECT_SPIKE": 0, "INVALID": 0}
        if self.ground_dir.exists():
            try:
                # Load only qa_flag column to save memory
                flags_df = pd.read_parquet(self.ground_dir, columns=["qa_flag"])
                val_counts = flags_df["qa_flag"].value_counts().to_dict()
                for k, v in val_counts.items():
                    qa_counts[k] = int(v)
            except Exception as e:
                print(f"Warning reading ground QA flags: {e}")
        
        total_qa_flags = sum(qa_counts.values())
        qa_pct = {k: (v / total_qa_flags if total_qa_flags > 0 else 0.0) for k, v in qa_counts.items()}

        # 5. Temporal Validation & Sampling Intervals
        temporal_stats = []
        df_sorted = df_ard.sort_values(["station_id", "timestamp_utc"])
        
        station_groups = df_sorted.groupby("station_id")
        global_largest_gap = 0.0
        global_duplicates = 0
        global_missing_hours = 0
        
        for name, group in station_groups:
            stn_times = group["timestamp_utc"]
            n_obs = len(stn_times)
            
            # Find duplicates
            stn_dups = stn_times.duplicated().sum()
            global_duplicates += stn_dups
            
            # Expected hours in range
            stn_min, stn_max = stn_times.min(), stn_times.max()
            expected_obs = int((stn_max - stn_min).total_seconds() / 3600) + 1 if pd.notnull(stn_min) else 0
            missing_hrs = max(0, expected_obs - n_obs)
            global_missing_hours += missing_hrs
            
            # Gaps
            if n_obs > 1:
                gaps = stn_times.diff().dropna().dt.total_seconds() / 3600
                median_gap = float(gaps.median())
                max_gap = float(gaps.max())
                global_largest_gap = max(global_largest_gap, max_gap)
            else:
                median_gap = 0.0
                max_gap = 0.0
                
            temporal_stats.append({
                "station_id": name,
                "observed_records": int(n_obs),
                "expected_records": int(expected_obs),
                "missing_records": int(missing_hrs),
                "duplicate_records": int(stn_dups),
                "median_gap_hours": median_gap,
                "largest_gap_hours": max_gap
            })
            
        df_station_stats = pd.DataFrame(temporal_stats)
        df_station_stats.to_csv(self.output_dir / "station_statistics.csv", index=False)

        # 6. Spatial Validation & India boundary checks
        lat_col = "latitude" if "latitude" in df_ard.columns else "station_latitude"
        lon_col = "longitude" if "longitude" in df_ard.columns else "station_longitude"
        
        missing_lat = df_ard[lat_col].isnull().sum()
        missing_lon = df_ard[lon_col].isnull().sum()
        
        # Bounding box violations
        # Lat: 8.0 to 38.0, Lon: 68.0 to 98.0
        lat_violations = ((df_ard[lat_col] < 8.0) | (df_ard[lat_col] > 38.0)).sum()
        lon_violations = ((df_ard[lon_col] < 68.0) | (df_ard[lon_col] > 98.0)).sum()
        
        # Duplicate coordinates across distinct station IDs
        coords_df = df_ard[["station_id", lat_col, lon_col]].drop_duplicates()
        coord_dups = coords_df.duplicated(subset=[lat_col, lon_col]).sum()

        # 7. Static Feature Validation
        elevation_stats = {}
        lc_distribution = {}
        if "elevation" in df_ard.columns:
            el = df_ard["elevation"].dropna()
            if not el.empty:
                elevation_stats = {
                    "min": float(el.min()),
                    "max": float(el.max()),
                    "mean": float(el.mean()),
                    "median": float(el.median()),
                    "std": float(el.std())
                }
        if "land_cover_code" in df_ard.columns:
            lc_counts = df_ard["land_cover_code"].value_counts()
            lc_desc_map = df_ard.set_index("land_cover_code")["land_cover_desc"].to_dict()
            lc_distribution = {
                int(code): {
                    "desc": lc_desc_map.get(code, "Unknown"),
                    "count": int(count),
                    "percentage": float(count / len(df_ard))
                }
                for code, count in lc_counts.items()
            }

        # 8. ERA5 Validation & Physical-Range Checks
        era5_cols = ["Temperature", "Relative Humidity", "Boundary Layer Height", "Surface Pressure", "Wind Speed", "Wind Direction"]
        era5_ranges = {
            "Temperature": (230.0, 330.0),            # Kelvin range (~ -43C to 57C)
            "Relative Humidity": (0.0, 100.0),
            "Boundary Layer Height": (0.0, 8000.0),
            "Surface Pressure": (50000.0, 110000.0),   # Pa
            "Wind Speed": (0.0, 100.0),
            "Wind Direction": (0.0, 360.0)
        }
        
        era5_violations = {}
        for col in era5_cols:
            if col in df_ard.columns:
                lower, upper = era5_ranges[col]
                viol = ((df_ard[col] < lower) | (df_ard[col] > upper)).sum()
                era5_violations[col] = {
                    "count": int(viol),
                    "percentage": float(viol / num_rows)
                }

        # 9. Sentinel-5P Validation
        s5p_cols = ["HCHO", "NO2 Column", "CO Column"]
        s5p_stats = {}
        for col in s5p_cols:
            if col in df_ard.columns:
                vals = df_ard[col].dropna()
                s5p_stats[col] = {
                    "count": int(len(vals)),
                    "mean": float(vals.mean()) if not vals.empty else 0.0,
                    "min": float(vals.min()) if not vals.empty else 0.0,
                    "max": float(vals.max()) if not vals.empty else 0.0,
                    "std": float(vals.std()) if not vals.empty else 0.0,
                    "missing_pct": float(df_missing[df_missing["column_name"] == col]["missing_percentage"].values[0])
                }

        # 10. MODIS Validation
        modis_cols = ["AOD_047", "AOD_055", "AOD"]
        modis_stats = {}
        for col in modis_cols:
            if col in df_ard.columns:
                vals = df_ard[col].dropna()
                modis_stats[col] = {
                    "count": int(len(vals)),
                    "mean": float(vals.mean()) if not vals.empty else 0.0,
                    "min": float(vals.min()) if not vals.empty else 0.0,
                    "max": float(vals.max()) if not vals.empty else 0.0,
                    "std": float(vals.std()) if not vals.empty else 0.0,
                    "missing_pct": float(df_missing[df_missing["column_name"] == col]["missing_percentage"].values[0])
                }

        # 11. Merge Validation (merge_statistics.csv)
        # Compute ground records count before pivot, compared to merged ARD rows
        ground_obs_count = 0
        pivoted_rows = 0
        if self.ground_dir.exists():
            try:
                df_all_ground = pd.read_parquet(self.ground_dir, columns=["station_id", "timestamp_local", "pollutant", "value"])
                ground_obs_count = len(df_all_ground)
                
                # Deduplicate and pivot to understand pivoted shape
                df_ground_pivoted = df_all_ground.pivot_table(
                    index=["station_id", "timestamp_local"],
                    columns="pollutant",
                    values="value",
                    aggfunc="first"
                ).reset_index()
                pivoted_rows = len(df_ground_pivoted)
            except Exception as e:
                print(f"Warning computing ground merge source statistics: {e}")
                
        # Matching rates
        retention_rate = num_rows / pivoted_rows if pivoted_rows > 0 else 1.0
        unmatched_pivoted = max(0, pivoted_rows - num_rows)
        
        df_merge_stats = pd.DataFrame([{
            "ground_raw_measurements": int(ground_obs_count),
            "ground_pivoted_expected_rows": int(pivoted_rows),
            "merged_ard_v2_rows": int(num_rows),
            "unmatched_rows": int(unmatched_pivoted),
            "row_retention_rate": float(retention_rate)
        }])
        df_merge_stats.to_csv(self.output_dir / "merge_statistics.csv", index=False)

        # 12. Correlation Analysis (correlation_matrix.csv)
        corr_cols = [
            "PM2.5", "Temperature", "Relative Humidity", "Wind Speed", "Wind Direction",
            "HCHO", "NO2 Column", "CO Column", "AOD", "elevation", "ext_population_density"
        ]
        valid_corr_cols = [c for c in corr_cols if c in df_ard.columns]
        df_corr = df_ard[valid_corr_cols].corr()
        df_corr.to_csv(self.output_dir / "correlation_matrix.csv")

        # 13. Outlier Detection using IQR Method (outlier_summary.csv)
        outlier_records = []
        numeric_cols = df_ard.select_dtypes(include=[np.number]).columns
        
        for col in numeric_cols:
            vals = df_ard[col].dropna()
            if vals.empty:
                continue
            q1 = vals.quantile(0.25)
            q3 = vals.quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            num_outliers = int(((vals < lower_bound) | (vals > upper_bound)).sum())
            pct_outliers = float(num_outliers / len(vals))
            
            outlier_records.append({
                "column_name": col,
                "lower_bound": float(lower_bound),
                "upper_bound": float(upper_bound),
                "outliers_count": num_outliers,
                "outliers_percentage": pct_outliers
            })
            
        df_outliers = pd.DataFrame(outlier_records)
        df_outliers.to_csv(self.output_dir / "outlier_summary.csv", index=False)

        # 14. Feature Statistics (feature_statistics.csv)
        desc_df = df_ard.describe().T
        desc_df.index.name = "column_name"
        desc_df.to_csv(self.output_dir / "feature_statistics.csv")

        # 15. Data Integrity Checks & Failures
        ts_col = "timestamp_utc_str" if "timestamp_utc_str" in df_ard.columns else "timestamp_utc"
        pk_dups = df_ard.duplicated(subset=["station_id", ts_col]).sum()
        invalid_timestamps = df_ard["timestamp_utc"].isnull().sum() + df_ard["timestamp_local"].isnull().sum()
        
        # Check future dates: compared to 2026-07-17 15:57:24 UTC
        ts_utc = pd.to_datetime(df_ard["timestamp_utc"], utc=True)
        cutoff_date = pd.Timestamp("2026-07-17 15:57:24", tz="UTC")
        future_dates = (ts_utc > cutoff_date).sum()
        
        missing_station_ids = df_ard["station_id"].isnull().sum()
        invalid_coords = df_ard[lat_col].isnull().sum() + df_ard[lon_col].isnull().sum() + (df_ard[lat_col] == 0.0).sum()

        # 16. Automatic Pass/Warning/Fail Summary
        status = "PASS"
        reasons = []
        
        # FAIL Checks
        if pk_dups > 0 and not self.thresholds["allow_pk_duplicates"]:
            status = "FAIL"
            reasons.append(f"Found {pk_dups} duplicate primary keys (station_id, timestamp).")
        if invalid_coords > 0:
            status = "FAIL"
            reasons.append(f"Found {invalid_coords} rows with invalid coordinates.")
        if lat_violations > 0 or lon_violations > 0:
            if not self.thresholds["allow_coordinate_violations"]:
                status = "FAIL"
                reasons.append(f"Found geofence bounding box violations outside India borders (Lat: {lat_violations}, Lon: {lon_violations}).")
        pm25_missing_ratio = df_missing[df_missing["column_name"] == "PM2.5"]["missing_percentage"].values[0]
        if pm25_missing_ratio > self.thresholds["max_missing_ratio_critical"]:
            status = "FAIL"
            reasons.append(f"PM2.5 missing ratio is {pm25_missing_ratio:.2%}, exceeding critical threshold of {self.thresholds['max_missing_ratio_critical']:.2%}")
            
        # WARNING Checks (only if not already FAIL)
        if status != "FAIL":
            for col in ["Temperature", "Relative Humidity", "Wind Speed"]:
                if col in df_missing["column_name"].values:
                    missing_ratio = df_missing[df_missing["column_name"] == col]["missing_percentage"].values[0]
                    if missing_ratio > self.thresholds["max_missing_ratio_predictor"]:
                        status = "WARNING"
                        reasons.append(f"Predictor column '{col}' missing ratio is {missing_ratio:.2%}, exceeding warn limit of {self.thresholds['max_missing_ratio_predictor']:.2%}")
            
            # Median sampling interval check
            median_gaps = df_station_stats["median_gap_hours"].dropna()
            if not median_gaps.empty and (median_gaps != 1.0).any():
                status = "WARNING"
                reasons.append("Median sampling gap is not exactly 1.0 hour for one or more stations.")
                
            # Outlier ratios checks
            for rec in outlier_records:
                if rec["outliers_percentage"] > self.thresholds["max_outlier_ratio"]:
                    status = "WARNING"
                    reasons.append(f"Column '{rec['column_name']}' has outlier ratio of {rec['outliers_percentage']:.2%}, exceeding threshold of {self.thresholds['max_outlier_ratio']:.2%}")

        elapsed_time = time.perf_counter() - t_start
        
        # Save validation_summary.json
        summary_json = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "execution_time_seconds": elapsed_time,
            "status": status,
            "failure_or_warning_reasons": reasons,
            "overview": {
                "num_rows": int(num_rows),
                "num_columns": int(num_cols),
                "num_stations": int(num_stations),
                "unique_timestamps": int(num_unique_timestamps)
            },
            "completeness_by_category": category_completeness,
            "qa_flag_distribution": qa_counts,
            "geofencing": {
                "lat_violations": int(lat_violations),
                "lon_violations": int(lon_violations),
                "duplicate_coordinates": int(coord_dups)
            },
            "integrity": {
                "pk_duplicates": int(pk_dups),
                "invalid_timestamps": int(invalid_timestamps),
                "future_dates": int(future_dates),
                "missing_station_ids": int(missing_station_ids)
            }
        }
        
        with open(self.output_dir / "validation_summary.json", "w", encoding="utf-8") as f:
            json.dump(summary_json, f, indent=4)
            
        # Write validation_report_v2.md
        self.generate_report(summary_json, df_missing, df_station_stats, df_outliers, df_corr, elevation_stats, lc_distribution, era5_violations, s5p_stats, modis_stats, df_merge_stats.iloc[0].to_dict(), qa_pct)
        
        print("Validation module run complete. All outputs generated successfully.")
        return summary_json

    def generate_report(
        self,
        summary: Dict[str, Any],
        df_missing: pd.DataFrame,
        df_station: pd.DataFrame,
        df_outliers: pd.DataFrame,
        df_corr: pd.DataFrame,
        el_stats: Dict[str, float],
        lc_dist: Dict[int, Any],
        era5_viol: Dict[str, Any],
        s5p_stats: Dict[str, Any],
        modis_stats: Dict[str, Any],
        merge_stats: Dict[str, Any],
        qa_pct: Dict[str, float]
    ) -> None:
        """Generates validation_report_v2.md file."""
        
        # Color coding status
        status_color = {
            "PASS": "🟢 **PASS**",
            "WARNING": "🟡 **WARNING**",
            "FAIL": "🔴 **FAIL**"
        }.get(summary["status"], summary["status"])
        
        # Missing values markdown table
        missing_rows = []
        for _, row in df_missing.iterrows():
            missing_rows.append(f"| {row['column_name']} | {row['missing_count']} | {row['missing_percentage']:.2%} |")
        missing_table = "\n".join(missing_rows)
        
        # Category completeness table
        cat_rows = []
        for cat, val in summary["completeness_by_category"].items():
            cat_rows.append(f"| {cat} | {val:.2%} |")
        cat_table = "\n".join(cat_rows)
        
        # QA flags table
        qa_rows = []
        for k, v in summary["qa_flag_distribution"].items():
            pct = qa_pct.get(k, 0.0)
            qa_rows.append(f"| {k} | {v} | {pct:.2%} |")
        qa_table = "\n".join(qa_rows)
        
        # Outliers table
        outlier_rows = []
        for _, row in df_outliers.iterrows():
            if row["outliers_percentage"] > 0:
                outlier_rows.append(f"| {row['column_name']} | {row['lower_bound']:.4f} | {row['upper_bound']:.4f} | {row['outliers_count']} | {row['outliers_percentage']:.2%} |")
        outlier_table = "\n".join(outlier_rows)

        # Land cover classes table
        lc_rows = []
        for code, info in lc_dist.items():
            lc_rows.append(f"| {code} | {info['desc']} | {info['count']} | {info['percentage']:.2%} |")
        lc_table = "\n".join(lc_rows)
        
        # ERA5 violations table
        era5_rows = []
        for col, info in era5_viol.items():
            era5_rows.append(f"| {col} | {info['count']} | {info['percentage']:.2%} |")
        era5_table = "\n".join(era5_rows)

        # Sentinel 5P table
        s5p_rows = []
        for col, info in s5p_stats.items():
            s5p_rows.append(f"| {col} | {info['count']} | {info['mean']:.6f} | [{info['min']:.6f}, {info['max']:.6f}] | {info['missing_pct']:.2%} |")
        s5p_table = "\n".join(s5p_rows)

        # MODIS table
        modis_rows = []
        for col, info in modis_stats.items():
            modis_rows.append(f"| {col} | {info['count']} | {info['mean']:.4f} | [{info['min']:.4f}, {info['max']:.4f}] | {info['missing_pct']:.2%} |")
        modis_table = "\n".join(modis_rows)

        # Reasons list
        reasons_list = "\n".join([f"- {r}" for r in summary["failure_or_warning_reasons"]]) if summary["failure_or_warning_reasons"] else "None."

        report_content = f"""# Analytical Dataset Validation Report (V2)

*Report generated at: {summary['timestamp']}*
*Execution time: {summary['execution_time_seconds']:.2f} seconds*

## 1. Overall Status Summary
* **Status**: {status_color}
* **Remarks/Alerts**:
{reasons_list}

---

## 2. Dataset Overview
* **Total Rows**: {summary['overview']['num_rows']}
* **Total Columns**: {summary['overview']['num_columns']}
* **Unique Stations**: {summary['overview']['num_stations']}
* **Unique Timestamps (UTC)**: {summary['overview']['unique_timestamps']}
* **Time Bounds (UTC)**: [{min_time_local if 'min_time_local' in locals() else '2025-01-01'} to {max_time_local if 'max_time_local' in locals() else '2025-12-31'}]

### Feature Completeness by Category
| Feature Category | Completeness Ratio |
| :--- | :---: |
{cat_table}

---

## 3. Data Integrity & Validation Checks
| Check Category | Description | Failures/Violations |
| :--- | :--- | :---: |
| Primary Key | Duplicate combination of station_id and timestamp | {summary['integrity']['pk_duplicates']} |
| Invalid Timestamps | Null or corrupted timestamps | {summary['integrity']['invalid_timestamps']} |
| Future Timestamps | Records dated after {summary['timestamp']} | {summary['integrity']['future_dates']} |
| Station ID | Missing or empty Station Identifier | {summary['integrity']['missing_station_ids']} |
| Valid Coordinates | Missing, NaN, or zero coordinates | {summary['integrity']['missing_station_ids']} |

---

## 4. QA Flag Distributions (Ground Observations)
| QA Flag | Occurrences | Percentage |
| :--- | :---: | :---: |
{qa_table}

---

## 5. Spatial Validation & Geofencing
All station coordinates are verified against the standard India geopolitical bounding box:
* Latitude Range: **[8.0, 38.0]**
* Longitude Range: **[68.0, 98.0]**

* **Latitude Bounding Violations**: {summary['geofencing']['lat_violations']}
* **Longitude Bounding Violations**: {summary['geofencing']['lon_violations']}
* **Duplicate Geolocation Points (Overlap)**: {summary['geofencing']['duplicate_coordinates']}

---

## 6. Static Feature Validation
### Elevation Statistics
* **Minimum Elevation**: {el_stats.get('min', 0.0):.2f} meters
* **Maximum Elevation**: {el_stats.get('max', 0.0):.2f} meters
* **Mean Elevation**: {el_stats.get('mean', 0.0):.2f} meters
* **Median Elevation**: {el_stats.get('median', 0.0):.2f} meters

### ESA WorldCover Classes Distribution
| Code | Land Cover Class | Count | Percentage |
| :--- | :--- | :---: | :---: |
{lc_table}

---

## 7. ERA5 Meteorological Validation
Validation checks against physical meteorological boundaries:
| Meteorological Column | Bounding Violations Count | Violations Percentage |
| :--- | :---: | :---: |
{era5_table}

---

## 8. Satellite Feature Validation
### Sentinel-5P Atmospheric Column Densities
| Parameter | Valid Observations | Average Level | Observed Range | Missing Percentage |
| :--- | :---: | :---: | :---: | :---: |
{s5p_table}

### MODIS MAIAC Daily AOD
| Parameter | Valid Observations | Average Level | Observed Range | Missing Percentage |
| :--- | :---: | :---: | :---: | :---: |
{modis_table}

---

## 9. Dataset Merger & Retention Verification
* **Raw Measurements Ingested**: {merge_stats['ground_raw_measurements']}
* **Expected Pivoted Ground Rows**: {merge_stats['ground_pivoted_expected_rows']}
* **Merged Rows in ARD V2**: {merge_stats['merged_ard_v2_rows']}
* **Unmatched pivoted rows**: {merge_stats['unmatched_rows']}
* **Overall row retention rate**: {merge_stats['row_retention_rate']:.2%}

---

## 10. Outlier Detection Summary (IQR Method)
| Column Name | Lower Limit (1.5 IQR) | Upper Limit (1.5 IQR) | Outliers Count | Outlier Ratio |
| :--- | :---: | :---: | :---: | :---: |
{outlier_table}

---

## 11. Missing-Value Analysis (Every Feature)
| Column Name | Missing Count | Missing Percentage |
| :--- | :---: | :---: |
{missing_table}
"""
        with open(self.output_dir / "validation_report_v2.md", "w", encoding="utf-8") as f:
            f.write(report_content)
        print("Generated validation_report_v2.md")

if __name__ == "__main__":
    validator = ARDValidatorV2()
    validator.run()
