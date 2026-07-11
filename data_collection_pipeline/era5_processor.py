"""ERA5 NetCDF → tabular CSV processor for the AKASH pipeline.

Responsibilities
----------------
* Read the ERA5 NetCDF file produced by ``era5_downloader.prepare_era5_download``.
* Flatten the 3-D grid (time × lat × lon) to a tidy long-format DataFrame.
* Rename variable short-names to the canonical column names expected by
  ``feature_engineering/merger.py`` (``ERA5_RENAME_MAP``).
* Derive ``Wind Speed`` and ``Wind Direction`` from U/V wind components.
* Write the result to ``processed_data/era5_meteorology.csv``.

Once this file exists, ``merger.load_era5_grid()`` will automatically pick it
up on the next feature-engineering run — no downstream changes required.

Usage (CLI)
-----------
::

    python -m data_collection_pipeline.era5_processor          # auto-detect paths
    python -m data_collection_pipeline.era5_processor \\
        --nc-file raw_data/era5_meteorological_india.nc \\
        --output  processed_data/era5_meteorology.csv

Usage (API)
-----------
::

    from data_collection_pipeline.era5_processor import process_era5_netcdf
    ok = process_era5_netcdf()          # uses config paths by default

Dependencies
------------
The ``netCDF4`` or ``xarray`` + ``scipy`` packages are required.  Both are
optional at import time; a clear ``ImportError`` is raised at call time if
neither is available.
"""

from __future__ import annotations

import argparse
import logging
import math
from pathlib import Path
from typing import Optional

import pandas as pd

from data_collection_pipeline import config

logger = logging.getLogger("data_collection_pipeline.era5_processor")

# ---------------------------------------------------------------------------
# Constants — kept in sync with feature_engineering/merger.py ERA5_RENAME_MAP
# ---------------------------------------------------------------------------

#: NetCDF variable short-name → canonical output column name
VARIABLE_RENAME_MAP: dict[str, str] = {
    "t2m": "Temperature",
    "2m_temperature": "Temperature",
    "r": "Relative Humidity",
    "relative_humidity": "Relative Humidity",
    "blh": "Boundary Layer Height",
    "boundary_layer_height": "Boundary Layer Height",
    "sp": "Surface Pressure",
    "surface_pressure": "Surface Pressure",
    "u10": "u_wind_component",
    "10m_u_component_of_wind": "u_wind_component",
    "v10": "v_wind_component",
    "10m_v_component_of_wind": "v_wind_component",
}

#: Columns written to the output CSV (order matters for merger compatibility)
OUTPUT_COLUMNS: list[str] = [
    "timestamp",
    "latitude",
    "longitude",
    "Temperature",
    "Relative Humidity",
    "Boundary Layer Height",
    "Surface Pressure",
    "u_wind_component",
    "v_wind_component",
    "Wind Speed",
    "Wind Direction",
]

_DEFAULT_NC_FILENAME: str = "era5_meteorological_india.nc"
_DEFAULT_CSV_FILENAME: str = "era5_meteorology.csv"


# ---------------------------------------------------------------------------
# NetCDF → DataFrame conversion
# ---------------------------------------------------------------------------


def _try_import_xarray() -> object:
    """Import xarray, raising ImportError with a helpful message if absent."""
    try:
        import xarray as xr  # noqa: PLC0415
        return xr
    except ImportError as exc:
        raise ImportError(
            "The 'xarray' package is required to process ERA5 NetCDF files.\n"
            "Install it with: pip install xarray netcdf4 scipy"
        ) from exc


