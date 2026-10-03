"""
Unit tests for the CPCB AQI Breakpoint Calculation module.
"""

import pytest
import math
from data_collection_pipeline.aqi_calculator import (
    calculate_sub_index,
    validate_cpcb_requirements,
    aggregate_aqi,
    calculate_overall_aqi,
    standardize_pollutant_name
)


def test_standardize_pollutant_name():
    """Test case-insensitivity and synonym standardisation."""
    assert standardize_pollutant_name("pm25") == "PM2.5"
    assert standardize_pollutant_name("PM2_5") == "PM2.5"
    assert standardize_pollutant_name("pm 2.5") == "PM2.5"
    assert standardize_pollutant_name("ozone") == "O3"
    assert standardize_pollutant_name("O3") == "O3"
    assert standardize_pollutant_name("lead") == "Pb"
    assert standardize_pollutant_name("unsupported_xyz") is None
    assert standardize_pollutant_name(None) is None


def test_exact_lower_breakpoint():
    """
    Test concentration exactly at the bottom of a bin.
    For PM2.5, Satisfactory range is 31.0 to 60.0, corresponding to AQI 51 to 100.
    At Cp = 31.0, sub-index should be 51.
    """
    sub_index_rounded = calculate_sub_index("PM2.5", 31.0, round_index=True)
    sub_index_float = calculate_sub_index("PM2.5", 31.0, round_index=False)
    
    assert sub_index_rounded == 51
    assert math.isclose(sub_index_float, 51.0)


def test_exact_upper_breakpoint():
    """
    Test concentration exactly at the top of a bin.
    For PM2.5, Satisfactory range is 31.0 to 60.0, corresponding to AQI 51 to 100.
    At Cp = 60.0, sub-index should be 100.
    """
    sub_index_rounded = calculate_sub_index("PM2.5", 60.0, round_index=True)
    sub_index_float = calculate_sub_index("PM2.5", 60.0, round_index=False)
    
    assert sub_index_rounded == 100
    assert math.isclose(sub_index_float, 100.0)


def test_mid_interval_interpolation():
    """
    Test linear interpolation inside a segment.
    For PM2.5, segment [31.0, 60.0] maps to [51.0, 100.0].
    At Cp = 45.0:
    Ip = ((100 - 51) / (60 - 31)) * (45 - 31) + 51
       = (49 / 29) * 14 + 51
       = 23.655 + 51 = 74.655.
    Rounded: 75.
    """
    sub_index_rounded = calculate_sub_index("PM2.5", 45.0, round_index=True)
    sub_index_float = calculate_sub_index("PM2.5", 45.0, round_index=False)
    
    assert sub_index_rounded == 75
    assert math.isclose(sub_index_float, 74.655172, rel_tol=1e-5)


def test_above_severe_threshold_capping():
    """
    Test concentration exceeding the highest breakpoint.
    For PM2.5, severe upper breakpoint is 380.0.
    At Cp = 450.0 (exceeding 380.0), sub-index should be capped at 500.
    """
    sub_index_rounded = calculate_sub_index("PM2.5", 450.0, round_index=True)
    sub_index_float = calculate_sub_index("PM2.5", 450.0, round_index=False)
    
    assert sub_index_rounded == 500
    assert sub_index_float == 500.0


def test_negative_and_nan_inputs():
    """Test handling of negative, NaN, and None concentration inputs."""
    assert calculate_sub_index("PM2.5", -10.0) is None
    assert calculate_sub_index("PM2.5", float("nan")) is None
    assert calculate_sub_index("PM2.5", None) is None


def test_validate_cpcb_requirements():
    """
    Test CPCB minimum data validation rules.
    - True if at least 3 pollutants present and at least one is PM2.5 or PM10.
    """
    # Case 1: Meets requirements (PM2.5, PM10, NO2 present)
    data_ok = {"PM2.5": 35.0, "PM10": 70.0, "NO2": 45.0}
    assert validate_cpcb_requirements(data_ok) is True
    
    # Case 2: 3 pollutants but NO PM2.5 or PM10 (fails)
    data_no_particulate = {"NO2": 45.0, "SO2": 20.0, "CO": 1.2}
    assert validate_cpcb_requirements(data_no_particulate) is False
    
    # Case 3: Only 2 pollutants present, even with PM2.5 (fails)
    data_insufficient_count = {"PM2.5": 35.0, "NO2": 45.0}
    assert validate_cpcb_requirements(data_insufficient_count) is False


def test_dominant_pollutant_ties():
    """
    Test tie-breaking logic when multiple pollutants share the highest sub-index.
    """
    # Sub-indices: PM2.5 = 100, PM10 = 100, NO2 = 50.
    # Tied for max: PM2.5 and PM10.
    sub_indices = {"PM2.5": 100, "PM10": 100, "NO2": 50}
    
    # Deterministic tie-breaker = True -> lexicographically first ('PM10' < 'PM2.5')
    aqi_det, dominant_det = aggregate_aqi(sub_indices, deterministic_tie_breaker=True)
    assert aqi_det == 100
    assert dominant_det == "PM10"
    
    # Deterministic tie-breaker = False -> returns list of all tied
    aqi_all, dominant_all = aggregate_aqi(sub_indices, deterministic_tie_breaker=False)
    assert aqi_all == 100
    assert dominant_all == ["PM10", "PM2.5"]


def test_calculate_overall_aqi():
    """
    Test unified helper with and without CPCB requirement enforcement.
    """
    # PM2.5 = 45.0 (sub-index = 75), PM10 = 80.0 (sub-index = 80), NO2 = 50.0 (sub-index = 62)
    concentrations = {"PM2.5": 45.0, "PM10": 80.0, "NO2": 50.0}
    
    sub_indices, overall_aqi, dominant = calculate_overall_aqi(
        concentrations,
        enforce_requirements=True,
        round_index=True
    )
    
    assert sub_indices["PM2.5"] == 75
    assert sub_indices["PM10"] == 80
    assert sub_indices["NO2"] == 62
    assert overall_aqi == 80
    assert dominant == "PM10"
    
    # Fails CPCB requirements but enforce_requirements=False
    incomplete_concentrations = {"PM2.5": 45.0, "NO2": 50.0}
    _, aqi_no_enforce, dominant_no_enforce = calculate_overall_aqi(
        incomplete_concentrations,
        enforce_requirements=False
    )
    assert aqi_no_enforce == 75
    assert dominant_no_enforce == "PM2.5"
    
    # Fails CPCB requirements and enforce_requirements=True -> AQI should be None
    _, aqi_enforce, dominant_enforce = calculate_overall_aqi(
        incomplete_concentrations,
        enforce_requirements=True
    )
    assert aqi_enforce is None
    assert dominant_enforce is None
