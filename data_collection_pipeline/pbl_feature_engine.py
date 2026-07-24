"""Planetary Boundary Layer (PBL) Feature Engine Module for AKASH AQI Pipeline.

Calculates three physically meaningful atmospheric features for AQI prediction:
1. Ventilation Index (m^2/s): PBL Height × Wind Speed
2. Inversion Lapse Rate (K/m): Potential Temperature Gradient (dTheta/dz) across PBL Height
3. Hygroscopic Growth Factor (dimensionless): Hanel aerosol water uptake (1 - RH/100)^(-0.25)

Numerical Stability Safeguards:
- Guaranteed zero NaNs, zero +inf, zero -inf in outputs.
- Safe division guards: PBL height clamped to >= 1.0 m for division.
- Safe range clamping: Relative Humidity clamped to [0.0%, 98.0%].
- Wind Speed & PBL Height guarded to >= 0.0.
- All non-numeric or missing inputs handled with valid fallbacks.
"""

from __future__ import annotations

import logging
import math
from typing import Union
import numpy as np
import pandas as pd

logger = logging.getLogger("data_collection_pipeline.pbl_feature_engine")

PBL_FEATURES = [
    "Ventilation Index",
    "Inversion Lapse Rate",
    "Hygroscopic Growth Factor",
]


def compute_ventilation_index(
    pbl_height: Union[float, np.ndarray, pd.Series],
    wind_speed: Union[float, np.ndarray, pd.Series],
) -> Union[float, np.ndarray, pd.Series]:
    """Calculate Ventilation Index (VI) in m^2/s.

    Formula:
        VI = max(0.0, PBLH) * max(0.0, Wind_Speed)

    Units: m^2/s
    Assumptions: Boundary layer is well-mixed horizontally and vertically.
    References: Holzworth (1972), US EPA Air Quality Index / NWS Standards.
    """
    if isinstance(pbl_height, (pd.Series, np.ndarray)) or isinstance(wind_speed, (pd.Series, np.ndarray)):
        pbl = pd.to_numeric(pd.Series(pbl_height), errors="coerce").fillna(0.0).clip(lower=0.0)
        ws = pd.to_numeric(pd.Series(wind_speed), errors="coerce").fillna(0.0).clip(lower=0.0)
        res = (pbl * ws).astype(np.float64)
        clean = np.nan_to_num(res.to_numpy(), nan=0.0, posinf=0.0, neginf=0.0)
        return clean if isinstance(pbl_height, np.ndarray) else pd.Series(clean, index=pbl.index, dtype=np.float64)

    try:
        pbl_val = max(0.0, float(pbl_height)) if (pbl_height is not None and not pd.isna(pbl_height)) else 0.0
        ws_val = max(0.0, float(wind_speed)) if (wind_speed is not None and not pd.isna(wind_speed)) else 0.0
        res = pbl_val * ws_val
        return 0.0 if (math.isnan(res) or math.isinf(res)) else float(res)
    except (ValueError, TypeError):
        return 0.0


def compute_inversion_lapse_rate(
    temperature: Union[float, np.ndarray, pd.Series],
    pbl_height: Union[float, np.ndarray, pd.Series],
    surface_pressure: Union[float, np.ndarray, pd.Series] = 101325.0,
    relative_humidity: Union[float, np.ndarray, pd.Series, None] = None,
) -> Union[float, np.ndarray, pd.Series]:
    """Calculate Boundary Layer Inversion Lapse Rate / Potential Temperature Gradient (dTheta/dz) in K/m.

    Formula:
        theta_surf = T_2m * (100000 / P_s) ** 0.286
        rho = P_s / (287.058 * T_2m)
        P_pbl = max(10000.0, P_s - rho * 9.81 * PBLH)
        T_pbl = T_2m - 0.0065 * PBLH
        theta_pbl = T_pbl * (100000 / P_pbl) ** 0.286
        Gamma_inv = (theta_pbl - theta_surf) / max(PBLH, 1.0)

    Units: K/m
    Assumptions: Hydrostatic approximation across planetary boundary layer depth.
    References: Stull, R. B. (1988) An Introduction to Boundary Layer Meteorology, Eq 1.5.
    """
    g = 9.81
    r_d = 287.058
    kappa = 0.286
    gamma_env = 0.0065
    p0 = 100000.0

    if (isinstance(temperature, (pd.Series, np.ndarray)) or
        isinstance(pbl_height, (pd.Series, np.ndarray)) or
        isinstance(surface_pressure, (pd.Series, np.ndarray))):

        temp_s = pd.to_numeric(pd.Series(temperature), errors="coerce").fillna(298.15).clip(lower=180.0, upper=350.0)
        pbl_s = pd.to_numeric(pd.Series(pbl_height), errors="coerce").fillna(500.0).clip(lower=1.0)
        sp_s = pd.to_numeric(pd.Series(surface_pressure), errors="coerce").fillna(101325.0).clip(lower=30000.0, upper=110000.0)

        theta_surf = temp_s * ((p0 / sp_s) ** kappa)
        rho = sp_s / (r_d * temp_s)
        p_pbl = (sp_s - (rho * g * pbl_s)).clip(lower=10000.0)
        t_pbl = temp_s - (gamma_env * pbl_s)
        theta_pbl = t_pbl * ((p0 / p_pbl) ** kappa)

        lapse_rate = (theta_pbl - theta_surf) / pbl_s
        clean = np.nan_to_num(lapse_rate.to_numpy(), nan=0.0, posinf=0.0, neginf=0.0)
        return clean if isinstance(temperature, np.ndarray) else pd.Series(clean, index=temp_s.index, dtype=np.float64)

    try:
        temp_val = min(max(float(temperature), 180.0), 350.0) if (temperature is not None and not pd.isna(temperature)) else 298.15
        pbl_val = max(1.0, float(pbl_height)) if (pbl_height is not None and not pd.isna(pbl_height)) else 500.0
        sp_val = min(max(float(surface_pressure), 30000.0), 110000.0) if (surface_pressure is not None and not pd.isna(surface_pressure)) else 101325.0

        theta_surf = temp_val * ((p0 / sp_val) ** kappa)
        rho = sp_val / (r_d * temp_val)
        p_pbl = max(10000.0, sp_val - (rho * g * pbl_val))
        t_pbl = temp_val - (gamma_env * pbl_val)
        theta_pbl = t_pbl * ((p0 / p_pbl) ** kappa)

        res = (theta_pbl - theta_surf) / pbl_val
        return 0.0 if (math.isnan(res) or math.isinf(res)) else float(res)
    except (ValueError, TypeError):
        return 0.0