def _netcdf_to_dataframe(nc_path: Path) -> pd.DataFrame:
    """Load an ERA5 NetCDF file and return a tidy long-format DataFrame.

    Parameters
    ----------
    nc_path:
        Absolute path to the ERA5 ``.nc`` file.

    Returns
    -------
    pd.DataFrame
        Columns: ``timestamp``, ``latitude``, ``longitude``, plus one column
        per variable renamed via :data:`VARIABLE_RENAME_MAP`.

    Raises
    ------
    FileNotFoundError
        If the NetCDF file does not exist at ``nc_path``.
    ImportError
        If ``xarray`` is not installed.
    ValueError
        If the file cannot be parsed as a valid ERA5 dataset.
    """
    if not nc_path.exists():
        raise FileNotFoundError(
            f"ERA5 NetCDF file not found: {nc_path}.\n"
            "Run era5_downloader.prepare_era5_download(dry_run=False) first."
        )

    xr = _try_import_xarray()
    logger.info("Loading ERA5 NetCDF from %s ...", nc_path)

    try:
        ds = xr.open_dataset(nc_path)  # type: ignore[attr-defined]
    except Exception as exc:  # noqa: BLE001
        raise ValueError(f"Cannot open ERA5 NetCDF file: {exc}") from exc

    logger.info(
        "Opened NetCDF with %d variable(s): %s",
        len(ds.data_vars),
        list(ds.data_vars),
    )

    # Rename variables to canonical names where known.
    rename_map = {
        var: VARIABLE_RENAME_MAP[var]
        for var in ds.data_vars
        if var in VARIABLE_RENAME_MAP
    }
    if rename_map:
        ds = ds.rename(rename_map)
        logger.info("Renamed NetCDF variables: %s", rename_map)

    # Convert to a tidy pandas DataFrame (time × lat × lon → rows).
    df = ds.to_dataframe().reset_index()
    ds.close()

    # Normalise dimension column names (xarray may use 'time'/'latitude'/'longitude'
    # or 'valid_time'/'lat'/'lon' depending on the ERA5 format version).
    dim_rename: dict[str, str] = {}
    for col in df.columns:
        col_lower = col.lower()
        if col_lower in {"time", "valid_time"}:
            dim_rename[col] = "timestamp"
        elif col_lower in {"lat", "latitude"}:
            dim_rename[col] = "latitude"
        elif col_lower in {"lon", "lng", "longitude"}:
            dim_rename[col] = "longitude"
    if dim_rename:
        df = df.rename(columns=dim_rename)
        logger.debug("Renamed dimension columns: %s", dim_rename)

    return df


# ---------------------------------------------------------------------------
# Wind speed / direction derivation
# ---------------------------------------------------------------------------


def _derive_wind_features(df: pd.DataFrame) -> pd.DataFrame:
    """Add ``Wind Speed`` and ``Wind Direction`` columns from U/V components.

    Parameters
    ----------
    df:
        DataFrame that may contain ``u_wind_component`` and ``v_wind_component``.

    Returns
    -------
    pd.DataFrame
        Input DataFrame with wind columns added (or NaN-filled if components
        are unavailable).
    """
    out = df.copy()

    if "u_wind_component" in out.columns and "v_wind_component" in out.columns:
        u = pd.to_numeric(out["u_wind_component"], errors="coerce")
        v = pd.to_numeric(out["v_wind_component"], errors="coerce")

        # Speed: magnitude of horizontal wind vector
        out["Wind Speed"] = (u**2 + v**2) ** 0.5

        # Direction: meteorological convention (degrees from north, clockwise)
        out["Wind Direction"] = (
            u.combine(v, lambda ui, vi: (
                (math.degrees(math.atan2(float(ui), float(vi))) + 360.0) % 360.0
                if (pd.notna(ui) and pd.notna(vi))
                else float("nan")
            ))
        )
        logger.info(
            "Derived Wind Speed and Wind Direction from U/V components "
            "(non-null rows: %d).",
            out["Wind Speed"].notna().sum(),
        )
    else:
        out["Wind Speed"] = float("nan")
        out["Wind Direction"] = float("nan")
        logger.warning(
            "u_wind_component and/or v_wind_component not found in NetCDF. "
            "Wind Speed and Wind Direction will be null."
        )

    return out


