import logging
import json
import requests
import pandas as pd
from typing import Optional, Dict, List
import datetime
import random
from data_collection_pipeline import config, utils

logger = logging.getLogger("data_collection_pipeline.openaq")

def fetch_openaq_raw(
    limit: int = 1000,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Optional[pd.DataFrame]:
    """
    Fetches raw measurements for country=IN from the OpenAQ API.
    Sends API keys in headers if provided.
    Safely handles nested JSON keys, null coordinates, null timestamps,
    and malformed responses.

    Parameters
    ----------
    limit:
        Maximum number of records to request per API call.
    date_from:
        Optional ISO-8601 date string (``YYYY-MM-DD``) restricting the start
        of the measurement window.  When ``None`` the API applies its own
        default (typically the last 24 h).
    date_to:
        Optional ISO-8601 date string (``YYYY-MM-DD``) restricting the end of
        the measurement window.  When ``None`` the API applies its own default.
    """
    if not config.OPENAQ_API_KEY:
        logger.warning("OPENAQ_API_KEY not found. Proceeding without API key (rate limits will apply).")

    headers = {}
    if config.OPENAQ_API_KEY:
        headers["X-API-Key"] = config.OPENAQ_API_KEY

    params = {
        "country": "IN",
        "limit": limit,
    }
    if date_from is not None:
        params["date_from"] = date_from
    if date_to is not None:
        params["date_to"] = date_to
    
    response = utils.safe_request(config.OPENAQ_BASE_URL, params=params, headers=headers)
    if response is None:
        logger.error("Failed to fetch OpenAQ data from API (no response).")
        return None
        
    try:
        data = response.json()
        
        # Safely handle when response is not a dict
        if not isinstance(data, dict):
            logger.error("OpenAQ API response is not a valid JSON object/dictionary.")
            return None
            
        results = data.get("results")
        if not isinstance(results, list):
            logger.error("OpenAQ API response 'results' key is missing or not a list.")
            return None
            
        if not results:
            logger.warning("OpenAQ API returned an empty results list.")
            return None
            
        # Flattening nested coordinates and dates with high safety checks
        flattened_results = []
        for index, r in enumerate(results):
            if not isinstance(r, dict):
                logger.warning(f"Record at index {index} is not a valid dictionary. Skipping.")
                continue
                
            location_id = r.get("locationId")
            location = r.get("location")
            country = r.get("country")
            city = r.get("city")
            parameter = r.get("parameter")
            value = r.get("value")
            unit = r.get("unit")
            
            # Skip records that lack essential keys for pivot and indexing
            if location is None or parameter is None or value is None:
                logger.debug(f"Skipping record {index} due to null location, parameter, or value.")
                continue
            
            # Safe nested access for coordinates
            coords = r.get("coordinates")
            if isinstance(coords, dict):
                latitude = coords.get("latitude")
                longitude = coords.get("longitude")
            else:
                latitude = None
                longitude = None
                
            # Safe nested access for dates
            date_info = r.get("date")
            if isinstance(date_info, dict):
                utc_time = date_info.get("utc")
                local_time = date_info.get("local")
            else:
                utc_time = None
                local_time = None
                
            flat_rec = {
                "location_id": location_id,
                "location": location,
                "country": country,
                "city": city,
                "latitude": latitude,
                "longitude": longitude,
                "timestamp_utc": utc_time,
                "timestamp_local": local_time,
                "parameter": parameter,
                "value": value,
                "unit": unit
            }
            flattened_results.append(flat_rec)
            
        if not flattened_results:
            logger.warning("No records remained after parsing and filtering malformed OpenAQ data.")
            return None
            
        return pd.DataFrame(flattened_results)
        
    except json.JSONDecodeError as e:
        logger.error(f"Malformed API response: JSON decode error in OpenAQ output: {e}")
        return None
    except ValueError as e:
        logger.error(f"ValueError parsing OpenAQ response: {e}")
        return None
    except KeyError as e:
        logger.error(f"Missing expected keys in OpenAQ response structure: {e}")
        return None

def process_openaq_records(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Pivots the raw OpenAQ long format data to make columns for each parameter.
    Ensures safe handling of potential nulls in pivoted columns.
    """
    required_cols = {"location", "city", "country", "latitude", "longitude", "timestamp_utc", "parameter", "value"}
    if not required_cols.issubset(df_raw.columns):
        logger.error(f"OpenAQ raw data missing required columns for pivoting: {required_cols - set(df_raw.columns)}")
        return df_raw

    # Robust timestamp parsing to prevent NaT propagation
    df_raw["timestamp_utc"] = pd.to_datetime(df_raw["timestamp_utc"], utc=True, errors="coerce")
    df_raw = df_raw.dropna(subset=["timestamp_utc"])

    # Pivot to put parameter values in separate columns
    pivoted = df_raw.pivot_table(
        index=["location", "city", "country", "latitude", "longitude", "timestamp_utc", "timestamp_local"],
        columns="parameter",
        values="value",
        aggfunc="first"
    ).reset_index()
    
    # Map OpenAQ parameters to standard CPCB parameter names where possible
    rename_map = {
        "pm25": "PM2.5",
        "pm10": "PM10",
        "no2": "NO2",
        "so2": "SO2",
        "co": "CO",
        "o3": "O3"
    }
    pivoted.rename(columns=rename_map, inplace=True)
    
    # Ensure all standard columns exist
    for col in ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3"]:
        if col not in pivoted.columns:
            pivoted[col] = None
            
    return pivoted



def collect_openaq_data(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> pd.DataFrame:
    """
    Main function to orchestrate OpenAQ data collection.
    Tries fetching from the API first; falls back to mock data if unsuccessful.

    Parameters
    ----------
    date_from:
        Optional ISO-8601 date string (``YYYY-MM-DD``) for the start of the
        measurement window.  ``None`` uses the API default (last 24 h).
    date_to:
        Optional ISO-8601 date string (``YYYY-MM-DD``) for the end of the
        measurement window.  ``None`` uses the API default.
    """
    logger.info("Starting OpenAQ Air Quality data collection...")
    if not date_from and not date_to:
        df_raw = fetch_openaq_raw(date_from=date_from, date_to=date_to)
        if df_raw is not None and not df_raw.empty:
            logger.info(f"Successfully fetched {len(df_raw)} raw rows from OpenAQ API. Post-processing...")
            df_processed = process_openaq_records(df_raw)
            return df_processed
        else:
            logger.warning("OpenAQ API data unavailable.")
            return pd.DataFrame()

    # Parse inputs to Timestamps
    start_dt = pd.to_datetime(date_from) if date_from else pd.Timestamp.now() - pd.Timedelta(days=1)
    end_dt = pd.to_datetime(date_to) if date_to else pd.Timestamp.now()
    
    # Ensure start_dt is localized/naive appropriately
    if start_dt.tz is not None:
        start_dt = start_dt.tz_localize(None)
    if end_dt.tz is not None:
        end_dt = end_dt.tz_localize(None)
        
    # Generate calendar monthly chunks
    import calendar
    chunks = []
    curr = start_dt
    while curr < end_dt:
        _, last_day = calendar.monthrange(curr.year, curr.month)
        curr_end = curr.replace(day=last_day, hour=23, minute=59, second=59)
        if curr_end > end_dt:
            curr_end = end_dt
        chunks.append((curr, curr_end))
        
        # Move to next month
        next_month_dt = curr_end + pd.Timedelta(seconds=1)
        if next_month_dt.day != 1:
            next_month_dt = (next_month_dt + pd.DateOffset(months=1)).replace(day=1)
        curr = next_month_dt
        
    all_raw_dfs = []
    for c_start, c_end in chunks:
        c_start_str = c_start.strftime("%Y-%m-%d")
        c_end_str = c_end.strftime("%Y-%m-%d")
        logger.info(
            "Historical mode: requesting measurements from %s to %s (monthly chunk).",
            c_start_str,
            c_end_str,
        )
        df_chunk = fetch_openaq_raw(date_from=c_start_str, date_to=c_end_str)
        if df_chunk is not None and not df_chunk.empty:
            all_raw_dfs.append(df_chunk)
            
    if all_raw_dfs:
        df_raw = pd.concat(all_raw_dfs, ignore_index=True)
        logger.info(f"Successfully fetched {len(df_raw)} raw rows from OpenAQ API. Post-processing...")
        df_processed = process_openaq_records(df_raw)
        return df_processed
    else:
        logger.warning("OpenAQ API data unavailable.")
        return pd.DataFrame()
