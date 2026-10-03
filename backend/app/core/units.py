"""
Unit conversions shared by every adapter and service (single source of truth).

HCHO vertical column density
  The data pipeline (Sentinel-5P TROPOMI via Earth Engine) reports mol/m².
  The API reports the conventional 10¹⁵ molecules/cm²:
      1 mol/m² = 6.02214076e23 molecules / 1e4 cm² = 6.02214076e19 molecules/cm²
               = 6.02214076e4 × 10¹⁵ molecules/cm²
"""

from __future__ import annotations

MOL_M2_TO_1E15_MOLEC_CM2 = 6.02214076e4


def hcho_mol_m2_to_1e15_molec_cm2(value_mol_m2: float) -> float:
    """Convert an HCHO column from mol/m² to 10¹⁵ molecules/cm² (3 decimals)."""
    return round(value_mol_m2 * MOL_M2_TO_1E15_MOLEC_CM2, 3)
