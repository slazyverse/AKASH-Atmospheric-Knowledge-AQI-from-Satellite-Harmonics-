"""
CPCB AQI Breakpoint Calculation Module.

This module implements the official Central Pollution Control Board (CPCB), India
National Air Quality Index (NAQI) sub-index and overall AQI calculation logic.
It handles concentration-to-index conversion using the segmented linear formula
for the eight major criteria pollutants: PM2.5, PM10, NO2, SO2, CO, O3, NH3, and Pb.

CPCB Sub-Index Segmented Linear Formula:
    Ip = [(I_Hi - I_Lo) / (BP_Hi - BP_Lo)] * (Cp - BP_Lo) + I_Lo

Where:
    Cp = truncated concentration of pollutant p
    BP_Hi = concentration breakpoint greater than or equal to Cp
    BP_Lo = concentration breakpoint less than or equal to Cp
    I_Hi = sub-index value corresponding to BP_Hi
    I_Lo = sub-index value corresponding to BP_Lo
"""

import logging
import math
from typing import Dict, List, Optional, Tuple, Union

logger = logging.getLogger(__name__)

# Standard rename map to canonicalise pollutant names
POLLUTANT_RENAME_MAP: Dict[str, str] = {
    "pm25": "PM2.5",
    "pm2_5": "PM2.5",
    "pm2.5": "PM2.5",
    "pm 2.5": "PM2.5",
    "PM25": "PM2.5",
    "PM2_5": "PM2.5",
    "PM2.5": "PM2.5",
    "pm10": "PM10",
    "PM10": "PM10",
    "no2": "NO2",
    "NO2": "NO2",
    "so2": "SO2",
    "SO2": "SO2",
    "co": "CO",
    "CO": "CO",
    "o3": "O3",
    "O3": "O3",
    "ozone": "O3",
    "OZONE": "O3",
    "nh3": "NH3",
    "NH3": "NH3",
    "pb": "Pb",
    "PB": "Pb",
    "Pb": "Pb",
    "lead": "Pb",
}

# CPCB Breakpoints Table
# Each list contains tuples of: (BP_Lo, BP_Hi, I_Lo, I_Hi)
# CO is in mg/m3; all other pollutants are in ug/m3.
CPCB_BREAKPOINTS: Dict[str, List[Tuple[float, float, float, float]]] = {
    "PM2.5": [
        (0.0, 30.0, 0.0, 50.0),
        (31.0, 60.0, 51.0, 100.0),
        (61.0, 90.0, 101.0, 200.0),
        (91.0, 120.0, 201.0, 300.0),
        (121.0, 250.0, 301.0, 400.0),
        (251.0, 380.0, 401.0, 500.0),
    ],
    "PM10": [
        (0.0, 50.0, 0.0, 50.0),
        (51.0, 100.0, 51.0, 100.0),
        (101.0, 250.0, 101.0, 200.0),
        (251.0, 350.0, 201.0, 300.0),
        (351.0, 430.0, 301.0, 400.0),
        (431.0, 510.0, 401.0, 500.0),
    ],
    "NO2": [
        (0.0, 40.0, 0.0, 50.0),
        (41.0, 80.0, 51.0, 100.0),
        (81.0, 180.0, 101.0, 200.0),
        (181.0, 280.0, 201.0, 300.0),
        (281.0, 400.0, 301.0, 400.0),
        (401.0, 560.0, 401.0, 500.0),
    ],
    "SO2": [
        (0.0, 40.0, 0.0, 50.0),
        (41.0, 80.0, 51.0, 100.0),
        (81.0, 380.0, 101.0, 200.0),
        (381.0, 800.0, 201.0, 300.0),
        (801.0, 1600.0, 301.0, 400.0),
        (1601.0, 1800.0, 401.0, 500.0),
    ],
    "CO": [
        (0.0, 1.0, 0.0, 50.0),
        (1.1, 2.0, 51.0, 100.0),
        (2.1, 10.0, 101.0, 200.0),
        (10.1, 17.0, 201.0, 300.0),
        (17.1, 34.0, 301.0, 400.0),
        (34.1, 50.0, 401.0, 500.0),
    ],
    "O3": [
        (0.0, 50.0, 0.0, 50.0),
        (51.0, 100.0, 51.0, 100.0),
        (101.0, 168.0, 101.0, 200.0),
        (169.0, 208.0, 201.0, 300.0),
        (209.0, 748.0, 301.0, 400.0),
        (749.0, 1000.0, 401.0, 500.0),
    ],
    "NH3": [
        (0.0, 200.0, 0.0, 50.0),
        (201.0, 400.0, 51.0, 100.0),
        (401.0, 800.0, 101.0, 200.0),
        (801.0, 1200.0, 201.0, 300.0),
        (1201.0, 1800.0, 301.0, 400.0),
        (1801.0, 2000.0, 401.0, 500.0),
    ],
    "Pb": [
        (0.0, 0.5, 0.0, 50.0),
        (0.6, 1.0, 51.0, 100.0),
        (1.1, 2.0, 101.0, 200.0),
        (2.1, 3.0, 201.0, 300.0),
        (3.1, 3.5, 301.0, 400.0),
        (3.6, 5.0, 401.0, 500.0),
    ],
}


