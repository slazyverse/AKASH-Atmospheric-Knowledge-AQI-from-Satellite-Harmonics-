"""
dashboard/components/footer.py — Shared page footer component.

Renders a consistent bottom-of-page footer with:
  - Data source attribution (satellite missions, sensor networks)
  - Platform version and sprint badge
  - Data disclaimer / scientific note
  - Links to documentation (placeholder in Day 2)

render_page_footer() is called at the end of every page module.
"""

from __future__ import annotations

import streamlit as st

from dashboard.core.config import dashboard_config
from dashboard.core.theme import BORDER_DEFAULT, PRIMARY, TEXT_MUTED, TEXT_SECONDARY


def render_page_footer(show_data_sources: bool = True) -> None:
    """
    Render the standard page footer.

    Args:
        show_data_sources: If True, shows satellite data attribution row.
                           Set to False for utility pages (e.g., Reports).
    """
    st.markdown(
        f"<hr style='border-color:{BORDER_DEFAULT};margin:40px 0 16px'>",
        unsafe_allow_html=True,
    )

    if show_data_sources:
        _render_data_sources()

    _render_footer_bar()


def _render_data_sources() -> None:
    """Render the satellite data source attribution block."""
    sources = [
        ("🛰️ Sentinel-5P", "TROPOMI — HCHO & NO₂"),
        ("🌍 MODIS/VIIRS",  "Fire Radiative Power"),
        ("📡 MERRA-2",      "Reanalysis meteorology"),
        ("🏭 CPCB",         "Ground-truth AQI sensors"),
    ]

    cols = st.columns(len(sources))
    for col, (name, detail) in zip(cols, sources):
        with col:
            st.markdown(
                f"""
                <div style="text-align:center;padding:8px 4px">
                  <div style="font-size:0.78rem;font-weight:600;color:{TEXT_SECONDARY}">
                    {name}
                  </div>
                  <div style="font-size:0.68rem;color:{TEXT_MUTED};margin-top:2px">
                    {detail}
                  </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        f"<hr style='border-color:{BORDER_DEFAULT};margin:12px 0'>",
        unsafe_allow_html=True,
    )


def _render_footer_bar() -> None:
    """Render the bottom bar with version, sprint, and disclaimer."""
    left_col, right_col = st.columns([3, 1])

    with left_col:
        st.markdown(
            f"""
            <div style="font-size:0.7rem;color:{TEXT_MUTED}">
              <strong style="color:{PRIMARY}">VAYU-DRISHTI</strong> ·
              v{dashboard_config.app_version} ·
              <span style="background:#21262D;border-radius:4px;
                           padding:1px 6px;font-size:0.65rem">
                Sprint: Day 2 — Dashboard Skeleton
              </span>
              <br>
              <span style="margin-top:4px;display:inline-block">
                ⚠️ Atmospheric data is indicative only.
                Not for regulatory or emergency decision-making without validation.
              </span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with right_col:
        st.markdown(
            f"""
            <div style="text-align:right;font-size:0.7rem;color:{TEXT_MUTED}">
              <div>📘 Docs</div>
              <div style="margin-top:2px">🔗 API</div>
              <div style="margin-top:2px">📝 Changelog</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
