"""Sentinel-5P / TROPOMI Satellite Data Collector for the AKASH pipeline.

Provides AOD, HCHO, NO2 column, SO2 column, CO column, and O3 column
retrievals over India via the Google Earth Engine (GEE) Python API.

Architecture
------------
This module is a **satellite ingestion collector** — symmetrical in role to
``cpcb_collector.py`` and ``openaq_collector.py``.  It produces the file
``processed_data/satellite_predictors.csv`` which is automatically consumed
by ``feature_engineering/merger.load_satellite_grid()`` on the next
feature-engineering run.

The output CSV schema is aligned to ``merger.py``'s ``SATELLITE_RENAME_MAP``
so that the merger can pick up the data without any downstream changes.

Data Sources
------------
Sentinel-5P TROPOMI products used:

* ``COPERNICUS/S5P/OFFL/L3_NO2``  — NO2 tropospheric column
* ``COPERNICUS/S5P/OFFL/L3_SO2``  — SO2 total vertical column
* ``COPERNICUS/S5P/OFFL/L3_CO``   — CO total column
* ``COPERNICUS/S5P/OFFL/L3_O3``   — O3 total column
* ``COPERNICUS/S5P/OFFL/L3_HCHO`` — HCHO total column
* ``MODIS/061/MOD04_3K``           — AOD 550 nm (Terra, 3 km)

Coordinate system
-----------------
Outputs grid cells at 0.1° resolution over India's bounding box
(6–38°N, 68–98°E).  Each row represents one (timestamp, latitude, longitude)
triplet.

GEE Authentication
------------------
Requires either:
* A valid ``earthengine authenticate`` session (``~/.config/earthengine/``), or
* The ``GEE_SERVICE_ACCOUNT`` and ``GEE_SERVICE_ACCOUNT_KEY_FILE`` environment
  variables pointing to a service-account JSON key, or
* The ``GEE_SERVICE_ACCOUNT_KEY_JSON`` environment variable containing the
  JSON key inline (useful for CI/CD secrets).

When GEE credentials are absent, the module exits cleanly with an explanatory
error rather than silently writing placeholder data.

Dependencies
------------
``earthengine-api`` (``pip install earthengine-api``) — optional at import
time; a ``MissingGeeCredentialsError`` is raised at call time when absent.

Usage
-----
::

    # CLI — collect latest satellite data for today
    python -m data_collection_pipeline.sentinel5p_collector

    # CLI — collect for a specific date
    python -m data_collection_pipeline.sentinel5p_collector \\
        --date 2026-07-07 \\
        --output processed_data/satellite_predictors.csv

    # API
    from data_collection_pipeline.sentinel5p_collector import collect_satellite_data
    success = collect_satellite_data(date_str="2026-07-07")
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from data_collection_pipeline import config

logger = logging.getLogger("data_collection_pipeline.sentinel5p")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: India bounding box [West, South, East, North]
INDIA_BBOX: Tuple[float, float, float, float] = (68.0, 6.0, 98.0, 38.0)

#: Output grid resolution in degrees
GRID_RESOLUTION_DEG: float = 0.1

#: Default temporal window around the target date (in days)
TEMPORAL_WINDOW_DAYS: int = 1

#: Sentinel-5P TROPOMI GEE collection IDs
S5P_COLLECTIONS: Dict[str, str] = {
    "NO2 Column":  "COPERNICUS/S5P/OFFL/L3_NO2",
    "SO2 Column":  "COPERNICUS/S5P/OFFL/L3_SO2",
    "CO Column":   "COPERNICUS/S5P/OFFL/L3_CO",
    "O3 Column":   "COPERNICUS/S5P/OFFL/L3_O3",
    "HCHO":        "COPERNICUS/S5P/OFFL/L3_HCHO",
}

#: Band names within each TROPOMI collection to extract
S5P_BAND_MAP: Dict[str, str] = {
    "NO2 Column":  "tropospheric_NO2_column_number_density",
    "SO2 Column":  "SO2_column_number_density",
    "CO Column":   "CO_column_number_density",
    "O3 Column":   "O3_column_number_density",
    "HCHO":        "tropospheric_HCHO_column_number_density",
}

#: MODIS AOD collection and band
AOD_COLLECTION: str = "MODIS/061/MOD04_3K"
AOD_BAND: str = "Optical_Depth_Land_And_Ocean"

#: Canonical output column order (matches merger.SATELLITE_RENAME_MAP keys)
OUTPUT_COLUMNS: List[str] = [
    "timestamp",
    "latitude",
    "longitude",
    "AOD",
    "HCHO",
    "NO2 Column",
    "SO2 Column",
    "CO Column",
    "O3 Column",
]

_DEFAULT_OUTPUT_FILENAME: str = "satellite_predictors.csv"


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class MissingGeeCredentialsError(RuntimeError):
    """Raised when Google Earth Engine credentials cannot be found."""


class GeeAuthenticationError(RuntimeError):
    """Raised when GEE authentication fails despite credentials being present."""


# ---------------------------------------------------------------------------
# GEE authentication helpers
# ---------------------------------------------------------------------------


def _try_import_ee() -> object:
    """Import the earthengine-api, raising ImportError with install instructions."""
    try:
        import ee  # noqa: PLC0415
        return ee
    except ImportError as exc:
        raise ImportError(
            "The 'earthengine-api' package is required for satellite data collection.\n"
            "Install it with: pip install earthengine-api\n"
            "Then authenticate: earthengine authenticate"
        ) from exc


def _gee_credentials_available() -> bool:
    """Return True if any GEE authentication method is detectable."""
    # Interactive / OAuth credentials
    gee_cred_path = Path.home() / ".config" / "earthengine" / "credentials"
    if gee_cred_path.exists():
        return True
    # Service-account credentials via environment variables
    if os.environ.get("GEE_SERVICE_ACCOUNT") and (
        os.environ.get("GEE_SERVICE_ACCOUNT_KEY_FILE")
        or os.environ.get("GEE_SERVICE_ACCOUNT_KEY_JSON")
    ):
        return True
    return False


def _authenticate_gee(ee: object) -> None:
    """Authenticate to Google Earth Engine.

    Tries the following methods in order:
    1. Service-account key file (``GEE_SERVICE_ACCOUNT`` + ``GEE_SERVICE_ACCOUNT_KEY_FILE``).
    2. Service-account key JSON string (``GEE_SERVICE_ACCOUNT`` + ``GEE_SERVICE_ACCOUNT_KEY_JSON``).
    3. Default interactive/OAuth credentials from ``~/.config/earthengine/``.

    Parameters
    ----------
    ee:
        Imported ``earthengine-api`` module.

    Raises
    ------
    MissingGeeCredentialsError
        When no credentials can be found.
    GeeAuthenticationError
        When credentials exist but authentication fails.
    """
    sa = os.environ.get("GEE_SERVICE_ACCOUNT")
    key_file = os.environ.get("GEE_SERVICE_ACCOUNT_KEY_FILE")
    key_json_str = os.environ.get("GEE_SERVICE_ACCOUNT_KEY_JSON")

    try:
        if sa and key_file and Path(key_file).exists():
            logger.info("Authenticating GEE via service-account key file: %s", key_file)
            credentials = ee.ServiceAccountCredentials(sa, key_file)  # type: ignore[attr-defined]
            ee.Initialize(credentials)  # type: ignore[attr-defined]
            logger.info("GEE authenticated via service-account key file.")
            return

        if sa and key_json_str:
            logger.info("Authenticating GEE via inline service-account JSON.")
            import tempfile  # noqa: PLC0415
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(key_json_str)
                tmp_path = tmp.name
            try:
                credentials = ee.ServiceAccountCredentials(sa, tmp_path)  # type: ignore[attr-defined]
                ee.Initialize(credentials)  # type: ignore[attr-defined]
            finally:
                Path(tmp_path).unlink(missing_ok=True)
            logger.info("GEE authenticated via inline service-account JSON.")
            return

        # Fall back to OAuth / interactive credentials
        gee_cred_path = Path.home() / ".config" / "earthengine" / "credentials"
        if gee_cred_path.exists():
            logger.info("Authenticating GEE via OAuth credentials at %s.", gee_cred_path)
            ee.Initialize()  # type: ignore[attr-defined]
            logger.info("GEE authenticated via OAuth credentials.")
            return

        raise MissingGeeCredentialsError(
            "No Google Earth Engine credentials found.\n"
            "Options:\n"
            "  1. Run: earthengine authenticate\n"
            "  2. Set GEE_SERVICE_ACCOUNT + GEE_SERVICE_ACCOUNT_KEY_FILE env vars.\n"
            "  3. Set GEE_SERVICE_ACCOUNT + GEE_SERVICE_ACCOUNT_KEY_JSON env vars."
        )

    except MissingGeeCredentialsError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise GeeAuthenticationError(
            f"GEE authentication failed: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# GEE data extraction
# ---------------------------------------------------------------------------


def _build_india_geometry(ee: object) -> object:
    """Return a GEE geometry covering India's bounding box."""
    west, south, east, north = INDIA_BBOX
    return ee.Geometry.Rectangle([west, south, east, north])  # type: ignore[attr-defined]


