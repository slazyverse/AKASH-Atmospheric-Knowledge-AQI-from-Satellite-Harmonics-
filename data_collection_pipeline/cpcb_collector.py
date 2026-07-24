import logging
import json
import random
import datetime
import pandas as pd
from typing import Optional, Dict, List
from data_collection_pipeline import config, utils
from data_collection_pipeline.dlq import handle_ingestion_failure

logger = logging.getLogger("data_collection_pipeline.cpcb")

def fetch_cpcb_raw(limit: int = 5000) -> Optional[pd.DataFrame]:
    """
    Fetches raw CPCB real-time AQI records from data.gov.in API.
    Handles pagination and returns a pandas DataFrame of the raw records.
    """
    if not config.DATA_GOV_API_KEY:
        handle_ingestion_failure(
            source="CPCB",
            operation="fetch_cpcb_raw",
            message="DATA_GOV_API_KEY missing from configuration.",
            logger_instance=logger,
        )

    all_records: List[Dict] = []
    offset = 0
    
    while True:
        params = {
            "api-key": config.DATA_GOV_API_KEY,
            "format": "json",
            "offset": offset,
            "limit": limit
        }
        
        try:
            response = utils.safe_request(config.CPCB_BASE_URL, params=params)
        except Exception as e:
            handle_ingestion_failure(
                source="CPCB",
                operation="fetch_cpcb_raw",
                message=f"Network error while fetching CPCB API: {e}",
                original_exception=e,
                logger_instance=logger,
            )

        if response is None:
            handle_ingestion_failure(
                source="CPCB",
                operation="fetch_cpcb_raw",
                message="Failed to fetch CPCB data from API (network failure or empty response).",
                logger_instance=logger,
            )
            
        try:
            data = response.json()
            
            if not isinstance(data, dict):
                handle_ingestion_failure(
                    source="CPCB",
                    operation="fetch_cpcb_raw",
                    message="CPCB API response is not a valid JSON dictionary.",
                    logger_instance=logger,
                )
                
            records = data.get("records")
            total = data.get("total")
            
            # Type and structural validation
            if not isinstance(records, list):
                handle_ingestion_failure(
                    source="CPCB",
                    operation="fetch_cpcb_raw",
                    message="CPCB response 'records' key is missing or is not a list.",
                    logger_instance=logger,
                )
            
            try:
                total_count = int(total) if total is not None else 0
            except ValueError:
                total_count = 0
                
            count = len(records)
            if count == 0:
                break
                
            all_records.extend(records)
            logger.info(f"Fetched {count} CPCB records. Total collected so far: {len(all_records)}/{total_count}")
            
            if len(all_records) >= limit:
                break
                
            offset += count
            if offset >= total_count:
                break
                
        except json.JSONDecodeError as e:
            handle_ingestion_failure(
                source="CPCB",
                operation="fetch_cpcb_raw",
                message=f"JSON decoding failed for CPCB response: {e}",
                original_exception=e,
                logger_instance=logger,
            )
        except KeyError as e:
            handle_ingestion_failure(
                source="CPCB",
                operation="fetch_cpcb_raw",
                message=f"Missing expected key in CPCB response structure: {e}",
                original_exception=e,
                logger_instance=logger,
            )
        except ValueError as e:
            handle_ingestion_failure(
                source="CPCB",
                operation="fetch_cpcb_raw",
                message=f"ValueError while parsing CPCB API parameters: {e}",
                original_exception=e,
                logger_instance=logger,
            )
            
    if not all_records:
        handle_ingestion_failure(
            source="CPCB",
            operation="fetch_cpcb_raw",
            message="No records returned from CPCB API.",
            logger_instance=logger,
        )
        
    return pd.DataFrame(all_records)

