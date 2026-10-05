"""
dashboard/pages/reports.py — Reports & data export page.

Report generation (PDF bulletins, scheduled reports) is not implemented, so
no report list is shown. What exists today is exporting the data currently
served by the API as CSV — each export is labelled with its source kind.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components import (
    render_info_notice,
    render_page_footer,
    render_page_header,
    render_source_badge,
)
from dashboard.core.theme import PRIMARY
from dashboard.services import fire_service, hcho_service, surface_aqi_service
from dashboard.services.data_sources import source_kind


def render() -> None:
    """Render the Reports & export page."""
    render_page_header(
        module_name="Reports",
        subtitle="Data exports from the API — report generation is not implemented yet",
        show_refresh_button=False,
        show_export_button=False,
    )

    st.markdown(f"<h4 style='color:{PRIMARY}'>📋 Report Generation</h4>", unsafe_allow_html=True)
    render_info_notice(
        "Unavailable: PDF bulletins and scheduled reports are not implemented. "
        "No report history exists, so none is listed."
    )

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    st.markdown(f"<h4 style='color:{PRIMARY}'>⬇️ Data Exports (CSV)</h4>", unsafe_allow_html=True)

    readings = surface_aqi_service.get_latest_readings()
    _export(
        "Station readings (latest per station)", "aqi",
        pd.DataFrame([vars(r) for r in readings]), "station_readings",
    )
    hotspots = hcho_service.get_hotspots(min_confidence=0.0)
    _export(
        "HCHO hotspot clusters", "hcho",
        pd.DataFrame([vars(h) for h in hotspots]), "hcho_hotspots",
    )
    fires = fire_service.get_active_fires(min_frp=0.0, hours=168)
    _export(
        "Fire detections (last 7 days of the source)", "fire",
        pd.DataFrame([vars(f) for f in fires]), "fire_detections",
    )

    render_page_footer(show_data_sources=False)


def _export(title: str, domain: str, df: pd.DataFrame, stem: str) -> None:
    """One export row: source badge + download button (disabled when empty)."""
    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown(f"**{title}** — {len(df)} row(s)")
        render_source_badge(domain, compact=True)
    with c2:
        st.download_button(
            "Download CSV",
            data=df.to_csv(index=False).encode("utf-8"),
            file_name=f"{stem}_{source_kind(domain)}.csv",
            mime="text/csv",
            disabled=df.empty,
            key=f"export_{stem}",
            width="stretch",
        )
