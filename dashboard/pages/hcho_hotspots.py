"""
dashboard/pages/hcho_hotspots.py — HCHO Hotspot Detection module page.

Displays formaldehyde (HCHO) column density hotspots derived from Sentinel-5P.

Day 2 Scope: Stub hotspot table, source attribution pie placeholder, detection criteria.
Day 3 Scope: Live TROPOMI data, interactive hotspot map, monthly trend chart.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components.empty_state import render_coming_soon, render_stub_badge
from dashboard.components.error_state import render_info_notice
from dashboard.components.footer import render_page_footer
from dashboard.components.header import render_page_header
from dashboard.components.loading import render_skeleton_chart
from dashboard.core.theme import (
    ACCENT_ORANGE,
    BG_ELEVATED,
    BORDER_DEFAULT,
    PRIMARY,
    TEXT_MUTED,
    TEXT_SECONDARY,
)
from dashboard.services import hcho_service


def render() -> None:
    """Render the HCHO Hotspots module page."""
    render_page_header(
        module_name="HCHO Hotspots",
        subtitle="Formaldehyde column density hotspots from Sentinel-5P TROPOMI",
        show_refresh_button=True,
    )

    render_info_notice(
        "Live Sentinel-5P data integration arrives in Day 3. "
        "Currently showing 3 illustrative stub hotspots."
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── What is HCHO? ─────────────────────────────────────────────────────────
    _render_hcho_explainer()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Filters ───────────────────────────────────────────────────────────────
    _render_filters()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Hotspot summary metrics ────────────────────────────────────────────────
    _render_hotspot_metrics()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Hotspot table ─────────────────────────────────────────────────────────
    st.markdown(f"<h4 style='color:{PRIMARY}'>⚗️ Detected Hotspots</h4>", unsafe_allow_html=True)
    render_stub_badge()
    _render_hotspot_table()

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Map placeholder ───────────────────────────────────────────────────────
    left, right = st.columns([3, 2])

    with left:
        st.markdown(f"<h4 style='color:{PRIMARY}'>🗺️ HCHO Density Map</h4>", unsafe_allow_html=True)
        render_coming_soon(
            "HCHO Column Density Map",
            planned_day="Day 3",
            features=[
                "Heatmap overlay of HCHO concentration (molecules/cm²)",
                "Threshold slider for hotspot visibility",
                "Temporal animation (past 30 days)",
                "Source type classification layer",
            ],
        )

    with right:
        st.markdown(f"<h4 style='color:{PRIMARY}'>📊 Source Attribution</h4>", unsafe_allow_html=True)
        render_coming_soon(
            "Source Attribution Chart",
            planned_day="Day 3",
            features=[
                "Donut chart: Industrial / Biogenic / Biomass",
                "Per-hotspot drill-down",
            ],
        )

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Trend chart placeholder ───────────────────────────────────────────────
    st.markdown(f"<h4 style='color:{PRIMARY}'>📈 Monthly HCHO Trend</h4>", unsafe_allow_html=True)
    st.markdown(
        f"<div style='font-size:0.82rem;color:{TEXT_MUTED};margin-bottom:8px'>"
        "12-month trend skeleton — live Plotly chart in Day 3</div>",
        unsafe_allow_html=True,
    )
    render_skeleton_chart(height_px=240)

    render_page_footer()


def _render_hcho_explainer() -> None:
    st.markdown(
        f"""
        <div style="background:{PRIMARY}18;border:1px solid {PRIMARY}44;
                    border-radius:12px;padding:16px 20px">
          <div style="font-size:0.88rem;font-weight:600;color:{PRIMARY};margin-bottom:6px">
            ℹ️ What is HCHO?
          </div>
          <div style="font-size:0.82rem;color:{TEXT_SECONDARY};line-height:1.6">
            <strong>Formaldehyde (HCHO)</strong> is a volatile organic compound (VOC) produced by
            industrial processes, biomass burning, and biogenic vegetation decay. Elevated HCHO levels
            indicate secondary pollutant formation risk and are linked to respiratory irritation.
            Sentinel-5P TROPOMI measures HCHO column density at 3.5×5.5 km resolution with daily coverage.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_filters() -> None:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.selectbox("📅 Date", ["Today", "Last 7 days", "Last 30 days"], key="hcho_date")
    with c2:
        st.selectbox("🏭 Source Type", ["All", "Industrial", "Biogenic", "Biomass Burning"], key="hcho_source")
    with c3:
        st.slider("🎯 Min Confidence", 0.5, 1.0, 0.6, 0.05, key="hcho_confidence")


def _render_hotspot_metrics() -> None:
    hotspots = hcho_service.get_hotspots()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("⚗️ Active Hotspots", str(len(hotspots)), "")
    with c2:
        avg_density = sum(h.column_density for h in hotspots) / max(len(hotspots), 1)
        st.metric("📊 Avg Column Density", f"{avg_density:.1f}", "×10¹⁵ mol/cm²")
    with c3:
        industrial = sum(1 for h in hotspots if h.source_type == "industrial")
        st.metric("🏭 Industrial Sources", str(industrial), "")
    with c4:
        high_conf = sum(1 for h in hotspots if h.confidence >= 0.85)
        st.metric("✅ High Confidence", str(high_conf), "≥ 0.85")


def _render_hotspot_table() -> None:
    hotspots = hcho_service.get_hotspots()
    rows = [
        {
            "ID": h.hotspot_id,
            "Latitude": h.latitude,
            "Longitude": h.longitude,
            "Column Density (×10¹⁵)": h.column_density,
            "Radius (km)": h.radius_km,
            "Source Type": h.source_type,
            "Confidence": f"{h.confidence:.0%}",
        }
        for h in hotspots
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
