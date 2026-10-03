"""
dashboard/pages/surface_aqi.py — Surface AQI module page.

Displays station AQI readings from the backend (currently static demo data).
The 30-day trend charts are SIMULATED from the latest reading — not real history.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
import pandas as pd
import streamlit as st

from dashboard.components import (
    render_aqi_spatial_map,
    render_aqi_time_series,
    render_pollutant_trend_comparison,
    render_aqi_category_distribution,
    render_info_notice,
    render_inline_warning,
    render_page_header,
    render_page_footer,
    render_no_data,
)
from dashboard.core.theme import (
    aqi_category,
    AQI_GOOD,
    AQI_MODERATE,
    AQI_POOR,
    AQI_SATISFACTORY,
    AQI_SEVERE,
    AQI_VERY_POOR,
    PRIMARY,
    TEXT_MUTED,
    TEXT_SECONDARY,
)
from dashboard.services import surface_aqi_service
from dashboard.services.data_sources import is_team_data, source_label


def _generate_mock_history(reading: Any, days: int = 7) -> pd.DataFrame:
    """SIMULATED history: a seeded random walk from the latest reading (not real data)."""
    import numpy as np
    
    # Deterministic generation per station to prevent jumpy charts on rerun
    seed_val = hash(reading.station_id) % 10000
    rng = np.random.default_rng(seed_val)
    
    dates = [datetime.utcnow() - timedelta(days=d) for d in range(days)]
    dates.reverse()
    
    data = []
    # Simple random walk starting from latest reading
    curr_aqi = reading.aqi_value
    curr_pm25 = reading.pm25
    curr_pm10 = reading.pm10
    curr_no2 = reading.no2
    curr_so2 = reading.so2
    curr_o3 = reading.o3
    curr_co = reading.co
    
    def step(value, sd, lo, hi):
        # A pollutant the station did not report stays missing (no simulated series)
        return None if value is None else max(lo, min(hi, value + rng.normal(0, sd)))

    for dt in dates:
        curr_aqi = max(10, min(500, int(curr_aqi + rng.normal(0, 15))))
        curr_pm25 = step(curr_pm25, 8, 5.0, 350.0)
        curr_pm10 = step(curr_pm10, 12, 10.0, 500.0)
        curr_no2 = step(curr_no2, 4, 2.0, 150.0)
        curr_so2 = step(curr_so2, 2, 1.0, 80.0)
        curr_o3 = step(curr_o3, 5, 5.0, 180.0)
        curr_co = step(curr_co, 0.1, 0.1, 10.0)
        
        data.append({
            "recorded_at": dt,
            "aqi_value": curr_aqi,
            "PM2.5": curr_pm25,
            "PM10": curr_pm10,
            "NO2": curr_no2,
            "SO2": curr_so2,
            "O3": curr_o3,
            "CO": curr_co
        })
    return pd.DataFrame(data)


def render() -> None:
    """Render the Surface AQI module page."""
    render_page_header(
        module_name="Surface AQI",
        subtitle=(
            f"Station AQI readings — {source_label('aqi')}"
            if is_team_data("aqi")
            else "Station AQI readings — currently static demo data, not live CPCB measurements"
        ),
        show_refresh_button=True,
        show_export_button=True,
    )

    # ── Single Data Fetch (Performance Optimization) ──────────────────────────
    # Sourced from region filter context
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
    st.markdown(
        f"<h4 style='color:{PRIMARY}'>🗺️ Spatial Distribution</h4>",
        unsafe_allow_html=True,
    )
    render_aqi_spatial_map(readings, key="surface_aqi_map_widget")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Station Data Table ────────────────────────────────────────────────────
    st.markdown(
        f"<h4 style='color:{PRIMARY}'>📍 Station Readings</h4>",
        unsafe_allow_html=True,
    )
    _render_station_table(readings)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Time series & Analysis Section ────────────────────────────────────────
    st.markdown(
        f"<h4 style='color:{PRIMARY}'>📈 Station Analysis & Trends</h4>",
        unsafe_allow_html=True,
    )
    
    # Station Selector for Drilldown
    station_names = [r.station_name for r in readings]
    if station_names:
        c1, _ = st.columns([2, 4])
        with c1:
            selected_station = st.selectbox(
                "Select Station for Temporal Analysis",
                station_names,
                key="aqi_analysis_station"
            )
        
        # Locate active reading
        active_reading = next(
            (r for r in readings if r.station_name == selected_station),
            readings[0]
        )
        
        # Simulated trend history (no historical data is integrated yet)
        history_df = _generate_mock_history(active_reading, days=30)
        render_inline_warning(
            "The AQI and pollutant trend charts below are SIMULATED (a seeded random walk "
            "from the latest reading). They are not real historical measurements."
        )
        
        # Render Tabs for different trends
        tab1, tab2, tab3 = st.tabs(["AQI Trend", "Pollutant Trends", "Regional Distribution"])
        with tab1:
            render_aqi_time_series(history_df, title=f"Simulated 30-Day AQI Trend (demo): {selected_station}")
        with tab2:
            render_pollutant_trend_comparison(history_df, title=f"Simulated Pollutant Trends (demo): {selected_station}")
        with tab3:
            # Show CPCB categories for all loaded stations in this region
            distribution_df = pd.DataFrame([{"Category": r.aqi_category} for r in readings])
            render_aqi_category_distribution(
                distribution_df,
                category_col="Category",
                title=f"CPCB Category Count ({selected_region} Network)"
            )
    else:
        render_no_data(title="Analysis Unavailable", message="No active stations found in this region.")

    render_page_footer()


def _render_filters() -> None:
    """Render region, date range, and pollutant filter controls."""
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
            "📅 Date Range", ["Today"], key="aqi_date_range", disabled=True,
            help="Only the latest snapshot is available until historical data is integrated.",
        )
    with c3:
        st.selectbox(
            "💨 Pollutant", ["AQI (Overall)"], key="aqi_pollutant", disabled=True,
            help="Per-pollutant views are not implemented yet; see the table for pollutant values.",
        )


def _render_summary_metrics(region: str) -> None:
    """Render AQI summary KPI cards."""
    summary = surface_aqi_service.get_regional_summary(region=region)
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("📊 Avg AQI", f"{summary.avg_aqi:.0f}", region)
    has_data = summary.station_count > 0
    with c2:
        st.metric("🔺 Max AQI", str(summary.max_aqi),
                  aqi_category(summary.max_aqi) if has_data else None, delta_color="off")
    with c3:
        st.metric("🔻 Min AQI", str(summary.min_aqi),
                  aqi_category(summary.min_aqi) if has_data else None, delta_color="off")
    with c4:
        st.metric("🏭 Dominant", summary.dominant_pollutant, "Pollutant", delta_color="off")
    with c5:
        st.metric("📡 Stations", str(summary.station_count),
                  "Team dataset" if is_team_data("aqi") else "Demo data", delta_color="off")


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


def _render_station_table(readings: list[Any]) -> None:
    """Render the station data table."""
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
    st.dataframe(df, width="stretch", hide_index=True)
