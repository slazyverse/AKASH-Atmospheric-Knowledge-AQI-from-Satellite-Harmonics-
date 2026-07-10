"""
ERA5 pipeline validation module for the AKASH pipeline.

Responsibilities
----------------
* Validate the generated ``era5_meteorology.csv`` against a set of
  structural and data-quality requirements.
* Detect CDS credentials and report exactly which source was found
  (or which is missing) with actionable remediation steps.
* Orchestrate the full ERA5 pipeline audit:
    CDS Auth → Download → NetCDF Processing → CSV Generation → Validation
* Write ``era5_pipeline_validation_report.md`` to the workspace root.

This module is VALIDATION AND REPORTING ONLY.
It does NOT modify any dataset, model, or feature value.
It does NOT fabricate ERA5 data.
It does NOT bypass authentication.
"""

from __future__ import annotations

import datetime
import logging
import os
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from data_collection_pipeline import config

logger = logging.getLogger("data_collection_pipeline.era5_validator")

# ---------------------------------------------------------------------------
# Required columns that must be present in a valid era5_meteorology.csv
# ---------------------------------------------------------------------------

REQUIRED_COLUMNS: List[str] = [
    "timestamp",
    "latitude",
    "longitude",
    "Temperature",
    "Relative Humidity",
    "Boundary Layer Height",
    "Surface Pressure",
    "Wind Speed",
    "Wind Direction",
]

_CDSAPI_RC_PATH: Path = Path.home() / ".cdsapirc"


# ---------------------------------------------------------------------------
# Credential diagnosis
# ---------------------------------------------------------------------------


def diagnose_credentials() -> Dict:
    """
    Detect CDS API credentials and return a structured status dict.

    Checks both ``~/.cdsapirc`` and the ``CDSAPI_KEY`` environment variable.
    Returns clear information about what was found and what is missing.

    Returns
    -------
    dict with keys:
        has_cdsapirc      : bool  — True if ~/.cdsapirc exists
        has_env_key       : bool  — True if CDSAPI_KEY env var is set
        overall           : bool  — True if at least one credential source exists
        source            : str   — human-readable label of the credential source
        cdsapirc_path     : str   — path checked for .cdsapirc
        missing_reason    : str   — empty string if credentials OK, otherwise explains what is missing
        remediation       : str   — instructions to fix missing credentials
    """
    has_cdsapirc = _CDSAPI_RC_PATH.exists()
    env_key = os.environ.get("CDSAPI_KEY", "")
    has_env_key = bool(env_key)

    overall = has_cdsapirc or has_env_key

    if has_cdsapirc and has_env_key:
        source = f"~/.cdsapirc (primary) + CDSAPI_KEY env var (also set)"
        missing_reason = ""
        remediation = ""
    elif has_cdsapirc:
        source = f"~/.cdsapirc file at {_CDSAPI_RC_PATH}"
        missing_reason = ""
        remediation = ""
    elif has_env_key:
        source = "CDSAPI_KEY environment variable"
        missing_reason = ""
        remediation = ""
    else:
        source = "None detected"
        missing_reason = (
            f"Neither ~/.cdsapirc (checked: {_CDSAPI_RC_PATH}) "
            "nor the CDSAPI_KEY environment variable is configured."
        )
        remediation = (
            "To enable live ERA5 downloads, do one of the following:\n"
            "\n"
            "Option A — Create ~/.cdsapirc:\n"
            "  1. Register at https://cds.climate.copernicus.eu/\n"
            "  2. Go to your profile page and copy your API key.\n"
            "  3. Create the file ~/.cdsapirc with contents:\n"
            "       url: https://cds.climate.copernicus.eu/api\n"
            "       key: <your-uid>:<your-api-key>\n"
            "\n"
            "Option B — Set environment variable:\n"
            "  set CDSAPI_KEY=<your-uid>:<your-api-key>   # Windows\n"
            "  export CDSAPI_KEY=<your-uid>:<your-api-key> # Linux/macOS\n"
            "\n"
            "After configuring credentials, re-run:\n"
            "  python data_collection_pipeline/scripts/run_pipeline.py --era5-only --no-dry-run"
        )

    if overall:
        logger.info(
            "[ERA5 CREDENTIALS] Credentials detected via: %s", source
        )
    else:
        logger.warning(
            "[ERA5 CREDENTIALS] No CDS API credentials found. "
            "ERA5 download will be skipped. %s",
            missing_reason,
        )
        logger.warning(
            "[ERA5 CREDENTIALS] Remediation: configure ~/.cdsapirc or set "
            "the CDSAPI_KEY environment variable. "
            "The remaining pipeline will continue using placeholder meteorological data."
        )

    return {
        "has_cdsapirc": has_cdsapirc,
        "has_env_key": has_env_key,
        "overall": overall,
        "source": source,
        "cdsapirc_path": str(_CDSAPI_RC_PATH),
        "missing_reason": missing_reason,
        "remediation": remediation,
    }


