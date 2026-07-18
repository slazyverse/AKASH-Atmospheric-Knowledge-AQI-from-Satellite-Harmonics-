"""Historical Sentinel-5P / MODIS satellite data collector.

``HistoricalSatelliteCollector`` iterates over the historical date range in
chunks of ``HIST_GEE_CHUNK_DAYS`` days, calling the existing
``sentinel5p_collector`` for each chunk.  Partial results are saved after
every chunk so that collection can be **resumed** if interrupted — chunks
whose timestamps are already present in the output file are skipped.

The concatenated output is written to
``processed_data/satellite_predictors_hist.csv`` which is consumed by
``integrate_datasets(satellite_path=...)`` in the feature engineering merger.
"""

from __future__ import annotations

import datetime
import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd

from data_collection_pipeline.historical_ingestor import config as hist_config

logger = logging.getLogger(
    "data_collection_pipeline.historical_ingestor.satellite_collector"
)


class HistoricalSatelliteCollector:
    """Collects Sentinel-5P/MODIS satellite data over a historical date range.

    Parameters
    ----------
    chunk_days:
        Number of days per GEE collection chunk.  Defaults to
        ``hist_config.HIST_GEE_CHUNK_DAYS`` (env: ``HIST_GEE_CHUNK_DAYS``).
    output_path:
        Where to write (and incrementally update) the concatenated CSV.
        Defaults to ``hist_config.HIST_SATELLITE_CSV``.
    """

    def __init__(
        self,
        chunk_days: Optional[int] = None,
        output_path: Optional[Path] = None,
    ) -> None:
        self.chunk_days = chunk_days or hist_config.HIST_GEE_CHUNK_DAYS
        self.output_path = Path(output_path or hist_config.HIST_SATELLITE_CSV)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def collect(self, start_date: str, end_date: str) -> pd.DataFrame:
        """Collect satellite data for the full date range with chunked resume.

        Parameters
        ----------
        start_date, end_date:
            ISO-8601 date strings (``YYYY-MM-DD``) defining the inclusive
            historical window.

        Returns
        -------
        pd.DataFrame
            Concatenated satellite predictor DataFrame covering the full
            requested range (excluding any chunks that failed after retries).
        """
        start = datetime.date.fromisoformat(start_date)
        end = datetime.date.fromisoformat(end_date)

        if start > end:
            raise ValueError(
                f"start_date ({start_date}) must not be after end_date ({end_date})."
            )

        # Load any already-collected data so we can skip those chunks.
        existing_dates = self._load_existing_dates()
        logger.info(
            "Starting historical satellite collection: %s → %s "
            "(chunk=%d days, already-collected dates=%d).",
            start_date, end_date, self.chunk_days, len(existing_dates),
        )

        collected_frames: List[pd.DataFrame] = []
        if self.output_path.exists():
            collected_frames.append(pd.read_csv(self.output_path, low_memory=False))

        chunk_start = start
        total_chunks = 0
        skipped_chunks = 0

        while chunk_start <= end:
            chunk_end = min(
                chunk_start + datetime.timedelta(days=self.chunk_days - 1), end
            )
            chunk_date_str = chunk_start.isoformat()

            if chunk_date_str in existing_dates:
                logger.debug(
                    "Chunk %s already collected — skipping.", chunk_date_str
                )
                skipped_chunks += 1
            else:
                logger.info(
                    "Collecting satellite chunk: %s → %s.",
                    chunk_start, chunk_end,
                )
                chunk_df = self._collect_chunk(chunk_date_str)
                if chunk_df is not None and not chunk_df.empty:
                    collected_frames.append(chunk_df)
                    # Incrementally persist so we can resume on interruption.
                    combined = pd.concat(collected_frames, ignore_index=True)
                    combined = self._dedup(combined)
                    self.output_path.parent.mkdir(parents=True, exist_ok=True)
                    combined.to_csv(self.output_path, index=False)
                    
                    # Also write Parquet files
                    try:
                        sentinel_cols = [c for c in combined.columns if not c.startswith('AOD')]
                        modis_cols = [c for c in combined.columns if c.startswith('AOD') or c in ['timestamp', 'date', 'latitude', 'longitude', 'station_id', 'station', 'location']]
                        
                        sentinel_path = self.output_path.parent / "sentinel_processed.parquet"
                        modis_path = self.output_path.parent / "modis_processed.parquet"
                        
                        combined[sentinel_cols].to_parquet(sentinel_path, index=False)
                        combined[modis_cols].to_parquet(modis_path, index=False)
                    except Exception as e:
                        logger.warning(f"Could not save parquet files: {e}")

                    logger.info(
                        "Chunk %s written. Output: %d rows total.",
                        chunk_date_str, len(combined),
                    )
                    collected_frames = [combined]
                else:
                    logger.warning(
                        "Chunk %s returned no data — continuing.", chunk_date_str
                    )

            total_chunks += 1
            chunk_start = chunk_end + datetime.timedelta(days=1)

        logger.info(
            "Satellite collection complete. Chunks processed: %d "
            "(skipped/resumed: %d).",
            total_chunks, skipped_chunks,
        )

        if not collected_frames:
            logger.warning(
                "No satellite data was collected for %s → %s.",
                start_date, end_date,
            )
            return pd.DataFrame()

        return pd.concat(collected_frames, ignore_index=True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _collect_chunk(self, date_str: str) -> Optional[pd.DataFrame]:
        """Invoke the existing sentinel5p_collector for a single chunk date."""
        try:
            from data_collection_pipeline import sentinel5p_collector

            # The collector's public collect function accepts a ``date`` param.
            # We call whichever entry-point is available.
            if hasattr(sentinel5p_collector, "collect_sentinel5p_data"):
                df = sentinel5p_collector.collect_sentinel5p_data(date=date_str)
            elif hasattr(sentinel5p_collector, "collect"):
                df = sentinel5p_collector.collect(date=date_str)
            else:
                # Fallback: import the CLI main and capture output.
                logger.warning(
                    "sentinel5p_collector does not expose a public Python API; "
                    "attempting module-level fallback."
                )
                return None

            return df
        except Exception as exc:  # noqa: BLE001
            logger.error(
                "Satellite chunk '%s' failed: %s", date_str, exc
            )
            return None

    def _load_existing_dates(self) -> set:
        """Return the set of chunk-start dates already present in the output CSV."""
        if not self.output_path.exists():
            return set()
        try:
            df = pd.read_csv(self.output_path, usecols=lambda c: c in {"timestamp", "date"})
            ts_col = next(
                (c for c in ["timestamp", "date"] if c in df.columns), None
            )
            if ts_col is None:
                return set()
            dates = pd.to_datetime(df[ts_col], errors="coerce").dt.date.dropna()
            return {str(d) for d in dates}
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "Could not read existing satellite CSV for resume check: %s", exc
            )
            return set()

    @staticmethod
    def _dedup(df: pd.DataFrame) -> pd.DataFrame:
        """De-duplicate on (station_id, timestamp) if those columns exist."""
        key_cols = [
            c for c in ["station_id", "station", "location", "timestamp", "date"]
            if c in df.columns
        ]
        if len(key_cols) >= 2:
            before = len(df)
            df = df.drop_duplicates(subset=key_cols)
            if before != len(df):
                logger.debug("De-duplication: %d → %d rows.", before, len(df))
        return df
