import pandas as pd
from typing import List
from historical_ingestor.cpcb.schema import CommonObservationSchema

# Physical boundaries for QA flags
QA_BOUNDS = {
    "PM2.5": {"min": 0, "max": 2000},
    "PM10": {"min": 0, "max": 2000},
    "NO2": {"min": 0, "max": 1000},
    "SO2": {"min": 0, "max": 1000},
    "CO": {"min": 0, "max": 100},
    "O3": {"min": 0, "max": 1000}
}

def validate_observation(pollutant: str, value: float) -> str:
    """
    Validates a single observation against physical boundaries.
    Returns the qa_flag (VALID, INVALID, SUSPECT)
    """
    if pd.isna(value):
        return "MISSING"
        
    bounds = QA_BOUNDS.get(pollutant)
    
    if bounds:
        if value < bounds["min"] or value > bounds["max"]:
            return "INVALID"
            
    # Additional logic for spikes or stuck values would go here.
    # For now, default to VALID.
    return "VALID"

def apply_qa_flags(observations: List[CommonObservationSchema]) -> List[CommonObservationSchema]:
    """Applies QA flags to a list of observations."""
    for obs in observations:
        obs.qa_flag = validate_observation(obs.pollutant, obs.value)
    return observations
