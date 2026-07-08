"""
dashboard/pages/fire_monitoring.py — Fire Monitoring module page.

Displays active fire detections with FRP values and AQI impact scores.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from dashboard.components import (
    render_fire_spatial_map,
    render_fire_count_timeline,
    render_info_notice,
    render_page_header,
    render_page_footer,
)
from dashboard.core.theme import (
    ACCENT_ORANGE,
    PRIMARY,
    STATUS_ERROR,
    TEXT_MUTED,
    TEXT_SECONDARY,
)
from dashboard.services import fire_service


def render() -> None:
    """Render the Fire Monitoring module page."""
    render_page_header(
        module_name="Fire Monitoring",
        subtitle="Active fire detections with Fire Radiative Power from MODIS/VIIRS",
        show_refresh_button=True,
    )

    # ── Active Alerts ─────────────────────────────────────────────────────────
    _render_active_alerts()

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Filters ───────────────────────────────────────────────────────────────
    _render_filters()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Single Data Fetch (Performance Optimization) ──────────────────────────
    min_frp = st.session_state.get("fire_min_frp", 10.0)
    satellite_filter = st.session_state.get("fire_satellite", "All")
    
    all_fires = fire_service.get_active_fires(min_frp=min_frp)
    if satellite_filter != "All":
        fires = [f for f in all_fires if f.satellite == satellite_filter]
    else:
        fires = all_fires

    # ── Fire Summary Metrics ──────────────────────────────────────────────────
    _render_fire_metrics(fires)

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Map and FRP Chart grid ────────────────────────────────────────────────
    left, right = st.columns([3, 2])

    with left:
        st.markdown(f"<h4 style='color:{ACCENT_ORANGE}'>🗺️ Fire Location Map</h4>", unsafe_allow_html=True)
        render_fire_spatial_map(fires, key="fire_spatial_map_widget")

    with right:
        st.markdown(f"<h4 style='color:{ACCENT_ORANGE}'>📊 FRP Distribution & Count</h4>", unsafe_allow_html=True)
        render_fire_count_timeline(fires, title="MODIS/VIIRS Fire Power & Detection Counts")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Fire Events Table ─────────────────────────────────────────────────────
    st.markdown(f"<h4 style='color:{ACCENT_ORANGE}'>🔥 Active Fire Details</h4>", unsafe_allow_html=True)
    _render_fire_table(fires)

    render_page_footer()


def _render_active_alerts() -> None:
    alerts = fire_service.get_active_alerts()
    if not alerts:
        return

    st.markdown(
        f"<div style='font-size:0.9rem;font-weight:600;color:{STATUS_ERROR};margin-bottom:8px'>"
        f"🚨 {len(alerts)} Active Alert{'s' if len(alerts) > 1 else ''}</div>",
        unsafe_allow_html=True,
    )

    for alert in alerts:
        sev_color = STATUS_ERROR if alert.severity == "critical" else ACCENT_ORANGE
        st.markdown(
            f"""
            <div style="background:{sev_color}18;border:1px solid {sev_color}66;
                        border-radius:10px;padding:12px 16px;margin-bottom:8px">
              <div style="display:flex;gap:10px;align-items:flex-start">
                <span style="font-size:1.2rem">
                  {"🔴" if alert.severity == "critical" else "🟠"}
                </span>
                <div>
                  <div style="font-size:0.85rem;font-weight:600;color:{sev_color};margin-bottom:4px">
                    [{alert.severity.upper()}] Fire Alert — Event {alert.fire_event_id}
                  </div>
                  <div style="font-size:0.8rem;color:{TEXT_SECONDARY}">{alert.message}</div>
                  <div style="font-size:0.72rem;color:{TEXT_MUTED};margin-top:4px">
                    Predicted AQI impact: <strong style="color:{ACCENT_ORANGE}">+{alert.aqi_impact_score:.0f}</strong> units
                  </div>
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_filters() -> None:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.selectbox("🌍 Region", ["All India", "North", "South", "East", "West", "Northeast"], key="fire_region")
    with c2:
        st.selectbox("🛰️ Satellite", ["All", "MODIS", "VIIRS-SNPP", "VIIRS-NOAA20"], key="fire_satellite")
    with c3:
        st.slider("⚡ Min FRP (MW)", 0, 500, 10, 10, key="fire_min_frp")


def _render_fire_metrics(fires: list[Any]) -> None:
    total_frp = sum(f.frp for f in fires)
    high_conf = sum(1 for f in fires if f.confidence == "high")
    land_covers = len(set(f.land_cover for f in fires))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("🔥 Active Fires", str(len(fires)), "Selected Detections")
    with c2:
        st.metric("⚡ Total FRP", f"{total_frp:.0f} MW", "Radiative Power")
    with c3:
        st.metric("✅ High Confidence", str(high_conf), "Detections")
    with c4:
        st.metric("🏭 Land Cover Types", str(land_covers), "Forest/Crop/Grass")


def _render_fire_table(fires: list[Any]) -> None:
    rows = [
        {
            "Event ID": f.event_id,
            "State": f.state,
            "District": f.district,
            "FRP (MW)": f.frp,
            "Brightness (K)": f.brightness,
            "Satellite": f.satellite,
            "Confidence": f.confidence,
            "Land Cover": f.land_cover,
        }
        for f in fires
    ]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
