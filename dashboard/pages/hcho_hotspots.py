"""
dashboard/pages/hcho_hotspots.py — HCHO Hotspots module page.

Displays HCHO hotspot clusters (team cluster_summary.json or its labelled
placeholder) and the daily station-collocated HCHO mean from the station
dataset. Source attribution, radius and confidence are not produced by any
team output, so they are shown as unavailable — never invented.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from dashboard.components import (
    render_daily_hcho_trend,
    render_hcho_spatial_map,
    render_map_withheld,
    render_info_notice,
    render_no_data,
    render_page_footer,
    render_page_header,
    render_source_badge,
)
from dashboard.core.theme import PRIMARY, TEXT_SECONDARY
from dashboard.services import hcho_service
from dashboard.services.data_sources import source_label


def render() -> None:
    """Render the HCHO Hotspots module page."""
    render_page_header(
        module_name="HCHO Hotspots",
        subtitle=f"Formaldehyde (HCHO) hotspot clusters — source: {source_label('hcho')}",
        show_refresh_button=True,
    )
    render_source_badge("hcho", "Hotspot clusters")

    # ── Filters ───────────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    with c1:
        st.selectbox(
            "📅 Date", ["Latest snapshot"], key="hcho_date", disabled=True,
            help="The hotspot contract carries no observation date; only the latest snapshot exists.",
        )
    with c2:
        st.selectbox(
            "🏭 Source Type", ["All", "Industrial", "Biogenic", "Biomass Burning", "Unknown"],
            key="hcho_source",
        )
    with c3:
        st.slider(
            "🎯 Min Confidence", 0.5, 1.0, 0.6, 0.05, key="hcho_confidence",
            help="Applies only to scored clusters; unscored clusters are always shown.",
        )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Single Data Fetch ─────────────────────────────────────────────────────
    min_conf = st.session_state.get("hcho_confidence", 0.6)
    source_filter = st.session_state.get("hcho_source", "All")
    all_hotspots = hcho_service.get_hotspots(min_confidence=min_conf)
    hotspots = (
        all_hotspots if source_filter == "All"
        else [h for h in all_hotspots if h.source_type.replace("_", " ").title() == source_filter]
    )

    _render_hotspot_metrics(hotspots)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)
    _render_hcho_explainer()
    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Map & Attribution Grid ────────────────────────────────────────────────
    left, right = st.columns([3, 2])
    with left:
        st.markdown(f"<h4 style='color:{PRIMARY}'>🗺️ HCHO Hotspot Map</h4>", unsafe_allow_html=True)
        if not render_map_withheld("hcho", "Hotspot map"):
            render_hcho_spatial_map(hotspots, key="hcho_spatial_map_widget")
    with right:
        st.markdown(f"<h4 style='color:{PRIMARY}'>📊 Source Attribution</h4>", unsafe_allow_html=True)
        render_info_notice(
            "Unavailable: no source-attribution output exists (the HCHO/NO₂ ratio "
            "classification and HYSPLIT back-trajectories are not implemented). "
            "Cluster source type is reported as 'unknown'."
        )

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Hotspot table ─────────────────────────────────────────────────────────
    st.markdown(f"<h4 style='color:{PRIMARY}'>⚗️ Hotspot Cluster Details</h4>", unsafe_allow_html=True)
    if hotspots:
        _render_hotspot_table(hotspots)
    else:
        render_no_data(
            title="No Hotspots",
            message="No clusters match, or the hotspot source / backend is unavailable.",
        )

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Station-collocated HCHO trend (from the station dataset) ──────────────
    st.markdown(f"<h4 style='color:{PRIMARY}'>📈 HCHO at Stations — Daily Mean</h4>", unsafe_allow_html=True)
    render_source_badge("hcho_trend", "Trend source (station dataset)")
    trend = hcho_service.get_trend(days=30)
    trend_df = pd.DataFrame(
        [{"date": p.obs_date, "column_density": p.mean_column_density} for p in trend]
    )
    render_daily_hcho_trend(trend_df, title="Daily mean satellite HCHO column at stations (×10¹⁵ molec/cm²)")
    if trend:
        basis = ("satellite overpass date" if trend[0].date_basis == "satellite_observation_date"
                 else "station observation date")
        per_day = ", ".join(f"{p.location_count} loc / {p.station_count} stn" for p in trend)
        st.caption(
            f"{len(trend)} day(s), dated by {basis}; distinct sampling locations / stations per "
            f"day: {per_day}. Each location counts once. Satellite column sampled at station "
            "coordinates — not a gridded national mean."
        )

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
        st.metric("⚗️ Hotspot Clusters", str(len(hotspots)))
    with c2:
        avg_density = sum(h.column_density for h in hotspots) / len(hotspots) if hotspots else None
        st.metric("📊 Avg Column Density", "N/A" if avg_density is None else f"{avg_density:.1f}",
                  "×10¹⁵ molec/cm²", delta_color="off")
    with c3:
        known = [h for h in hotspots if h.source_type != "unknown"]
        st.metric("🏭 Attributed Sources", str(len(known)) if known else "N/A",
                  None if known else "not attributed by source", delta_color="off")
    with c4:
        scored = [h for h in hotspots if h.confidence is not None]
        if scored:
            high_conf = sum(1 for h in scored if h.confidence >= 0.85)
            st.metric("✅ High Confidence", str(high_conf), "≥ 0.85", delta_color="off")
        else:
            st.metric("✅ High Confidence", "N/A", "not scored by source", delta_color="off")


def _render_hotspot_table(hotspots: list[Any]) -> None:
    rows = [
        {
            "ID": h.hotspot_id,
            "Latitude": h.latitude,
            "Longitude": h.longitude,
            "Column Density (×10¹⁵)": h.column_density,
            "Radius (km)": h.radius_km,
            "Source Type": h.source_type.replace("_", " ").title(),
            "Confidence": f"{h.confidence:.0%}" if h.confidence is not None else "not scored",
            "Detected": h.detected_at.strftime("%Y-%m-%d") if h.detected_at else "no date in source",
            "Stations": h.station_count,
            "Distinct locations": h.member_locations,
            "Location": h.location_quality,
        }
        for h in hotspots
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
