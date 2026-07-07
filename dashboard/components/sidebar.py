"""
dashboard/components/sidebar.py — Shared navigation sidebar.

Renders the left sidebar with:
  - Brand logo and project name
  - Module navigation (radio group styled as nav links)
  - Backend API status indicator
  - Data freshness timestamp
  - Project version footer

Design decisions:
  - Navigation is implemented as st.radio with custom CSS, not st.page_link.
    This gives full control over active-state styling and keeps routing purely
    in session state — no file-system routing conflicts with Streamlit's
    native multi-page runner.
  - API status indicator is purely cosmetic in Day 2; it will probe the live
    backend health endpoint from Day 3 onwards.
"""

from __future__ import annotations

from datetime import datetime
import streamlit as st

from dashboard.core.config import dashboard_config
from dashboard.core.state import navigate_to
from dashboard.core.theme import (
    ACCENT_ORANGE,
    BG_ELEVATED,
    BORDER_DEFAULT,
    MODULE_ICONS,
    PRIMARY,
    STATUS_ERROR,
    STATUS_OK,
    STATUS_WARNING,
    TEXT_MUTED,
    TEXT_SECONDARY,
)
from dashboard.services.api_client import APIClient

# Ordered list defines both navigation sequence and display labels
NAVIGATION_MODULES: list[str] = [
    "Home",
    "Surface AQI",
    "HCHO Hotspots",
    "Fire Monitoring",
    "AQI Forecast",
    "Explainable AI",
    "Reports",
]


def render_sidebar() -> str:
    """
    Render the full left sidebar and return the currently selected page name.

    Returns:
        The display name of the currently active module.
    """
    with st.sidebar:
        _render_brand()
        st.markdown(f"<hr style='border-color:{BORDER_DEFAULT};margin:8px 0'>", unsafe_allow_html=True)
        selected = _render_navigation()
        st.markdown(f"<hr style='border-color:{BORDER_DEFAULT};margin:8px 0'>", unsafe_allow_html=True)
        _render_api_status()
        st.markdown(f"<hr style='border-color:{BORDER_DEFAULT};margin:8px 0'>", unsafe_allow_html=True)
        _render_sidebar_footer()

    return selected


def _render_brand() -> None:
    """Render the project brand identity block."""
    st.markdown(
        f"""
        <div style="padding:16px 4px 8px 4px">
          <div style="display:flex;align-items:center;gap:10px">
            <span style="font-size:2rem">🌐</span>
            <div>
              <div style="font-size:1.1rem;font-weight:700;color:{PRIMARY};
                          letter-spacing:0.03em;line-height:1.2">
                VAYU-DRISHTI
              </div>
              <div style="font-size:0.7rem;color:{TEXT_MUTED};letter-spacing:0.08em;
                          text-transform:uppercase">
                Atmospheric Intelligence
              </div>
            </div>
          </div>
          <div style="margin-top:6px;font-size:0.7rem;color:{TEXT_MUTED}">
            v{dashboard_config.app_version}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_navigation() -> str:
    """
    Render the navigation radio group and update session state on change.

    Returns:
        The currently selected page name.
    """
    current = st.session_state.get("current_page", "Home")

    # Ensure current page is valid (guards against stale session state)
    if current not in NAVIGATION_MODULES:
        current = "Home"

    # Build display labels with icons
    options = [f"{MODULE_ICONS.get(m, '•')}  {m}" for m in NAVIGATION_MODULES]
    current_index = NAVIGATION_MODULES.index(current)

    st.markdown(
        f"<div style='font-size:0.7rem;font-weight:600;color:{TEXT_SECONDARY};"
        f"letter-spacing:0.1em;text-transform:uppercase;padding:0 4px 6px'>Navigation</div>",
        unsafe_allow_html=True,
    )

    selection_label = st.radio(
        label="navigation",
        options=options,
        index=current_index,
        label_visibility="collapsed",
        key="sidebar_nav",
    )

    # Extract plain module name from "icon  Module Name" format
    selected_module = selection_label.split("  ", 1)[-1].strip()

    if selected_module != current:
        navigate_to(selected_module)
        st.rerun()

    return selected_module


def _render_api_status() -> None:
    """
    Render a visual indicator for backend API connectivity.

    Day 3: Call APIClient().health_check(timeout=1.0) to get the live status.
    Throttled to run at most once every 10 seconds to keep UI responsive.
    """
    client = APIClient()
    now = datetime.now()
    last_checked = st.session_state.get("api_last_checked")
    api_reachable = st.session_state.get("api_reachable", None)

    # Check status at most once every 10 seconds to prevent Streamlit UI from blocking
    if last_checked is None or (now - last_checked).total_seconds() > 10:
        api_reachable = client.health_check(timeout=1.0)
        st.session_state["api_reachable"] = api_reachable
        st.session_state["api_last_checked"] = now
        if api_reachable:
            st.session_state["last_successful_sync"] = now

    if api_reachable is True:
        dot_color, label, detail = STATUS_OK, "Backend Connected", "Live data active"
    else:
        dot_color, label, detail = STATUS_ERROR, "Backend Offline", "Using stub fallback data"

    st.markdown(
        f"""
        <div style="padding:6px 4px">
          <div style="font-size:0.7rem;font-weight:600;color:{TEXT_SECONDARY};
                      letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px">
            System Status
          </div>
          <div style="display:flex;align-items:center;gap:8px;padding:8px 10px;
                      background:{BG_ELEVATED};border-radius:8px;
                      border:1px solid {BORDER_DEFAULT}">
            <div style="width:8px;height:8px;border-radius:50%;
                        background:{dot_color};
                        box-shadow:0 0 6px {dot_color}66;
                        flex-shrink:0"></div>
            <div>
              <div style="font-size:0.8rem;font-weight:500;color:#E6EDF3">{label}</div>
              <div style="font-size:0.7rem;color:{TEXT_MUTED}">{detail}</div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Data freshness status (uses last successful sync time)
    last_sync = st.session_state.get("last_successful_sync")
    if last_sync:
        freshness_time = last_sync.strftime("%Y-%m-%d %H:%M:%S")
        freshness_detail = f"⏱ Updated: {freshness_time}<br><span style='font-size:0.7rem'>Sync successful</span>"
    else:
        freshness_detail = "⏱ No live data yet<br><span style='font-size:0.7rem'>Awaiting connection</span>"

    st.markdown(
        f"""
        <div style="padding:6px 4px 2px">
          <div style="font-size:0.7rem;font-weight:600;color:{TEXT_SECONDARY};
                      letter-spacing:0.1em;text-transform:uppercase;margin-bottom:6px">
            Data Freshness
          </div>
          <div style="font-size:0.75rem;color:{TEXT_MUTED};
                      padding:6px 10px;background:{BG_ELEVATED};
                      border-radius:8px;border:1px solid {BORDER_DEFAULT}">
            {freshness_detail}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_sidebar_footer() -> None:
    """Render project environment and copyright at the bottom of the sidebar."""
    st.markdown(
        f"""
        <div style="padding:8px 4px;font-size:0.68rem;color:{TEXT_MUTED}">
          <div>📡 VAYU-DRISHTI Platform</div>
          <div style="margin-top:4px">Environment: <strong>Development</strong></div>
          <div style="margin-top:4px">Sprint: <strong>Day 2 — Dashboard</strong></div>
          <div style="margin-top:8px;color:{TEXT_MUTED}">
            © 2026 AKASH Project Team
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
