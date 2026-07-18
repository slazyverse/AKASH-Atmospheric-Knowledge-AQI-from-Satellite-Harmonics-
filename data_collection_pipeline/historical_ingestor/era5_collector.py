"""Historical ERA5 meteorological data collector.

``HistoricalERA5Collector`` iterates over the historical date range one
calendar month at a time, calling the modified
``era5_downloader.prepare_era5_download`` (Phase 1 S2-06) with a
``start_date`` override for each month, then running
``era5_processor.process_era5_netcdf`` to convert the downloaded NetCDF to a
tabular CSV.

Monthly CSVs are concatenated and written to
``processed_data/era5_meteorology_hist.csv``.

**Resume logic**: months whose NetCDF files already exist on disk are skipped
so that a long multi-year collection can be interrupted and restarted safely.
"""

from __future__ import annotations

import calendar
import datetime
import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd

from data_collection_pipeline import era5_downloader, era5_processor, config
from data_collection_pipeline.historical_ingestor import config as hist_config

logger = logging.getLogger(
    "data_collection_pipeline.historical_ingestor.era5_collector"
)


class HistoricalERA5Collector:
    """Collects ERA5 meteorological data over a historical date range.

    Parameters
    ----------
    chunk_months:
        Number of calendar months per CDS API batch.  Defaults to
        ``hist_config.HIST_ERA5_CHUNK_MONTHS`` (env: ``HIST_ERA5_CHUNK_MONTHS``).
    output_path:
        Where to write the final concatenated ERA5 CSV.
        Defaults to ``hist_config.HIST_ERA5_CSV``.
    nc_output_dir:
        Directory where monthly NetCDF files are cached.  Defaults to
        ``config.RAW_DATA_DIR / "historical" / "era5"``.
    """

    def __init__(
        self,
        chunk_months: Optional[int] = None,
        output_path: Optional[Path] = None,
        nc_output_dir: Optional[Path] = None,
    ) -> None:
        self.chunk_months = chunk_months or hist_config.HIST_ERA5_CHUNK_MONTHS
        self.output_path = Path(output_path or hist_config.HIST_ERA5_CSV)
        self.nc_output_dir = Path(
            nc_output_dir or config.RAW_DATA_DIR / "historical" / "era5"
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def collect(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Collect ERA5 data for the full date range with monthly chunking.

        Parameters
        ----------
        start_date, end_date:
            ISO-8601 date strings (``YYYY-MM-DD``) for the inclusive range.

        Returns
        -------
        pd.DataFrame
            Concatenated ERA5 meteorology DataFrame covering the full range.
        """
        start = datetime.date.fromisoformat(start_date)
        end = datetime.date.fromisoformat(end_date)

        if start > end:
            raise ValueError(
                f"start_date ({start_date}) must not be after end_date ({end_date})."
            )

        self.nc_output_dir.mkdir(parents=True, exist_ok=True)
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        months = self._generate_month_list(start, end)
        logger.info(
            "Starting historical ERA5 collection: %s → %s (%d month(s)).",
            start_date, end_date, len(months),
        )

        collected_frames: List[pd.DataFrame] = []
        skipped = 0

        for year, month in months:
            nc_path = self.nc_output_dir / f"era5_{year}_{month:02d}.nc"
            csv_path = self.nc_output_dir / f"era5_{year}_{month:02d}.csv"

            if csv_path.exists():
                logger.info(
                    "Month %d-%02d already collected (%s) — loading from cache.",
                    year, month, csv_path.name,
                )
                try:
                    df = pd.read_csv(csv_path, low_memory=False)
                    collected_frames.append(df)
                    skipped += 1
                    continue
                except Exception as exc:  # noqa: BLE001
                    logger.warning(
                        "Failed to load cached CSV %s: %s — re-collecting.",
                        csv_path.name, exc,
                    )

            logger.info("Collecting ERA5 month: %d-%02d.", year, month)
            month_first = datetime.date(year, month, 1)
            month_last = datetime.date(year, month, calendar.monthrange(year, month)[1])

            success = era5_downloader.prepare_era5_download(
                start_date=month_first.isoformat(),
                end_date=month_last.isoformat(),
                output_filename=nc_path.name,
                dry_run=False,
            )

            if not success:
                logger.warning(
                    "ERA5 download for %d-%02d failed — skipping month.", year, month
                )
                continue

            # Move the downloaded NC from raw_data/ to our historical cache dir.
            raw_nc = config.RAW_DATA_DIR / nc_path.name
            if raw_nc.exists() and raw_nc != nc_path:
                raw_nc.rename(nc_path)

            # Convert the NetCDF to CSV using the existing processor.
            csv_written = era5_processor.process_era5_netcdf(
                input_path=nc_path,
                output_path=csv_path,
            )

            if csv_written and csv_path.exists():
                try:
                    df = pd.read_csv(csv_path, low_memory=False)
                    collected_frames.append(df)
                    logger.info(
                        "ERA5 month %d-%02d processed: %d rows.", year, month, len(df)
                    )
                except Exception as exc:  # noqa: BLE001
                    logger.error(
                        "Failed to read processed ERA5 CSV %s: %s", csv_path, exc
                    )
            else:
                logger.warning(
                    "ERA5 processing for %d-%02d did not produce a CSV.", year, month
                )

        logger.info(
            "ERA5 collection complete. Months: %d total, %d cached/skipped, %d newly collected.",
            len(months), skipped, len(months) - skipped,
        )

        if not collected_frames:
            logger.warning(
                "No ERA5 data was collected for %s → %s.", start_date, end_date
            )
            return pd.DataFrame()

        combined = pd.concat(collected_frames, ignore_index=True)
        
        # Save to CSV
        combined.to_csv(self.output_path, index=False)
        logger.info(
            "Historical ERA5 dataset written to %s (%d rows).",
            self.output_path, len(combined),
        )
        
        # Save to Parquet
        parquet_path = self.output_path.with_suffix('.parquet')
        try:
            combined.to_parquet(parquet_path, index=False)
            logger.info("Historical ERA5 dataset also written to %s", parquet_path)
        except Exception as e:
            logger.warning("Could not write Parquet file (is pyarrow installed?): %s", e)
            
        return combined

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _generate_month_list(
        start: datetime.date, end: datetime.date
    ) -> List[tuple]:
        """Return a sorted list of (year, month) tuples spanning start→end."""
        months = []
        current = datetime.date(start.year, start.month, 1)
        end_month = datetime.date(end.year, end.month, 1)
        while current <= end_month:
            months.append((current.year, current.month))
            # Advance to next month.
            if current.month == 12:
                current = datetime.date(current.year + 1, 1, 1)
            else:
                current = datetime.date(current.year, current.month + 1, 1)
        return months
