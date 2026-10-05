"""
Unit conversions and unit-plausibility rules shared by every adapter and
service (single source of truth).

HCHO vertical column density
  The data pipeline (Sentinel-5P TROPOMI via Earth Engine) reports mol/m².
  The API reports the conventional 10¹⁵ molecules/cm²:
      1 mol/m² = 6.02214076e23 molecules / 1e4 cm² = 6.02214076e19 molecules/cm²
               = 6.02214076e4 × 10¹⁵ molecules/cm²

CO ground concentration
  The dataset contract (team feature schema) states CO in mg/m³. Ambient CO in
  Indian cities is typically 0.3–3 mg/m³ and the CPCB 'Poor' band starts at
  10 mg/m³, so a network-wide MEDIAN above 10 mg/m³ means the column is not in
  mg/m³. Values are then served as reported but flagged "unit unverified" —
  never rescaled, because the true unit is unknown.
"""

from __future__ import annotations

MOL_M2_TO_1E15_MOLEC_CM2 = 6.02214076e4
CO_PLAUSIBLE_MEDIAN_MG_M3 = 10.0


def hcho_mol_m2_to_1e15_molec_cm2(value_mol_m2: float) -> float:
    """Convert an HCHO column from mol/m² to 10¹⁵ molecules/cm² (3 decimals)."""
    return round(value_mol_m2 * MOL_M2_TO_1E15_MOLEC_CM2, 3)
