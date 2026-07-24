import json
from typing import List, Dict, Any
from historical_ingestor.config import BASE_URL, API_KEY, REQUEST_TIMEOUT
from historical_ingestor.utils import make_request_with_retry
from historical_ingestor.logger import logger

def fetch_measurements(sensor_id: int, start_date: str, end_date: str, sensor_meta: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """Fetch measurements for a specific sensor and time range from OpenAQ.
    
    Splits the time range into monthly (30-day) chunks to avoid deep paging and 408 timeouts.
    Uses cached sensor metadata to skip chunks outside the active period.
    Strictly validates responses and rejects empty or malformed JSON payloads.
    """
    if not API_KEY:
        raise RuntimeError("OPENAQ_API_KEY is not configured. Real-time/historical OpenAQ v3 API requires a valid API key.")
        
    import pandas as pd
    import time
    
    # Parse active range from sensor metadata
    s_start_dt = None
    s_end_dt = None
    if sensor_meta:
        dt_first = sensor_meta.get("datetimeFirst")
        dt_last = sensor_meta.get("datetimeLast")
        s_start = dt_first.get("utc") if isinstance(dt_first, dict) else None
        s_end = dt_last.get("utc") if isinstance(dt_last, dict) else None
        if s_start:
            s_start_dt = pd.to_datetime(s_start)
        if s_end:
            s_end_dt = pd.to_datetime(s_end)

    start_dt = pd.to_datetime(start_date)
    end_dt = pd.to_datetime(end_date)
    
    # Check active range overlap if available
    if s_start_dt and end_dt < s_start_dt:
        logger.debug(f"Skipping fetch for sensor {sensor_id}: active range starts later.")
        return []
    if s_end_dt and start_dt > s_end_dt:
        logger.debug(f"Skipping fetch for sensor {sensor_id}: active range ended earlier.")
        return []
        
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
        # Move to the start of the next month
        next_month_dt = curr_end + pd.Timedelta(seconds=1)
        if next_month_dt.day != 1:
            next_month_dt = (next_month_dt + pd.DateOffset(months=1)).replace(day=1)
        curr = next_month_dt
        
    measurements = []
    headers = {"X-API-Key": API_KEY}
    url = f"{BASE_URL}/sensors/{sensor_id}/measurements"
    
    for c_start, c_end in chunks:
        # Check active range overlap for this specific chunk
        if s_start_dt and c_end < s_start_dt:
            continue
        if s_end_dt and c_start > s_end_dt:
            continue
            
        start_str = c_start.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str = c_end.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        logger.info(f"Fetching sensor {sensor_id} measurements from {start_str} to {end_str}...")
        
        params = {
            "datetime_from": start_str,
            "datetime_to": end_str,
            "limit": 1000,
            "page": 1
        }
        
        chunk_results_count = 0
        while True:
            time.sleep(0.3)  # Rate limiting sleep
            try:
                response = make_request_with_retry(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
                if not response.text.strip():
                    raise ValueError(f"Received empty response body from measurements endpoint for sensor {sensor_id}.")
                    
                data = response.json()
                if not isinstance(data, dict) or "results" not in data:
                    raise ValueError(f"Malformed response from measurements endpoint for sensor {sensor_id}.")
                    
                results = data.get("results", [])
                if not results:
                    break
                    
                measurements.extend(results)
                chunk_results_count += len(results)
                
                if len(results) < params["limit"]:
                    break
                    
                params["page"] += 1
            except Exception as e:
                logger.error(f"Error fetching measurements for sensor {sensor_id} chunk {start_str}-{end_str}: {e}")
                raise
                
        logger.info(f"Fetched {chunk_results_count} records for chunk {start_str} to {end_str}.")
        
    return measurements

def fetch_sensor_metadata(sensor_id: int) -> Dict[str, Any]:
    """Fetch metadata for a specific sensor from OpenAQ."""
    if not API_KEY:
        raise RuntimeError("OPENAQ_API_KEY is not configured.")
        
    url = f"{BASE_URL}/sensors/{sensor_id}"
    headers = {"X-API-Key": API_KEY}
    
    try:
        response = make_request_with_retry(url, headers=headers, timeout=REQUEST_TIMEOUT)
        data = response.json()
        if not isinstance(data, dict):
            raise ValueError(f"Malformed response from sensors endpoint for {sensor_id}.")
            
        results = data.get("results", [])
        if not results:
            # Maybe the API structure for single sensor returns directly?
            # Or if it's in results
            if "datetimeFirst" in data:
                return data
            raise ValueError(f"No sensor found for ID {sensor_id}.")
            
        return results[0]
    except Exception as e:
        logger.error(f"Error fetching sensor metadata for sensor {sensor_id}: {e}")
        raise