def compute_hygroscopic_growth_factor(
    relative_humidity: Union[float, np.ndarray, pd.Series],
    gamma: float = 0.25,
) -> Union[float, np.ndarray, pd.Series]:
    """Calculate Aerosol Hygroscopic Growth Factor f(RH).

    Formula:
        f(RH) = (1 - RH_clamped / 100.0) ** (-gamma)

    Units: Dimensionless (ratio)
    Assumptions: Hanel aerosol water uptake model, RH capped at 98.0% to prevent infinite aerosol growth.
    References: Hanel (1976), Petters & Kreidenweis (2007), Pitchford et al. (2007).
    """
    if isinstance(relative_humidity, (pd.Series, np.ndarray)):
        rh_s = pd.to_numeric(pd.Series(relative_humidity), errors="coerce").fillna(50.0).clip(0.0, 98.0)
        growth = (1.0 - (rh_s / 100.0)) ** (-gamma)
        clean = np.nan_to_num(growth.to_numpy(), nan=1.0, posinf=1.0, neginf=1.0)
        return clean if isinstance(relative_humidity, np.ndarray) else pd.Series(clean, index=rh_s.index, dtype=np.float64)

    try:
        rh_val = min(max(float(relative_humidity), 0.0), 98.0) if (relative_humidity is not None and not pd.isna(relative_humidity)) else 50.0
        res = (1.0 - (rh_val / 100.0)) ** (-gamma)
        return 1.0 if (math.isnan(res) or math.isinf(res)) else float(res)
    except (ValueError, TypeError):
        return 1.0


def compute_pbl_features(df: pd.DataFrame) -> pd.DataFrame:
    """Compute all 3 PBL features and attach them to DataFrame.

    Ensures no NaNs or inf values exist in the output features.
    """
    features = df.copy()

    pbl_col = "Boundary Layer Height"
    ws_col = "Wind Speed"
    temp_col = "Temperature"
    sp_col = "Surface Pressure"
    rh_col = "Relative Humidity"

    pbl_series = features[pbl_col] if pbl_col in features.columns else pd.Series(500.0, index=features.index)
    ws_series = features[ws_col] if ws_col in features.columns else pd.Series(0.0, index=features.index)
    temp_series = features[temp_col] if temp_col in features.columns else pd.Series(298.15, index=features.index)
    sp_series = features[sp_col] if sp_col in features.columns else pd.Series(101325.0, index=features.index)
    rh_series = features[rh_col] if rh_col in features.columns else pd.Series(50.0, index=features.index)

    features["Ventilation Index"] = compute_ventilation_index(pbl_series, ws_series)
    features["Inversion Lapse Rate"] = compute_inversion_lapse_rate(temp_series, pbl_series, sp_series, rh_series)
    features["Hygroscopic Growth Factor"] = compute_hygroscopic_growth_factor(rh_series)

    # Enforce strict non-null, finite values
    features["Ventilation Index"] = pd.to_numeric(features["Ventilation Index"], errors="coerce").fillna(0.0)
    features["Ventilation Index"] = np.nan_to_num(features["Ventilation Index"], nan=0.0, posinf=0.0, neginf=0.0)

    features["Inversion Lapse Rate"] = pd.to_numeric(features["Inversion Lapse Rate"], errors="coerce").fillna(0.0)
    features["Inversion Lapse Rate"] = np.nan_to_num(features["Inversion Lapse Rate"], nan=0.0, posinf=0.0, neginf=0.0)

    features["Hygroscopic Growth Factor"] = pd.to_numeric(features["Hygroscopic Growth Factor"], errors="coerce").fillna(1.0)
    features["Hygroscopic Growth Factor"] = np.nan_to_num(features["Hygroscopic Growth Factor"], nan=1.0, posinf=1.0, neginf=1.0)

    logger.info("Successfully computed PBL features: %s", PBL_FEATURES)
    return features