def standardize_pollutant_name(name: str) -> Optional[str]:
    """
    Standardizes a pollutant string representation to CPCB standard names.
    
    Args:
        name: Raw name of the pollutant (e.g. 'pm25', 'ozone').
        
    Returns:
        Canonical standardized name or None if unsupported.
    """
    if not isinstance(name, str):
        return None
    cleaned = name.strip().replace(" ", "").replace("-", "").lower()
    return POLLUTANT_RENAME_MAP.get(name, POLLUTANT_RENAME_MAP.get(cleaned, None))


def truncate_concentration(pollutant: str, value: float) -> Optional[float]:
    """
    Truncates the concentration value based on CPCB standard decimal precision.
    PM2.5, PM10, NO2, SO2, O3, NH3 are truncated to integer.
    CO, Pb are truncated to 1 decimal place.
    
    Args:
        pollutant: Standardized pollutant name.
        value: Raw float concentration value.
        
    Returns:
        Truncated float value, or None if input is invalid.
    """
    if value is None or value != value:
        return None
    if value < 0.0:
        return None
        
    canonical = standardize_pollutant_name(pollutant)
    if not canonical:
        return None
        
    # Standard float representation correction
    rounded = round(value, 6)
    if canonical in {"CO", "Pb"}:
        return math.floor(rounded * 10.0) / 10.0
    else:
        return float(math.floor(rounded))


def calculate_sub_index(
    pollutant: str,
    concentration: float,
    round_index: bool = True
) -> Optional[Union[int, float]]:
    """
    Calculates the AQI sub-index for a single pollutant concentration using CPCB breakpoints.
    
    If the concentration exceeds the maximum severe breakpoint defined for the pollutant,
    the sub-index is capped at 500.
    
    Args:
        pollutant: Name of the pollutant (case-insensitive, automatically standardized).
        concentration: Measured pollutant concentration (non-negative float).
        round_index: If True, rounds the final sub-index to the nearest integer.
        
    Returns:
        The calculated sub-index as int or float, or None if concentration is negative,
        NaN, or the pollutant is unsupported.
    """
    canonical_name = standardize_pollutant_name(pollutant)
    if not canonical_name:
        logger.warning(f"Unsupported pollutant requested: {pollutant}")
        return None
        
    if concentration is None or concentration != concentration:
        return None
        
    if concentration < 0.0:
        logger.warning(f"Negative concentration ({concentration}) provided for {canonical_name}. Returning None.")
        return None
        
    # Truncate concentration per CPCB rules
    cp = truncate_concentration(canonical_name, concentration)
    if cp is None:
        return None
        
    breakpoints = CPCB_BREAKPOINTS[canonical_name]
    
    # Check if concentration exceeds the highest breakpoint limit
    max_bp_hi = breakpoints[-1][1]
    if cp > max_bp_hi:
        logger.debug(f"Concentration {cp} exceeds highest breakpoint {max_bp_hi} for {canonical_name}. Capping sub-index at 500.")
        return 500 if round_index else 500.0
        
    # Match the correct breakpoint interval
    matched_range = None
    for bp_lo, bp_hi, i_lo, i_hi in breakpoints:
        if bp_lo <= cp <= bp_hi:
            matched_range = (bp_lo, bp_hi, i_lo, i_hi)
            break
            
    if not matched_range:
        logger.error(f"Concentration {cp} (raw: {concentration}) for {canonical_name} could not be matched to any breakpoint range.")
        return None
        
    bp_lo, bp_hi, i_lo, i_hi = matched_range
    
    if bp_hi == bp_lo:
        sub_index = i_hi
    else:
        # Segmented linear interpolation formula
        sub_index = ((i_hi - i_lo) / (bp_hi - bp_lo)) * (cp - bp_lo) + i_lo
        
    if round_index:
        return int(round(sub_index))
        
    return sub_index