def _date_range(date_str: str, window_days: int = TEMPORAL_WINDOW_DAYS) -> Tuple[str, str]:
    """Return (start_date, end_date) strings for a ±window_days window."""
    centre = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    start = centre - datetime.timedelta(days=window_days)
    end = centre + datetime.timedelta(days=window_days + 1)  # GEE end is exclusive
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _extract_band_mean(
    ee: object,
    collection_id: str,
    band_name: str,
    start: str,
    end: str,
    geometry: object,
    scale_m: int = 11_132,  # ~0.1° at equator
) -> Optional[pd.DataFrame]:
    """Extract the spatial mean of one band from a GEE image collection.

    Parameters
    ----------
    ee:
        earthengine-api module.
    collection_id:
        GEE collection string (e.g. ``"COPERNICUS/S5P/OFFL/L3_NO2"``).
    band_name:
        Band / property name within the collection.
    start, end:
        ISO date strings (inclusive start, exclusive end).
    geometry:
        GEE geometry over which to compute the mean.
    scale_m:
        Reduction scale in metres.

    Returns
    -------
    pd.DataFrame or None
        DataFrame with columns [timestamp, latitude, longitude, <feature>],
        or None if the collection is empty for the given period.
    """
    col = (
        ee.ImageCollection(collection_id)  # type: ignore[attr-defined]
        .filterDate(start, end)
        .filterBounds(geometry)
        .select(band_name)
    )

    size = col.size().getInfo()
    if size == 0:
        logger.warning(
            "No images found in %s for %s–%s over India.", collection_id, start, end
        )
        return None

    logger.debug(
        "Reducing %d image(s) from %s (band=%s).", size, collection_id, band_name
    )
    # Compute temporal mean for the period.
    mean_image = col.mean()

    # Sample the mean image over the India bounding box at 0.1° resolution.
    sample = mean_image.sample(
        region=geometry,
        scale=scale_m,
        projection="EPSG:4326",
        geometries=True,
    )

    features = sample.getInfo().get("features", [])
    if not features:
        logger.warning("No sample pixels returned for %s.", collection_id)
        return None

    rows = []
    for feat in features:
        coords = feat.get("geometry", {}).get("coordinates", [None, None])
        props = feat.get("properties", {})
        val = props.get(band_name)
        rows.append({
            "timestamp": start,
            "latitude": coords[1],
            "longitude": coords[0],
            band_name: val,
        })

    df = pd.DataFrame(rows)
    return df


