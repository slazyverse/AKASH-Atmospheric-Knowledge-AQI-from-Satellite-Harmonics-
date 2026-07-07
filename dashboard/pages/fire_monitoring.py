"""
dashboard/pages/fire_monitoring.py — Fire Monitoring module page.

Displays active fire detections with FRP values and AQI impact scores.

Day 2 Scope: Active fire table, alert banners, FRP metrics, map/chart stubs.
Day 3 Scope: Live MODIS/VIIRS data, interactive fire map, trajectory forecasting.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components.empty_state import render_coming_soon, render_stub_badge
from dashboard.components.error_state import render_info_notice, render_inline_warning
from dashboard.components.footer import render_page_footer
from dashboard.components.header import render_page_header
from dashboard.components.loading import render_skeleton_chart
from dashboard.core.theme import (
    ACCENT_ORANGE,
    BG_ELEVATED,
    BORDER_DEFAULT,
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

    render_info_notice("Live satellite fire data arrives in Day 3. Displaying 4 stub fire events and 2 alerts.")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Active Alerts ─────────────────────────────────────────────────────────
    _render_active_alerts()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Filters ───────────────────────────────────────────────────────────────
    _render_filters()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Fire Summary Metrics ──────────────────────────────────────────────────
    _render_fire_metrics()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Fire Events Table ─────────────────────────────────────────────────────
    st.markdown(f"<h4 style='color:{ACCENT_ORANGE}'>🔥 Active Fire Events</h4>", unsafe_allow_html=True)
    render_stub_badge()
    _render_fire_table()

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Map and FRP Chart placeholders ────────────────────────────────────────
    left, right = st.columns([3, 2])

    with left:
        st.markdown(f"<h4 style='color:{ACCENT_ORANGE}'>🗺️ Fire Location Map</h4>", unsafe_allow_html=True)
        render_coming_soon(
            "Active Fire Map",
            planned_day="Day 3",
            features=[
                "MODIS/VIIRS active fire points coloured by FRP intensity",
                "Smoke trajectory overlay (HYSPLIT)",
                "Affected AQI station radius circles",
                "Satellite base layer (true colour / thermal IR)",
            ],
        )

    with right:
        st.markdown(f"<h4 style='color:{ACCENT_ORANGE}'>📊 FRP Distribution</h4>", unsafe_allow_html=True)
        render_skeleton_chart(height_px=240)

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


def _render_fire_metrics() -> None:
    fires = fire_service.get_active_fires()
    total_frp = sum(f.frp for f in fires)
    high_conf = sum(1 for f in fires if f.confidence == "high")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("🔥 Active Fires", str(len(fires)), "Last 24h")
    with c2:
        st.metric("⚡ Total FRP", f"{total_frp:.0f} MW", "Radiative Power")
    with c3:
        st.metric("✅ High Confidence", str(high_conf), "Detections")
    with c4:
        st.metric("🏭 Land Cover Types", "4", "Forest/Crop/Grass/Shrub")


def _render_fire_table() -> None:
    fires = fire_service.get_active_fires()
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
