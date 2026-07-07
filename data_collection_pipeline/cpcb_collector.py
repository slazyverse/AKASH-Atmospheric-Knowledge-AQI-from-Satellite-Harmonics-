import logging
import json
import random
import datetime
import pandas as pd
from typing import Optional, Dict, List
from data_collection_pipeline import config, utils

logger = logging.getLogger("data_collection_pipeline.cpcb")

def fetch_cpcb_raw(limit: int = 5000) -> Optional[pd.DataFrame]:
    """
    Fetches raw CPCB real-time AQI records from data.gov.in API.
    Handles pagination and returns a pandas DataFrame of the raw records.
    """
    if not config.DATA_GOV_API_KEY:
        logger.warning("DATA_GOV_API_KEY not found in config. Falling back to Mock Data.")
        return None

    all_records: List[Dict] = []
    offset = 0
    
    while True:
        params = {
            "api-key": config.DATA_GOV_API_KEY,
            "format": "json",
            "offset": offset,
            "limit": limit
        }
        
        response = utils.safe_request(config.CPCB_BASE_URL, params=params)
        if response is None:
            logger.error("Failed to fetch CPCB data from API (no response).")
            return None
            
        try:
            data = response.json()
            
            if not isinstance(data, dict):
                logger.error("CPCB API response is not a valid JSON dictionary.")
                return None
                
            records = data.get("records")
            total = data.get("total")
            
            # Type and structural validation
            if not isinstance(records, list):
                logger.error("CPCB response 'records' key is missing or is not a list.")
                return None
            
            try:
                total_count = int(total) if total is not None else 0
            except ValueError:
                total_count = 0
                
            count = len(records)
            if count == 0:
                break
                
            all_records.extend(records)
            logger.info(f"Fetched {count} CPCB records. Total collected so far: {len(all_records)}/{total_count}")
            
            offset += count
            if offset >= total_count:
                break
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decoding failed for CPCB response: {e}")
            return None
        except KeyError as e:
            logger.error(f"Missing expected key in CPCB response structure: {e}")
            return None
        except ValueError as e:
            logger.error(f"ValueError while parsing CPCB API parameters: {e}")
            return None
            
    if not all_records:
        return None
        
    return pd.DataFrame(all_records)

def process_cpcb_records(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Pivots the raw long-format CPCB records into a wide-format DataFrame
    containing columns for PM2.5, PM10, NO2, SO2, CO, O3, AQI and station details.
    """
    required_cols = {'country', 'state', 'city', 'station', 'last_update', 'pollutant_id', 'pollutant_avg'}
    if not required_cols.issubset(df_raw.columns):
        logger.error(f"CPCB Raw data missing required columns: {required_cols - set(df_raw.columns)}")
        return df_raw

    # Pivot the data to wide format
    pivoted = df_raw.pivot_table(
        index=["country", "state", "city", "station", "last_update"],
        columns="pollutant_id",
        values="pollutant_avg",
        aggfunc="first"
    ).reset_index()
    
    # Standardize column names (Rename OZONE to O3)
    pivoted.rename(columns={"OZONE": "O3"}, inplace=True)
    
    # Ensure standard pollutants exist in the DataFrame columns
    standard_pollutants = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "AQI"]
    for poll in standard_pollutants:
        if poll not in pivoted.columns:
            pivoted[poll] = None
            
    # Re-order columns for clarity
    cols = ["country", "state", "city", "station", "last_update"] + standard_pollutants
    existing_cols = [c for c in cols if c in pivoted.columns]
    return pivoted[existing_cols]

def generate_mock_cpcb_data() -> pd.DataFrame:
    """
    Generates realistic CPCB air quality and station data for validation and testing
    when API keys are missing or API request fails.
    """
    logger.info("Generating realistic mock CPCB air quality data...")
    stations = [
        {"state": "Delhi", "city": "Delhi", "station": "Anand Vihar, Delhi - DPCC"},
        {"state": "Delhi", "city": "Delhi", "station": "Dwarka-Sector 8, Delhi - DPCC"},
        {"state": "Maharashtra", "city": "Mumbai", "station": "Bandra Kurla Complex, Mumbai - MPCB"},
        {"state": "Maharashtra", "city": "Mumbai", "station": "Colaba, Mumbai - MPCB"},
        {"state": "Karnataka", "city": "Bengaluru", "station": "Silk Board, Bengaluru - KSPCB"},
        {"state": "Karnataka", "city": "Bengaluru", "station": "Peenya, Bengaluru - KSPCB"},
        {"state": "West Bengal", "city": "Kolkata", "station": "Victoria, Kolkata - WBPCB"},
        {"state": "West Bengal", "city": "Kolkata", "station": "Jadavpur, Kolkata - WBPCB"},
        {"state": "Tamil Nadu", "city": "Chennai", "station": "Velachery, Chennai - TNPCB"},
        {"state": "Telangana", "city": "Hyderabad", "station": "Sanathnagar, Hyderabad - TSPCB"},
        {"state": "Uttar Pradesh", "city": "Lucknow", "station": "Lalbagh, Lucknow - UPPCB"},
        {"state": "Bihar", "city": "Patna", "station": "Rajbansi Nagar, Patna - BSPCB"},
    ]
    
    mock_records = []
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:00:00")
    
    for s in stations:
        aqi = random.randint(30, 450)
        pm25 = int(aqi * random.uniform(0.6, 0.9))
        pm10 = int(aqi * random.uniform(1.2, 1.8))
        no2 = int(aqi * random.uniform(0.15, 0.3))
        so2 = int(aqi * random.uniform(0.05, 0.15))
        co = round(aqi * random.uniform(0.005, 0.015), 2)
        o3 = int(aqi * random.uniform(0.2, 0.4))
        
        record = {
            "country": "India",
            "state": s["state"],
            "city": s["city"],
            "station": s["station"],
            "last_update": now,
            "PM2.5": pm25,
            "PM10": pm10,
            "NO2": no2,
            "SO2": so2,
            "CO": co,
            "O3": o3,
            "AQI": aqi
        }
        mock_records.append(record)
        
    return pd.DataFrame(mock_records)

def collect_cpcb_data() -> pd.DataFrame:
    """
    Main function to orchestrate CPCB data collection.
    Tries fetching from the API first; falls back to mock data if unsuccessful.
    """
    logger.info("Starting CPCB Air Quality data collection...")
    df_raw = fetch_cpcb_raw()
    
    if df_raw is not None and not df_raw.empty:
        logger.info(f"Successfully fetched {len(df_raw)} raw rows from CPCB API. Post-processing...")
        df_processed = process_cpcb_records(df_raw)
        return df_processed
    else:
        logger.warning("CPCB API data unavailable. Reverting to fallback mock data.")
        return generate_mock_cpcb_data()
