import pandas as pd
import numpy as np

# Map various CPCB notations to our standardized schema
POLLUTANT_MAPPING = {
    "pm25": "PM2.5",
    "pm2.5": "PM2.5",
    "pm 2.5": "PM2.5",
    "pm10": "PM10",
    "pm 10": "PM10",
    "no2": "NO2",
    "no": "NO",
    "nox": "NOX",
    "nh3": "NH3",
    "so2": "SO2",
    "co": "CO",
    "o3": "O3",
    "ozone": "O3",
    "voc": "VOC",
    # Met variables
    "at": "AT",
    "rh": "RH",
    "ws": "WS",
    "wd": "WD",
    "bp": "BP",
    "rf": "RF",
    "sr": "SR"
}

def standardize_pollutant_name(raw_name: str) -> str:
    """Standardizes a pollutant name."""
    clean_name = str(raw_name).strip().lower()
    return POLLUTANT_MAPPING.get(clean_name, raw_name.upper())

def standardize_units(pollutant: str, raw_unit: str = None) -> str:
    """Returns standard unit for a given pollutant. Converts from ppb to ug/m3 if needed (placeholder logic)."""
    # For now, enforce the standard units for the project
    if pollutant == "CO":
        return "mg/m³"
    elif pollutant in ["AT", "RH", "WS", "WD", "BP", "RF", "SR"]:
        # Standard met units
        units = {"AT": "°C", "RH": "%", "WS": "m/s", "WD": "deg", "BP": "mmHg", "RF": "mm", "SR": "W/m²"}
        return units.get(pollutant, "")
    return "µg/m³"

def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Cleans the wide dataframe.
    - Standardizes column names
    - Converts timestamps to UTC
    - Handles missing values (NaN)
    """
    df_cleaned = df.copy()
    
    # Standardize column names for metadata and time
    col_mapping = {}
    for col in df_cleaned.columns:
        col_lower = col.strip().lower()
        if col_lower in ['timestamp', 'date', 'datetime', 'last_update']:
            col_mapping[col] = 'timestamp_local'
        elif col_lower in ['station', 'station_name']:
            col_mapping[col] = 'station'
            
    df_cleaned.rename(columns=col_mapping, inplace=True)
    
    # Parse timestamp
    if 'timestamp_local' in df_cleaned.columns:
        # Assuming IST (+5:30) for local data
        df_cleaned['timestamp_local'] = pd.to_datetime(df_cleaned['timestamp_local'], errors='coerce')
        # Create UTC timestamp by subtracting 5 hours and 30 minutes
        df_cleaned['timestamp_utc'] = df_cleaned['timestamp_local'] - pd.Timedelta(hours=5, minutes=30)
        
    # Replace common null strings
    df_cleaned.replace(['None', 'NA', 'NaN', '', '-999', -999], np.nan, inplace=True)
    
    return df_cleaned
