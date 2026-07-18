"""ERA5 Meteorological Data Downloader for the AKASH pipeline.

Responsibilities
----------------
* Build the CDS API request dictionary from config.
* Write the request specification to raw_data/era5_request_spec.json (always).
* Write a standalone helper download script to raw_data/download_era5_script.py (always).
* When ``dry_run=False``, execute the actual CDS API download via ``cdsapi``
  and save the NetCDF output to raw_data/era5_meteorological_india.nc.

Downstream conversion (NetCDF → era5_meteorology.csv) is handled by
``era5_processor.py`` in this same package.

Backward compatibility
----------------------
The public function signature ``prepare_era5_download(dry_run=...)`` is
preserved.  The default value of ``dry_run`` is now determined by the
environment:

* If the environment variable ``CDSAPI_KEY`` or file ``~/.cdsapirc`` exists,
  ``dry_run`` defaults to ``False`` (live mode).
* Otherwise it defaults to ``True`` (spec-only mode), preserving the original
  safe behaviour for environments without credentials.

Callers that pass an explicit ``dry_run`` argument are not affected.
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from data_collection_pipeline import config

logger = logging.getLogger("data_collection_pipeline.era5")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CDSAPI_RC_PATH: Path = Path.home() / ".cdsapirc"
_CDS_DATASET: str = "reanalysis-era5-single-levels"
_DEFAULT_OUTPUT_FILENAME: str = "era5_meteorological_india.nc"


# ---------------------------------------------------------------------------
# Credential helpers
# ---------------------------------------------------------------------------


def _cds_credentials_available() -> bool:
    """Return True if CDS API credentials are discoverable in the environment."""
    if _CDSAPI_RC_PATH.exists():
        logger.debug("CDS API credentials found at %s", _CDSAPI_RC_PATH)
        return True
    if os.environ.get("CDSAPI_KEY"):
        logger.debug("CDS API credentials found via CDSAPI_KEY environment variable.")
        return True
    return False


def _resolve_dry_run_default() -> bool:
    """Determine the default dry_run mode based on credential availability.

    Returns
    -------
    bool
        ``False`` (live mode) when CDS credentials are present.
        ``True``  (spec-only mode) when credentials are absent.
    """
    if _cds_credentials_available():
        logger.info(
            "CDS API credentials detected — defaulting to live download mode "
            "(dry_run=False).  Pass dry_run=True to override."
        )
        return False
    logger.warning(
        "[ERA5 CREDENTIALS] No CDS API credentials found. "
        "Checked: ~/.cdsapirc (%s) — NOT FOUND; "
        "CDSAPI_KEY environment variable — NOT SET. "
        "Defaulting to dry-run mode (no CDS API call). "
        "ERA5 download is SKIPPED. "
        "Configure ~/.cdsapirc or set CDSAPI_KEY to enable live downloads.",
        _CDSAPI_RC_PATH,
    )
    return True


def diagnose_credentials() -> dict:
    """Detect CDS API credentials and return a structured status dictionary.

    Checks both ``~/.cdsapirc`` and the ``CDSAPI_KEY`` environment variable.
    Provides actionable remediation steps when credentials are absent.

    Returns
    -------
    dict
        Keys: ``has_cdsapirc``, ``has_env_key``, ``overall``, ``source``,
        ``cdsapirc_path``, ``missing_reason``, ``remediation``.
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
            "  python data_collection_pipeline/scripts/run_pipeline.py "
            "--era5-only --no-dry-run"
        )

    if overall:
        logger.info(
            "[ERA5 CREDENTIALS] Credentials detected via: %s", source
        )
    else:
        logger.warning(
            "[ERA5 CREDENTIALS] No CDS API credentials found. "
            "Checked ~/.cdsapirc (%s): NOT FOUND. "
            "Checked CDSAPI_KEY env var: NOT SET. "
            "ERA5 download will be skipped. "
            "The pipeline will continue with placeholder meteorological data.",
            _CDSAPI_RC_PATH,
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
# Request dict builder
# ---------------------------------------------------------------------------


def get_era5_request_dict(
    year: str = "2026",
    month: str = "07",
    day: str = "01",
    variables: Optional[List[str]] = None,
) -> Dict:
    """Build the CDS API request dictionary for ERA5 single-levels reanalysis.

    The spatial area is fixed to India's bounding box (North, West, South,
    East) as configured in ``config.ERA5_BOUNDING_BOX``.

    Parameters
    ----------
    year:
        Four-digit year string, e.g. ``"2026"``.
    month:
        Two-digit month string, e.g. ``"07"``.
    day:
        Two-digit day string, e.g. ``"01"``.
    variables:
        List of ERA5 variable short names to request.  Defaults to
        ``config.ERA5_DEFAULT_VARIABLES``.

    Returns
    -------
    dict
        CDS API request payload.
    """
    if variables is None:
        variables = config.ERA5_DEFAULT_VARIABLES.copy()
        
    # Ensure variables required by the ML pipeline/validator are downloaded
    if "surface_pressure" not in variables:
        variables.append("surface_pressure")
    if "2m_dewpoint_temperature" not in variables:
        variables.append("2m_dewpoint_temperature")

    return {
        "product_type": "reanalysis",
        "format": "netcdf",
        "variable": variables,
        "year": year,
        "month": month,
        "day": day,
        "time": [
            "00:00", "01:00", "02:00", "03:00", "04:00", "05:00",
            "06:00", "07:00", "08:00", "09:00", "10:00", "11:00",
            "12:00", "13:00", "14:00", "15:00", "16:00", "17:00",
            "18:00", "19:00", "20:00", "21:00", "22:00", "23:00",
        ],
        # North, West, South, East
        "area": config.ERA5_BOUNDING_BOX,
    }


# ---------------------------------------------------------------------------
# Spec and helper-script writers (always executed)
# ---------------------------------------------------------------------------


def _write_request_spec(spec_path: Path, request_dict: Dict) -> bool:
    """Persist the CDS API request dict as JSON.

    Returns
    -------
    bool
        True on success, False on I/O error.
    """
    try:
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        with open(spec_path, "w", encoding="utf-8") as fh:
            json.dump(request_dict, fh, indent=4)
        logger.info("Saved ERA5 request specification to %s", spec_path)
        return True
    except OSError as exc:
        logger.error("Failed to write ERA5 request specification: %s", exc)
        return False


def _write_helper_script(script_path: Path, request_dict: Dict, target_nc_name: str) -> bool:
    """Write a standalone Python script that can download ERA5 data manually.

    Returns
    -------
    bool
        True on success, False on I/O error.
    """
    script_content = (
        "# Auto-generated script to download ERA5 data for India.\n"
        "# Requirements: pip install cdsapi\n"
        "# Configure credentials: ~/.cdsapirc or CDSAPI_KEY env var.\n\n"
        "import cdsapi\n\n"
        "client = cdsapi.Client()\n\n"
        f"dataset = {repr(_CDS_DATASET)}\n"
        f"request = {json.dumps(request_dict, indent=4)}\n"
        f"target = {repr(target_nc_name)}\n\n"
        'print(f"Downloading ERA5 data to {target} ...")\n'
        "client.retrieve(dataset, request, target)\n"
        'print("Download complete!")\n'
    )
    try:
        script_path.parent.mkdir(parents=True, exist_ok=True)
        with open(script_path, "w", encoding="utf-8") as fh:
            fh.write(script_content)
        logger.info("Saved standalone ERA5 download helper script to %s", script_path)
        return True
    except OSError as exc:
        logger.error("Failed to write ERA5 helper script: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Live download
# ---------------------------------------------------------------------------


def _execute_cds_download(request_dict: Dict, target_path: Path) -> bool:
    """Invoke the CDS API client and save the NetCDF file.

    Parameters
    ----------
    request_dict:
        CDS API request payload (from :func:`get_era5_request_dict`).
    target_path:
        Absolute path where the downloaded ``.nc`` file will be saved.

    Returns
    -------
    bool
        True on success, False on any error.
    """
    logger.info("Initiating CDS API download → %s", target_path)

    if not _cds_credentials_available():
        logger.error(
            "CDS API credentials not found.  Please create ~/.cdsapirc or "
            "set the CDSAPI_KEY environment variable and retry."
        )
        return False

    try:
        import cdsapi  # noqa: PLC0415 — lazy import to avoid hard dependency
    except ImportError:
        logger.error(
            "The 'cdsapi' package is not installed.  "
            "Run: pip install cdsapi>=0.7.0"
        )
        return False

    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
        client = cdsapi.Client()
        logger.info(
            "Requesting dataset '%s' with %d variable(s) for %s/%s/%s ...",
            _CDS_DATASET,
            len(request_dict.get("variable", [])),
            request_dict.get("year"),
            request_dict.get("month"),
            request_dict.get("day"),
        )
        client.retrieve(_CDS_DATASET, request_dict, str(target_path))
        logger.info("[ERA5 DOWNLOAD] Downloaded archive:\n%s", target_path.name)
        
        import zipfile
        import shutil
        
        if zipfile.is_zipfile(target_path):
            logger.info("[ERA5 ZIP] ZIP archive detected.")
            extract_dir = target_path.parent / "era5_extract"
            extract_dir.mkdir(parents=True, exist_ok=True)
            
            with zipfile.ZipFile(target_path, 'r') as zf:
                zf.extractall(extract_dir)
                extracted_files = zf.namelist()
                logger.info("[ERA5 ZIP] Extracted %d NetCDF files.", len(extracted_files))
                for f in extracted_files:
                    logger.info("[ERA5 ZIP] Extracted:\n%s", f)
                    
            nc_files = list(extract_dir.glob("*.nc"))
            if nc_files:
                selected_nc = next((nc for nc in nc_files if "instant" in nc.name), nc_files[0])
                logger.info("[ERA5 ZIP] Selected:\n%s", selected_nc.name)
                
                logger.info("[ERA5] Injecting derived variables (Relative Humidity) into NetCDF...")
                try:
                    import xarray as xr
                    import numpy as np
                    
                    with xr.open_dataset(selected_nc) as ds:
                        ds_mod = ds.copy(deep=True)
                        
                        if "d2m" in ds_mod and "t2m" in ds_mod:
                            t_c = ds_mod["t2m"] - 273.15
                            d_c = ds_mod["d2m"] - 273.15
                            # August-Roche-Magnus approximation
                            rh = 100.0 * np.exp((17.625 * d_c) / (243.04 + d_c)) / np.exp((17.625 * t_c) / (243.04 + t_c))
                            ds_mod["r"] = rh
                            logger.info("[ERA5 ZIP] Calculated Relative Humidity (r) from t2m and d2m.")
                            
                        target_path.unlink(missing_ok=True)
                        ds_mod.to_netcdf(target_path)
                except Exception as e:
                    logger.error("[ERA5 ZIP] Failed to process NetCDF via xarray: %s", e)
                    target_path.unlink(missing_ok=True)
                    shutil.move(str(selected_nc), str(target_path))
            else:
                logger.error("[ERA5 ZIP] No NetCDF files found in the extracted archive.")
                return False
                
        logger.info(
            "ERA5 NetCDF downloaded successfully: %s (%.1f MB)",
            target_path,
            target_path.stat().st_size / 1_048_576,
        )
        return True

    except Exception as exc:  # noqa: BLE001 — cdsapi raises varied exceptions
        # Classify the most common failure modes for actionable log messages.
        exc_str = str(exc).lower()
        if "401" in exc_str or "unauthorized" in exc_str or "authentication" in exc_str:
            logger.error(
                "CDS API authentication failed (HTTP 401).  "
                "Verify your API key in ~/.cdsapirc or CDSAPI_KEY."
            )
        elif "403" in exc_str or "forbidden" in exc_str:
            logger.error(
                "CDS API request forbidden (HTTP 403).  "
                "Check dataset access permissions for your account."
            )
        elif "quota" in exc_str or "limit" in exc_str:
            logger.error(
                "CDS API quota exceeded.  Wait for the queue to clear and retry."
            )
        elif "timeout" in exc_str:
            logger.error(
                "CDS API request timed out.  The ERA5 dataset may be large; "
                "consider narrowing the date range or variable list."
            )
        else:
            logger.error("CDS API download failed: %s", exc)
        return False


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def prepare_era5_download(
    year: str = "2026",
    month: str = "07",
    day: str = "01",
    variables: Optional[List[str]] = None,
    output_filename: str = _DEFAULT_OUTPUT_FILENAME,
    dry_run: Optional[bool] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> bool:
    """Prepare and optionally execute the ERA5 meteorological data download.

    Always writes:
    * ``raw_data/era5_request_spec.json`` — machine-readable request payload.
    * ``raw_data/download_era5_script.py`` — standalone helper script.

    When ``dry_run=False``, additionally downloads:
    * ``raw_data/<output_filename>`` — ERA5 NetCDF file.

    The NetCDF file must subsequently be converted to a tabular CSV by
    ``era5_processor.process_era5_netcdf()`` before it can be consumed by
    the feature-engineering merger.

    Parameters
    ----------
    year, month, day:
        Date identifiers for the ERA5 request.  Overridden when ``start_date``
        is provided.
    variables:
        ERA5 variable short names to include.  Defaults to
        ``config.ERA5_DEFAULT_VARIABLES``.
    output_filename:
        Name of the NetCDF output file, saved under ``raw_data/``.
    start_date:
        Optional ISO-8601 date string (``YYYY-MM-DD``).  When supplied the
        ``year``, ``month``, and ``day`` positional arguments are overridden
        with the values parsed from this string.  Intended for use by the
        historical ingestion pipeline; ignored when ``None``.
    end_date:
        Optional ISO-8601 date string (``YYYY-MM-DD``).  Currently stored in
        the request spec for documentation purposes.  ERA5 single-level daily
        requests are best made one day at a time; the historical ERA5 collector
        iterates month-by-month and sets this to the last day of the month.
    dry_run:
        * ``True``  — write spec + helper script only (no API call).
        * ``False`` — write spec + helper script AND execute CDS API download.
        * ``None``  — auto-detect: ``False`` if credentials exist, else ``True``.

    Returns
    -------
    bool
        True if all requested operations completed without error.
    """
    # If start_date is supplied by the historical pipeline, override year/month/day.
    if start_date is not None:
        try:
            import datetime as _dt
            _sd = _dt.date.fromisoformat(start_date)
            year = str(_sd.year)
            month = f"{_sd.month:02d}"
            day = f"{_sd.day:02d}"
            logger.info(
                "Historical mode: start_date=%s → year=%s month=%s day=%s.",
                start_date, year, month, day,
            )
        except ValueError as exc:
            logger.error(
                "Invalid start_date format '%s': %s.  Expected YYYY-MM-DD.  "
                "Falling back to positional year/month/day arguments.",
                start_date, exc,
            )

    # Resolve dry_run default from environment when caller passes None.
    if dry_run is None:
        dry_run = _resolve_dry_run_default()

    logger.info(
        "ERA5 preparation starting (dry_run=%s, date=%s-%s-%s).",
        dry_run, year, month, day,
    )

    request_dict = get_era5_request_dict(year, month, day, variables)
    raw_dir = config.RAW_DATA_DIR
    spec_path = raw_dir / "era5_request_spec.json"
    script_path = raw_dir / "download_era5_script.py"
    target_nc_path = raw_dir / output_filename

    # Always write the spec and helper script.
    if not _write_request_spec(spec_path, request_dict):
        return False
    if not _write_helper_script(script_path, request_dict, output_filename):
        return False

    if dry_run:
        logger.info(
            "[DRY RUN] Spec written to %s.  "
            "No API call made.  To download, run: python %s  "
            "or call prepare_era5_download(dry_run=False).",
            spec_path,
            script_path,
        )
        return True

    # Execute live download.
    success = _execute_cds_download(request_dict, target_nc_path)
    if success:
        logger.info(
            "ERA5 NetCDF ready at %s.  "
            "Next step: run era5_processor.process_era5_netcdf() to convert "
            "to processed_data/era5_meteorology.csv for feature engineering.",
            target_nc_path,
        )
    else:
        logger.error(
            "ERA5 download failed.  "
            "The pipeline will fall back to placeholder meteorological data "
            "until a valid NetCDF is available at %s.",
            target_nc_path,
        )
    return success