# ---------------------------------------------------------------------------
# CSV validation
# ---------------------------------------------------------------------------


def validate_era5_csv(
    csv_path: Optional[Path] = None,
) -> Dict:
    """
    Validate a generated ``era5_meteorology.csv`` against structural and
    data-quality requirements.

    Checks performed
    ----------------
    1. File existence
    2. Non-empty (at least 1 row)
    3. Required columns present
    4. No duplicate (timestamp, latitude, longitude) triplets
    5. Latitude and longitude columns are populated (non-null)
    6. Meteorological variables are at least partially populated (not entirely null)

    Parameters
    ----------
    csv_path:
        Path to the CSV to validate.  Defaults to
        ``config.PROCESSED_DATA_DIR / "era5_meteorology.csv"``.

    Returns
    -------
    dict with keys:
        passed         : bool
        file_exists    : bool
        row_count      : int
        column_checks  : dict[str, bool]   — required col → present?
        duplicate_rows : int
        null_pct       : dict[str, float]  — column → null percentage
        issues         : list[str]         — human-readable problem descriptions
        warnings       : list[str]
    """
    if csv_path is None:
        csv_path = config.PROCESSED_DATA_DIR / "era5_meteorology.csv"

    result: Dict = {
        "passed": False,
        "file_exists": False,
        "row_count": 0,
        "column_checks": {},
        "duplicate_rows": 0,
        "null_pct": {},
        "issues": [],
        "warnings": [],
    }

    # --- Check 1: File existence ---
    if not csv_path.exists():
        result["issues"].append(
            f"era5_meteorology.csv not found at {csv_path}. "
            "Run --era5-only (with credentials) or --process-era5 first."
        )
        logger.error("[ERA5 VALIDATOR] File not found: %s", csv_path)
        return result

    result["file_exists"] = True
    logger.info("[ERA5 VALIDATOR] Found era5_meteorology.csv at %s", csv_path)

    # --- Load ---
    try:
        df = pd.read_csv(csv_path)
    except Exception as exc:  # noqa: BLE001
        result["issues"].append(f"Failed to read CSV: {exc}")
        logger.error("[ERA5 VALIDATOR] Cannot read CSV: %s", exc)
        return result

    result["row_count"] = len(df)

    # --- Check 2: Non-empty ---
    if len(df) == 0:
        result["issues"].append("era5_meteorology.csv exists but contains 0 data rows.")
        logger.error("[ERA5 VALIDATOR] CSV is empty.")
        return result

    logger.info("[ERA5 VALIDATOR] CSV loaded: %d rows, %d columns.", len(df), len(df.columns))

    # --- Check 3: Required columns ---
    for col in REQUIRED_COLUMNS:
        present = col in df.columns
        result["column_checks"][col] = present
        if not present:
            result["issues"].append(f"Required column '{col}' is missing from era5_meteorology.csv.")
            logger.error("[ERA5 VALIDATOR] Missing required column: '%s'", col)
        else:
            logger.info("[ERA5 VALIDATOR] Column '%s': present ✓", col)

    # --- Check 4: Duplicate timestamp/lat/lon triplets ---
    key_cols = [c for c in ["timestamp", "latitude", "longitude"] if c in df.columns]
    if len(key_cols) == 3:
        dup_count = int(df.duplicated(subset=key_cols).sum())
        result["duplicate_rows"] = dup_count
        if dup_count > 0:
            result["warnings"].append(
                f"{dup_count} duplicate (timestamp, latitude, longitude) triplets detected."
            )
            logger.warning("[ERA5 VALIDATOR] %d duplicate timestamp/lat/lon triplets.", dup_count)
        else:
            logger.info("[ERA5 VALIDATOR] No duplicate timestamp/lat/lon triplets. ✓")

    # --- Check 5 & 6: Null percentages ---
    all_check_cols = REQUIRED_COLUMNS + [
        c for c in df.columns if c not in REQUIRED_COLUMNS
    ]
    for col in all_check_cols:
        if col in df.columns:
            null_pct = float(df[col].isna().mean() * 100)
            result["null_pct"][col] = round(null_pct, 2)
            if col in ("latitude", "longitude") and null_pct > 0:
                result["issues"].append(
                    f"Column '{col}' has {null_pct:.1f}% null values — "
                    "coordinate data must be fully populated."
                )
                logger.error("[ERA5 VALIDATOR] '%s' has %.1f%% null values.", col, null_pct)
            elif col in (
                "Temperature", "Relative Humidity", "Boundary Layer Height",
                "Surface Pressure", "Wind Speed", "Wind Direction"
            ) and null_pct == 100.0 and col in df.columns:
                result["issues"].append(
                    f"Meteorological column '{col}' is entirely null (100% missing). "
                    "The ERA5 NetCDF may not contain this variable."
                )
                logger.error(
                    "[ERA5 VALIDATOR] '%s' is 100%% null — variable absent from NetCDF.", col
                )
            else:
                if col in REQUIRED_COLUMNS:
                    logger.info(
                        "[ERA5 VALIDATOR] Column '%-30s'  null=%.1f%%", col, null_pct
                    )

    result["passed"] = len(result["issues"]) == 0
    if result["passed"]:
        logger.info("[ERA5 VALIDATOR] Validation PASSED — all checks met.")
    else:
        logger.error(
            "[ERA5 VALIDATOR] Validation FAILED — %d issue(s) found.", len(result["issues"])
        )

    return result


