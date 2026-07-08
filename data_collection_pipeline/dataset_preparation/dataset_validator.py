import logging
import datetime
from pathlib import Path
from typing import Dict, Any, List, Union, Optional
import pandas as pd
import numpy as np

from data_collection_pipeline import config
from data_collection_pipeline.utils import logger

# Required columns for the merged feature table
REQUIRED_COLUMNS: List[str] = [
    "Station ID",
    "Station Name",
    "City",
    "State",
    "Latitude",
    "Longitude",
    "Date",
    "Time",
    "PM2.5",
    "PM10",
    "NO2",
    "SO2",
    "CO",
    "O3"
]

# Expected columns (including meteorological/satellite variables and derived metrics)
EXPECTED_COLUMNS: List[str] = REQUIRED_COLUMNS + [
    "Temperature",
    "Relative Humidity",
    "Boundary Layer Height",
    "Wind Speed",
    "Wind Direction",
    "Surface Pressure",
    "AOD",
    "HCHO",
    "NO2 Column",
    "SO2 Column",
    "CO Column",
    "O3 Column",
    "Day of Week",
    "Month",
    "Season",
    "Weekend Flag",
    "satellite_match_distance_km",
    "era5_match_distance_km"
]


def validate_required_columns(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validates if all required columns are present in the DataFrame.
    
    Args:
        df: The pandas DataFrame representing the merged feature table.
        
    Returns:
        A dictionary summarizing the column presence validation.
    """
    logger.info("Validating required columns...")
    missing_required = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    missing_expected = [col for col in EXPECTED_COLUMNS if col not in df.columns and col not in REQUIRED_COLUMNS]
    
    status = "PASSED"
    if missing_required:
        status = "FAILED"
        logger.error(f"Missing required columns: {missing_required}")
    elif missing_expected:
        status = "WARNING"
        logger.warning(f"Missing expected columns (non-critical): {missing_expected}")
    else:
        logger.info("All required and expected columns are present.")
        
    return {
        "status": status,
        "missing_required": missing_required,
        "missing_expected": missing_expected
    }


def validate_dtypes(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validates that the columns have correct and consistent data types.
    
    Args:
        df: The pandas DataFrame representing the merged feature table.
        
    Returns:
        A dictionary summarizing the data type validation.
    """
    logger.info("Validating column data types...")
    mismatches: Dict[str, Dict[str, str]] = {}
    
    numeric_cols = [
        "Latitude", "Longitude", "PM2.5", "PM10", "NO2", "SO2", "CO", "O3",
        "Temperature", "Relative Humidity", "Boundary Layer Height", "Wind Speed",
        "Wind Direction", "Surface Pressure", "AOD", "HCHO", "NO2 Column",
        "SO2 Column", "CO Column", "O3 Column", "Day of Week", "Month",
        "satellite_match_distance_km", "era5_match_distance_km"
    ]
    
    string_cols = ["Station ID", "Station Name", "City", "State", "Date", "Time", "Season"]
    bool_cols = ["Weekend Flag"]
    
    for col in df.columns:
        if col in numeric_cols:
            if not pd.api.types.is_numeric_dtype(df[col]):
                mismatches[col] = {
                    "expected": "numeric",
                    "actual": str(df[col].dtype)
                }
        elif col in string_cols:
            # Strings in pandas are typically of object or string dtype
            if not (pd.api.types.is_object_dtype(df[col]) or pd.api.types.is_string_dtype(df[col])):
                mismatches[col] = {
                    "expected": "string/object",
                    "actual": str(df[col].dtype)
                }
        elif col in bool_cols:
            if not (pd.api.types.is_bool_dtype(df[col]) or pd.api.types.is_numeric_dtype(df[col])):
                mismatches[col] = {
                    "expected": "boolean/numeric",
                    "actual": str(df[col].dtype)
                }
                
    status = "PASSED"
    if mismatches:
        status = "FAILED"
        logger.error(f"Data type mismatches found: {mismatches}")
    else:
        logger.info("All column data types are consistent.")
        
    return {
        "status": status,
        "mismatches": mismatches
    }


def validate_missing_values(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Checks for missing values across all columns of the dataset.
    
    Args:
        df: The pandas DataFrame representing the merged feature table.
        
    Returns:
        A dictionary summarizing the missing values analysis.
    """
    logger.info("Validating missing values...")
    missing_summary: Dict[str, Dict[str, Any]] = {}
    critical_columns = ["Station ID", "Latitude", "Longitude", "Date", "Time"]
    critical_missing: List[str] = []
    
    total_rows = len(df)
    
    for col in df.columns:
        missing_count = int(df[col].isna().sum())
        missing_pct = (missing_count / total_rows * 100.0) if total_rows > 0 else 0.0
        missing_summary[col] = {
            "count": missing_count,
            "percentage": round(missing_pct, 4)
        }
        
        if col in critical_columns and missing_count > 0:
            critical_missing.append(col)
            
    status = "PASSED"
    if critical_missing:
        status = "FAILED"
        logger.error(f"Critical columns have missing values: {critical_missing}")
    else:
        # Check for high missing rates (> 20%) in non-placeholder columns
        # Meteorological and Satellite variables might be empty placeholders (100% missing) by design
        placeholder_cols = [
            "Temperature", "Relative Humidity", "Boundary Layer Height", "Wind Speed",
            "Wind Direction", "Surface Pressure", "AOD", "HCHO", "NO2 Column",
            "SO2 Column", "CO Column", "O3 Column"
        ]
        high_missing_non_placeholder = []
        for col, stats in missing_summary.items():
            if col not in placeholder_cols and stats["percentage"] > 20.0:
                high_missing_non_placeholder.append(col)
                
        if high_missing_non_placeholder:
            status = "WARNING"
            logger.warning(f"High missing values (>20%) in non-placeholder columns: {high_missing_non_placeholder}")
            
    return {
        "status": status,
        "critical_missing_columns": critical_missing,
        "missing_summary": missing_summary
    }


def validate_duplicate_rows(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Checks for completely identical rows in the dataset.
    
    Args:
        df: The pandas DataFrame representing the merged feature table.
        
    Returns:
        A dictionary summarizing the duplicate rows check.
    """
    logger.info("Validating duplicate rows...")
    duplicate_count = int(df.duplicated().sum())
    
    status = "PASSED"
    if duplicate_count > 0:
        status = "FAILED"
        logger.error(f"Found {duplicate_count} duplicate rows in the dataset.")
    else:
        logger.info("No duplicate rows found.")
        
    return {
        "status": status,
        "duplicate_count": duplicate_count
    }


def validate_duplicate_station_time(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Checks if there are multiple entries for the same station at the same timestamp (Date + Time).
    
    Args:
        df: The pandas DataFrame representing the merged feature table.
        
    Returns:
        A dictionary summarizing the duplicate station-time records check.
    """
    logger.info("Validating duplicate station-time records...")
    
    check_cols: List[str] = []
    if "Station ID" in df.columns:
        check_cols.append("Station ID")
    elif "Station Name" in df.columns:
        check_cols.append("Station Name")
        
    if "Date" in df.columns:
        check_cols.append("Date")
    if "Time" in df.columns:
        check_cols.append("Time")
        
    status = "PASSED"
    duplicate_count = 0
    duplicate_keys: List[Dict[str, Any]] = []
    
    if len(check_cols) >= 2:
        duplicates = df[df.duplicated(subset=check_cols, keep=False)]
        duplicate_count = int(df.duplicated(subset=check_cols).sum())
        if duplicate_count > 0:
            status = "FAILED"
            logger.error(f"Found {duplicate_count} duplicate station-time combinations using subset {check_cols}.")
            # Extract sample of duplicated keys
            dup_keys_df = duplicates[check_cols].drop_duplicates()
            duplicate_keys = dup_keys_df.to_dict(orient="records")
        else:
            logger.info("No duplicate station-time combinations found.")
    else:
        status = "WARNING"
        logger.warning(f"Could not perform duplicate station-time check due to missing columns. Checked subset: {check_cols}")
        
    return {
        "status": status,
        "duplicate_count": duplicate_count,
        "duplicate_keys_sample": duplicate_keys[:10]
    }


def validate_timestamps(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validates that the Date and Time fields are correctly formatted and chronological (not in future).
    
    Args:
        df: The pandas DataFrame representing the merged feature table.
        
    Returns:
        A dictionary summarizing the timestamp validation.
    """
    logger.info("Validating timestamps...")
    invalid_dates_count = 0
    invalid_times_count = 0
    future_timestamps_count = 0
    
    invalid_dates: List[Dict[str, Any]] = []
    invalid_times: List[Dict[str, Any]] = []
    future_timestamps: List[Dict[str, Any]] = []
    
    now = datetime.datetime.now()
    
    for idx, row in df.iterrows():
        date_val = row.get("Date")
        time_val = row.get("Time")
        
        parsed_date = None
        parsed_time = None
        
        # 1. Validate Date (Expected YYYY-MM-DD)
        if pd.isna(date_val):
            invalid_dates_count += 1
            invalid_dates.append({"row_index": idx, "value": date_val, "reason": "Missing Date"})
        else:
            try:
                date_str = str(date_val).strip()
                parsed_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                invalid_dates_count += 1
                invalid_dates.append({"row_index": idx, "value": date_val, "reason": "Invalid YYYY-MM-DD format"})
                
        # 2. Validate Time (Expected HH:MM:SS)
        if pd.isna(time_val):
            invalid_times_count += 1
            invalid_times.append({"row_index": idx, "value": time_val, "reason": "Missing Time"})
        else:
            try:
                time_str = str(time_val).strip()
                parsed_time = datetime.datetime.strptime(time_str, "%H:%M:%S").time()
            except ValueError:
                invalid_times_count += 1
                invalid_times.append({"row_index": idx, "value": time_val, "reason": "Invalid HH:MM:SS format"})
                
        # 3. Check for future timestamp (allowing a small 1-hour grace window)
        if parsed_date and parsed_time:
            dt = datetime.datetime.combine(parsed_date, parsed_time)
            if dt > now + datetime.timedelta(hours=1):
                future_timestamps_count += 1
                future_timestamps.append({
                    "row_index": idx,
                    "date": str(date_val),
                    "time": str(time_val),
                    "reason": "Timestamp is in the future relative to system time"
                })
                
    status = "PASSED"
    if invalid_dates_count > 0 or invalid_times_count > 0 or future_timestamps_count > 0:
        status = "FAILED"
        logger.error(
            f"Timestamp validation failed: {invalid_dates_count} invalid dates, "
            f"{invalid_times_count} invalid times, {future_timestamps_count} future timestamps."
        )
    else:
        logger.info("All timestamps are valid.")
        
    return {
        "status": status,
        "invalid_dates_count": invalid_dates_count,
        "invalid_times_count": invalid_times_count,
        "future_timestamps_count": future_timestamps_count,
        "invalid_dates_sample": invalid_dates[:5],
        "invalid_times_sample": invalid_times[:5],
        "future_timestamps_sample": future_timestamps[:5]
    }


def validate_coordinates(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Validates that Latitude and Longitude values are physical and within expected bounds.
    
    Args:
        df: The pandas DataFrame representing the merged feature table.
        
    Returns:
        A dictionary summarizing the coordinate validation.
    """
    logger.info("Validating coordinates...")
    invalid_coords_count = 0
    outside_india_count = 0
    
    invalid_coords: List[Dict[str, Any]] = []
    outside_india: List[Dict[str, Any]] = []
    
    for idx, row in df.iterrows():
        lat = row.get("Latitude")
        lon = row.get("Longitude")
        
        if pd.isna(lat) or pd.isna(lon):
            invalid_coords_count += 1
            invalid_coords.append({"row_index": idx, "lat": lat, "lon": lon, "reason": "Missing coordinate"})
            continue
            
        try:
            lat_val = float(lat)
            lon_val = float(lon)
            
            # Check physical bounds: Latitude [-90, 90], Longitude [-180, 180]
            if not (-90.0 <= lat_val <= 90.0) or not (-180.0 <= lon_val <= 180.0):
                invalid_coords_count += 1
                invalid_coords.append({
                    "row_index": idx,
                    "lat": lat_val,
                    "lon": lon_val,
                    "reason": "Outside physical limits (-90 to 90 lat, -180 to 180 lon)"
                })
                continue
                
            # Check India bounding box: Latitude [6.0, 38.0], Longitude [68.0, 98.0]
            lat_min, lat_max = 6.0, 38.0
            lon_min, lon_max = 68.0, 98.0
            
            if not (lat_min <= lat_val <= lat_max) or not (lon_min <= lon_val <= lon_max):
                outside_india_count += 1
                outside_india.append({
                    "row_index": idx,
                    "lat": lat_val,
                    "lon": lon_val,
                    "reason": "Outside bounding box covering India (6-38 lat, 68-98 lon)"
                })
        except (ValueError, TypeError):
            invalid_coords_count += 1
            invalid_coords.append({"row_index": idx, "lat": lat, "lon": lon, "reason": "Non-numeric coordinate value"})
            
    status = "PASSED"
    if invalid_coords_count > 0:
        status = "FAILED"
        logger.error(f"Coordinate validation failed: {invalid_coords_count} invalid coordinates.")
    elif outside_india_count > 0:
        status = "WARNING"
        logger.warning(f"Coordinate warning: {outside_india_count} records fall outside India's bounding box.")
    else:
        logger.info("All coordinates are valid.")
        
    return {
        "status": status,
        "invalid_coords_count": invalid_coords_count,
        "outside_india_count": outside_india_count,
        "invalid_coords_sample": invalid_coords[:5],
        "outside_india_sample": outside_india[:5]
    }


def validate_merged_table(file_path: Optional[Union[str, Path]] = None) -> Dict[str, Any]:
    """
    Reads the merged feature table and runs all validation checks on it.
    
    Args:
        file_path: Optional path to the merged feature table CSV. If None,
                   uses config.FEATURES_DIR / "merged_feature_table.csv".
                   
    Returns:
        A comprehensive validation summary dictionary.
    """
    if file_path is None:
        file_path = config.FEATURES_DIR / "merged_feature_table.csv"
    else:
        file_path = Path(file_path)
        
    logger.info(f"Initiating full dataset validation on: {file_path}")
    
    if not file_path.exists():
        msg = f"Merged feature table file not found: {file_path}"
        logger.error(msg)
        return {
            "validation_passed": False,
            "error": msg,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
    try:
        df = pd.read_csv(file_path)
    except Exception as e:
        msg = f"Failed to parse merged feature table CSV: {e}"
        logger.error(msg)
        return {
            "validation_passed": False,
            "error": msg,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
    logger.info(f"Successfully loaded dataset with {len(df)} rows and {len(df.columns)} columns.")
    
    # Execute validation routines
    req_cols_res = validate_required_columns(df)
    dtypes_res = validate_dtypes(df)
    missing_vals_res = validate_missing_values(df)
    duplicate_rows_res = validate_duplicate_rows(df)
    dup_station_time_res = validate_duplicate_station_time(df)
    timestamps_res = validate_timestamps(df)
    coords_res = validate_coordinates(df)
    
    results = [
        req_cols_res,
        dtypes_res,
        missing_vals_res,
        duplicate_rows_res,
        dup_station_time_res,
        timestamps_res,
        coords_res
    ]
    
    overall_status = "PASSED"
    if any(res["status"] == "FAILED" for res in results):
        overall_status = "FAILED"
    elif any(res["status"] == "WARNING" for res in results):
        overall_status = "WARNING"
        
    logger.info(f"Overall validation status: {overall_status}")
    
    return {
        "dataset_name": file_path.name,
        "dataset_path": str(file_path.resolve()),
        "validation_status": overall_status,
        "timestamp": datetime.datetime.now().isoformat(),
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "checks": {
            "required_columns": req_cols_res,
            "dtypes": dtypes_res,
            "missing_values": missing_vals_res,
            "duplicate_rows": duplicate_rows_res,
            "duplicate_station_time": dup_station_time_res,
            "timestamps": timestamps_res,
            "coordinates": coords_res
        }
    }
