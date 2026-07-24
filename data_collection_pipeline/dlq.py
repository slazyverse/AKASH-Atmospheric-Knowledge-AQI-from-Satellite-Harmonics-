"""Dead Letter Queue (DLQ) infra and failure handling for AKASH pipeline."""

import datetime
import json
import logging
import math
from pathlib import Path
import uuid
from typing import Any, Dict, Optional

from data_collection_pipeline.exceptions import IngestionError

logger = logging.getLogger("data_collection_pipeline.dlq")

DLQ_DIR = Path("logs/dlq")


def _make_json_serializable(obj: Any) -> Any:
    """Recursively converts complex payloads to JSON-serializable structures.

    Converts datetimes, Paths, numpy scalars/arrays, pandas Timestamps/NA/NaT,
    sets, tuples, and bytes. Falls back to str() for any unhandled type.
    """
    if obj is None:
        return None

    # Handle pandas NA / NaT
    try:
        import pandas as pd
        if obj is pd.NA or obj is pd.NaT:
            return None
    except ImportError:
        pass

    # Handle datetime / Timestamp / date
    if isinstance(obj, (datetime.datetime, datetime.date)):
        return obj.isoformat()

    # Handle pathlib.Path
    if isinstance(obj, Path):
        return str(obj)

    # Handle bytes
    if isinstance(obj, bytes):
        try:
            return obj.decode("utf-8", errors="replace")
        except Exception:
            return str(obj)

    # Handle numpy types
    try:
        import numpy as np
        if isinstance(obj, (np.integer, np.bool_)):
            return obj.item()
        if isinstance(obj, np.floating):
            return str(obj) if (np.isnan(obj) or np.isinf(obj)) else obj.item()
        if isinstance(obj, np.ndarray):
            return [_make_json_serializable(x) for x in obj.tolist()]
    except ImportError:
        pass

    # Handle standard primitives
    if isinstance(obj, (int, str, bool)):
        return obj

    if isinstance(obj, float):
        if math.isnan(obj) or math.isinf(obj):
            return str(obj)
        return obj

    # Handle containers
    if isinstance(obj, dict):
        return {str(k): _make_json_serializable(v) for k, v in obj.items()}

    if isinstance(obj, (list, tuple, set)):
        return [_make_json_serializable(x) for x in obj]

    # Fallback to string representation
    return str(obj)


def write_dlq(
    source: str,
    operation: str,
    error_type: str,
    message: str,
    exception: str,
    payload: Optional[Dict[str, Any]] = None,
    dlq_dir: Optional[Path] = None,
) -> Path:
    """Writes a structured DLQ JSON record upon ingestion failure.

    Ensures atomic creation and unique filenames to prevent overwrite under concurrency.
    Applies _make_json_serializable to guarantee json.dump success.
    """
    target_dir = Path(dlq_dir) if dlq_dir is not None else DLQ_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    now_utc = datetime.datetime.now(datetime.timezone.utc)
    timestamp_iso = now_utc.isoformat()
    ts_slug = now_utc.strftime("%Y%m%dT%H%M%S_%f")
    unique_id = uuid.uuid4().hex[:8]

    record = {
        "timestamp": timestamp_iso,
        "source": source,
        "operation": operation,
        "error_type": error_type,
        "message": message,
        "exception": str(exception),
        "payload": _make_json_serializable(payload or {}),
    }

    safe_source = source.lower().replace("-", "_").replace(" ", "_")
    filename = f"dlq_{safe_source}_{ts_slug}_{unique_id}.json"
    dlq_path = target_dir / filename

    try:
        with open(dlq_path, "x", encoding="utf-8") as f:
            json.dump(record, f, indent=2)
    except FileExistsError:
        # Fallback with full UUID if collision occurs
        unique_id = uuid.uuid4().hex
        filename = f"dlq_{safe_source}_{ts_slug}_{unique_id}.json"
        dlq_path = target_dir / filename
        with open(dlq_path, "x", encoding="utf-8") as f:
            json.dump(record, f, indent=2)

    return dlq_path


def handle_ingestion_failure(
    source: str,
    operation: str,
    message: str,
    original_exception: Optional[Exception] = None,
    payload: Optional[Dict[str, Any]] = None,
    logger_instance: Optional[logging.Logger] = None,
    dlq_dir: Optional[Path] = None,
) -> None:
    """Standardized failure flow:

    1. Attempt DLQ JSON file write (failures logged, never swallow original error)
    2. Log ERROR
    3. Raise IngestionError from original_exception (preserving exception chain)
    """
    error_type = (
        type(original_exception).__name__
        if original_exception
        else "IngestionError"
    )
    exc_str = str(original_exception) if original_exception else message
    log = logger_instance or logger

    dlq_path = None
    try:
        dlq_path = write_dlq(
            source=source,
            operation=operation,
            error_type=error_type,
            message=message,
            exception=exc_str,
            payload=payload,
            dlq_dir=dlq_dir,
        )
        log.error(
            "Ingestion failure in %s (%s): %s | DLQ written to %s",
            source,
            operation,
            message,
            dlq_path,
            exc_info=original_exception,
        )
    except Exception as dlq_exc:
        log.error(
            "Ingestion failure in %s (%s): %s | Failed to write DLQ file: %s",
            source,
            operation,
            message,
            dlq_exc,
            exc_info=original_exception,
        )

    if original_exception:
        raise IngestionError(
            source=source,
            operation=operation,
            message=message,
            original_exception=original_exception,
            payload=payload,
        ) from original_exception
    else:
        raise IngestionError(
            source=source,
            operation=operation,
            message=message,
            original_exception=None,
            payload=payload,
        )
