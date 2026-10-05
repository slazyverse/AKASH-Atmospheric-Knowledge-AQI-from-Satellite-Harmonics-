"""
dashboard/pages/surface_aqi.py — Surface AQI module page.

Displays station AQI readings and each station's observed history from the
backend. The source (team dataset or labelled placeholder fixture) is shown
from GET /api/v1/sources; nothing on this page is generated client-side.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from dashboard.components import (
    render_aqi_category_distribution,
    render_aqi_spatial_map,
    render_aqi_time_series,
    render_map_withheld,
    render_no_data,
    render_page_footer,
    render_page_header,
    render_pollutant_trend_comparison,
    render_source_badge,
)
from dashboard.core.theme import (
    AQI_GOOD,
    AQI_MODERATE,
    AQI_POOR,
    AQI_SATISFACTORY,
    AQI_SEVERE,
    AQI_VERY_POOR,
    PRIMARY,
    TEXT_MUTED,
    aqi_category,
)
from dashboard.services import surface_aqi_service
from dashboard.services.data_sources import has_limitation, source_label

_TREND_WINDOWS = {"Last 7 days": 7, "Last 30 days": 30, "Last 90 days": 90}


def _history_frame(points: list[Any]) -> pd.DataFrame:
    """Observed history → chart frame (missing pollutants stay NaN, never filled)."""
    return pd.DataFrame([
        {
            "recorded_at": p.recorded_at,
            "aqi_value": p.aqi_value,
            "PM2.5": p.pm25, "PM10": p.pm10, "NO2": p.no2,
            "SO2": p.so2, "O3": p.o3, "CO": p.co,
        }
        for p in points
    ])


def render() -> None:
    """Render the Surface AQI module page."""
    render_page_header(
        module_name="Surface AQI",
        subtitle=f"Station AQI readings — source: {source_label('aqi')}",
        show_refresh_button=True,
        show_export_button=True,
    )
    render_source_badge("aqi", "Station data")

    # ── Single Data Fetch ─────────────────────────────────────────────────────
    selected_region = st.session_state.get("aqi_region", "India")
    readings = surface_aqi_service.get_latest_readings(region=selected_region)

    # ── Summary KPIs ──────────────────────────────────────────────────────────
    _render_summary_metrics(selected_region)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Filters row ───────────────────────────────────────────────────────────
    _render_filters()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── AQI Severity Legend ───────────────────────────────────────────────────
    _render_aqi_legend()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Map Section ───────────────────────────────────────────────────────────
    st.markdown(f"<h4 style='color:{PRIMARY}'>🗺️ Spatial Distribution</h4>", unsafe_allow_html=True)
    if not render_map_withheld("aqi", "Station map"):
        render_aqi_spatial_map(readings, key="surface_aqi_map_widget")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Station Data Table ────────────────────────────────────────────────────
    st.markdown(f"<h4 style='color:{PRIMARY}'>📍 Station Readings</h4>", unsafe_allow_html=True)
    if readings:
        _render_station_table(readings)
    else:
        render_no_data(
            title="No Station Readings",
            message="No data for this region, or the data source / backend is unavailable.",
        )

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Observed history & analysis ───────────────────────────────────────────
    st.markdown(f"<h4 style='color:{PRIMARY}'>📈 Station History & Analysis</h4>", unsafe_allow_html=True)
    if not readings:
        render_no_data(title="Analysis Unavailable", message="No active stations found in this region.")
        render_page_footer()
        return

    # Keyed by station ID: station names are not guaranteed unique across networks
    by_id = {r.station_id: r for r in readings}
    c1, _ = st.columns([2, 4])
    with c1:
        selected_id = st.selectbox(
            "Select Station for Temporal Analysis", list(by_id), key="aqi_analysis_station",
            format_func=lambda sid: f"{by_id[sid].station_name} ({sid})",
        )
    station = by_id.get(selected_id, readings[0])
    selected_station = station.station_name
    days = _TREND_WINDOWS[st.session_state.get("aqi_trend_window", "Last 30 days")]
    history = surface_aqi_service.get_time_series(station.station_id, days=days)
    history_df = _history_frame(history)
    st.caption(
        f"{len(history)} observation(s) from the data source ({source_label('aqi')}). "
        "Missing pollutant values are gaps, not zeros. Nothing here is simulated."
    )

    tab1, tab2, tab3 = st.tabs(["AQI History", "Pollutant History", "Regional Distribution"])
    with tab1:
        render_aqi_time_series(history_df, title=f"Observed AQI: {selected_station}")
    with tab2:
        render_pollutant_trend_comparison(history_df, title=f"Observed Pollutants: {selected_station}")
    with tab3:
        distribution_df = pd.DataFrame([{"Category": r.aqi_category} for r in readings])
        render_aqi_category_distribution(
            distribution_df,
            category_col="Category",
            title=f"CPCB Category Count ({selected_region})",
        )

    render_page_footer()


def _render_filters() -> None:
    """Render region, history-window and pollutant controls."""
    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        st.selectbox(
            "🌍 Region",
            ["India", "North India", "Central India", "East India",
             "Northeast India", "West India", "South India"],
            key="aqi_region",
        )
    with c2:
        st.selectbox(
            "📅 History window", list(_TREND_WINDOWS), index=1, key="aqi_trend_window",
            help="Window for the station history charts, ending at the source's latest date.",
        )
    with c3:
        st.selectbox(
            "💨 Pollutant", ["AQI (Overall)"], key="aqi_pollutant", disabled=True,
            help="Per-pollutant maps are not implemented; see the table and history charts.",
        )


def _render_summary_metrics(region: str) -> None:
    """Render AQI summary KPI cards."""
    summary = surface_aqi_service.get_regional_summary(region=region)
    has_data = summary.station_count > 0
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("📊 Avg AQI", f"{summary.avg_aqi:.0f}" if has_data else "N/A", region,
                  delta_color="off")
    with c2:
        st.metric("🔺 Max AQI", str(summary.max_aqi) if has_data else "N/A",
                  aqi_category(summary.max_aqi) if has_data else None, delta_color="off")
    with c3:
        st.metric("🔻 Min AQI", str(summary.min_aqi) if has_data else "N/A",
                  aqi_category(summary.min_aqi) if has_data else None, delta_color="off")
    with c4:
        st.metric("🏭 Dominant", summary.dominant_pollutant, "not computed", delta_color="off")
    with c5:
        as_of = str(summary.date_to) if summary.date_to else None
        st.metric("📡 Stations", str(summary.station_count), as_of, delta_color="off")


def _render_aqi_legend() -> None:
    """Render the CPCB AQI category colour legend."""
    categories = [
        ("Good",          "0–50",   AQI_GOOD),
        ("Satisfactory",  "51–100", AQI_SATISFACTORY),
        ("Moderate",      "101–200", AQI_MODERATE),
        ("Poor",          "201–300", AQI_POOR),
        ("Very Poor",     "301–400", AQI_VERY_POOR),
        ("Severe",        "401–500", AQI_SEVERE),
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


def _render_station_table(readings: list[Any]) -> None:
    """Render the station data table (missing pollutants shown as empty)."""
    co_label = "CO (unit unverified)" if has_limitation("aqi", "co_unit_unverified") else "CO (mg/m³)"
    rows = [
        {
            "Station": r.station_name,
            "AQI": r.aqi_value,
            "Category": r.aqi_category,
            "PM2.5 (µg/m³)": r.pm25,
            "PM10 (µg/m³)": r.pm10,
            "NO2 (µg/m³)": r.no2,
            "SO2 (µg/m³)": r.so2,
            co_label: r.co,
            "O3 (µg/m³)": r.o3,
            "Observed": r.recorded_at.strftime("%Y-%m-%d %H:%M"),
            "Location": r.location_quality,
        }
        for r in readings
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