# ---------------------------------------------------------------------------
# Validation report writer
# ---------------------------------------------------------------------------


def write_validation_report(
    credential_info: Dict,
    download_status: str,   # "PASS" | "FAIL" | "SKIPPED (no credentials)" | "SKIPPED (dry_run)"
    processing_status: str, # "PASS" | "FAIL" | "SKIPPED"
    csv_validation: Dict,
    runtime_seconds: float,
    output_path: Path,
    extra_notes: Optional[List[str]] = None,
) -> None:
    """
    Write ``era5_pipeline_validation_report.md`` to ``output_path``.

    Parameters
    ----------
    credential_info  : dict from ``diagnose_credentials()``.
    download_status  : string describing the download outcome.
    processing_status: string describing the NetCDF→CSV processing outcome.
    csv_validation   : dict from ``validate_era5_csv()``.
    runtime_seconds  : total elapsed seconds for the ERA5 pipeline run.
    output_path      : where to write the report (workspace root recommended).
    extra_notes      : optional list of additional notes to include.
    """
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    overall_passed = (
        credential_info["overall"]
        and download_status == "PASS"
        and processing_status == "PASS"
        and csv_validation.get("passed", False)
    )
    overall_badge = "✅ PASS" if overall_passed else "❌ FAIL"

    # Build null % table rows
    null_rows = []
    for col, pct in csv_validation.get("null_pct", {}).items():
        flag = " ⚠️" if pct == 100.0 else ""
        null_rows.append(f"| {col} | {pct:.1f}% |{flag}")

    null_table = (
        "\n".join(null_rows)
        if null_rows
        else "| (no data — CSV not generated) | — |"
    )

    # Column check rows
    col_check_rows = []
    for col, present in csv_validation.get("column_checks", {}).items():
        badge = "✅ Present" if present else "❌ Missing"
        col_check_rows.append(f"| `{col}` | {badge} |")
    col_check_section = (
        "\n".join(col_check_rows)
        if col_check_rows
        else "| (CSV not generated) | — |"
    )

    issues = csv_validation.get("issues", [])
    warnings = csv_validation.get("warnings", [])
    issue_section = (
        "\n".join(f"* ❌ {i}" for i in issues) if issues else "* None"
    )
    warning_section = (
        "\n".join(f"* ⚠️  {w}" for w in warnings) if warnings else "* None"
    )

    cred_icon = "✅" if credential_info["overall"] else "❌"
    dl_icon = "✅" if download_status == "PASS" else ("⏳" if "SKIPPED" in download_status else "❌")
    proc_icon = "✅" if processing_status == "PASS" else ("⏳" if "SKIPPED" in processing_status else "❌")
    csv_icon = "✅" if csv_validation.get("passed") else ("⏳" if not csv_validation.get("file_exists") else "❌")

    remediation_section = (
        f"\n```\n{credential_info['remediation']}\n```"
        if credential_info.get("remediation")
        else ""
    )

    extra_section = (
        "\n".join(f"* {n}" for n in extra_notes)
        if extra_notes
        else "* None"
    )

    report = f"""# ERA5 Pipeline Validation Report

> Generated: {timestamp}

---

## Overall Result: {overall_badge}

| Stage | Status |
|-------|--------|
| CDS Authentication | {cred_icon} {credential_info['source']} |
| ERA5 Download | {dl_icon} {download_status} |
| NetCDF → CSV Processing | {proc_icon} {processing_status} |
| CSV Generation & Validation | {csv_icon} {"PASS" if csv_validation.get("passed") else ("SKIPPED" if not csv_validation.get("file_exists") else "FAIL")} |

**Total Runtime:** {runtime_seconds:.1f} seconds

---

## Authentication Details

| Property | Value |
|----------|-------|
| **~/.cdsapirc exists** | {"✅ Yes" if credential_info["has_cdsapirc"] else "❌ No"} |
| **CDSAPI_KEY env var set** | {"✅ Yes" if credential_info["has_env_key"] else "❌ No"} |
| **Credential source used** | {credential_info["source"]} |
| **Checked path** | `{credential_info["cdsapirc_path"]}` |

{"### Missing Credentials" if credential_info.get("missing_reason") else ""}
{f"> [!WARNING]" if credential_info.get("missing_reason") else ""}
{credential_info.get("missing_reason", "") if credential_info.get("missing_reason") else ""}

{"### Remediation Steps" if credential_info.get("remediation") else ""}
{remediation_section}

---

## CSV Validation Results

| Metric | Value |
|--------|-------|
| **File exists** | {"✅ Yes" if csv_validation.get("file_exists") else "❌ No"} |
| **Row count** | {csv_validation.get("row_count", 0)} |
| **Duplicate timestamp/lat/lon** | {csv_validation.get("duplicate_rows", "—")} |
| **Validation status** | {"✅ PASS" if csv_validation.get("passed") else ("⏳ SKIPPED" if not csv_validation.get("file_exists") else "❌ FAIL")} |

### Required Column Presence

| Column | Status |
|--------|--------|
{col_check_section}

### Null Percentage per Variable

| Column | Null % |
|--------|--------|
{null_table}

---

## Issues

{issue_section}

## Warnings

{warning_section}

## Additional Notes

{extra_section}

---

*Report generated by `era5_validator.py` | AKASH Pipeline — Team RAPTORS*
"""

    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        logger.info("[ERA5 VALIDATOR] Validation report written to %s", output_path)
    except OSError as exc:
        logger.error("[ERA5 VALIDATOR] Failed to write validation report: %s", exc)


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def run_era5_pipeline_validation(
    download_success: bool,
    processing_success: bool,
    dry_run: bool,
    credential_info: Dict,
    runtime_seconds: float,
    report_path: Optional[Path] = None,
    csv_path: Optional[Path] = None,
) -> Dict:
    """
    Run the full ERA5 pipeline validation and write the report.

    Parameters
    ----------
    download_success    : True if NetCDF was downloaded successfully.
    processing_success  : True if NetCDF was converted to CSV successfully.
    dry_run             : True if the pipeline ran in dry-run mode.
    credential_info     : dict from ``diagnose_credentials()``.
    runtime_seconds     : elapsed time for the ERA5 run.
    report_path         : where to write the report. Defaults to workspace root.
    csv_path            : path to validate. Defaults to processed_data/era5_meteorology.csv.

    Returns
    -------
    dict with keys ``passed``, ``csv_validation``, ``download_status``,
    ``processing_status``.
    """
    if report_path is None:
        report_path = config.BASE_DIR.parent / "era5_pipeline_validation_report.md"
    if csv_path is None:
        csv_path = config.PROCESSED_DATA_DIR / "era5_meteorology.csv"

    # Determine stage statuses
    if dry_run:
        download_status = "SKIPPED (dry_run=True — no CDS API call made)"
    elif not credential_info["overall"]:
        download_status = "SKIPPED (no credentials — ERA5 download not attempted)"
    elif download_success:
        download_status = "PASS"
    else:
        download_status = "FAIL"

    if dry_run or not credential_info["overall"]:
        processing_status = "SKIPPED (download was not executed)"
    elif not download_success:
        processing_status = "SKIPPED (download failed)"
    elif processing_success:
        processing_status = "PASS"
    else:
        processing_status = "FAIL"

    # Run CSV validation
    csv_validation = validate_era5_csv(csv_path=csv_path)

    # Compose extra notes
    extra_notes: List[str] = []
    if dry_run:
        extra_notes.append(
            "Pipeline ran in dry-run mode. Only the ERA5 request spec and helper "
            "script were written. No CDS API call was made."
        )
    if not credential_info["overall"]:
        extra_notes.append(
            "CDS credentials were absent. The pipeline continues with placeholder "
            "meteorological data until credentials are configured."
        )
    if csv_validation.get("file_exists") and csv_validation.get("passed"):
        extra_notes.append(
            "era5_meteorology.csv is valid. The next --integrate-only run will "
            "automatically consume real ERA5 data instead of placeholders."
        )
    elif csv_validation.get("file_exists") and not csv_validation.get("passed"):
        extra_notes.append(
            "era5_meteorology.csv exists but failed validation. "
            "Review the issues above and re-run --era5-only --no-dry-run."
        )
    else:
        extra_notes.append(
            "era5_meteorology.csv was not found. Feature engineering will use "
            "placeholder meteorological data until the file is generated."
        )

    write_validation_report(
        credential_info=credential_info,
        download_status=download_status,
        processing_status=processing_status,
        csv_validation=csv_validation,
        runtime_seconds=runtime_seconds,
        output_path=report_path,
        extra_notes=extra_notes,
    )

    overall_passed = (
        credential_info["overall"]
        and download_success
        and processing_success
        and csv_validation.get("passed", False)
    )

    logger.info(
        "[ERA5 VALIDATOR] Pipeline validation complete. "
        "Overall=%s | download=%s | processing=%s | csv=%s",
        "PASS" if overall_passed else "FAIL",
        download_status,
        processing_status,
        "PASS" if csv_validation.get("passed") else "FAIL/SKIPPED",
    )

    return {
        "passed": overall_passed,
        "csv_validation": csv_validation,
        "download_status": download_status,
        "processing_status": processing_status,
    }