def process_cpcb_records(df_raw: pd.DataFrame) -> pd.DataFrame:
    """
    Pivots the raw long-format CPCB records into a wide-format DataFrame
    containing columns for PM2.5, PM10, NO2, SO2, CO, O3, AQI and station details.
    """
    required_cols = {'country', 'state', 'city', 'station', 'last_update', 'pollutant_id', 'avg_value'}
    if not required_cols.issubset(df_raw.columns):
        logger.error(f"CPCB Raw data missing required columns: {required_cols - set(df_raw.columns)}")
        return df_raw

    # Pivot the data to wide format
    pivoted = df_raw.pivot_table(
        index=["country", "state", "city", "station", "last_update"],
        columns="pollutant_id",
        values="avg_value",
        aggfunc="first"
    ).reset_index()
    
    # Standardize column names (Rename OZONE to O3)
    pivoted.rename(columns={"OZONE": "O3"}, inplace=True)
    
    # Ensure standard pollutants exist in the DataFrame columns
    standard_pollutants = ["PM2.5", "PM10", "NO2", "SO2", "CO", "O3", "AQI"]
    for poll in standard_pollutants:
        if poll not in pivoted.columns:
            pivoted[poll] = None

    # Calculate AQI based on Indian AQI formulas if it is not present or entirely null
    if pivoted["AQI"].isna().all():
        logger.info("Live CPCB raw AQI is null. Calculating Indian standard AQI from pollutants...")
        aqi_values = []
        for _, r in pivoted.iterrows():
            aqi_val = None
            # PM2.5 sub-index
            pm25 = r.get("PM2.5")
            pm25_sub = None
            if pd.notna(pm25):
                try:
                    val = float(pm25)
                    if val <= 30: pm25_sub = val * 50 / 30
                    elif val <= 60: pm25_sub = 50 + (val - 30) * 50 / 30
                    elif val <= 90: pm25_sub = 100 + (val - 60) * 100 / 30
                    elif val <= 120: pm25_sub = 200 + (val - 90) * 100 / 30
                    elif val <= 250: pm25_sub = 300 + (val - 120) * 100 / 130
                    else: pm25_sub = 400 + (val - 250) * 100 / 750
                except (ValueError, TypeError):
                    pass
            
            # PM10 sub-index
            pm10 = r.get("PM10")
            pm10_sub = None
            if pd.notna(pm10):
                try:
                    val = float(pm10)
                    if val <= 50: pm10_sub = val * 50 / 50
                    elif val <= 100: pm10_sub = 50 + (val - 50) * 50 / 50
                    elif val <= 250: pm10_sub = 100 + (val - 100) * 100 / 150
                    elif val <= 350: pm10_sub = 200 + (val - 250) * 100 / 100
                    elif val <= 430: pm10_sub = 300 + (val - 350) * 100 / 80
                    else: pm10_sub = 400 + (val - 430) * 100 / 570
                except (ValueError, TypeError):
                    pass

            # NO2 sub-index
            no2 = r.get("NO2")
            no2_sub = None
            if pd.notna(no2):
                try:
                    val = float(no2)
                    if val <= 40: no2_sub = val * 50 / 40
                    elif val <= 80: no2_sub = 50 + (val - 40) * 50 / 40
                    elif val <= 180: no2_sub = 100 + (val - 80) * 100 / 100
                    elif val <= 280: no2_sub = 200 + (val - 180) * 100 / 100
                    elif val <= 400: no2_sub = 300 + (val - 280) * 100 / 120
                    else: no2_sub = 400 + (val - 400) * 100 / 600
                except (ValueError, TypeError):
                    pass

            sub_indices = [s for s in [pm25_sub, pm10_sub, no2_sub] if s is not None]
            if sub_indices and (pm25_sub is not None or pm10_sub is not None):
                aqi_val = max(sub_indices)
            else:
                all_subs = [s for s in [pm25_sub, pm10_sub, no2_sub] if s is not None]
                if all_subs:
                    aqi_val = max(all_subs)
                else:
                    aqi_val = 50.0  # safe default

            aqi_values.append(round(aqi_val))
        pivoted["AQI"] = aqi_values
            
    # Re-order columns for clarity
    cols = ["country", "state", "city", "station", "last_update"] + standard_pollutants
    existing_cols = [c for c in cols if c in pivoted.columns]
    return pivoted[existing_cols]

def generate_mock_cpcb_data(window_days: int = 1) -> pd.DataFrame:
    """
    Generates realistic CPCB air quality and station data for validation and testing
    when API keys are missing or API request fails. Supports a configurable window_days
    to generate historical daily records.
    """
    logger.info(f"Generating realistic mock CPCB air quality data for {window_days} day(s)...")
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
    base_time = datetime.datetime.now()
    
    for d in range(window_days):
        now = (base_time - datetime.timedelta(days=d)).strftime("%Y-%m-%d 12:00:00")
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
 
def collect_cpcb_data(window_days: int = 1) -> pd.DataFrame:
    """
    Main function to orchestrate CPCB data collection.
    Fetches real-time observations from the CPCB API. Raises IngestionError on failure.
    """
    logger.info("Starting CPCB Air Quality data collection...")
    df_raw = fetch_cpcb_raw()
    
    if df_raw is None or df_raw.empty:
        handle_ingestion_failure(
            source="CPCB",
            operation="collect_cpcb_data",
            message="CPCB API returned no data.",
            logger_instance=logger,
        )

    logger.info(f"Successfully fetched {len(df_raw)} raw rows from CPCB API. Post-processing...")
    df_processed = process_cpcb_records(df_raw)
    if df_processed is None or df_processed.empty:
        handle_ingestion_failure(
            source="CPCB",
            operation="process_cpcb_records",
            message="Failed to process CPCB records into wide DataFrame.",
            logger_instance=logger,
        )
    return df_processed
