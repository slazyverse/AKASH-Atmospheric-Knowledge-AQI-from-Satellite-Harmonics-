"""
Earth Engine Configuration Module.

Maintains settings, paths, bounding coordinates, and environment variables
for the Google Earth Engine data pipeline.

Required Environment Variables
-------------------------------
GEE_PROJECT_ID
    Google Cloud Project ID that is registered for Earth Engine access.
    Example::

        GEE_PROJECT_ID=aqi-satellite

    The pipeline will raise an ``EnvironmentError`` at import time if this
    variable is not set, rather than silently using a wrong project.

Optional Environment Variables
-------------------------------
EE_SA_KEY_PATH
    Absolute path to a service-account JSON key file. When provided the
    initializer uses service-account auth instead of OAuth/user credentials.
"""

import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

# Base directories
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent.parent

# ---------------------------------------------------------------------------
# Google Cloud / Earth Engine project identity
# ---------------------------------------------------------------------------

def _resolve_gee_project_id() -> str:
    """Return the GEE project ID from environment, with deprecation warnings.

    Resolution order:
    1. ``GEE_PROJECT_ID``   — canonical, required variable (new name).
    2. ``EE_PROJECT``       — legacy alias (deprecated; emits warning).
    3. ``GCP_PROJECT``      — legacy alias (deprecated; emits warning).

    Raises
    ------
    EnvironmentError
        When none of the above variables are set.
    """
    project_id = os.getenv("GEE_PROJECT_ID")
    if project_id:
        return project_id

    # Check legacy aliases and warn
    for legacy_var in ("EE_PROJECT", "GCP_PROJECT"):
        legacy_val = os.getenv(legacy_var)
        if legacy_val:
            logger.warning(
                "Environment variable '%s' is deprecated. "
                "Please rename it to GEE_PROJECT_ID. "
                "Support for '%s' will be removed in a future release.",
                legacy_var,
                legacy_var,
            )
            return legacy_val

    raise EnvironmentError(
        "GEE_PROJECT_ID environment variable is not set.\n"
        "\n"
        "This variable is required to initialize Google Earth Engine with a\n"
        "registered Google Cloud Project.\n"
        "\n"
        "To fix this, add the following line to your .env file or shell:\n"
        "\n"
        "    GEE_PROJECT_ID=aqi-satellite\n"
        "\n"
        "If you are running in CI/CD, set GEE_PROJECT_ID as a secret or\n"
        "environment variable in your pipeline configuration."
    )


# Canonical project ID — single source of truth for the entire codebase.
GEE_PROJECT_ID: str = _resolve_gee_project_id()

# Service-account key path (optional — leave empty for OAuth/user credentials)
EE_SA_KEY_PATH: str = os.getenv("EE_SA_KEY_PATH", "")

# ---------------------------------------------------------------------------
# Spatial and temporal defaults
# ---------------------------------------------------------------------------

# Default Bounding Box for India: [West Longitude, South Latitude, East Longitude, North Latitude]
INDIA_BBOX = [68.1, 6.7, 97.4, 35.5]

# Default Temporal Settings
DEFAULT_START_DATE = "2026-01-01"
DEFAULT_END_DATE = "2026-12-31"
