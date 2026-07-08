"""
dashboard/pages/hcho_hotspots.py — HCHO Hotspot Detection module page.

Displays formaldehyde (HCHO) column density hotspots derived from Sentinel-5P.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
import pandas as pd
import streamlit as st

from dashboard.components import (
    render_hcho_spatial_map,
    render_source_attribution_donut,
    render_daily_hcho_trend,
    render_info_notice,
    render_page_header,
    render_page_footer,
    render_no_data,
)
from dashboard.core.theme import (
    PRIMARY,
    TEXT_MUTED,
    TEXT_SECONDARY,
)
from dashboard.services import hcho_service


def _generate_mock_hcho_trends() -> pd.DataFrame:
    """Generate mock 12-month HCHO column density trends."""
    import numpy as np
    dates = pd.date_range(end=datetime.utcnow(), periods=12, freq="ME")
    rng = np.random.default_rng(88)
    data = []
    baseline = 11.2
    for idx, dt in enumerate(dates):
        # Seasonal peak in summer due to biogenic activity
        seasonal = 2.4 * np.sin(2 * np.pi * (idx + 3) / 12)
        density = max(1.0, baseline + seasonal + rng.normal(0, 0.6))
        data.append({
            "date": dt.strftime("%Y-%m"),
            "column_density": density
        })
    return pd.DataFrame(data)


def render() -> None:
    """Render the HCHO Hotspots module page."""
    render_page_header(
        module_name="HCHO Hotspots",
        subtitle="Formaldehyde column density hotspots from Sentinel-5P TROPOMI",
        show_refresh_button=True,
    )

    # ── Filters ───────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        st.selectbox("📅 Date", ["Today", "Last 7 days", "Last 30 days"], key="hcho_date")
    with c2:
        st.selectbox("🏭 Source Type", ["All", "Industrial", "Biogenic", "Biomass Burning"], key="hcho_source")
    with c3:
        st.slider("🎯 Min Confidence", 0.5, 1.0, 0.6, 0.05, key="hcho_confidence")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Single Data Fetch ─────────────────────────────────────────────────────
    min_conf = st.session_state.get("hcho_confidence", 0.6)
    source_filter = st.session_state.get("hcho_source", "All")
    
    all_hotspots = hcho_service.get_hotspots(min_confidence=min_conf)
    if source_filter != "All":
        hotspots = [h for h in all_hotspots if h.source_type.replace("_", " ").title() == source_filter]
    else:
        hotspots = all_hotspots

    # ── Hotspot summary metrics ────────────────────────────────────────────────
    _render_hotspot_metrics(hotspots)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── What is HCHO? ─────────────────────────────────────────────────────────
    _render_hcho_explainer()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Map & Attribution Grid ────────────────────────────────────────────────
    left, right = st.columns([3, 2])

    with left:
        st.markdown(f"<h4 style='color:{PRIMARY}'>🗺️ HCHO Density Map</h4>", unsafe_allow_html=True)
        render_hcho_spatial_map(hotspots, key="hcho_spatial_map_widget")

    with right:
        st.markdown(f"<h4 style='color:{PRIMARY}'>📊 Source Attribution</h4>", unsafe_allow_html=True)
        hotspot_ids = [h.hotspot_id for h in hotspots]
        if hotspot_ids:
            selected_hotspot = st.selectbox(
                "Select Hotspot for Profile", 
                hotspot_ids, 
                key="hcho_attribution_select"
            )
            attribution_data = hcho_service.get_source_attribution(selected_hotspot)
            render_source_attribution_donut(attribution_data, title=f"Source Attribution: {selected_hotspot}")
        else:
            render_no_data(
                title="Attribution Unavailable",
                message="Select different filter settings to display source breakdown.",
            )

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Hotspot table ─────────────────────────────────────────────────────────
    st.markdown(f"<h4 style='color:{PRIMARY}'>⚗️ Active Hotspot Details</h4>", unsafe_allow_html=True)
    _render_hotspot_table(hotspots)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Trend chart ───────────────────────────────────────────────────────────
    st.markdown(f"<h4 style='color:{PRIMARY}'>📈 Monthly HCHO Trend</h4>", unsafe_allow_html=True)
    trend_df = _generate_mock_hcho_trends()
    render_daily_hcho_trend(trend_df, title="12-Month Mean Formaldehyde Column Density (India)")

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


def _render_hotspot_metrics(hotspots: list[Any]) -> None:
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


def _render_hotspot_table(hotspots: list[Any]) -> None:
    rows = [
        {
            "ID": h.hotspot_id,
            "Latitude": h.latitude,
            "Longitude": h.longitude,
            "Column Density (×10¹⁵)": h.column_density,
            "Radius (km)": h.radius_km,
            "Source Type": h.source_type.replace("_", " ").title(),
            "Confidence": f"{h.confidence:.0%}",
        }
        for h in hotspots
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
