import os
from typing import List, Dict, Any
from historical_ingestor.config import BASE_URL, COUNTRY, API_KEY, REQUEST_TIMEOUT, POLLUTANT_MAP
from historical_ingestor.utils import make_request_with_retry
from historical_ingestor.logger import logger

def fetch_locations() -> List[Dict[str, Any]]:
    """Fetch all location metadata for the given country from OpenAQ."""
    if not API_KEY:
        raise RuntimeError("OPENAQ_API_KEY is not configured. Real-time/historical OpenAQ v3 API requires a valid API key.")
        
    url = f"{BASE_URL}/locations"
    params = {
        "iso": COUNTRY,
        "limit": 100,
        "page": 1
    }
    headers = {"X-API-Key": API_KEY}
    
    locations = []
    logger.info(f"Fetching locations for country {COUNTRY} using OpenAQ v3 API...")
    
    while True:
        try:
            response = make_request_with_retry(url, params=params, headers=headers, timeout=REQUEST_TIMEOUT)
            if not response.text.strip():
                raise ValueError("Received an empty response body from OpenAQ locations endpoint.")
                
            data = response.json()
            if not isinstance(data, dict) or "results" not in data:
                raise ValueError("OpenAQ API response is malformed or missing the 'results' key.")
                
            results = data.get("results", [])
            if not results and params["page"] == 1:
                raise ValueError(f"No locations found for country {COUNTRY} on page 1 of locations API.")
                
            if not results:
                break
                
            locations.extend(results)
            
            found = data.get("meta", {}).get("found", 0)
            logger.info(f"Fetched {len(locations)} / {found} locations.")
            
            if len(results) < params["limit"]:
                break
                
            params["page"] += 1
        except Exception as e:
            logger.error(f"Error fetching locations: {e}")
            raise
        
    logger.info(f"Successfully fetched {len(locations)} locations in {COUNTRY}.")
    return locations

def extract_location_metadata(locations: List[Dict[str, Any]]) -> Dict[int, Dict[str, Any]]:
    """Extract relevant metadata from raw location data, including sensor mapping.
    
    Strictly rejects locations with missing coordinates, missing IDs, or missing/invalid sensor names.
    """
    metadata = {}
    for loc in locations:
        loc_id = loc.get("id")
        if loc_id is None:
            logger.warning("Rejected location: ID is missing.")
            continue
            
        coords = loc.get("coordinates")
        if coords is None:
            logger.warning(f"Rejected location {loc_id}: coordinates dictionary is missing.")
            continue
            
        lat = coords.get("latitude")
        lon = coords.get("longitude")
        if lat is None or lon is None:
            logger.warning(f"Rejected location {loc_id}: latitude or longitude is missing.")
            continue
            
        # Parse country representation
        country_data = loc.get("country")
        country_name = COUNTRY
        if isinstance(country_data, dict):
            country_name = country_data.get("name", COUNTRY)
        elif isinstance(country_data, str):
            country_name = country_data
            
        # Parse sensors and map them to targeted pollutants
        sensors = loc.get("sensors", [])
        sensor_map = {}
        
        if sensors:
            for s in sensors:
                s_id = s.get("id")
                if s_id is None:
                    continue
                param_obj = s.get("parameter")
                param_name = None
                if isinstance(param_obj, dict):
                    param_name = param_obj.get("name")
                elif isinstance(param_obj, str):
                    param_name = param_obj
                else:
                    param_name = s.get("name")
                
                # Check match against target pollutants (reject missing pollutant names)
                if param_name:
                    for pollutant, api_name in POLLUTANT_MAP.items():
                        if param_name.lower() == api_name.lower():
                            sensor_map[pollutant] = {
                                "id": s_id,
                                "unit": s.get("unit") or "µg/m³"
                            }
                            
        # Reject location if it has no valid sensors for targeted pollutants
        if not sensor_map:
            logger.warning(f"Rejected location {loc_id}: no valid sensors for targeted pollutants.")
            continue
            
        metadata[loc_id] = {
            "location_id": loc_id,
            "station_name": loc.get("name") or f"Station {loc_id}",
            "latitude": lat,
            "longitude": lon,
            "city": loc.get("locality") or loc.get("city"),
            "state": loc.get("state"),
            "country": country_name,
            "sensors": sensor_map
        }
    return metadata
