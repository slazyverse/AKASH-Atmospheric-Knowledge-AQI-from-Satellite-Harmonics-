"""Unit tests for PBL Feature Engine (ISSUE-#04)."""

import math
import pytest
import numpy as np
import pandas as pd

from data_collection_pipeline.pbl_feature_engine import (
    PBL_FEATURES,
    compute_ventilation_index,
    compute_inversion_lapse_rate,
    compute_hygroscopic_growth_factor,
    compute_pbl_features,
)
from data_collection_pipeline.feature_engineering.feature_builder import build_features, ALL_FEATURES


# ============================================================================
# 1. Ventilation Index Tests
# ============================================================================

def test_ventilation_index_normal_conditions():
    """VI under standard atmospheric conditions: PBLH=1000m, Wind Speed=5m/s -> 5000 m^2/s."""
    vi = compute_ventilation_index(pbl_height=1000.0, wind_speed=5.0)
    assert pytest.approx(vi, rel=1e-5) == 5000.0


def test_ventilation_index_zero_wind_speed():
    """VI with zero wind speed: PBLH=1000m, Wind Speed=0m/s -> 0 m^2/s."""
    vi = compute_ventilation_index(pbl_height=1000.0, wind_speed=0.0)
    assert vi == 0.0


def test_ventilation_index_zero_pbl_height():
    """VI with zero PBL height: PBLH=0m, Wind Speed=5m/s -> 0 m^2/s."""
    vi = compute_ventilation_index(pbl_height=0.0, wind_speed=5.0)
    assert vi == 0.0


def test_ventilation_index_missing_or_invalid_values():
    """VI with missing/NaN values returns 0.0 without raising errors or returning NaN."""
    assert compute_ventilation_index(pbl_height=None, wind_speed=5.0) == 0.0
    assert compute_ventilation_index(pbl_height=1000.0, wind_speed=np.nan) == 0.0
    assert compute_ventilation_index(pbl_height=np.nan, wind_speed=np.nan) == 0.0


# ============================================================================
# 2. Inversion Lapse Rate Tests
# ============================================================================

def test_inversion_lapse_rate_inversion_present():
    """Inversion present: T=300K, PBLH=500m, Ps=101325Pa -> potential temperature gradient ≈ 0.003525 K/m."""
    lr = compute_inversion_lapse_rate(temperature=300.0, pbl_height=500.0, surface_pressure=101325.0)
    assert pytest.approx(lr, rel=1e-3) == 0.003525


def test_inversion_lapse_rate_temperature_sensitivity():
    """Verify temperature is active in calculation (higher T leads to different potential temp gradient)."""
    lr1 = compute_inversion_lapse_rate(temperature=280.0, pbl_height=500.0, surface_pressure=101325.0)
    lr2 = compute_inversion_lapse_rate(temperature=310.0, pbl_height=500.0, surface_pressure=101325.0)
    assert lr1 != lr2


def test_inversion_lapse_rate_missing_inputs():
    """Missing temperature/pressure/PBLH handled safely with fallback defaults and no NaNs."""
    lr_missing_t = compute_inversion_lapse_rate(temperature=None, pbl_height=500.0)
    assert not math.isnan(lr_missing_t) and not math.isinf(lr_missing_t)

    lr_missing_pbl = compute_inversion_lapse_rate(temperature=300.0, pbl_height=None)
    assert not math.isnan(lr_missing_pbl) and not math.isinf(lr_missing_pbl)


# ============================================================================
# 3. Hygroscopic Growth Factor Tests
# ============================================================================

def test_hygroscopic_growth_factor_rh_zero():
    """RH = 0%: f(0) = (1 - 0)^(-0.25) = 1.0."""
    gf = compute_hygroscopic_growth_factor(relative_humidity=0.0)
    assert pytest.approx(gf, rel=1e-5) == 1.0


def test_hygroscopic_growth_factor_rh_50():
    """RH = 50%: f(50) = (0.5)^(-0.25) ≈ 1.1892."""
    gf = compute_hygroscopic_growth_factor(relative_humidity=50.0)
    assert pytest.approx(gf, rel=1e-4) == 1.189207


def test_hygroscopic_growth_factor_rh_90():
    """RH = 90%: f(90) = (0.1)^(-0.25) ≈ 1.7783."""
    gf = compute_hygroscopic_growth_factor(relative_humidity=90.0)
    assert pytest.approx(gf, rel=1e-4) == 1.778279


def test_hygroscopic_growth_factor_rh_upper_limit():
    """RH near upper limit (RH = 98%): f(98) = (0.02)^(-0.25) ≈ 2.6591."""
    gf = compute_hygroscopic_growth_factor(relative_humidity=98.0)
    assert pytest.approx(gf, rel=1e-4) == 2.659148


def test_hygroscopic_growth_factor_invalid_rh():
    """Invalid RH (< 0%, > 100%, NaN) is safely clamped and never produces NaN/inf."""
    assert compute_hygroscopic_growth_factor(relative_humidity=-10.0) == 1.0
    assert pytest.approx(compute_hygroscopic_growth_factor(relative_humidity=150.0), rel=1e-4) == 2.659148
    assert compute_hygroscopic_growth_factor(relative_humidity=np.nan) == 1.189207115002721


# ============================================================================
# 4. Pipeline Integration & Numerical Stability Tests
# ============================================================================

def test_pipeline_integration_build_features():
    """Verify build_features() generates all 3 PBL features without NaNs or infs."""
    df_raw = pd.DataFrame({
        "timestamp": pd.date_range("2026-07-24 00:00:00", periods=5, freq="h"),
        "Temperature": [290.0, 295.0, 300.0, np.nan, 310.0],
        "Relative Humidity": [30.0, 50.0, 90.0, 99.0, np.nan],
        "Boundary Layer Height": [400.0, 0.0, 1200.0, np.nan, 800.0],
        "Surface Pressure": [101325.0, 100000.0, np.nan, 95000.0, 102000.0],
        "u_wind_component": [3.0, 0.0, -4.0, np.nan, 2.0],
        "v_wind_component": [4.0, 0.0, 3.0, np.nan, 0.0],
    })

    features = build_features(df_raw)

    # 1. Verify feature existence
    for col in PBL_FEATURES:
        assert col in features.columns, f"Feature '{col}' missing from build_features output"

    # 2. Verify features included in ALL_FEATURES schema
    for col in PBL_FEATURES:
        assert col in ALL_FEATURES, f"Feature '{col}' missing from ALL_FEATURES list"

    # 3. Verify data type
    for col in PBL_FEATURES:
        assert pd.api.types.is_numeric_dtype(features[col]), f"Feature '{col}' is not numeric dtype"

    # 4. Numerical Stability Proof (No NaN, No +inf, No -inf)
    for col in PBL_FEATURES:
        assert features[col].isna().sum() == 0, f"Feature '{col}' contains NaN values"
        assert np.isfinite(features[col]).all(), f"Feature '{col}' contains non-finite (inf) values"

    # 5. Verify physical value ranges
    assert (features["Ventilation Index"] >= 0.0).all()
    assert (features["Inversion Lapse Rate"] >= 0.0).all()
    assert (features["Hygroscopic Growth Factor"] >= 1.0).all()
