"""
dashboard/components/error_state.py — Error and API-down UI components.

Provides standardised error presentation across all modules:
  - render_api_error()        — Backend unreachable banner
  - render_data_error()       — Data fetch / parse failure card
  - render_inline_warning()   — Subtle inline warning strip
  - render_critical_alert()   — Full-page blocking error for unrecoverable failures

Design decisions:
  - Error components accept an optional `on_retry` callable (a button callback)
    so the caller decides whether to re-fetch data. This keeps error UI decoupled
    from data-fetching logic.
  - In Day 2, these components are demonstrated with stub text.
    Day 3 services will raise typed exceptions that map to these components.
"""

from __future__ import annotations

from typing import Callable

import streamlit as st

from dashboard.core.state import clear_error
from dashboard.core.theme import (
    ACCENT_ORANGE,
    BG_ELEVATED,
    BORDER_DEFAULT,
    STATUS_ERROR,
    STATUS_INFO,
    STATUS_WARNING,
    TEXT_MUTED,
    TEXT_SECONDARY,
)


def render_api_error(
    api_url: str = "http://localhost:8000",
    on_retry: Callable[[], None] | None = None,
) -> None:
    """
    Render a banner indicating the backend API is unreachable.

    Args:
        api_url:  The URL that was attempted (for user debugging context).
        on_retry: Optional callback invoked when user clicks "Retry".
    """
    st.markdown(
        f"""
        <div style="background:{STATUS_ERROR}22;border:1px solid {STATUS_ERROR}66;
                    border-radius:12px;padding:20px 24px;margin-bottom:20px">
          <div style="display:flex;align-items:flex-start;gap:12px">
            <span style="font-size:1.5rem;flex-shrink:0">🔴</span>
            <div>
              <div style="font-size:1rem;font-weight:600;color:{STATUS_ERROR};
                          margin-bottom:4px">API Server Unreachable</div>
              <div style="font-size:0.85rem;color:{TEXT_SECONDARY};margin-bottom:8px">
                The VAYU-DRISHTI backend could not be reached at:
                <code style="background:{BG_ELEVATED};padding:1px 6px;border-radius:4px;
                             font-size:0.8rem">{api_url}</code>
              </div>
              <div style="font-size:0.8rem;color:{TEXT_MUTED}">
                Possible causes: Server not started · Network unreachable · Port blocked<br>
                Try: <code style="font-size:0.75rem">cd backend &amp;&amp; uvicorn app.main:app --reload</code>
              </div>
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if on_retry:
        if st.button("🔄 Retry Connection", key="retry_api_connection"):
            on_retry()


def render_data_error(
    message: str,
    module: str = "Unknown",
    details: str = "",
    on_retry: Callable[[], None] | None = None,
) -> None:
    """
    Render a data-fetch or data-parse error card within a module.

    Args:
        message:  Short human-readable error description.
        module:   Name of the module where the error occurred.
        details:  Technical detail / stack trace excerpt (optional).
        on_retry: Optional retry callback.
    """
    with st.container():
        st.markdown(
            f"""
            <div style="background:{ACCENT_ORANGE}18;border:1px solid {ACCENT_ORANGE}55;
                        border-radius:12px;padding:16px 20px;margin-bottom:16px">
              <div style="font-size:0.9rem;font-weight:600;color:{ACCENT_ORANGE};
                          margin-bottom:6px">⚠️ Data Unavailable — {module}</div>
              <div style="font-size:0.82rem;color:{TEXT_SECONDARY};margin-bottom:6px">
                {message}
              </div>
              {'<div style="font-size:0.75rem;color:' + TEXT_MUTED + ';font-family:monospace;'
               'background:' + BG_ELEVATED + ';padding:6px 8px;border-radius:4px;'
               'margin-top:6px">' + details + '</div>'
               if details else ''}
            </div>
            """,
            unsafe_allow_html=True,
        )

        btn_cols = st.columns([1, 8])
        with btn_cols[0]:
            if on_retry and st.button("🔄 Retry", key=f"retry_{module}"):
                on_retry()
        with btn_cols[1]:
            if st.button("✖ Dismiss", key=f"dismiss_{module}"):
                clear_error()
                st.rerun()


def render_inline_warning(message: str) -> None:
    """
    Render a subtle inline warning strip (non-blocking).

    Args:
        message: Warning text to display.
    """
    st.markdown(
        f"""
        <div style="background:{STATUS_WARNING}18;border-left:3px solid {STATUS_WARNING};
                    border-radius:0 6px 6px 0;padding:8px 12px;margin:8px 0;
                    font-size:0.82rem;color:{TEXT_SECONDARY}">
          ⚠️ {message}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_info_notice(message: str) -> None:
    """
    Render an informational notice strip.

    Args:
        message: Information text to display.
    """
    st.markdown(
        f"""
        <div style="background:{STATUS_INFO}18;border-left:3px solid {STATUS_INFO};
                    border-radius:0 6px 6px 0;padding:8px 12px;margin:8px 0;
                    font-size:0.82rem;color:{TEXT_SECONDARY}">
          ℹ️ {message}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_critical_alert(
    title: str,
    message: str,
    severity: str = "error",
) -> None:
    """
    Render a full-width critical alert box (e.g., for configuration failures).

    Args:
        title:    Bold alert title.
        message:  Detailed message text.
        severity: One of "error", "warning", "info".
    """
    colour_map = {
        "error":   (STATUS_ERROR,   "🔴"),
        "warning": (STATUS_WARNING, "⚠️"),
        "info":    (STATUS_INFO,    "ℹ️"),
    }
    colour, icon = colour_map.get(severity, (STATUS_ERROR, "🔴"))

    st.markdown(
        f"""
        <div style="background:{colour}18;border:2px solid {colour}88;
                    border-radius:12px;padding:24px 28px;margin:16px 0">
          <div style="font-size:1.1rem;font-weight:700;color:{colour};margin-bottom:8px">
            {icon} {title}
          </div>
          <div style="font-size:0.88rem;color:{TEXT_SECONDARY}">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
