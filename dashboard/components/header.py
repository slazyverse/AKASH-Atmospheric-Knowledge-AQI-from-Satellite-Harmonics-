"""
dashboard/components/header.py — Shared page header component.

Renders a consistent top-of-page header containing:
  - Module icon + title
  - Subtitle / description
  - Breadcrumb trail (Home > Module)
  - Optional "last updated" badge
  - Optional action buttons row (e.g., Refresh, Export)

All pages call render_page_header() as their first element, ensuring
visual consistency across the entire application.
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from dashboard.core.theme import (
    BORDER_DEFAULT,
    MODULE_ICONS,
    PRIMARY,
    TEXT_MUTED,
    TEXT_SECONDARY,
)


def render_page_header(
    module_name: str,
    subtitle: str = "",
    last_updated: datetime | None = None,
    show_refresh_button: bool = False,
    show_export_button: bool = False,
) -> bool:
    """
    Render the standard page header block.

    Args:
        module_name:        Display name of the current module (e.g. "Surface AQI").
        subtitle:           One-line description shown below the title.
        last_updated:       If provided, displays a "last updated" badge.
        show_refresh_button: If True, renders a Refresh action button.
        show_export_button:  If True, renders an Export action button.

    Returns:
        True if the user clicked Refresh (so the page can trigger a reload).
        Always False when show_refresh_button is False.
    """
    icon = MODULE_ICONS.get(module_name, "📊")
    refresh_clicked = False

    # ── Breadcrumb ───────────────────────────────────────────────────────────
    crumb_home = "Home" if module_name != "Home" else ""
    breadcrumb_html = (
        f'<span style="color:{TEXT_MUTED}">🏠 Home</span>'
        f'<span style="color:{TEXT_MUTED}"> › </span>'
        f'<span style="color:{PRIMARY}">{module_name}</span>'
        if crumb_home
        else f'<span style="color:{PRIMARY}">🏠 Home</span>'
    )

    st.markdown(
        f'<div style="font-size:0.78rem;margin-bottom:12px">{breadcrumb_html}</div>',
        unsafe_allow_html=True,
    )

    # ── Title row ────────────────────────────────────────────────────────────
    title_col, action_col = st.columns([5, 1])

    with title_col:
        st.markdown(
            f"""
            <div style="display:flex;align-items:center;gap:14px;margin-bottom:4px">
              <span style="font-size:2.2rem;line-height:1">{icon}</span>
              <div>
                <h1 style="margin:0;font-size:1.8rem;font-weight:700;
                           color:#E6EDF3;line-height:1.15">{module_name}</h1>
                <p style="margin:4px 0 0;font-size:0.9rem;color:{TEXT_SECONDARY}">
                  {subtitle}
                </p>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with action_col:
        if last_updated:
            time_str = last_updated.strftime("%H:%M UTC")
            st.markdown(
                f"""
                <div style="text-align:right;padding-top:12px">
                  <div style="font-size:0.7rem;color:{TEXT_MUTED};
                              background:#21262D;border-radius:6px;
                              padding:4px 8px;display:inline-block;
                              border:1px solid {BORDER_DEFAULT}">
                    🕐 {time_str}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ── Action buttons ───────────────────────────────────────────────────────
    if show_refresh_button or show_export_button:
        btn_cols = st.columns([1] * (int(show_refresh_button) + int(show_export_button)) + [8])
        col_idx = 0
        if show_refresh_button:
            with btn_cols[col_idx]:
                refresh_clicked = st.button("🔄 Refresh", key=f"refresh_{module_name}")
            col_idx += 1
        if show_export_button:
            with btn_cols[col_idx]:
                st.button("⬇️ Export", key=f"export_{module_name}")

    # ── Divider ──────────────────────────────────────────────────────────────
    st.markdown(
        f"<hr style='border-color:{BORDER_DEFAULT};margin:12px 0 20px'>",
        unsafe_allow_html=True,
    )

    return refresh_clicked
