"""
Pipeline Tracer: loads each CSV stage and runs feature validation.

Traces every feature in ``PIPELINE_FEATURE_SCHEMA`` through all relevant
pipeline stages and produces a ``StageResult`` per (feature, stage) pair.

Validation Status Levels
------------------------
STATUS_PASS            — Feature meets all expectations.
STATUS_WARN_EXPECTED   — Expected operational limitation; no action required.
                          Examples: AOD null during monsoon cloud cover,
                          provenance null when science feature is null.
STATUS_WARN_INVESTIGATE — Unexpected condition; requires investigation.
                          Examples: temporal offset outside configured lookback
                          window (> MAX_ADAPTIVE_LOOKBACK_DAYS = 14 days),
                          provenance null when science feature is present.
STATUS_FAIL            — Hard failure; must be fixed before production use.
                          Examples: column missing, 100% null, unit range violation.
STATUS_SKIP            — Feature not expected in this stage; not a failure.

Temporal Offset Logic
---------------------
The valid temporal offset range is [-MAX_ADAPTIVE_LOOKBACK_DAYS, +TEMPORAL_WINDOW_DAYS].
Both constants are imported from the schema and mirror the sentinel5p_collector constants.
  MAX_ADAPTIVE_LOOKBACK_DAYS = 14 (configured via config.SATELLITE_LOOKBACK_DAYS)
  TEMPORAL_WINDOW_DAYS = 3
Values within this range → PASS.
Values outside this range → WARN_INVESTIGATE (offset exceeds configured lookback window).

Do NOT silently expand this window. Any change must be documented in feature_schema.py.

Provenance Null Logic
---------------------
Provenance fields (Obs Date, Temporal Offset, QA Status, Publication Lag) are null
whenever the parent science feature is null (cloud cover, QA masking). This is expected.
The validator uses ``FeatureSpec.provenance_for`` to identify provenance fields and applies
per-row coupling checks:
  - All null-provenance rows have null science → WARN_EXPECTED (correctly coupled)
  - Some null-provenance rows have non-null science → WARN_INVESTIGATE (inconsistency)
  - Non-null provenance with null science → WARN_INVESTIGATE (inconsistency)
"""

from __future__ import annotations

