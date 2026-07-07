"""
dashboard/core/state.py — Centralised st.session_state initialisation.

All session state keys used across the application are declared here.
Calling init_session_state() at the top of app.py guarantees that every
subsequent page and component can safely read these keys without a KeyError.

Design decision:
  Using a single initialisation function (rather than scattered
  `if "key" not in st.session_state` guards throughout pages) means:
    - Every possible state key is visible in one place.
    - Pages are free to read state without defensive boilerplate.
    - Adding a new key requires editing exactly one file.
"""

from __future__ import annotations

import streamlit as st

from dashboard.core.config import dashboard_config


def init_session_state() -> None:
    """
    Ensure all session_state keys exist with their default values.

    Must be called once at the very beginning of app.py, before any
    page or component is rendered.
    """
    defaults: dict[str, object] = {
        # ── Navigation ───────────────────────────────────────────────────────
        "current_page": dashboard_config.default_page,

        # ── API Status ──────────────────────────────────────────────────────
        "api_reachable": None,          # None = unchecked, True/False after probe
        "api_last_checked": None,       # datetime or None
        "last_successful_sync": None,   # datetime or None

        # ── Data Cache ──────────────────────────────────────────────────────
        "aqi_data": None,               # Latest Surface AQI dataset
        "hcho_data": None,              # Latest HCHO detection dataset
        "fire_data": None,              # Latest Fire Monitoring dataset
        "forecast_data": None,          # Latest AQI Forecast dataset
        "xai_data": None,               # Latest XAI explanation payload
        "report_list": None,            # List of available report metadata

        # ── UI Preferences ──────────────────────────────────────────────────
        "selected_region": "India",     # Default geographic filter
        "selected_date_range": "7d",    # Default temporal filter
        "chart_type": "line",           # Default chart rendering mode

        # ── Error State ─────────────────────────────────────────────────────
        "last_error": None,             # Last error message (str or None)
        "error_module": None,           # Which module triggered the error
    }

    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


def navigate_to(page: str) -> None:
    """
    Update the current page in session state.

    Args:
        page: The display name of the target page (must match MODULE_ICONS keys).
    """
    st.session_state["current_page"] = page


def clear_error() -> None:
    """Reset error state after the user acknowledges it."""
    st.session_state["last_error"] = None
    st.session_state["error_module"] = None


def set_error(message: str, module: str = "Unknown") -> None:
    """
    Record an error in session state so any component can surface it.

    Args:
        message: Human-readable error description.
        module:  The module name where the error occurred.
    """
    st.session_state["last_error"] = message
    st.session_state["error_module"] = module
