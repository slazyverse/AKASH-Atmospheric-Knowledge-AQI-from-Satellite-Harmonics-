"""Custom exceptions for AKASH data collection pipeline."""

from typing import Optional, Dict, Any


class IngestionError(Exception):
    """Raised when data ingestion fails in production pipelines.

    Attributes:
        source (str): Name of data collector source (e.g. 'CPCB', 'ERA5', 'Sentinel-5P').
        operation (str): Ingestion operation that failed (e.g. 'fetch_cpcb_raw', 'download_historical_month').
        message (str): Human-readable error description.
        original_exception (Optional[Exception]): Original cause exception if any.
        payload (Dict[str, Any]): Relevant execution context payload.
    """

    def __init__(
        self,
        source: str,
        operation: str,
        message: str,
        original_exception: Optional[Exception] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> None:
        formatted_msg = f"[{source}::{operation}] {message}"
        super().__init__(formatted_msg)
        self.source = source
        self.operation = operation
        self.message = message
        self.original_exception = original_exception
        self.payload = payload or {}