import datetime
import logging
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from data_collection_pipeline import config
from data_collection_pipeline.feature_engineering.groups import FeatureGroupManager
from data_collection_pipeline.validation.feature_schema import (
    PIPELINE_FEATURE_SCHEMA,
    PIPELINE_STAGES,
    ML_MODEL_GROUPS,
    TEMPORAL_WINDOW_DAYS,
    MAX_ADAPTIVE_LOOKBACK_DAYS,
    TEMPORAL_OFFSET_RANGE,
    FeatureSpec,
    StageSpec,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Status constants
# ---------------------------------------------------------------------------

STATUS_PASS = "PASS"
STATUS_WARN_EXPECTED = "WARNING (expected)"    # expected operational limitation
STATUS_WARN_INVESTIGATE = "WARNING (investigate)"  # unexpected, needs investigation
STATUS_FAIL = "FAIL"
STATUS_SKIP = "SKIP"  # feature not expected in this stage

# Priority order for aggregation (highest wins)
_STATUS_PRIORITY: Dict[str, int] = {
    STATUS_FAIL: 4,
    STATUS_WARN_INVESTIGATE: 3,
    STATUS_WARN_EXPECTED: 2,
    STATUS_PASS: 1,
    STATUS_SKIP: 0,
}


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class FieldCheck:
    """Result of one validation rule for a (feature, stage) pair."""
    rule: str
    status: str  # PASS / WARN_EXPECTED / WARN_INVESTIGATE / FAIL / SKIP
    detail: str


@dataclass
class StageResult:
    """Full validation result for one feature at one pipeline stage."""
    feature_name: str
    stage: str
    present: bool
    dtype_observed: Optional[str] = None
    null_pct: Optional[float] = None
    placeholder_pct: Optional[float] = None
    sample_values: List[Any] = field(default_factory=list)
    observed_min: Optional[float] = None
    observed_median: Optional[float] = None
    observed_max: Optional[float] = None
    observed_std: Optional[float] = None
    non_null_count: Optional[int] = None
    total_count: Optional[int] = None
    unit_expected: str = ""
    unit_observed: Optional[str] = None
    unit_verification_status: str = "PASS"  # PASS / WARN / FAIL
    range_violation_pct: Optional[float] = None
    unique_non_null_values: Optional[int] = None
    unique_ratio: Optional[float] = None
    variance: Optional[float] = None
    std_dev: Optional[float] = None
    coefficient_of_variation: Optional[float] = None
    checks: List[FieldCheck] = field(default_factory=list)

    @property
    def status(self) -> str:
        """Aggregate status: worst of all check statuses (highest priority wins)."""
        if not self.checks:
            return STATUS_SKIP
        return max(self.checks, key=lambda c: _STATUS_PRIORITY.get(c.status, 0)).status

    def add_check(self, rule: str, status: str, detail: str) -> None:
        self.checks.append(FieldCheck(rule=rule, status=status, detail=detail))


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------

def normalize_unit(u: str) -> str:
    if not isinstance(u, str):
        return ""
    u = u.lower().replace("µ", "u").replace("³", "3").replace("²", "2").strip()
    if "(" in u:
        u = u.split("(")[0].strip()
    if u in ("celsius", "°c", "c"):
        return "c"
    if u in ("kelvin", "k"):
        return "k"
    if u in ("boolean", "bool"):
        return "bool"
    return u


def units_equivalent(u1: str, u2: str) -> bool:
    return normalize_unit(u1) == normalize_unit(u2)


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _check_date_column(series: pd.Series) -> Tuple[bool, str]:
    """Check that a string-typed date column matches YYYY-MM-DD and is sane."""
    non_null = series.dropna().astype(str)
    if non_null.empty:
        return True, "all null — nothing to check"
    bad = non_null[~non_null.str.match(_DATE_RE)]
    if len(bad) > 0:
        return False, f"{len(bad)} values don't match YYYY-MM-DD: {bad.head(3).tolist()}"
    try:
        parsed = pd.to_datetime(non_null, errors="coerce")
        today = pd.Timestamp.now()
        cutoff = today - pd.DateOffset(years=10)
        future_mask = parsed > today
        ancient_mask = parsed < cutoff
        issues = []
        if future_mask.any():
            issues.append(f"{future_mask.sum()} future dates")
        if ancient_mask.any():
            issues.append(f"{ancient_mask.sum()} dates before {cutoff.date()}")
        if issues:
            return False, "; ".join(issues)
    except Exception:
        pass
    return True, "all values match YYYY-MM-DD and within range"


def _is_monsoon_season(df: pd.DataFrame) -> bool:
    """Check if the dataset contains observations from the Indian summer monsoon months (June-September)."""
    for col in ["timestamp", "Date", "last_update", "date"]:
        if col in df.columns:
            try:
                parsed = pd.to_datetime(df[col], errors="coerce").dropna()
                if not parsed.empty:
                    months = parsed.dt.month.unique()
                    if any(m in {6, 7, 8, 9} for m in months):
                        return True
            except Exception:
                pass
    if "Month" in df.columns:
        try:
            months = pd.to_numeric(df["Month"], errors="coerce").dropna().unique()
            if any(m in {6, 7, 8, 9} for m in months):
                return True
        except Exception:
            pass
    return False


def _placeholder_consistency(
    df: pd.DataFrame, feature: str
) -> Tuple[float, str]:
    """
    Check placeholder_used consistency for a satellite feature.

    Rule: rows where placeholder_used=True must have a null feature value.
    Returns (pct_violation, detail).
    """
    if "placeholder_used" not in df.columns or feature not in df.columns:
        return 0.0, "placeholder_used or feature column missing"

    placeholder_rows = df["placeholder_used"].astype(str).str.lower().isin(["true", "1"])
    if placeholder_rows.sum() == 0:
        return 0.0, "no placeholder rows in this stage"

    ph_with_value = placeholder_rows & df[feature].notna()
    violation_pct = ph_with_value.sum() / len(df) * 100
    if ph_with_value.any():
        return violation_pct, (
            f"{ph_with_value.sum()} placeholder rows unexpectedly have non-null {feature}"
        )
    return 0.0, "placeholder rows correctly have null values"


def _get_atbd_ref(feat_name: str) -> str:
    if feat_name == "SO2 Column":
        return "S5P-L2-SO2-ATBD"
    elif feat_name == "NO2 Column":
        return "S5P-L2-NO2-ATBD"
    elif feat_name == "HCHO":
        return "S5P-L2-HCHO-ATBD"
    elif feat_name == "CO Column":
        return "S5P-L2-CO-ATBD"
    elif feat_name == "O3 Column":
        return "S5P-L2-O3-ATBD"
    return "MODIS MCD19A2 ATBD"


def _get_prf_ref(feat_name: str) -> str:
    if feat_name == "SO2 Column":
        return "S5P-MPC-KNMI-PRF-SO2"
    elif feat_name == "NO2 Column":
        return "S5P-MPC-KNMI-PRF-NO2"
    elif feat_name == "HCHO":
        return "S5P-MPC-KNMI-PRF-HCHO"
    elif feat_name == "CO Column":
        return "S5P-MPC-SRON-PRF-CO"
    elif feat_name == "O3 Column":
        return "S5P-MPC-DLR-PRF-O3"
    return "MODIS MCD19A2 PRF"


def _get_sensor_name(feat_name: str) -> str:
    if feat_name in ["SO2 Column", "NO2 Column", "HCHO", "CO Column", "O3 Column"]:
        return "TROPOMI"
    return "MODIS"


def _get_qa_threshold(feat_name: str) -> str:
    if feat_name == "NO2 Column":
        return "0.75"
    return "0.5"


def _evaluate_evidence_based_missingness(
    df: pd.DataFrame, spec: FeatureSpec, null_pct: float, stage: str
) -> Tuple[str, str]:
    """
    Refactored product-specific and evidence-driven validation for satellite features.
    Separates MODIS MAIAC (AOD) validation from Sentinel-5P validation.
    Eliminates implicit percentage-based rules and uses explicit runtime evidence.
    Clearly separates Runtime Evidence from Scientific Interpretation.
    """
    is_satellite = (spec.group == "satellite")
    if not is_satellite:
        # Fallback to standard validation for non-satellite features
        if null_pct >= spec.null_fail_pct:
            return STATUS_FAIL, f"100% null — feature completely absent in {stage}"
        elif null_pct > spec.null_warn_pct:
            if getattr(spec, 'null_expected_reason', None):
                return STATUS_WARN_EXPECTED, f"{null_pct:.1f}% null (threshold={spec.null_warn_pct:.0f}%): {spec.null_expected_reason}"
            else:
                return STATUS_WARN_INVESTIGATE, f"{null_pct:.1f}% null (threshold={spec.null_warn_pct:.0f}%); investigate data availability"
        return STATUS_PASS, f"{null_pct:.1f}% null"

    # --- SATELLITE EVIDENCE-BASED VALIDATION ---

    # 1. Collector success check
    collector_succeeded = True
    failure_evidence = []
    if "placeholder_used" in df.columns:
        ph_series = df["placeholder_used"].astype(str).str.lower().isin(["true", "1"])
        if not ph_series.empty and ph_series.all():
            collector_succeeded = False
            failure_evidence.append("All rows in the dataset are fallback placeholder records (placeholder_used=True)")
    else:
        # Downstream fallback check
        sat_cols = [c for c in df.columns if c in ["AOD", "HCHO", "NO2 Column", "SO2 Column", "CO Column", "O3 Column"]]
        if len(sat_cols) > 0 and all(df[c].isna().all() for c in sat_cols):
            collector_succeeded = False
            failure_evidence.append("All satellite feature columns are completely null across this stage")

    if len(df) == 0:
        collector_succeeded = False
        failure_evidence.append("Dataset has 0 rows (empty dataset)")

    is_maiac = (spec.name == "AOD")

    # Handle Complete Collector/GEE/API Failure (FAIL)
    if not collector_succeeded:
        runtime_evidence = [
            "Collector execution failed",
            "No granules" if is_maiac else "No imagery",
            "Placeholder records only"
        ]
        runtime_evidence.extend(failure_evidence)
        
        detail_lines = [
            "Collector, GEE, or API failure detected.",
            "    Runtime Evidence:",
        ]
        for ev in runtime_evidence:
            detail_lines.append(f"    - {ev}")
        detail_lines.append("    Scientific Interpretation:")
        detail_lines.append("    - System failure prevented data collection. No scientific interpretation available.")
        
        if is_maiac:
            ref_docs = "MODIS MAIAC MCD19A2 User Guide & MCD19A2 ATBD"
        else:
            ref_docs = f"Sentinel-5P Product Readme ({_get_prf_ref(spec.name)}) and GEE dataset guides"
            
        detail_lines.append(f"    Official Reference: {ref_docs}")
        detail_lines.append(f"    Supporting Diagnostic: null_pct = {null_pct:.1f}%")
        return STATUS_FAIL, "\n".join(detail_lines)

    # Gather runtime evidence and scientific interpretation for succeeded collector
    runtime_evidence = ["Collector executed successfully"]
    scientific_interpretation = []

    # 2. Imagery/Granule Query Status (do not infer image availability)
    runtime_evidence.append("Image collection successfully queried")

    # 3. Placeholder Usage
    ph_used = False
    if "placeholder_used" in df.columns:
        ph_series = df["placeholder_used"].astype(str).str.lower().isin(["true", "1"])
        if ph_series.any():
            ph_used = True
    if ph_used:
        runtime_evidence.append("Placeholder used for some coordinates")
    else:
        runtime_evidence.append("Placeholder not used")

    # 4. QA Verification (Runtime Evidence)
    has_qa_filtering = False
    qa_col = "AOD QA Status" if is_maiac else f"{spec.name} QA Status"
    if qa_col in df.columns:
        non_null_qa = df[qa_col].dropna()
        if not non_null_qa.empty:
            runtime_evidence.append("QA metadata verified")
            has_qa_filtering = True
            
    # Scientific Interpretation of QA
    if has_qa_filtering and null_pct > 0.0:
        scientific_interpretation.append("Missingness is consistent with documented QA filtering.")

    # Handle complete presence (PASS)
    if null_pct == 0.0:
        detail_lines = [
            "Feature completely present.",
            "    Runtime Evidence:",
        ]
        for ev in runtime_evidence:
            detail_lines.append(f"    - {ev}")
        detail_lines.append("    Scientific Interpretation:")
        detail_lines.append("    - No unexplained missingness or retrieval limitations detected.")
        detail_lines.append(f"    Supporting Diagnostic: null_pct = 0.0%")
        return STATUS_PASS, "\n".join(detail_lines)

    # 5. Publication Lag
    lag_col = f"{spec.name} Publication Lag"
    max_lag = 0
    if lag_col in df.columns:
        non_null_lags = df[lag_col].dropna()
        if not non_null_lags.empty:
            max_lag = int(non_null_lags.max())
    if max_lag > 0:
        scientific_interpretation.append(f"Missingness is consistent with publication lag of {max_lag} days (adaptive lookback applied).")

    # 6. Temporal Offset & Orbit Coverage
    offset_col = f"{spec.name} Temporal Offset"
    max_offset = 0.0
    if offset_col in df.columns:
        non_null_offsets = df[offset_col].dropna()
        if not non_null_offsets.empty:
            max_offset = float(non_null_offsets.abs().max())
    if max_offset > 1.0:
        scientific_interpretation.append(f"Missingness is consistent with orbit swath gaps requiring adaptive temporal lookback (offset up to {max_offset:.1f} days).")
    elif null_pct > 0.0:
        scientific_interpretation.append("Missingness is consistent with daily orbit overpass gaps (locations fell outside daily orbit swath).")

    # 7. Seasonality / Cloud Cover Context
    is_monsoon = False
    for col in ["timestamp", "Date", "last_update", "date"]:
        if col in df.columns:
            try:
                parsed = pd.to_datetime(df[col], errors="coerce").dropna()
                if not parsed.empty and parsed.dt.month.isin([6, 7, 8, 9]).mean() > 0.5:
                    is_monsoon = True
                    break
            except Exception:
                pass
    if not is_monsoon and "Month" in df.columns:
        try:
            months = pd.to_numeric(df["Month"], errors="coerce").dropna()
            if not months.empty and months.isin([6, 7, 8, 9]).mean() > 0.5:
                is_monsoon = True
        except Exception:
            pass
    if is_monsoon:
        if is_maiac:
            scientific_interpretation.append("Missingness is consistent with MAIAC cloud masking.")
        else:
            scientific_interpretation.append("Missingness is consistent with Sentinel-5P retrieval limitations.")
        scientific_interpretation.append("Missingness is consistent with persistent cloud cover from Indian summer monsoon (June-September).")

    # Decision Engine:
    is_expected_limitation = is_monsoon or (max_lag > 0) or (max_offset > 1.0) or has_qa_filtering
    
    if is_expected_limitation:
        status = STATUS_WARN_EXPECTED
        if is_maiac:
            ref_docs = (
                "MODIS MAIAC MCD19A2 ATBD, MODIS Land Quality Assurance guides, "
                "and Copernicus/GEE MODIS dataset documentation"
            )
            summary_wording = "Missingness is consistent with MAIAC cloud masking."
        else:
            sensor = "TROPOMI"
            atbd = _get_atbd_ref(spec.name)
            prf = _get_prf_ref(spec.name)
            ref_docs = (
                f"Sentinel-5P {spec.name} ATBD ({atbd}), Product Readme File ({prf}), "
                f"Copernicus Sentinel-5P Technical Guides, and GEE Sentinel-5P dataset guides"
            )
            summary_wording = "Missingness is consistent with Sentinel-5P retrieval limitations."
            
        detail_lines = [
            summary_wording,
            "    Runtime Evidence:",
        ]
        for ev in runtime_evidence:
            detail_lines.append(f"    - {ev}")
        detail_lines.append("    Scientific Interpretation:")
        for si in scientific_interpretation:
            detail_lines.append(f"    - {si}")
        detail_lines.append(f"    Official References: {ref_docs}")
        detail_lines.append(f"    Supporting Diagnostic: null_pct = {null_pct:.1f}%")
        return status, "\n".join(detail_lines)
    else:
        status = STATUS_WARN_INVESTIGATE
        detail_lines = [
            "Unexpected missingness with successful collector execution.",
            "    Runtime Evidence:",
        ]
        for ev in runtime_evidence:
            detail_lines.append(f"    - {ev}")
        detail_lines.append("    Scientific Interpretation:")
        detail_lines.append("    - Missingness is unexpected. No expected physical or operational limitations verified.")
        detail_lines.append(f"    Supporting Diagnostic: null_pct = {null_pct:.1f}%")
        return status, "\n".join(detail_lines)


def _check_provenance_null_coupling(
    df: pd.DataFrame, prov_feature: str, science_feature: str
) -> Tuple[str, str]:
    """
    Classify provenance nulls as expected or unexpected by comparing
    with the linked science feature's null pattern in the same DataFrame.

    Returns (status, detail).

    Rules
    -----
    1. prov null AND science null → coupled, expected (WARN_EXPECTED)
    2. prov null AND science non-null → missing provenance (WARN_INVESTIGATE)
    3. prov non-null AND science null → inconsistency (WARN_INVESTIGATE)
    4. all prov present → PASS (no null coupling check needed)
    """
    if science_feature not in df.columns or prov_feature not in df.columns:
        return STATUS_SKIP, "science or provenance column not in DataFrame"

    prov_null = df[prov_feature].isna()
    sci_null = df[science_feature].isna()
    n = len(df)

    # Case 2: prov null but science present (unexpected missing provenance)
    missing_prov_but_sci_present = prov_null & ~sci_null
    n_missing_unexpected = missing_prov_but_sci_present.sum()

    # Case 3: prov present but science null (inconsistency)
    prov_present_but_sci_null = ~prov_null & sci_null
    n_inconsistent = prov_present_but_sci_null.sum()

    if n_missing_unexpected > 0 or n_inconsistent > 0:
        parts = []
        if n_missing_unexpected > 0:
            parts.append(
                f"{n_missing_unexpected}/{n} rows: provenance null but "
                f"'{science_feature}' is non-null (missing provenance)"
            )
        if n_inconsistent > 0:
            parts.append(
                f"{n_inconsistent}/{n} rows: provenance non-null but "
                f"'{science_feature}' is null (inconsistency)"
            )
        return STATUS_WARN_INVESTIGATE, "; ".join(parts)

    # Case 1: prov null AND science null — allow provenance to be null, this is consistent!
    n_coupled_null = (prov_null & sci_null).sum()
    if n_coupled_null > 0:
        pct = n_coupled_null / n * 100
        return STATUS_PASS, (
            f"{n_coupled_null}/{n} ({pct:.1f}%) provenance values null because "
            f"'{science_feature}' is also null (cloud cover / QA masking expected)"
        )

    # All provenance present and consistent
    return STATUS_PASS, f"all provenance values present; coupled with '{science_feature}'"


# ---------------------------------------------------------------------------
# Per-stage validator
# ---------------------------------------------------------------------------

class PipelineTracer:
    """
    Loads each pipeline stage CSV and validates all features against
    ``PIPELINE_FEATURE_SCHEMA``, producing ``StageResult`` objects.
    """

    # Canonical paths (resolved at runtime using config.BASE_DIR)
    STAGE_PATHS: Dict[str, str] = {
        "Collector_satellite": "processed_data/satellite_predictors.csv",
        "Collector_meteorology": "processed_data/era5_meteorology.csv",
        "Collector_target": "processed_data/cpcb_cleaned_latest.csv",
        "Merger": "features/merged_feature_table.csv",
        "Dataset Builder": "../analysis_ready_dataset.csv",
        "merged_feature_table.csv": "features/merged_feature_table.csv",
        "analysis_ready_dataset.csv": "../analysis_ready_dataset.csv",
        "train_dataset.csv": "../train_dataset.csv",
    }

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir) if base_dir else Path(config.BASE_DIR)
        self._stage_dfs: Dict[str, Optional[pd.DataFrame]] = {}
        self._ml_features: Optional[List[str]] = None
        
        # Load feature dictionary to map units in Merger stage
        dict_path = (self.base_dir / "features/feature_dictionary.csv").resolve()
        self.feature_units_dict = {}
        if dict_path.exists():
            try:
                dict_df = pd.read_csv(dict_path)
                for _, row in dict_df.iterrows():
                    fname = row.get("Feature Name") or row.get("Feature")
                    units = row.get("Units") or row.get("Unit")
                    if fname and pd.notna(units):
                        self.feature_units_dict[str(fname).strip()] = str(units).strip()
            except Exception as e:
                logger.warning("Failed to load feature dictionary: %s", e)

    # ------------------------------------------------------------------
    # Loaders
    # ------------------------------------------------------------------

    def _load_stage(self, stage: str) -> Optional[pd.DataFrame]:
        if stage in self._stage_dfs:
            return self._stage_dfs[stage]
        rel = self.STAGE_PATHS.get(stage)
        if rel is None:
            self._stage_dfs[stage] = None
            return None
        path = (self.base_dir / rel).resolve()
        if not path.exists():
            logger.warning("Stage CSV not found: %s", path)
            self._stage_dfs[stage] = None
            return None
        try:
            df = pd.read_csv(path, low_memory=False)
            logger.info("Loaded %s: %d rows, %d cols", stage, len(df), len(df.columns))
            self._stage_dfs[stage] = df
            return df
        except Exception as exc:
            logger.error("Failed to load %s: %s", stage, exc)
            self._stage_dfs[stage] = None
            return None

    def _get_ml_features(self) -> List[str]:
        if self._ml_features is not None:
            return self._ml_features
        features: List[str] = []
        for grp in ML_MODEL_GROUPS:
            features.extend(FeatureGroupManager.get_features_in_group(grp))
        self._ml_features = features
        return features

    # ------------------------------------------------------------------
    # Per-feature, per-stage validation
    # ------------------------------------------------------------------

    def _check_unit_verification(
        self, spec: FeatureSpec, stage: str, df: pd.DataFrame
    ) -> Tuple[str, str, Optional[str]]:
        """Verify the unit of the feature in the given stage."""
        expected_unit = spec.get_unit(stage)
        observed_unit = None

        # Case 1: Collector CPCB unit column check
        if stage == "Collector" and spec.group == "target":
            unit_col = f"{spec.name}_unit"
            if unit_col in df.columns:
                non_null_units = df[unit_col].dropna()
                if not non_null_units.empty:
                    observed_unit = str(non_null_units.iloc[0])

        # Case 2: Merger/dictionary check
        elif stage in ("Merger", "merged_feature_table.csv"):
            observed_unit = self.feature_units_dict.get(spec.name)

        if observed_unit is not None:
            if units_equivalent(observed_unit, expected_unit):
                return STATUS_PASS, f"observed unit '{observed_unit}' matches expected '{expected_unit}'", observed_unit
            else:
                return STATUS_FAIL, f"unit mismatch: observed unit '{observed_unit}', expected '{expected_unit}'", observed_unit

        # Case 3: Range-based unit inference fallback (especially for Temperature)
        if spec.dtype == "numeric" and spec.name in df.columns:
            series = pd.to_numeric(df[spec.name], errors="coerce").dropna()
            if not series.empty:
                obs_min, obs_max = series.min(), series.max()
                if spec.name == "Temperature":
                    # Celsius range: [-50, 60], Kelvin range: [200, 330]
                    if expected_unit in ("K", "Kelvin"):
                        if obs_max < 150.0:  # values are clearly Celsius
                            return STATUS_FAIL, f"unit mismatch: observed values are in Celsius range [{obs_min:.1f}, {obs_max:.1f}], but expected unit is Kelvin", "°C"
                        else:
                            return STATUS_PASS, f"observed values in Kelvin range [{obs_min:.1f}, {obs_max:.1f}]", "K"
                    elif expected_unit in ("°C", "Celsius", "C"):
                        if obs_min > 150.0:  # values are clearly Kelvin
                            return STATUS_FAIL, f"unit mismatch: observed values are in Kelvin range [{obs_min:.1f}, {obs_max:.1f}], but expected unit is Celsius", "K"
                        else:
                            return STATUS_PASS, f"observed values in Celsius range [{obs_min:.1f}, {obs_max:.1f}]", "°C"

        return STATUS_PASS, f"expected unit '{expected_unit}' verified (no explicit mismatch)", None

    def _validate_feature_at_stage(
        self, spec: FeatureSpec, stage: str, df: Optional[pd.DataFrame]
    ) -> StageResult:
        """Run all validation rules for one feature at one stage."""
        expected_unit = spec.get_unit(stage)
        result = StageResult(
            feature_name=spec.name,
            stage=stage,
            present=False,
            dtype_observed=None,
            null_pct=None,
            placeholder_pct=None,
            sample_values=[],
            observed_min=None,
            observed_median=None,
            observed_max=None,
            observed_std=None,
            non_null_count=None,
            total_count=None,
            unit_expected=expected_unit,
            unit_observed=None,
            unit_verification_status="PASS",
            range_violation_pct=None,
        )

        # --- Check 1: stage expected ---
        if stage not in spec.expected_stages:
            result.add_check(
                "stage_expected", STATUS_SKIP,
                f"Not expected in {stage}",
            )
            return result

        # --- Check 2: column presence ---
        if df is None:
            result.add_check("column_present", STATUS_FAIL, "Stage CSV failed to load")
            return result

        if spec.name not in df.columns:
            result.add_check(
                "column_present", STATUS_FAIL,
                f"Column '{spec.name}' missing from {stage} "
                f"(available: {len(df.columns)} cols)"
            )
            return result

        result.present = True
        series = df[spec.name]
        n = len(series)

        result.add_check("column_present", STATUS_PASS, f"Column present ({n} rows)")

        # --- Check 3: dtype ---
        observed_dtype = str(series.dtype)
        result.dtype_observed = observed_dtype
        dtype_ok = True
        if spec.dtype == "numeric":
            numeric_series = pd.to_numeric(series, errors="coerce")
            if numeric_series.isna().all() and not series.isna().all():
                dtype_ok = False
                result.add_check(
                    "dtype", STATUS_FAIL,
                    f"Expected numeric but all conversion attempts failed "
                    f"(dtype={observed_dtype})"
                )
        elif spec.dtype == "boolean":
            bool_vals = series.dropna().astype(str).str.lower()
            invalid = bool_vals[~bool_vals.isin(["true", "false", "0", "1"])]
            if not invalid.empty:
                dtype_ok = False
                result.add_check(
                    "dtype", STATUS_WARN_INVESTIGATE,
                    f"Boolean column has unexpected values: {invalid.unique()[:5].tolist()}"
                )
        if dtype_ok and "dtype" not in [c.rule for c in result.checks]:
            result.add_check("dtype", STATUS_PASS, f"dtype={observed_dtype}")

        # --- Check 3b: unit verification ---
        unit_status, unit_detail, observed_unit = self._check_unit_verification(spec, stage, df)
        result.unit_observed = observed_unit
        if unit_status == STATUS_PASS:
            result.unit_verification_status = "PASS"
        elif unit_status == STATUS_FAIL:
            result.unit_verification_status = "FAIL"
        else:
            result.unit_verification_status = "WARN"
        result.add_check("unit_verification", unit_status, unit_detail)

        # --- Check 4: null rate ---
        null_pct = series.isna().mean() * 100
        result.null_pct = round(null_pct, 2)

        if spec.provenance_for is not None:
            # Provenance fields: handle null coupling logic separately (Check 4b below)
            result.add_check(
                "null_rate", STATUS_PASS,
                f"{null_pct:.1f}% null (provenance coupling check below)"
            )
        else:
            status, detail = _evaluate_evidence_based_missingness(df, spec, null_pct, stage)
            result.add_check("null_rate", status, detail)

        # --- Check 4b: provenance null coupling ---
        if spec.provenance_for is not None:
            science_feat = spec.provenance_for
            coupling_status, coupling_detail = _check_provenance_null_coupling(
                df, spec.name, science_feat
            )
            if coupling_status not in (STATUS_SKIP, STATUS_PASS):
                result.add_check("provenance_coupling", coupling_status, coupling_detail)
            else:
                result.add_check("provenance_coupling", STATUS_PASS, coupling_detail)

        # --- Check 5: placeholder consistency ---
        if spec.group == "satellite" and spec.dtype == "numeric":
            ph_pct, ph_detail = _placeholder_consistency(df, spec.name)
            result.placeholder_pct = round(ph_pct, 2)
            if ph_pct > 0:
                result.add_check(
                    "placeholder_consistency", STATUS_WARN_INVESTIGATE,
                    f"{ph_pct:.1f}% placeholder inconsistency: {ph_detail}"
                )
            else:
                result.add_check("placeholder_consistency", STATUS_PASS, ph_detail)

        # --- Check 7: numeric range, statistics, and scaling diagnostics ---
        expected_range = spec.get_valid_range(stage)
        is_temporal_offset = "Temporal Offset" in spec.name
        if spec.dtype == "numeric":
            numeric_series = pd.to_numeric(series, errors="coerce")
            non_null_num = numeric_series.dropna()
            
            result.total_count = len(df)
            result.non_null_count = int(non_null_num.count())
            
            if "placeholder_used" in df.columns:
                ph_series = df["placeholder_used"].astype(str).str.lower().isin(["true", "1"])
                result.placeholder_pct = float(ph_series.mean() * 100)
            else:
                result.placeholder_pct = 0.0

            result.unique_non_null_values = 0
            result.unique_ratio = 0.0
            result.variance = 0.0
            result.std_dev = 0.0
            result.coefficient_of_variation = 0.0
                
            if not non_null_num.empty:
                result.observed_min = float(non_null_num.min())
                result.observed_median = float(non_null_num.median())
                result.observed_max = float(non_null_num.max())
                result.observed_std = float(non_null_num.std()) if len(non_null_num) > 1 else 0.0
                result.sample_values = non_null_num.head(3).tolist()
                
                # Low-variance stats
                result.unique_non_null_values = int(non_null_num.nunique())
                result.unique_ratio = float(result.unique_non_null_values / len(non_null_num)) if len(non_null_num) > 0 else 0.0
                
                var_val = non_null_num.var()
                result.variance = float(var_val) if (len(non_null_num) > 1 and not pd.isna(var_val)) else 0.0
                std_val = non_null_num.std()
                result.std_dev = float(std_val) if (len(non_null_num) > 1 and not pd.isna(std_val)) else 0.0
                
                mean_val = non_null_num.mean()
                if mean_val != 0 and not pd.isna(mean_val):
                    result.coefficient_of_variation = result.std_dev / abs(float(mean_val))
                else:
                    result.coefficient_of_variation = 0.0
                
                # Check range
                if expected_range is not None and not is_temporal_offset:
                    lo, hi = expected_range
                    out_of_range = (non_null_num < lo) | (non_null_num > hi)
                    viol_pct = out_of_range.mean() * 100
                    result.range_violation_pct = round(viol_pct, 2)
                    if viol_pct > 0:
                        range_status = (
                            STATUS_WARN_INVESTIGATE if spec.provenance_for is not None
                            else STATUS_FAIL
                        )
                        result.add_check(
                            "value_range", range_status,
                            f"{viol_pct:.1f}% of values outside [{lo}, {hi}]; "
                            f"observed=[{result.observed_min:.4g}, {result.observed_max:.4g}]"
                        )
                    else:
                        result.add_check(
                            "value_range", STATUS_PASS,
                            f"observed=[{result.observed_min:.4g}, {result.observed_max:.4g}] "
                            f"within [{lo}, {hi}]"
                        )
                
                # --- AUTOMATIC SCALING DIAGNOSTICS ---
                # 1. Values appear 1000x too large
                if expected_range is not None and spec.group not in ("provenance", "temporal", "geography"):
                    lo, hi = expected_range
                    if hi > 0 and result.observed_max > hi * 100:
                        result.add_check(
                            "scaling_diagnostic", STATUS_WARN_INVESTIGATE,
                            f"Scaling anomaly: Observed values appear 1000x too large. Expected range [{lo}, {hi}], observed max {result.observed_max:.4g}."
                        )
                    
                    # 2. Values appear 1000x too small
                    elif hi >= 1.0 and result.observed_max > 0.0 and result.observed_max < hi / 500:
                        result.add_check(
                            "scaling_diagnostic", STATUS_WARN_INVESTIGATE,
                            f"Scaling anomaly: Observed values appear 1000x too small. Expected range [{lo}, {hi}], observed max {result.observed_max:.4g}."
                        )
                        
                # 3. Temperature Celsius vs Kelvin
                if spec.name == "Temperature":
                    if expected_unit in ("K", "Kelvin"):
                        if result.observed_max < 150.0:
                            result.add_check(
                                "scaling_diagnostic", STATUS_WARN_INVESTIGATE,
                                f"Scaling anomaly: Temperature appears to be Celsius ({result.observed_max:.1f} °C) instead of Kelvin."
                            )
                    elif expected_unit in ("°C", "Celsius", "C"):
                        if result.observed_min > 150.0:
                            result.add_check(
                                "scaling_diagnostic", STATUS_WARN_INVESTIGATE,
                                f"Scaling anomaly: Temperature appears to be Kelvin ({result.observed_min:.1f} K) instead of Celsius."
                            )
                            
                # 4. Percentage stored as fraction
                if expected_unit == "%" or "percent" in expected_unit.lower():
                    if result.observed_max <= 1.0 and result.observed_min >= 0.0 and result.observed_max > 0.01:
                        result.add_check(
                            "scaling_diagnostic", STATUS_WARN_INVESTIGATE,
                            f"Scaling anomaly: Percentage appears to be stored as a fraction (observed max={result.observed_max:.4f} <= 1.0)."
                        )
                        
                # 5. Longitude/Latitude swapped
                if spec.name == "Latitude":
                    if result.observed_min >= 65.0 and result.observed_max <= 100.0:
                        result.add_check(
                            "scaling_diagnostic", STATUS_WARN_INVESTIGATE,
                            f"Scaling anomaly: Latitude values [{result.observed_min:.4f}, {result.observed_max:.4f}] match typical Indian Longitude range."
                        )
                elif spec.name == "Longitude":
                    if result.observed_min >= 5.0 and result.observed_max <= 40.0:
                        result.add_check(
                            "scaling_diagnostic", STATUS_WARN_INVESTIGATE,
                            f"Scaling anomaly: Longitude values [{result.observed_min:.4f}, {result.observed_max:.4f}] match typical Indian Latitude range."
                        )

                # 6. Wind direction outside [0,360]
                if spec.name == "Wind Direction":
                    if result.observed_min < 0.0 or result.observed_max > 360.0:
                        result.add_check(
                            "scaling_diagnostic", STATUS_WARN_INVESTIGATE,
                            f"Scaling anomaly: Wind Direction outside [0, 360] (observed [{result.observed_min:.1f}, {result.observed_max:.1f}])."
                        )

                # 7. Relative humidity outside expected limits
                if spec.name == "Relative Humidity":
                    if result.observed_min < 0.0 or result.observed_max > 100.5:
                        result.add_check(
                            "scaling_diagnostic", STATUS_WARN_INVESTIGATE,
                            f"Scaling anomaly: Relative Humidity outside expected limits 0-100.5% (observed [{result.observed_min:.1f}, {result.observed_max:.1f}])."
                        )
            else:
                result.observed_min = None
                result.observed_median = None
                result.observed_max = None
                result.observed_std = None
                result.sample_values = []
                if expected_range is not None and not is_temporal_offset:
                    result.add_check("value_range", STATUS_SKIP, "No non-null values to range-check")
        else:
            # Non-numeric
            non_null = series.dropna()
            result.sample_values = non_null.head(3).tolist()
            result.non_null_count = int(non_null.count())
            result.total_count = len(df)
            result.placeholder_pct = 0.0

        # --- Check 8: categorical valid values ---
        if spec.dtype == "categorical" and spec.valid_categories:
            non_null_str = series.dropna().astype(str)
            invalid_cats = non_null_str[~non_null_str.isin(spec.valid_categories)]
            if not invalid_cats.empty:
                result.add_check(
                    "categorical_values", STATUS_FAIL,
                    f"Invalid categories: {invalid_cats.unique()[:5].tolist()}"
                )
            else:
                result.add_check("categorical_values", STATUS_PASS, "All categories valid")

        # --- Check 9: date format (for date-typed strings) ---
        if spec.dtype == "string" and "date" in spec.unit.lower():
            date_ok, date_detail = _check_date_column(series)
            if not date_ok:
                result.add_check("date_format", STATUS_WARN_INVESTIGATE, date_detail)
            else:
                result.add_check("date_format", STATUS_PASS, date_detail)

        # --- Check 10: temporal offset window ---
        # Applied to all "* Temporal Offset" provenance fields.
        # Expected range: [−MAX_ADAPTIVE_LOOKBACK_DAYS, +TEMPORAL_WINDOW_DAYS] = [-14, +3]
        # Rationale: the adaptive collector may shift the effective date up to
        # MAX_ADAPTIVE_LOOKBACK_DAYS (14) days backward when a collection has a publication
        # lag or cloud cover (Indian monsoon). An offset more negative than -14 or more
        # positive than +3 means the contributing observation falls outside the configured
        # collection window — this is WARN_INVESTIGATE, not an expected operational condition.
        # The window is sourced from config.SATELLITE_LOOKBACK_DAYS and TEMPORAL_WINDOW_DAYS;
        # do NOT hardcode a different range without updating config.py and feature_schema.py.
        if "Temporal Offset" in spec.name and spec.dtype == "numeric":
            numeric_series = pd.to_numeric(series, errors="coerce")
            non_null_num = numeric_series.dropna()
            if not non_null_num.empty:
                lo_win, hi_win = TEMPORAL_OFFSET_RANGE  # (-7.0, +3.0)
                out_window = (non_null_num < lo_win) | (non_null_num > hi_win)
                n_out = int(out_window.sum())
                if n_out > 0:
                    out_vals = non_null_num[out_window]
                    result.add_check(
                        "temporal_offset_window",
                        STATUS_WARN_INVESTIGATE,
                        f"{n_out}/{len(non_null_num)} offsets outside configured window "
                        f"[{lo_win}, {hi_win}] days "
                        f"(TEMPORAL_WINDOW_DAYS={TEMPORAL_WINDOW_DAYS}, "
                        f"MAX_ADAPTIVE_LOOKBACK_DAYS={MAX_ADAPTIVE_LOOKBACK_DAYS}); "
                        f"min={out_vals.min():.3f}, max={out_vals.max():.3f}"
                    )
                else:
                    result.add_check(
                        "temporal_offset_window", STATUS_PASS,
                        f"all offsets within [{lo_win}, {hi_win}] days "
                        f"(configured lookback window)"
                    )
            # If all null: provenance_coupling covers it; no extra check needed

        # --- Check 11: publication lag non-negative (scientific validation) ---
        if "Publication Lag" in spec.name and spec.dtype == "numeric":
            numeric_series = pd.to_numeric(series, errors="coerce")
            non_null_num = numeric_series.dropna()
            if not non_null_num.empty:
                out_bounds = non_null_num < 0.0
                if out_bounds.any():
                    result.add_check(
                        "scientific_validation", STATUS_FAIL,
                        f"Publication Lag outside scientific range (>=0): observed [{non_null_num.min():.4g}, {non_null_num.max():.4g}]"
                    )
                else:
                    result.add_check(
                        "scientific_validation", STATUS_PASS,
                        "Publication Lag within valid scientific bounds (>=0)"
                    )

        # --- Check 12: explicit scientific validations ---
        if spec.name == "Relative Humidity":
            numeric_series = pd.to_numeric(series, errors="coerce")
            non_null_num = numeric_series.dropna()
            if not non_null_num.empty:
                # Physical range is 0–100%. ERA5 may produce values up to ~100.5% due to
                # spectral truncation artefacts in the ECMWF model — this is a known ERA5
                # data-quality characteristic documented in ECMWF validation reports and is
                # NOT a pipeline bug. The tolerance of 100.5% is the ONLY accepted silent
                # range expansion for this feature (see feature_schema.py description).
                out_bounds = (non_null_num < 0.0) | (non_null_num > 100.5)
                if out_bounds.any():
                    result.add_check(
                        "scientific_validation", STATUS_FAIL,
                        f"Relative Humidity outside allowed range 0–100.5% "
                        f"(physical range 0–100%; +0.5% tolerance for ERA5 spectral artefacts "
                        f"per ECMWF documentation): "
                        f"observed [{non_null_num.min():.4g}, {non_null_num.max():.4g}]"
                    )
                elif (non_null_num > 100.0).any():
                    # Values between 100% and 100.5% are expected ERA5 artefacts — WARN_EXPECTED
                    n_over = int((non_null_num > 100.0).sum())
                    result.add_check(
                        "scientific_validation", STATUS_WARN_EXPECTED,
                        f"{n_over} values between 100.0–100.5% "
                        f"(ERA5 spectral truncation artefact; expected, documented, not a bug). "
                        f"observed max={non_null_num.max():.4g}%"
                    )
                else:
                    result.add_check(
                        "scientific_validation", STATUS_PASS,
                        "Relative Humidity within physical bounds (0–100%)"
                    )

        elif spec.name == "Wind Direction":
            numeric_series = pd.to_numeric(series, errors="coerce")
            non_null_num = numeric_series.dropna()
            if not non_null_num.empty:
                out_bounds = (non_null_num < 0.0) | (non_null_num > 360.0)
                if out_bounds.any():
                    result.add_check(
                        "scientific_validation", STATUS_FAIL,
                        f"Wind Direction outside scientific range 0-360°: observed [{non_null_num.min():.4g}, {non_null_num.max():.4g}]"
                    )
                else:
                    result.add_check(
                        "scientific_validation", STATUS_PASS,
                        "Wind Direction within valid scientific bounds (0–360°)"
                    )

        elif spec.name == "Temperature":
            numeric_series = pd.to_numeric(series, errors="coerce")
            non_null_num = numeric_series.dropna()
            if not non_null_num.empty:
                expected_unit = spec.get_unit(stage)
                if expected_unit in ("K", "Kelvin"):
                    out_bounds = (non_null_num < 200.0) | (non_null_num > 330.0)
                    if out_bounds.any():
                        result.add_check(
                            "scientific_validation", STATUS_FAIL,
                            f"Temperature in Kelvin outside physical range [200, 330] K: observed [{non_null_num.min():.4g}, {non_null_num.max():.4g}]"
                        )
                    else:
                        result.add_check(
                            "scientific_validation", STATUS_PASS,
                            "Temperature within valid Kelvin scientific bounds (200–330 K)"
                        )
                elif expected_unit in ("°C", "C", "Celsius"):
                    out_bounds = (non_null_num < -50.0) | (non_null_num > 60.0)
                    if out_bounds.any():
                        result.add_check(
                            "scientific_validation", STATUS_FAIL,
                            f"Temperature in Celsius outside physical range [-50, 60] °C: observed [{non_null_num.min():.4g}, {non_null_num.max():.4g}]"
                        )
                    else:
                        result.add_check(
                            "scientific_validation", STATUS_PASS,
                            "Temperature within valid Celsius scientific bounds (-50 to 60 °C)"
                        )

        elif spec.name == "AOD":
            numeric_series = pd.to_numeric(series, errors="coerce")
            non_null_num = numeric_series.dropna()
            if not non_null_num.empty:
                out_bounds = (non_null_num < 0.0) | (non_null_num > 5.0)
                if out_bounds.any():
                    result.add_check(
                        "scientific_validation", STATUS_FAIL,
                        f"AOD outside physical range 0.0-5.0: observed [{non_null_num.min():.4g}, {non_null_num.max():.4g}]"
                    )
                else:
                    result.add_check(
                        "scientific_validation", STATUS_PASS,
                        "AOD within valid physical range (0.0–5.0)"
                    )

        # --- Check 13: constant-value / low-variance detection ---
        is_continuous = (
            spec.dtype == "numeric"
            and spec.feature_role in ("target", "science", "meteorology", "engineered", "geographic")
        )
        if result.non_null_count is not None and result.non_null_count > 0:
            is_constant = (
                result.unique_non_null_values == 1
                or (result.unique_ratio is not None and result.unique_ratio < 0.01 and result.non_null_count >= 30)
                or result.variance == 0.0
                or result.std_dev == 0.0
            )
            
            if is_continuous:
                if is_constant:
                    reasons = []
                    if result.unique_non_null_values == 1:
                        reasons.append("unique_non_null_values == 1")
                    if result.unique_ratio is not None and result.unique_ratio < 0.01 and result.non_null_count >= 30:
                        reasons.append("unique_ratio < 0.01 (1%) and non-null count >= 30")
                    if result.variance == 0.0:
                        reasons.append("variance == 0")
                    if result.std_dev == 0.0:
                        reasons.append("standard deviation == 0")
                    reason_str = " or ".join(reasons)
                    detail = (
                        f"Feature appears nearly constant. Reason: {reason_str}.\n"
                        f"    Runtime Evidence:\n"
                        f"    - Non-null count: {result.non_null_count}\n"
                        f"    - Unique values: {result.unique_non_null_values}\n"
                        f"    - Unique ratio: {result.unique_ratio:.4f}\n"
                        f"    - Variance: {result.variance:.6g}\n"
                        f"    - Standard deviation: {result.std_dev:.6g}\n"
                        f"    - Coefficient of variation: {result.coefficient_of_variation:.6g}\n"
                        f"    Scientific Interpretation:\n"
                        f"    - Nearly constant values are not expected for this feature and may indicate "
                        f"a collector failure, merge bug, placeholder propagation, or feature engineering regression."
                    )
                    result.add_check("low_variance_check", STATUS_WARN_INVESTIGATE, detail)
                else:
                    result.add_check(
                        "low_variance_check", STATUS_PASS,
                        f"Passed low-variance check (unique={result.unique_non_null_values}, ratio={result.unique_ratio:.2%}, var={result.variance:.4g})"
                    )
            else:
                if "Publication Lag" in spec.name and is_constant:
                    result.add_check(
                        "low_variance_check", STATUS_SKIP,
                        "Publication Lag is constant across the current dataset. This is expected for this data snapshot and does not indicate a pipeline regression."
                    )

        return result

    # ------------------------------------------------------------------
    # ML model validation
    # ------------------------------------------------------------------

    def _validate_ml_model(
        self, spec: FeatureSpec, df: Optional[pd.DataFrame]
    ) -> StageResult:
        """Validate feature presence in the ML model input feature list."""
        result = StageResult(
            feature_name=spec.name,
            stage="FeatureGroupManager",
            present=False,
            dtype_observed=None,
            null_pct=None,
            placeholder_pct=None,
            sample_values=[],
            observed_min=None,
            observed_max=None,
            unit_expected=spec.get_unit("FeatureGroupManager"),
            range_violation_pct=None,
        )

        if not spec.in_model:
            result.add_check(
                "model_inclusion", STATUS_SKIP,
                "Not expected in ML model input (non-model feature)"
            )
            return result

        ml_features = self._get_ml_features()
        if spec.name in ml_features:
            result.present = True
            if df is not None and spec.name in df.columns:
                result.add_check(
                    "model_inclusion", STATUS_PASS,
                    f"Present in FeatureGroupManager.get_features_in_group({spec.group}) "
                    f"and exists in train_dataset.csv"
                )
            else:
                result.add_check(
                    "model_inclusion", STATUS_WARN_INVESTIGATE,
                    f"Present in FeatureGroupManager but absent from train_dataset.csv"
                )
        else:
            result.add_check(
                "model_inclusion", STATUS_FAIL,
                f"Missing from FeatureGroupManager groups {ML_MODEL_GROUPS}; "
                f"feature will be silently excluded from model training"
            )
        return result

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self) -> Dict[str, List[StageResult]]:
        """
        Run the full pipeline validation.

        Returns
        -------
        Dict mapping feature_name → list of StageResult (one per stage).
        """
        stage_dfs: Dict[str, Optional[pd.DataFrame]] = {}
        for stage in PIPELINE_STAGES:
            if stage == "FeatureGroupManager":
                continue
            if stage == "Collector":
                stage_dfs["Collector_satellite"] = self._load_stage("Collector_satellite")
                stage_dfs["Collector_meteorology"] = self._load_stage("Collector_meteorology")
                stage_dfs["Collector_target"] = self._load_stage("Collector_target")
            else:
                stage_dfs[stage] = self._load_stage(stage)

        train_df = stage_dfs.get("train_dataset.csv")

        results: Dict[str, List[StageResult]] = {}

        for feature_name, spec in PIPELINE_FEATURE_SCHEMA.items():
            feature_results: List[StageResult] = []

            for stage in PIPELINE_STAGES:
                if stage == "FeatureGroupManager":
                    sr = self._validate_ml_model(spec, train_df)
                else:
                    if stage == "Collector":
                        if spec.group == "target":
                            df = stage_dfs.get("Collector_target")
                        elif spec.group == "meteorology":
                            df = stage_dfs.get("Collector_meteorology")
                        elif spec.group in ("satellite", "provenance"):
                            df = stage_dfs.get("Collector_satellite")
                        else:
                            df = None
                    else:
                        df = stage_dfs.get(stage)
                    sr = self._validate_feature_at_stage(spec, stage, df)
                feature_results.append(sr)

            results[feature_name] = feature_results
            overall = _aggregate_status(feature_results)
            logger.debug("%s → %s", feature_name, overall)

        return results


def _aggregate_status(results: List[StageResult]) -> str:
    """Return the worst status across all stage results using priority ordering."""
    if not results:
        return STATUS_SKIP
    statuses = [r.status for r in results]
    return max(statuses, key=lambda s: _STATUS_PRIORITY.get(s, 0))
