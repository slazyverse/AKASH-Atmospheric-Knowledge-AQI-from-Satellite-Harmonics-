"""
dashboard/core/config.py — Configuration bridge for the VAYU-DRISHTI dashboard.

Responsibilities:
  1. Load the top-level PROJECT_CONFIG.yaml (project metadata, version, status).
  2. Expose typed constants consumed by all dashboard pages and components.
  3. Load optional environment variables (.env) for local development overrides.

Design decisions:
  - Reading PROJECT_CONFIG.yaml rather than importing backend Settings avoids a
    hard dependency on backend's pydantic-settings install in the dashboard venv.
    The dashboard is intentionally deployable independently (e.g., Streamlit Cloud)
    without the full backend dependency tree.
  - API_BASE_URL defaults to localhost:8000 and is overridden by VAYU_API_URL env
    variable. Day 3 API calls will use this value via the api_client module.
  - @dataclass(frozen=True) prevents accidental mutation of config at runtime.
  - A module-level singleton (dashboard_config) is created once and imported
    everywhere — identical pattern to backend's get_settings() + @lru_cache.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Load .env from the dashboard directory (or project root as fallback)
_ENV_PATH = Path(__file__).parents[1] / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=False)

# Project root = two levels up from dashboard/core/
_REPO_ROOT = Path(__file__).parents[2]
_PROJECT_CONFIG_PATH = _REPO_ROOT / "PROJECT_CONFIG.yaml"


def _load_project_config() -> dict[str, Any]:
    """
    Parse PROJECT_CONFIG.yaml from the repository root.

    Returns an empty dict if the file is absent (e.g., in CI environments
    that strip non-essential files) rather than crashing at import time.
    """
    if not _PROJECT_CONFIG_PATH.exists():
        return {}
    with _PROJECT_CONFIG_PATH.open("r", encoding="utf-8") as fh:
        return yaml.safe_load(fh) or {}


@dataclass(frozen=True)
class DashboardConfig:
    """
    Typed, immutable configuration consumed by all dashboard modules.

    Attributes are sourced from (in priority order):
      1. Environment variables (highest priority — for deployment overrides)
      2. PROJECT_CONFIG.yaml  (project metadata defaults)
      3. Hard-coded defaults  (lowest priority — used when nothing else is set)
    """
    # ── Application Identity ─────────────────────────────────────────────────
    app_name: str = "VAYU-DRISHTI"
    app_version: str = "0.2.0-dashboard"
    app_description: str = (
        "Atmospheric Knowledge — AQI from Satellite Harmonics. "
        "Scientific geospatial analytics for air quality monitoring, "
        "HCHO detection, fire alerts, and AI-driven forecasting."
    )
    project_status: str = "IN PROGRESS"

    # ── Backend API Connection (used from Day 3 onwards) ─────────────────────
    api_base_url: str = "http://localhost:8000"
    api_v1_prefix: str = "/api/v1"
    api_timeout_seconds: int = 30

    # ── Dashboard Behaviour ──────────────────────────────────────────────────
    default_page: str = "Home"
    auto_refresh_seconds: int = 300   # 5-minute default for live data panels
    max_data_points: int = 1000       # Cap for chart performance

    # ── Feature Flags (Day 3+ will flip these to True) ───────────────────────
    enable_live_api: bool = False
    enable_map_layers: bool = False
    enable_ml_forecast: bool = False

    # ── Data Freshness Warning Threshold ─────────────────────────────────────
    stale_data_minutes: int = 60

    @property
    def api_v1_url(self) -> str:
        """Full base URL for all v1 API calls."""
        return f"{self.api_base_url}{self.api_v1_prefix}"

    @property
    def health_url(self) -> str:
        """Backend health check endpoint."""
        return f"{self.api_v1_url}/health"

    @property
    def version_url(self) -> str:
        """Backend version endpoint."""
        return f"{self.api_v1_url}/version"


def _build_config() -> DashboardConfig:
    """
    Construct the DashboardConfig singleton by merging all config sources.

    Override order: env vars > PROJECT_CONFIG.yaml > dataclass defaults.
    """
    raw = _load_project_config()
    project_meta: dict[str, Any] = raw.get("project", {})

    return DashboardConfig(
        app_name=os.getenv("VAYU_APP_NAME", project_meta.get("name", "VAYU-DRISHTI")),
        app_version=os.getenv("VAYU_APP_VERSION", project_meta.get("version", "0.2.0-dashboard")),
        project_status=os.getenv("VAYU_STATUS", project_meta.get("status", "IN PROGRESS")),
        api_base_url=os.getenv("VAYU_API_URL", "http://localhost:8000"),
        api_v1_prefix=os.getenv("VAYU_API_V1_PREFIX", "/api/v1"),
        api_timeout_seconds=int(os.getenv("VAYU_API_TIMEOUT", "30")),
        enable_live_api=os.getenv("VAYU_ENABLE_LIVE_API", "false").lower() == "true",
        enable_map_layers=os.getenv("VAYU_ENABLE_MAP_LAYERS", "false").lower() == "true",
        enable_ml_forecast=os.getenv("VAYU_ENABLE_ML_FORECAST", "false").lower() == "true",
    )


# ── Module-level singleton (created once at import time) ──────────────────────
dashboard_config: DashboardConfig = _build_config()
