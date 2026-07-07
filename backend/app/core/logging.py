"""
Structured logging configuration using structlog.

Design decisions:
  - structlog is preferred over stdlib logging directly because it natively
    supports structured key-value context, context variables (per-request
    request_id binding), and pluggable renderers for JSON vs. console output.
  - Shared processor chain: both structlog-native loggers and stdlib loggers
    (used by SQLAlchemy, uvicorn, alembic) pass through the same processors,
    ensuring every log line has the same schema regardless of its source.
  - _add_service_name: injects the APP_NAME into every record so log
    aggregators can filter by service without any additional configuration.
  - _drop_color_message_key: uvicorn injects a 'color_message' key that
    duplicates 'event' in JSON output. We strip it to keep logs clean.
  - In development (LOG_FORMAT=console): colourised, human-readable output.
  - In production (LOG_FORMAT=json): newline-delimited JSON for Datadog,
    Loki, Grafana, CloudWatch, and similar aggregators.
  - configure_logging() must be called before any logger is instantiated.
    main.py calls it as the very first action after importing settings.
"""

from __future__ import annotations

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor


def _add_service_name(
    logger: Any,
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """Inject the service name into every log record."""
    from app.core.config import get_settings

    event_dict["service"] = get_settings().APP_NAME.lower().replace(" ", "-")
    return event_dict


def _drop_color_message_key(
    logger: Any,
    method: str,
    event_dict: EventDict,
) -> EventDict:
    """
    Remove the 'color_message' key injected by uvicorn.

    uvicorn adds this key for its own terminal output. In JSON log lines it
    produces a duplicate of 'event', which inflates log volume and confuses
    parsers. We strip it here so all renderers see a clean event dict.
    """
    event_dict.pop("color_message", None)
    return event_dict


def configure_logging(log_level: str = "INFO", log_format: str = "json") -> None:
    """
    Install the structlog processor chain and configure stdlib logging.

    Call this function exactly once, before any logging takes place —
    typically as the first statement in main.py after importing Settings.

    Args:
        log_level:  One of DEBUG, INFO, WARNING, ERROR, CRITICAL.
        log_format: "json" for structured output; "console" for human-readable.
    """
    shared_processors: list[Processor] = [
        # Merge any context variables bound with structlog.contextvars.bind_contextvars()
        # (e.g., request_id injected by the request ID middleware).
        structlog.contextvars.merge_contextvars,
        # Standard enrichment processors
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.ExtraAdder(),
        # Custom enrichment
        _add_service_name,
        _drop_color_message_key,
        # ISO 8601 UTC timestamp on every record
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        # Render the 'stack_info' key when present
        structlog.processors.StackInfoRenderer(),
    ]

    # Choose the final renderer based on deployment context
    renderer: Processor
    if log_format == "console":
        renderer = structlog.dev.ConsoleRenderer(colors=True, exception_formatter=structlog.dev.plain_traceback)
    else:
        renderer = structlog.processors.JSONRenderer()

    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        # Pre-chain: applied to records from stdlib loggers (uvicorn, sqlalchemy)
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(log_level.upper())

    # ── Unify uvicorn logging with the application pipeline ───────────────────
    # Uvicorn configures its own StreamHandler on uvicorn, uvicorn.error, and
    # uvicorn.access loggers before importing the application module. If left
    # in place, uvicorn log records are formatted by uvicorn's own formatter
    # (plain text, with ANSI colours) rather than our structlog pipeline, causing
    # two different log formats in the same output stream.
    #
    # Fix: clear uvicorn's own handlers and set propagate=True. Records then
    # flow to the root logger, which uses our single structlog handler. All log
    # lines — application and server — now share one structured JSON pipeline.
    for uvicorn_logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uvicorn_logger = logging.getLogger(uvicorn_logger_name)
        uvicorn_logger.handlers = []   # Remove uvicorn's own StreamHandler
        uvicorn_logger.propagate = True  # Propagate to root (structlog handler)

    # ── Suppress chatty third-party loggers ───────────────────────────────────
    # SQLAlchemy engine logs every SQL statement at INFO; this is too verbose
    # in production but useful during development (LOG_LEVEL=DEBUG).
    third_party_log_level = logging.DEBUG if log_level.upper() == "DEBUG" else logging.WARNING
    for logger_name in ("uvicorn.access", "sqlalchemy.engine", "alembic"):
        logging.getLogger(logger_name).setLevel(third_party_log_level)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Return a bound structlog logger for the given module name.

    Usage:
        logger = get_logger(__name__)
        logger.info("Sensor registered", sensor_id=42, location="Delhi")

    Args:
        name: Typically __name__ of the calling module.
    """
    return structlog.get_logger(name)
