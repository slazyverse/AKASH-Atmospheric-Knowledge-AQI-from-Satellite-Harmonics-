"""
Centralized Feature Validation Schema for the AQI pipeline.

Defines every feature with:
  - Expected data type
  - Expected unit, with per-stage overrides for features that legitimately change units
    between pipeline stages (e.g. Temperature: K in ERA5 raw, Celsius if converted)
  - Valid numeric range
  - Source dataset
  - Which pipeline stages the feature must appear in
  - Whether the feature must be in the ML model input

Temporal offset window
----------------------
The satellite collector uses:
  TEMPORAL_WINDOW_DAYS = 3       (±3 days around the effective date)
  MAX_ADAPTIVE_LOOKBACK_DAYS = 14 (max backward shift when collection has publication lag
                                   or cloud cover during the Indian monsoon; configured
                                   via config.SATELLITE_LOOKBACK_DAYS)

The expected offset range for any product is therefore:
  [-MAX_ADAPTIVE_LOOKBACK_DAYS, +TEMPORAL_WINDOW_DAYS] = [-14, +3]

  Observations within this window → PASS (adaptive shift is operating within design limits).
  Observations outside this window → WARNING (investigate) (the contributing observation
  falls outside the configured collection window; not a normal operational condition).

Do NOT silently expand this range without a documented scientific justification. Any change
to SATELLITE_LOOKBACK_DAYS must be reflected in both config.py and this docstring.

Provenance null coupling
------------------------
Provenance fields (Obs Date, Temporal Offset, QA Status, Publication Lag) are null whenever
the parent science feature is null (e.g. AOD=null due to cloud cover). In that case,
provenance nulls are WARN_EXPECTED, not data-quality warnings. The validator reads the
PROVENANCE_SCIENCE_MAP to apply this conditional logic.

Per-stage unit support
----------------------
StageSpec lets a feature declare a different unit at a specific pipeline stage.

Pipeline stages (PIPELINE_STAGES)
----------------------------------
1. satellite_predictors  – processed_data/satellite_predictors.csv
2. merged_feature_table  – features/merged_feature_table.csv
3. analysis_ready_dataset – analysis_ready_dataset.csv (root)
4. train_dataset         – train_dataset.csv (root)
5. ml_model              – FeatureGroupManager model input
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from data_collection_pipeline import config

# ---------------------------------------------------------------------------
# Pipeline temporal window constants — kept in sync with sentinel5p_collector
# ---------------------------------------------------------------------------

#: Default ±window around the effective date (days); mirrors TEMPORAL_WINDOW_DAYS
TEMPORAL_WINDOW_DAYS: int = 3

#: Maximum backward lookback when target date has no imagery; mirrors MAX_ADAPTIVE_LOOKBACK_DAYS
MAX_ADAPTIVE_LOOKBACK_DAYS: int = getattr(config, "SATELLITE_LOOKBACK_DAYS", 7)

#: Derived valid temporal offset range: [-MAX_ADAPTIVE_LOOKBACK_DAYS, +TEMPORAL_WINDOW_DAYS]
TEMPORAL_OFFSET_RANGE: Tuple[float, float] = (
    float(-MAX_ADAPTIVE_LOOKBACK_DAYS),
    float(TEMPORAL_WINDOW_DAYS),
)

# ---------------------------------------------------------------------------
# Stage constants
# ---------------------------------------------------------------------------

PIPELINE_STAGES: List[str] = [
    "Collector",
    "Merger",
    "Dataset Builder",
    "merged_feature_table.csv",
    "analysis_ready_dataset.csv",
    "train_dataset.csv",
    "FeatureGroupManager",
]

#: Feature groups consumed by the ML model (mirrors baseline_model.py)
ML_MODEL_GROUPS: List[str] = ["satellite", "meteorology", "geography", "temporal"]

# ---------------------------------------------------------------------------
# Provenance ↔ science feature coupling
#
# Each provenance field is null when the corresponding science feature is null.
# The validator uses this map to avoid reporting provenance nulls as data-quality
# warnings when the science feature is also null (expected: cloud cover, QA fail).
# ---------------------------------------------------------------------------

#: Maps provenance field name → science feature name
PROVENANCE_SCIENCE_MAP: Dict[str, str] = {
    f"{product} {prov}": product
    for product in ["AOD", "HCHO", "NO2 Column", "SO2 Column", "CO Column", "O3 Column"]
    for prov in ["Obs Date", "Temporal Offset", "QA Status", "Publication Lag"]
}


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class StageSpec:
    """Per-pipeline-stage unit and range override.

    When a feature legitimately changes unit between stages (e.g. Temperature
    Kelvin → Celsius after conversion), add a StageSpec for each relevant stage.
    If valid_range is None the parent FeatureSpec.valid_range applies unchanged.
    """
    unit: str
    valid_range: Optional[Tuple[float, float]] = None


@dataclass
class FeatureSpec:
    """Specification for a single pipeline feature.

    Parameters
    ----------
    name : Column name as it appears in pipeline CSVs.
    group : Logical group: target | satellite | meteorology | geography |
            temporal | provenance | metadata.
    dtype : Expected dtype category: numeric | categorical | boolean | datetime | string.
    unit : Default unit (used for any stage without a stage_overrides entry).
    source : Origin dataset or system.
    description : Human-readable description.
    valid_range : (min, max) for numeric; None = no range check.
    stage_overrides : Dict mapping stage name → StageSpec for per-stage checks.
    expected_stages : Stages where this feature MUST be present.
    in_model : True if this feature must appear in ML model input.
    valid_categories : Allowed values for categorical dtype.
    null_warn_pct : Warn if null percentage exceeds this threshold (0–100).
    null_fail_pct : Fail if null percentage meets or exceeds this threshold (0–100).
    provenance_for : Science feature name if this is a provenance field; None otherwise.
                     When set, null checks are conditional on the science feature's
                     nullness (provenance null when science null → WARN_EXPECTED).
    """
    name: str
    group: str
    dtype: str
    unit: str
    source: str
    description: str
    valid_range: Optional[Tuple[float, float]] = None
    stage_overrides: Dict[str, StageSpec] = field(default_factory=dict)
    expected_stages: List[str] = field(default_factory=list)
    in_model: bool = False
    valid_categories: Optional[List[str]] = None
    null_warn_pct: float = 20.0
    null_fail_pct: float = 100.0
    provenance_for: Optional[str] = None  # science feature this provenance field belongs to
    null_expected_reason: Optional[str] = None  # if set, high null rate is WARN_EXPECTED
    context_aware_validation: bool = False
    product_family: Optional[str] = None  # e.g., "modis_maiac", "sentinel5p"
    feature_role: str = ""

    def __post_init__(self):
        if not self.feature_role:
            if self.group == "provenance":
                self.feature_role = "provenance"
            elif self.group == "target":
                self.feature_role = "target"
            elif self.group == "meteorology":
                self.feature_role = "meteorology"
            elif self.group == "geography":
                self.feature_role = "geographic" if self.dtype == "numeric" else "categorical"
            elif self.group == "temporal":
                self.feature_role = "temporal" if (self.dtype != "categorical" and self.dtype != "boolean") else "categorical"
            elif self.dtype in ("categorical", "boolean", "string"):
                self.feature_role = "categorical"
            elif self.group == "satellite":
                self.feature_role = "science"
            else:
                self.feature_role = "provenance"

    def get_unit(self, stage: str) -> str:
        override = self.stage_overrides.get(stage)
        return override.unit if override else self.unit

    def get_valid_range(self, stage: str) -> Optional[Tuple[float, float]]:
        override = self.stage_overrides.get(stage)
        if override and override.valid_range is not None:
            return override.valid_range
        return self.valid_range


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _all_stages(*exclude: str) -> List[str]:
    """Return all PIPELINE_STAGES except the ones listed."""
    return [s for s in PIPELINE_STAGES if s not in exclude]


# ---------------------------------------------------------------------------
# Centralized feature schema
# ---------------------------------------------------------------------------

PIPELINE_FEATURE_SCHEMA: Dict[str, FeatureSpec] = {

    # =========================================================================
    # 1. Target / Ground-truth pollutants (CPCB)
    # =========================================================================
    "PM2.5": FeatureSpec(
        name="PM2.5", group="target", dtype="numeric", unit="µg/m³",
        source="CPCB", description="Fine particulate matter (PM2.5) ground concentration",
        valid_range=(0.0, 1000.0),
        expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
    ),
    "PM10": FeatureSpec(
        name="PM10", group="target", dtype="numeric", unit="µg/m³",
        source="CPCB", description="Coarse particulate matter (PM10) ground concentration",
        valid_range=(0.0, 1500.0),
        expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
    ),
    "NO2": FeatureSpec(
        name="NO2", group="target", dtype="numeric", unit="µg/m³",
        source="CPCB", description="NO2 ground concentration",
        valid_range=(0.0, 1000.0),
        expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
    ),
    "SO2": FeatureSpec(
        name="SO2", group="target", dtype="numeric", unit="µg/m³",
        source="CPCB", description="SO2 ground concentration",
        valid_range=(0.0, 2000.0),
        expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
    ),
    "CO": FeatureSpec(
        name="CO", group="target", dtype="numeric", unit="mg/m³",
        source="CPCB", description="CO ground concentration",
        valid_range=(0.0, 100.0),
        expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
    ),
    "O3": FeatureSpec(
        name="O3", group="target", dtype="numeric", unit="µg/m³",
        source="CPCB", description="Ozone ground concentration",
        valid_range=(0.0, 1000.0),
        expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
    ),
    "AQI": FeatureSpec(
        name="AQI", group="target", dtype="numeric", unit="index",
        source="CPCB", description="Air Quality Index (0–500 scale)",
        valid_range=(0.0, 500.0),
        expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
        null_fail_pct=100.0,
    ),

    # =========================================================================
    # 2. Satellite science features
    #
    # AOD NOTE: Physical range 0.0–5.0 (physical AOD units after ×0.001 scaling).
    # AOD null rate is typically >50% during Indian monsoon (June–September) due to
    # cloud cover — this is WARN_EXPECTED, not a pipeline bug.
    # =========================================================================
    "AOD": FeatureSpec(
        name="AOD", group="satellite", dtype="numeric",
        unit="unitless (physical AOD, scale factor 0.001 applied)",
        source="MODIS MAIAC",
        description=(
            "Aerosol Optical Depth at 550 nm. Physical range 0-5. "
            "MODIS stores as integer * 0.001; scale factor is applied in the collector. "
            "Null rate >50% during Indian monsoon (June-September) is expected due to "
            "cloud cover masking - classified WARN_EXPECTED, not a data-quality failure."
        ),
        valid_range=(0.0, 5.0),
        expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
        in_model=True,
        context_aware_validation=True,
        product_family="modis_maiac",
        null_expected_reason=(
            "MODIS MAIAC Level-2 AOD retrievals (MCD19A2) are severely limited by persistent cloud "
            "cover and surface reflectance issues during the Indian summer monsoon (June-September). "
            "Missing granules are expected. The standard AOD_QA bitmask is applied to select "
            "best-quality retrievals, natively dropping cloud-contaminated pixels. "
            "Refer to the MODIS MAIAC ATBD and User Guide."
        ),
    ),
    "HCHO": FeatureSpec(
        name="HCHO", group="satellite", dtype="numeric", unit="mol/m2",
        source="TROPOMI S5P OFFL L3_HCHO",
        description=(
            "Formaldehyde (HCHO) tropospheric vertical column density. "
            "Small negative values (to ~-0.001 mol/m2) are physically valid in clean-air "
            "scenes due to TROPOMI retrieval noise; KNMI specification retains them."
        ),
        valid_range=(-0.001, 0.01),
        expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
        in_model=True,
        context_aware_validation=True,
        product_family="sentinel5p",
        null_expected_reason=(
            "TROPOMI Sentinel-5P Level-2 Formaldehyde retrievals are heavily constrained by monsoon "
            "cloud cover. Standard quality filtering uses qa_value > 0.5 to exclude cloud-contaminated, "
            "snow/ice, or high solar zenith angle pixels as recommended in the KNMI HCHO Product Readme "
            "(S5P-MPC-KNMI-PRF-HCHO). GEE ingests the operational Level-3 gridded dataset which already "
            "applies this standard quality filter. Our secondary pipeline QA filtering (cloud_fraction < 0.5) "
            "further masks remaining contaminated pixels. Refer to the Sentinel-5P HCHO ATBD (S5P-L2-HCHO-ATBD)."
        ),
    ),
    "NO2 Column": FeatureSpec(
        name="NO2 Column", group="satellite", dtype="numeric", unit="mol/m2",
        source="TROPOMI S5P OFFL L3_NO2",
        description="Tropospheric NO2 vertical column number density",
        valid_range=(0.0, 0.01),
        expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
        in_model=True,
        context_aware_validation=True,
        product_family="sentinel5p",
        null_expected_reason=(
            "TROPOMI Sentinel-5P Level-2 NO2 retrievals require qa_value > 0.75 for standard application "
            "to ensure cloud-free conditions (cloud fraction < 0.2) as per the KNMI NO2 Product Readme "
            "(S5P-MPC-KNMI-PRF-NO2). GEE ingests the gridded Level-3 dataset which has this standard "
            "filtering pre-applied. Our secondary pipeline QA filtering (cloud_fraction < 0.5) ensures "
            "ML consistency. During the monsoon, high cloud masking leads to typical data loss. "
            "Refer to the Sentinel-5P NO2 ATBD (S5P-L2-NO2-ATBD)."
        ),
    ),
    "SO2 Column": FeatureSpec(
        name="SO2 Column", group="satellite", dtype="numeric", unit="mol/m2",
        source="TROPOMI S5P OFFL L3_SO2",
        description=(
            "SO2 total vertical column density. Negative values (to ~-0.001 mol/m2) are "
            "physically valid in very-low-SO2 scenes; TROPOMI SO2 retrieval is an "
            "incremental measurement relative to a reference spectrum."
        ),
        valid_range=(-0.001, 0.05),
        expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
        in_model=True,
        context_aware_validation=True,
        product_family="sentinel5p",
        null_expected_reason=(
            "TROPOMI Sentinel-5P Level-2 SO2 UV retrievals (310-325 nm via DOAS) are highly sensitive to "
            "noise, Rayleigh scattering, and ozone absorption. The standard quality threshold is qa_value > 0.5 "
            "to remove cloud, snow/ice, and large solar zenith angle scenes, as specified in the KNMI SO2 "
            "Product Readme (S5P-MPC-KNMI-PRF-SO2). GEE ingests the Level-3 gridded dataset pre-filtered at this "
            "threshold. Our secondary pipeline QA filtering (cloud_fraction < 0.5) and monsoon cloud cover "
            "masking result in data missingness of up to 80% over India in summer months. Refer to the "
            "Sentinel-5P SO2 ATBD (S5P-L2-SO2-ATBD)."
        ),
    ),
    "CO Column": FeatureSpec(
        name="CO Column", group="satellite", dtype="numeric", unit="mol/m2",
        source="TROPOMI S5P OFFL L3_CO",
        description="CO total column number density",
        valid_range=(0.0, 0.5),
        expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
        in_model=True,
        context_aware_validation=True,
        product_family="sentinel5p",
        null_expected_reason=(
            "TROPOMI Sentinel-5P Level-2 CO retrievals in the SWIR band are less sensitive to thin clouds "
            "but are still masked under thick cloud cover. Standard quality filtering uses qa_value > 0.5 "
            "as per the SRON CO Product Readme (S5P-MPC-SRON-PRF-CO). GEE gridded Level-3 products are "
            "pre-filtered at this threshold. Our secondary pipeline QA filtering (cloud_fraction < 0.5) "
            "masks out heavy cloud contamination. Refer to the Sentinel-5P CO ATBD (S5P-L2-CO-ATBD)."
        ),
    ),
    "O3 Column": FeatureSpec(
        name="O3 Column", group="satellite", dtype="numeric", unit="mol/m2",
        source="TROPOMI S5P OFFL L3_O3",
        description="O3 total vertical column density",
        valid_range=(0.0, 0.5),
        expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
        in_model=True,
        context_aware_validation=True,
        product_family="sentinel5p",
        null_expected_reason=(
            "TROPOMI Sentinel-5P Level-2 Ozone UV retrievals require qa_value > 0.5 for standard data use, "
            "which excludes cloudy or snow/ice pixels as specified in the DLR O3 Product Readme "
            "(S5P-MPC-DLR-PRF-O3). GEE ingests the Level-3 gridded dataset which has this quality screening "
            "pre-applied. Our secondary pipeline QA filtering (cloud_fraction < 0.5) further removes "
            "cloudy pixels. Refer to the Sentinel-5P O3 ATBD (S5P-L2-O3-ATBD)."
        ),
    ),

    # =========================================================================
    # 3. Meteorological features (ERA5)
    #
    # Temperature is stored in Kelvin throughout the pipeline (ERA5 native unit).
    # If a future conversion to Celsius is added, uncomment the stage_overrides
    # block and update valid_range for converted stages.
    # =========================================================================
    "Temperature": FeatureSpec(
        name="Temperature", group="meteorology", dtype="numeric",
        unit="K",
        source="ERA5",
        description=(
            "2 m air temperature. Stored in Kelvin throughout the pipeline (ERA5 native). "
            "Valid range 200–330 K covers terrestrial surface temperatures for India. "
            "If a Kelvin → Celsius conversion is added downstream, add a StageSpec "
            "with unit='°C' and valid_range=(-50.0, 60.0) for the converted stages."
        ),
        valid_range=(200.0, 330.0),
        # Celsius stage override — uncomment when conversion is implemented:
        # stage_overrides={
        #     "merged_feature_table": StageSpec(unit="°C", valid_range=(-50.0, 60.0)),
        # },
        expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
        in_model=True,
    ),
    "Relative Humidity": FeatureSpec(
        name="Relative Humidity", group="meteorology", dtype="numeric", unit="%",
        source="ERA5",
        description=(
            "Relative humidity. Physical range strictly 0–100%. "
            "ERA5 may occasionally produce values marginally above 100% due to "
            "spectral truncation artefacts in the ECMWF model (values up to ~100.5% "
            "are documented in ECMWF validation reports and are not a pipeline bug). "
            "valid_range is set to (0.0, 100.5) to prevent false FAIL for these "
            "known artefacts; the scientific_validation check (Check 12) "
            "distinguishes: values in [100.0, 100.5] → WARN_EXPECTED (ERA5 artefact, documented); "
            "values above 100.5 → FAIL (genuine out-of-range). "
            "This is the ONLY accepted expansion beyond physical range and is "
            "explicitly documented here — do NOT expand further without scientific justification."
        ),
        valid_range=(0.0, 100.5),
        expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
        in_model=True,
    ),
    "Boundary Layer Height": FeatureSpec(
        name="Boundary Layer Height", group="meteorology", dtype="numeric", unit="m",
        source="ERA5", description="Planetary boundary layer height",
        valid_range=(0.0, 6000.0),
        expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
        in_model=True,
    ),
    "Wind Speed": FeatureSpec(
        name="Wind Speed", group="meteorology", dtype="numeric", unit="m/s",
        source="ERA5 (derived)", description="Wind speed derived from U/V components",
        valid_range=(0.0, 100.0),
        expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
        in_model=True,
    ),
    "Wind Direction": FeatureSpec(
        name="Wind Direction", group="meteorology", dtype="numeric", unit="degrees",
        source="ERA5 (derived)",
        description="Wind direction (meteorological convention). Range strictly 0–360°.",
        valid_range=(0.0, 360.0),
        expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
        in_model=True,
    ),
    "Surface Pressure": FeatureSpec(
        name="Surface Pressure", group="meteorology", dtype="numeric", unit="Pa",
        source="ERA5", description="Surface atmospheric pressure",
        valid_range=(45000.0, 110000.0),
        expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
        in_model=True,
    ),

    # =========================================================================
    # 4. Geographic features
    # =========================================================================
    "Latitude": FeatureSpec(
        name="Latitude", group="geography", dtype="numeric", unit="degrees",
        source="Station registry", description="Station latitude (India: ~6–38°N)",
        valid_range=(5.0, 40.0),
        expected_stages=["Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
        in_model=True,
    ),
    "Longitude": FeatureSpec(
        name="Longitude", group="geography", dtype="numeric", unit="degrees",
        source="Station registry", description="Station longitude (India: ~65–100°E)",
        valid_range=(65.0, 100.0),
        expected_stages=["Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
        in_model=True,
    ),
    "Elevation": FeatureSpec(
        name="Elevation", group="geography", dtype="numeric", unit="m",
        source="DEM", description="Altitude above sea level",
        valid_range=(-100.0, 9000.0),
        expected_stages=[],
        in_model=False,
    ),
    "Distance to Coast": FeatureSpec(
        name="Distance to Coast", group="geography", dtype="numeric", unit="km",
        source="GIS", description="Distance to nearest shoreline",
        valid_range=(0.0, 2000.0),
        expected_stages=[],
        in_model=False,
    ),
    "Land Cover Class": FeatureSpec(
        name="Land Cover Class", group="geography", dtype="categorical", unit="class index",
        source="MODIS", description="Dominant land cover type index",
        expected_stages=[],
        in_model=False,
    ),

    # =========================================================================
    # 5. Temporal / derived features
    # =========================================================================
    "Day of Week": FeatureSpec(
        name="Day of Week", group="temporal", dtype="numeric", unit="index (0=Monday)",
        source="Derived from timestamp", description="Day of week (0=Monday, 6=Sunday)",
        valid_range=(0.0, 6.0),
        expected_stages=["Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
        in_model=True,
    ),
    "Month": FeatureSpec(
        name="Month", group="temporal", dtype="numeric", unit="index (1–12)",
        source="Derived from timestamp", description="Calendar month (1–12)",
        valid_range=(1.0, 12.0),
        expected_stages=["Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
        in_model=True,
    ),
    "Season": FeatureSpec(
        name="Season", group="temporal", dtype="categorical", unit="category",
        source="Derived from Month",
        description="India meteorological season: Winter, Pre-Monsoon, Monsoon, Post-Monsoon",
        valid_categories=["Winter", "Pre-Monsoon", "Monsoon", "Post-Monsoon"],
        expected_stages=["Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
        in_model=True,
    ),
    "Weekend Flag": FeatureSpec(
        name="Weekend Flag", group="temporal", dtype="boolean", unit="bool",
        source="Derived from Day of Week",
        description="True if Saturday or Sunday",
        expected_stages=["Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
        in_model=True,
    ),

    # =========================================================================
    # 6. Satellite provenance / metadata fields
    #
    # Provenance fields are null whenever the corresponding science feature is null.
    # The validator uses PROVENANCE_SCIENCE_MAP to distinguish:
    #   - provenance_null AND science_null   → WARN_EXPECTED (cloud cover / QA mask)
    #   - provenance_null AND science present → WARN_INVESTIGATE (missing provenance)
    #   - provenance present AND science_null → WARN_INVESTIGATE (inconsistency)
    # =========================================================================
    **{
        f"{product} Obs Date": FeatureSpec(
            name=f"{product} Obs Date",
            group="provenance",
            dtype="string",
            unit="date (YYYY-MM-DD)",
            source="GEE / satellite collector",
            description=(
                f"Actual acquisition date of the {product} observation used. "
                f"Null when the science feature is null (cloud cover / QA masking)."
            ),
            expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
            in_model=False,
            null_warn_pct=20.0,
            provenance_for=product,
        )
        for product in ["AOD", "HCHO", "NO2 Column", "SO2 Column", "CO Column", "O3 Column"]
    },
    **{
        f"{product} Temporal Offset": FeatureSpec(
            name=f"{product} Temporal Offset",
            group="provenance",
            dtype="numeric",
            unit="days",
            source="GEE / satellite collector",
            description=(
                f"Temporal offset of the {product} observation from the effective target date "
                f"(negative = earlier, positive = later). "
                f"Expected range: [{-MAX_ADAPTIVE_LOOKBACK_DAYS}, +{TEMPORAL_WINDOW_DAYS}] days, "
                f"where {MAX_ADAPTIVE_LOOKBACK_DAYS} = MAX_ADAPTIVE_LOOKBACK_DAYS and "
                f"{TEMPORAL_WINDOW_DAYS} = TEMPORAL_WINDOW_DAYS. "
                f"Values outside this range are flagged WARN_INVESTIGATE. "
                f"Null when the science feature is null."
            ),
            valid_range=TEMPORAL_OFFSET_RANGE,
            expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
            in_model=False,
            null_warn_pct=20.0,
            provenance_for=product,
        )
        for product in ["AOD", "HCHO", "NO2 Column", "SO2 Column", "CO Column", "O3 Column"]
    },
    **{
        f"{product} Publication Lag": FeatureSpec(
            name=f"{product} Publication Lag",
            group="provenance",
            dtype="numeric",
            unit="days",
            source="GEE / satellite collector",
            description=(
                f"Publication lag of the {product} collection relative to the requested date "
                f"(0 = available on time, N = N days behind). Must be non-negative. "
                f"Null when the science feature is null."
            ),
            valid_range=(0.0, 30.0),
            expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
            in_model=False,
            provenance_for=product,
        )
        for product in ["AOD", "HCHO", "NO2 Column", "SO2 Column", "CO Column", "O3 Column"]
    },
    **{
        f"{product} QA Status": FeatureSpec(
            name=f"{product} QA Status",
            group="provenance",
            dtype="numeric",
            unit="qa_value",
            source="GEE / satellite collector",
            description=(
                f"QA value for {product}. "
                f"Sentinel-5P cloud fraction: 0–1 (threshold <0.5). "
                f"MODIS MAIAC AOD: AOD_QA bitmask integer (non-negative). "
                f"CO Column has no native QA band; sentinel value -1 is used. "
                f"Null when the science feature is null."
            ),
            valid_range=(-1.0, 32767.0),
            expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
            in_model=False,
            null_warn_pct=20.0,
            provenance_for=product,
        )
        for product in ["AOD", "HCHO", "NO2 Column", "SO2 Column", "CO Column", "O3 Column"]
    },

    # =========================================================================
    # 7. Pipeline-level metadata / provenance
    # =========================================================================
    "placeholder_used": FeatureSpec(
        name="placeholder_used",
        group="provenance",
        dtype="boolean",
        unit="bool",
        source="sentinel5p_collector / merger",
        description=(
            "True when this row is a NaN sentinel inserted because the station returned "
            "no data from any GEE product. Rows where placeholder_used=True must have all "
            "satellite features null; rows where placeholder_used=False and satellite features "
            "are null indicate cloud/QA masking (expected)."
        ),
        expected_stages=["Collector", "Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
        in_model=False,
    ),
    "requested_date": FeatureSpec(
        name="requested_date",
        group="provenance",
        dtype="string",
        unit="date (YYYY-MM-DD)",
        source="sentinel5p_collector",
        description="The originally requested satellite acquisition date before adaptive shifting",
        expected_stages=["Collector"],
        in_model=False,
    ),
    "satellite_match_distance_km": FeatureSpec(
        name="satellite_match_distance_km",
        group="provenance",
        dtype="numeric",
        unit="km",
        source="feature_engineering merger",
        description="Distance between CPCB station and nearest satellite grid point",
        valid_range=(0.0, 50.0),
        expected_stages=["Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
        in_model=False,
    ),
    "era5_match_distance_km": FeatureSpec(
        name="era5_match_distance_km",
        group="provenance",
        dtype="numeric",
        unit="km",
        source="feature_engineering merger",
        description="Distance between CPCB station and nearest ERA5 grid point",
        valid_range=(0.0, 50.0),
        expected_stages=["Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
        in_model=False,
    ),

    # =========================================================================
    # 8. Station metadata
    # =========================================================================
    "Station ID": FeatureSpec(
        name="Station ID", group="metadata", dtype="string", unit="id",
        source="CPCB station registry",
        description="Unique CPCB monitoring station code (e.g. DL_01)",
        expected_stages=["Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
    ),
    "Station Name": FeatureSpec(
        name="Station Name", group="metadata", dtype="string", unit="name",
        source="CPCB station registry",
        description="Human-readable name of the monitoring station",
        expected_stages=["Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
    ),
    "Date": FeatureSpec(
        name="Date", group="metadata", dtype="string", unit="date (YYYY-MM-DD)",
        source="Pipeline",
        description="Observation date string",
        expected_stages=["Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
    ),
    "Time": FeatureSpec(
        name="Time", group="metadata", dtype="string", unit="time (HH:MM:SS)",
        source="Pipeline",
        description="Observation time string",
        expected_stages=["Merger", "Dataset Builder", "merged_feature_table.csv", "analysis_ready_dataset.csv", "train_dataset.csv"],
    ),
}
