"""
dashboard/pages/surface_aqi.py — Surface AQI module page.

Displays real-time AQI readings from CPCB monitoring stations.

Day 2 Scope: Stub data table, AQI severity legend, metric cards, empty chart area.
Day 3 Scope: Live station data, Plotly map, time-series charts.
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
    AQI_GOOD,
    AQI_MODERATE,
    AQI_POOR,
    AQI_SATISFACTORY,
    AQI_SEVERE,
    AQI_VERY_POOR,
    BG_ELEVATED,
    BORDER_DEFAULT,
    PRIMARY,
    TEXT_MUTED,
    TEXT_SECONDARY,
)
from dashboard.services import surface_aqi_service


def render() -> None:
    """Render the Surface AQI module page."""
    render_page_header(
        module_name="Surface AQI",
        subtitle="Real-time air quality index readings from CPCB monitoring stations",
        show_refresh_button=True,
        show_export_button=True,
    )

    render_info_notice("Live station data arrives in Day 3. Displaying 4 illustrative stub readings.")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Filters row ───────────────────────────────────────────────────────────
    _render_filters()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Summary KPIs ──────────────────────────────────────────────────────────
    _render_summary_metrics()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── AQI Severity Legend ───────────────────────────────────────────────────
    _render_aqi_legend()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Station Data Table ────────────────────────────────────────────────────
    st.markdown(
        f"<h4 style='color:{PRIMARY}'>📍 Station Readings</h4>",
        unsafe_allow_html=True,
    )
    render_stub_badge()
    _render_station_table()

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Map placeholder ───────────────────────────────────────────────────────
    st.markdown(
        f"<h4 style='color:{PRIMARY}'>🗺️ Spatial Distribution</h4>",
        unsafe_allow_html=True,
    )
    render_coming_soon(
        "Interactive Station Map",
        planned_day="Day 3",
        features=[
            "Choropleth map of AQI across India",
            "Station markers with click-to-detail popups",
            "Toggle: satellite imagery / road / terrain base layers",
            "Animation player for 24-hour AQI evolution",
        ],
    )

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Time series placeholder ───────────────────────────────────────────────
    st.markdown(
        f"<h4 style='color:{PRIMARY}'>📈 AQI Time Series</h4>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='font-size:0.82rem;color:{TEXT_MUTED};margin-bottom:8px'>"
        "Chart skeleton shown below — live Plotly chart in Day 3</div>",
        unsafe_allow_html=True,
    )
    render_skeleton_chart(height_px=280)

    render_page_footer()


def _render_filters() -> None:
    """Render region, date range, and pollutant filter controls."""
    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        st.selectbox("🌍 Region", ["India", "North India", "South India", "East India", "West India"], key="aqi_region")
    with c2:
        st.selectbox("📅 Date Range", ["Today", "Last 7 days", "Last 30 days", "Custom"], key="aqi_date_range")
    with c3:
        st.selectbox("💨 Pollutant", ["AQI (Overall)", "PM2.5", "PM10", "NO2", "SO2", "CO", "O3"], key="aqi_pollutant")


def _render_summary_metrics() -> None:
    """Render AQI summary KPI cards."""
    summary = surface_aqi_service.get_regional_summary()
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("📊 Avg AQI", f"{summary.avg_aqi:.0f}", "National")
    with c2:
        st.metric("🔺 Max AQI", str(summary.max_aqi), "Severe zone")
    with c3:
        st.metric("🔻 Min AQI", str(summary.min_aqi), "Clean zone")
    with c4:
        st.metric("🏭 Dominant", summary.dominant_pollutant, "Pollutant")
    with c5:
        st.metric("📡 Stations", str(summary.station_count), "Active")


def _render_aqi_legend() -> None:
    """Render the CPCB AQI category colour legend."""
    categories = [
        ("Good",          "0–50",   AQI_GOOD),
        ("Satisfactory",  "51–100", AQI_SATISFACTORY),
        ("Moderate",      "101–200",AQI_MODERATE),
        ("Poor",          "201–300",AQI_POOR),
        ("Very Poor",     "301–400",AQI_VERY_POOR),
        ("Severe",        "401–500",AQI_SEVERE),
    ]
    cols = st.columns(len(categories))
    for col, (label, rng, color) in zip(cols, categories):
        with col:
            st.markdown(
                f"""
                <div style="text-align:center;padding:6px 4px;
                            background:{color}22;border:1px solid {color}66;
                            border-radius:8px">
                  <div style="font-size:0.75rem;font-weight:600;color:{color}">{label}</div>
                  <div style="font-size:0.68rem;color:{TEXT_MUTED}">{rng}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_station_table() -> None:
    """Render the stub station data table."""
    readings = surface_aqi_service.get_latest_readings()
    rows = [
        {
            "Station": r.station_name,
            "AQI": r.aqi_value,
            "Category": r.aqi_category,
            "PM2.5 (µg/m³)": r.pm25,
            "PM10 (µg/m³)": r.pm10,
            "NO2 (µg/m³)": r.no2,
            "O3 (µg/m³)": r.o3,
        }
        for r in readings
    ]
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)