def validate_cpcb_requirements(pollutant_data: Dict[str, float]) -> bool:
    """
    Checks if the minimum data requirements for calculating CPCB AQI are satisfied.
    
    Official CPCB Rule:
    - At least three valid pollutants must be present.
    - At least one of those three must be either PM2.5 or PM10.
    
    Args:
        pollutant_data: Dictionary mapping pollutant names to concentration values.
        
    Returns:
        True if the requirements are met, False otherwise.
    """
    valid_pollutants = set()
    has_particulate = False
    
    for k, v in pollutant_data.items():
        canonical_name = standardize_pollutant_name(k)
        if canonical_name and v is not None and v == v and v >= 0.0:
            valid_pollutants.add(canonical_name)
            if canonical_name in {"PM2.5", "PM10"}:
                has_particulate = True
                
    return len(valid_pollutants) >= 3 and has_particulate


def aggregate_aqi(
    sub_indices: Dict[str, Union[int, float]],
    deterministic_tie_breaker: bool = True
) -> Tuple[Optional[Union[int, float]], Optional[Union[str, List[str]]]]:
    """
    Aggregates individual pollutant sub-indices into an overall AQI and identifies dominant pollutant(s).
    
    The overall AQI is the maximum of the calculated sub-indices.
    
    Args:
        sub_indices: Dictionary mapping standard pollutant names (e.g. 'PM2.5') to computed sub-indices.
        deterministic_tie_breaker: If True, returns the lexicographically first pollutant name in case of a tie.
                                    If False, returns a list of all tied dominant pollutants.
                                    
    Returns:
        A tuple of (overall_aqi, dominant_pollutant_or_list) or (None, None) if no valid sub-indices are provided.
    """
    valid_indices = {
        standardize_pollutant_name(k): v
        for k, v in sub_indices.items()
        if v is not None and v == v and standardize_pollutant_name(k) is not None
    }
    
    if not valid_indices:
        return None, None
        
    overall_aqi = max(valid_indices.values())
    
    # Identify all pollutants that share the maximum sub-index
    tied_pollutants = sorted([k for k, v in valid_indices.items() if v == overall_aqi])
    
    if deterministic_tie_breaker:
        dominant = tied_pollutants[0]
    else:
        dominant = tied_pollutants
        
    return overall_aqi, dominant


def calculate_overall_aqi(
    pollutant_concentrations: Dict[str, float],
    enforce_requirements: bool = False,
    round_index: bool = True,
    deterministic_tie_breaker: bool = True
) -> Tuple[Dict[str, Optional[Union[int, float]]], Optional[Union[int, float]], Optional[Union[str, List[str]]]]:
    """
    Exposes a unified calculation helper for CPCB AQI.
    
    Calculates sub-indices for all valid input concentrations, aggregates to
    find the overall AQI, and resolves the dominant pollutant.
    
    Args:
        pollutant_concentrations: Dictionary of {pollutant_name: concentration_value}.
        enforce_requirements: If True, overall AQI is returned as None if CPCB requirements are not met.
                              If False, returns overall AQI based on whatever valid sub-indices are computed.
        round_index: If True, rounds sub-indices and overall AQI to standard integers.
        deterministic_tie_breaker: If True, resolves dominant pollutant ties lexicographically.
        
    Returns:
        A tuple of:
          - Dict of {pollutant_name: sub_index_or_None}
          - Overall AQI (number or None)
          - Dominant pollutant(s) (string, list of strings, or None)
    """
    sub_indices: Dict[str, Optional[Union[int, float]]] = {}
    
    for k, v in pollutant_concentrations.items():
        canonical_name = standardize_pollutant_name(k)
        if canonical_name:
            sub_indices[canonical_name] = calculate_sub_index(canonical_name, v, round_index=round_index)
            
    clean_sub_indices = {k: v for k, v in sub_indices.items() if v is not None}
    
    if enforce_requirements and not validate_cpcb_requirements(pollutant_concentrations):
        logger.info("CPCB minimum requirements not met. Overall AQI returned as None.")
        overall_aqi, dominant = None, None
    else:
        overall_aqi, dominant = aggregate_aqi(clean_sub_indices, deterministic_tie_breaker=deterministic_tie_breaker)
        
    return sub_indices, overall_aqi, dominant
