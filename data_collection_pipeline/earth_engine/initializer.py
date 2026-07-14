"""
Earth Engine Initialization Module.

Handles GEE authentication and initialization, supporting both interactive
user credentials and non-interactive service accounts.

The project ID is always sourced from the ``GEE_PROJECT_ID`` environment
variable via :mod:`data_collection_pipeline.earth_engine.config`. This is
the single source of truth — no project ID is ever hardcoded here.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global flag to track if Earth Engine was successfully initialized
_EE_INITIALIZED = False


def is_ee_initialized() -> bool:
    """Returns True if Earth Engine has been successfully initialized in this process."""
    return _EE_INITIALIZED


def initialize_ee(
    sa_key_path: Optional[str] = None,
    project: Optional[str] = None
) -> bool:
    """
    Initializes Google Earth Engine Python API.

    Tries to authenticate using the provided service account key or falls back
    to standard user credentials stored locally.

    The *project* parameter defaults to ``GEE_PROJECT_ID`` from the config
    module when not explicitly provided. Passing ``project=None`` without the
    env var set will raise an ``EnvironmentError`` at config import time, so
    callers always get a fast, actionable failure.

    Args:
        sa_key_path: Path to the service account private key JSON file (optional).
            Falls back to ``EE_SA_KEY_PATH`` from config when not provided.
        project: Google Cloud Project ID to use for Earth Engine requests.
            Defaults to ``GEE_PROJECT_ID`` from
            :mod:`data_collection_pipeline.earth_engine.config`.

    Returns:
        True if initialization succeeded, False otherwise.

    Raises:
        EnvironmentError: If ``GEE_PROJECT_ID`` is not set (raised by the
            config module at import time).
    """
    global _EE_INITIALIZED

    try:
        import ee
    except ImportError:
        logger.error(
            "Earth Engine Python API ('earthengine-api') is not installed. "
            "Please run 'pip install earthengine-api' to use this module."
        )
        return False

    if _EE_INITIALIZED:
        logger.debug("Earth Engine already initialized.")
        return True

    # Resolve configuration — import triggers EnvironmentError if GEE_PROJECT_ID unset
    from data_collection_pipeline import config

    resolved_project = project or config.GEE_PROJECT_ID
    resolved_sa_key = sa_key_path or config.EE_SA_KEY_PATH or None

    try:
        if resolved_sa_key:
            logger.info(
                "Attempting GEE initialization via service account key: %s",
                resolved_sa_key,
            )
            try:
                ee.Initialize(
                    credentials=ee.ServiceAccountCredentials(None, resolved_sa_key),
                    project=resolved_project,
                )
                logger.info(
                    "Earth Engine initialized successfully using Service Account "
                    "(project=%s).",
                    resolved_project,
                )
                _EE_INITIALIZED = True
                return True
            except Exception as e:
                logger.warning(
                    "Failed service account credentials setup: %s. "
                    "Falling back to default Initialize.",
                    e,
                )

        # Fallback/Default Initialize — always pass the project
        logger.info(
            "Attempting standard GEE initialization using local user credentials "
            "(project=%s)…",
            resolved_project,
        )
        ee.Initialize(project=resolved_project)
        logger.info(
            "Earth Engine initialized successfully (project=%s).",
            resolved_project,
        )
        _EE_INITIALIZED = True
        return True

    except Exception as e:
        logger.error(
            "Failed to initialize Earth Engine (project=%s): %s\n"
            "Ensure you have:\n"
            "  1. Run 'earthengine authenticate' in your shell, or\n"
            "  2. Configured GEE_SERVICE_ACCOUNT / GEE_SERVICE_ACCOUNT_KEY_FILE, and\n"
            "  3. Set GEE_PROJECT_ID to a project that has Earth Engine enabled.",
            resolved_project,
            e,
        )
        _EE_INITIALIZED = False
        return False