# ---------------------------------------------------------------------------
# Main collection function
# ---------------------------------------------------------------------------


def collect_satellite_data(
    date_str: Optional[str] = None,
    output_path: Optional[Path] = None,
    temporal_window_days: int = TEMPORAL_WINDOW_DAYS,
) -> bool:
    """Collect Sentinel-5P TROPOMI and MODIS AOD data for the specified date.

    Parameters
    ----------
    date_str:
        Target date in ``"YYYY-MM-DD"`` format.  Defaults to today's date.
    output_path:
        Destination CSV path.  Defaults to
        ``config.PROCESSED_DATA_DIR / "satellite_predictors.csv"``.
    temporal_window_days:
        Temporal averaging window (±days around ``date_str``).

    Returns
    -------
    bool
        ``True`` on success, ``False`` on any unrecoverable error.

    Side effects
    ------------
    On success, writes ``processed_data/satellite_predictors.csv``.  The next
    feature-engineering run will automatically consume this file instead of
    the placeholder grid.
    """
    date_str = date_str or datetime.date.today().strftime("%Y-%m-%d")
    output_path = output_path or (config.PROCESSED_DATA_DIR / _DEFAULT_OUTPUT_FILENAME)

    logger.info(
        "Satellite data collection starting (date=%s, window=±%d day(s)).",
        date_str,
        temporal_window_days,
    )

    # ------------------------------------------------------------------
    # Step 1: Import and authenticate GEE
    # ------------------------------------------------------------------
    try:
        ee = _try_import_ee()
    except ImportError as exc:
        logger.error("%s", exc)
        return False

    if not _gee_credentials_available():
        logger.error(
            "No GEE credentials detected.  "
            "Run 'earthengine authenticate' or configure service-account "
            "environment variables (GEE_SERVICE_ACCOUNT + key).  "
            "Satellite data collection aborted."
        )
        return False

    try:
        _authenticate_gee(ee)
    except (MissingGeeCredentialsError, GeeAuthenticationError) as exc:
        logger.error("%s", exc)
        return False

    # ------------------------------------------------------------------
    # Step 2: Build temporal range and geometry
    # ------------------------------------------------------------------
    start_date, end_date = _date_range(date_str, temporal_window_days)
    geometry = _build_india_geometry(ee)

    logger.info(
        "Fetching satellite data for %s–%s over India [%.1f–%.1f°N, %.1f–%.1f°E].",
        start_date, end_date,
        INDIA_BBOX[1], INDIA_BBOX[3],
        INDIA_BBOX[0], INDIA_BBOX[2],
    )

    # ------------------------------------------------------------------
    # Step 3: Fetch each Sentinel-5P band
    # ------------------------------------------------------------------
    product_frames: List[pd.DataFrame] = []
    all_failed = True

    for feature_name, collection_id in S5P_COLLECTIONS.items():
        band_name = S5P_BAND_MAP[feature_name]
        logger.info("  Fetching %-14s from %s ...", feature_name, collection_id)
        try:
            df_band = _extract_band_mean(
                ee, collection_id, band_name, start_date, end_date, geometry
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("  Failed to fetch %s: %s", feature_name, exc)
            continue

        if df_band is not None and not df_band.empty:
            df_band = df_band.rename(columns={band_name: feature_name})
            product_frames.append(df_band)
            all_failed = False
            logger.info("  %-14s  rows=%d", feature_name, len(df_band))
        else:
            logger.warning("  %-14s  no data returned.", feature_name)

    # ------------------------------------------------------------------
    # Step 4: Fetch MODIS AOD
    # ------------------------------------------------------------------
    logger.info("  Fetching %-14s from %s ...", "AOD", AOD_COLLECTION)
    try:
        df_aod = _extract_band_mean(
            ee, AOD_COLLECTION, AOD_BAND, start_date, end_date, geometry
        )
        if df_aod is not None and not df_aod.empty:
            df_aod = df_aod.rename(columns={AOD_BAND: "AOD"})
            product_frames.append(df_aod)
            all_failed = False
            logger.info("  %-14s  rows=%d", "AOD", len(df_aod))
        else:
            logger.warning("  %-14s  no data returned.", "AOD")
    except Exception as exc:  # noqa: BLE001
        logger.error("  Failed to fetch AOD: %s", exc)

    if all_failed:
        logger.error(
            "All satellite product retrievals failed.  "
            "Check GEE credentials, network access, and GEE quotas."
        )
        return False

    # ------------------------------------------------------------------
    # Step 5: Merge all products on (timestamp, latitude, longitude)
    # ------------------------------------------------------------------
    if not product_frames:
        logger.error("No satellite product DataFrames to merge.")
        return False

    # Round coordinates to GRID_RESOLUTION_DEG for consistent join keys.
    def _round_coords(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df["latitude"] = df["latitude"].round(int(-round(
            __import__("math").log10(GRID_RESOLUTION_DEG)
        )))
        df["longitude"] = df["longitude"].round(int(-round(
            __import__("math").log10(GRID_RESOLUTION_DEG)
        )))
        return df

    merged = _round_coords(product_frames[0])
    for df_prod in product_frames[1:]:
        df_prod = _round_coords(df_prod)
        merged = merged.merge(
            df_prod,
            on=["timestamp", "latitude", "longitude"],
            how="outer",
        )

    # Ensure all expected output columns exist (fill absent ones with NaN).
    for col in OUTPUT_COLUMNS:
        if col not in merged.columns:
            merged[col] = float("nan")

    # ------------------------------------------------------------------
    # Step 6: Write output CSV
    # ------------------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_cols = [c for c in OUTPUT_COLUMNS if c in merged.columns]
    extra_cols = [c for c in merged.columns if c not in OUTPUT_COLUMNS]
    merged[final_cols + extra_cols].to_csv(output_path, index=False)

    null_summary = {
        col: f"{merged[col].isna().mean() * 100:.1f}%"
        for col in OUTPUT_COLUMNS[3:]  # skip timestamp/lat/lon
        if col in merged.columns
    }
    logger.info(
        "Satellite predictors CSV written to %s (%d rows).  Null rates: %s",
        output_path,
        len(merged),
        null_summary,
    )
    return True


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sentinel5p_collector",
        description=(
            "Collect Sentinel-5P TROPOMI and MODIS AOD satellite data for "
            "the AKASH feature-engineering pipeline."
        ),
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="Target date for data collection.  Defaults to today.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            f"Output CSV path.  Default: processed_data/{_DEFAULT_OUTPUT_FILENAME}"
        ),
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=TEMPORAL_WINDOW_DAYS,
        metavar="N",
        help=(
            "Temporal averaging window: ±N days around the target date.  "
            f"Default: {TEMPORAL_WINDOW_DAYS}."
        ),
    )
    return parser


if __name__ == "__main__":
    from data_collection_pipeline import utils

    utils.setup_logging()
    args = _build_cli_parser().parse_args()
    success = collect_satellite_data(
        date_str=args.date,
        output_path=args.output,
        temporal_window_days=args.window_days,
    )
    sys.exit(0 if success else 1)