# ---------------------------------------------------------------------------
# Output writer
# ---------------------------------------------------------------------------


def _write_csv(df: pd.DataFrame, csv_path: Path) -> None:
    """Write the processed ERA5 DataFrame to CSV.

    Parameters
    ----------
    df:
        Tidy ERA5 DataFrame with canonical column names.
    csv_path:
        Absolute path for the output CSV.
    """
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    # Write only columns that actually exist in the DataFrame; preserve order.
    present_cols = [c for c in OUTPUT_COLUMNS if c in df.columns]
    extra_cols = [c for c in df.columns if c not in OUTPUT_COLUMNS]
    final_cols = present_cols + extra_cols

    df[final_cols].to_csv(csv_path, index=False)
    logger.info(
        "ERA5 meteorology CSV written to %s (%d rows, %d columns).",
        csv_path,
        len(df),
        len(final_cols),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def process_era5_netcdf(
    nc_path: Optional[Path] = None,
    output_path: Optional[Path] = None,
) -> bool:
    """Convert an ERA5 NetCDF file to a tabular CSV for feature engineering.

    Parameters
    ----------
    nc_path:
        Path to the ERA5 NetCDF file.  Defaults to
        ``config.RAW_DATA_DIR / "era5_meteorological_india.nc"``.
    output_path:
        Destination CSV path.  Defaults to
        ``config.PROCESSED_DATA_DIR / "era5_meteorology.csv"``.

    Returns
    -------
    bool
        ``True`` on success, ``False`` on any unrecoverable error.

    Side effects
    ------------
    On success, writes ``processed_data/era5_meteorology.csv``.  The next run
    of ``feature_engineering/merger.py`` will automatically consume this file
    instead of the placeholder grid.
    """
    nc_path = nc_path or (config.RAW_DATA_DIR / _DEFAULT_NC_FILENAME)
    output_path = output_path or (config.PROCESSED_DATA_DIR / _DEFAULT_CSV_FILENAME)

    logger.info(
        "ERA5 processor starting: %s → %s",
        nc_path,
        output_path,
    )

    try:
        df = _netcdf_to_dataframe(nc_path)
    except FileNotFoundError as exc:
        logger.error("%s", exc)
        return False
    except (ImportError, ValueError) as exc:
        logger.error("ERA5 NetCDF loading failed: %s", exc)
        return False

    df = _derive_wind_features(df)

    # Sanity check: log null rates for key columns before writing.
    key_cols = [
        "Temperature", "Relative Humidity", "Boundary Layer Height", "Surface Pressure",
    ]
    for col in key_cols:
        if col in df.columns:
            null_pct = df[col].isna().mean() * 100
            logger.info("  %-28s  null=%.1f%%", col, null_pct)

    try:
        _write_csv(df, output_path)
    except OSError as exc:
        logger.error("Failed to write ERA5 CSV: %s", exc)
        return False

    logger.info(
        "ERA5 processing complete.  "
        "Feature engineering will now use real meteorological data "
        "from %s.",
        output_path,
    )
    return True


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="era5_processor",
        description=(
            "Convert a downloaded ERA5 NetCDF file to the tabular CSV consumed "
            "by the AKASH feature-engineering merger."
        ),
    )
    parser.add_argument(
        "--nc-file",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Path to the ERA5 .nc file.  "
            f"Default: raw_data/{_DEFAULT_NC_FILENAME}"
        ),
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "Destination CSV path.  "
            f"Default: processed_data/{_DEFAULT_CSV_FILENAME}"
        ),
    )
    return parser


if __name__ == "__main__":
    import sys
    from data_collection_pipeline import utils

    utils.setup_logging()
    args = _build_cli_parser().parse_args()
    success = process_era5_netcdf(nc_path=args.nc_file, output_path=args.output)
    sys.exit(0 if success else 1)
