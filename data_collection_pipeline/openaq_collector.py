import logging
import json
import requests
import pandas as pd
from typing import Optional, Dict, List
import datetime
import random
from data_collection_pipeline import config, utils

logger = logging.getLogger("data_collection_pipeline.openaq")

def fetch_openaq_raw(limit: int = 1000) -> Optional[pd.DataFrame]:
    """
    Fetches raw measurements for country=IN from the OpenAQ API.
    Sends API keys in headers if provided.
    Safely handles nested JSON keys, null coordinates, null timestamps,
    and malformed responses.
    """
    if not config.OPENAQ_API_KEY:
        logger.warning("OPENAQ_API_KEY not found in config. Falling back to Mock Data.")
        return None

    headers = {
        "X-API-Key": config.OPENAQ_API_KEY
    }
    
    params = {
        "country": "IN",
        "limit": limit
    }
    
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
                "utc_time": utc_time,
                "local_time": local_time,
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
    required_cols = {"location", "city", "country", "latitude", "longitude", "utc_time", "parameter", "value"}
    if not required_cols.issubset(df_raw.columns):
        logger.error(f"OpenAQ raw data missing required columns for pivoting: {required_cols - set(df_raw.columns)}")
        return df_raw

    # Pivot to put parameter values in separate columns
    pivoted = df_raw.pivot_table(
        index=["location", "city", "country", "latitude", "longitude", "utc_time"],
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

def generate_mock_openaq_data() -> pd.DataFrame:
    """
    Generates realistic OpenAQ data for testing.
    Uses stations with coordinates inside India.
    """
    logger.info("Generating realistic mock OpenAQ air quality data...")
    stations = [
        {"location": "Anand Vihar, Delhi - DPCC", "city": "Delhi", "lat": 28.6476, "lon": 77.3158},
        {"location": "Bandra Kurla Complex, Mumbai - MPCB", "city": "Mumbai", "lat": 19.0626, "lon": 72.8617},
        {"location": "Silk Board, Bengaluru - KSPCB", "city": "Bengaluru", "lat": 12.9174, "lon": 77.6228},
        {"location": "Victoria, Kolkata - WBPCB", "city": "Kolkata", "lat": 22.5448, "lon": 88.3426},
        {"location": "Velachery, Chennai - TNPCB", "city": "Chennai", "lat": 12.9894, "lon": 80.2172},
        {"location": "Sanathnagar, Hyderabad - TSPCB", "city": "Hyderabad", "lat": 17.4589, "lon": 78.4412},
        {"location": "Lalbagh, Lucknow - UPPCB", "city": "Lucknow", "lat": 26.8524, "lon": 80.9392},
        {"location": "Rajbansi Nagar, Patna - BSPCB", "city": "Patna", "lat": 25.6025, "lon": 85.1112},
    ]
    
    mock_records = []
    now_utc = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:00:00Z")
    
    for s in stations:
        pm25 = random.uniform(15.0, 300.0)
        pm10 = pm25 * random.uniform(1.2, 2.0)
        no2 = random.uniform(5.0, 80.0)
        so2 = random.uniform(2.0, 30.0)
        co = random.uniform(0.1, 4.0)
        o3 = random.uniform(10.0, 150.0)
        
        row = {
            "location": s["location"],
            "city": s["city"],
            "country": "IN",
            "latitude": s["lat"],
            "longitude": s["lon"],
            "utc_time": now_utc,
            "PM2.5": round(pm25, 2),
            "PM10": round(pm10, 2),
            "NO2": round(no2, 2),
            "SO2": round(so2, 2),
            "CO": round(co, 2),
            "O3": round(o3, 2)
        }
        mock_records.append(row)
        
    return pd.DataFrame(mock_records)

def collect_openaq_data() -> pd.DataFrame:
    """
    Main function to orchestrate OpenAQ data collection.
    Tries fetching from the API first; falls back to mock data if unsuccessful.
    """
    logger.info("Starting OpenAQ Air Quality data collection...")
    df_raw = fetch_openaq_raw()
    
    if df_raw is not None and not df_raw.empty:
        logger.info(f"Successfully fetched {len(df_raw)} raw rows from OpenAQ API. Post-processing...")
        df_processed = process_openaq_records(df_raw)
        return df_processed
    else:
        logger.warning("OpenAQ API data unavailable. Reverting to fallback mock data.")
        return generate_mock_openaq_data()
