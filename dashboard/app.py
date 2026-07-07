"""
dashboard/app.py — VAYU-DRISHTI Streamlit Dashboard Entrypoint.

This is the single file that `streamlit run dashboard/app.py` executes.

Architecture:
  1. Page configuration (must be the very first Streamlit call).
  2. CSS injection from theme constants.
  3. Session state initialisation.
  4. Sidebar rendering → returns the selected module name.
  5. Page router → dispatches to the correct page module's render() function.

Design decisions:
  - Session-state router instead of Streamlit's native multi-page file structure.
    Reason: native multi-page routing does not support a persistent shared sidebar
    with active-state styling and session-state-aware navigation badges.
    All pages remain in a single Python process, sharing the same session_state.

  - Page modules expose a single render() function.
    Each module is independently maintainable and testable.
    Adding a new module requires: one new file in pages/, one new entry in
    PAGE_ROUTER, and one new entry in sidebar NAVIGATION_MODULES. Nothing else.

  - import at module level: Streamlit's hot-reload reruns this entire file on
    every interaction. Module-level imports are cached by Python's import
    machinery, so there is no repeated I/O overhead.

Usage:
    cd <repo-root>
    pip install -r dashboard/requirements.txt
    streamlit run dashboard/app.py
"""

from __future__ import annotations

import sys
from pathlib import Path

# ── Path bootstrap ─────────────────────────────────────────────────────────────
# Ensure the repo root is on sys.path so `dashboard.*` imports resolve correctly
# whether the script is run from the repo root or from the dashboard/ directory.
_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# ── Streamlit import (must happen before any other st calls) ──────────────────
import streamlit as st

# ── Internal imports ───────────────────────────────────────────────────────────
from dashboard.core.config import dashboard_config
from dashboard.core.state import init_session_state
from dashboard.core.theme import CUSTOM_CSS
from dashboard.components.sidebar import render_sidebar

# ── Page module imports ────────────────────────────────────────────────────────
from dashboard.pages import (
    aqi_forecast,
    explainable_ai,
    fire_monitoring,
    hcho_hotspots,
    home,
    reports,
    surface_aqi,
)

# ── Page router mapping ────────────────────────────────────────────────────────
# Maps sidebar display names → page module render() functions.
# To add a new module: create pages/my_module.py with a render() function,
# import it here, and add an entry to this dict. Nothing else changes.
PAGE_ROUTER: dict[str, callable] = {
    "Home":             home.render,
    "Surface AQI":      surface_aqi.render,
    "HCHO Hotspots":    hcho_hotspots.render,
    "Fire Monitoring":  fire_monitoring.render,
    "AQI Forecast":     aqi_forecast.render,
    "Explainable AI":   explainable_ai.render,
    "Reports":          reports.render,
}


def _configure_page() -> None:
    """
    Set Streamlit page metadata and layout.

    Must be the FIRST Streamlit call in the script.
    Called unconditionally on every script rerun.
    """
    st.set_page_config(
        page_title="VAYU-DRISHTI — Atmospheric Intelligence",
        page_icon="🌐",
        layout="wide",
        initial_sidebar_state="expanded",
        menu_items={
            "Get Help": None,
            "Report a bug": None,
            "About": (
                f"**VAYU-DRISHTI** v{dashboard_config.app_version}\n\n"
                "Atmospheric Knowledge — AQI from Satellite Harmonics.\n\n"
                "A scientific geospatial analytics platform for air quality "
                "monitoring, HCHO detection, fire alerts, and AI-driven forecasting."
            ),
        },
    )


def _inject_css() -> None:
    """Inject the global CSS from core/theme.py."""
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


def main() -> None:
    """
    Main application entry point.

    Execution order on every Streamlit rerun:
      1. Configure page (must be first)
      2. Inject global CSS
      3. Initialise session state
      4. Render sidebar → get selected page
      5. Route to selected page's render()
    """
    _configure_page()
    _inject_css()
    init_session_state()

    # Render sidebar — returns the currently active module name
    selected_page = render_sidebar()

    # Route to the appropriate page module
    page_renderer = PAGE_ROUTER.get(selected_page)

    if page_renderer is None:
        # Defensive fallback — should never happen with a well-formed sidebar
        st.error(
            f"Unknown page '{selected_page}'. "
            "Please select a module from the sidebar."
        )
        home.render()
        return

    page_renderer()


if __name__ == "__main__":
    main()
