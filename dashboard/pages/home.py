"""
dashboard/pages/home.py — VAYU-DRISHTI Home / Overview page.

The Home page serves as the mission control overview:
  - Platform introduction and current-day summary KPIs
  - Quick-access status cards for each module
  - Announcement / system status banner
  - Sprint progress and upcoming features
"""

from __future__ import annotations

from datetime import datetime

import streamlit as st

from dashboard.components.empty_state import render_stub_badge
from dashboard.components.error_state import render_info_notice
from dashboard.components.footer import render_page_footer
from dashboard.components.header import render_page_header
from dashboard.core.config import dashboard_config
from dashboard.core.state import navigate_to
from dashboard.core.theme import (
    aqi_category,
    ACCENT_ORANGE,
    AQI_GOOD,
    AQI_MODERATE,
    AQI_VERY_POOR,
    BG_ELEVATED,
    BORDER_DEFAULT,
    PRIMARY,
    STATUS_WARNING,
    TEXT_MUTED,
    TEXT_SECONDARY,
)
from dashboard.services import (
    fire_service,
    forecast_service,
    hcho_service,
    surface_aqi_service,
)
from dashboard.services.data_sources import is_team_data, source_label


def render() -> None:
    """Render the Home overview page."""
    render_page_header(
        module_name="Home",
        subtitle="VAYU-DRISHTI — Satellite-based air-quality intelligence for India (development build)",
    )

    api_reachable = st.session_state.get("api_reachable", False)
    if api_reachable:
        render_info_notice(
            f"Backend connected. Data sources — AQI & stations: {source_label('aqi')}; "
            f"HCHO: {source_label('hcho')}; fire: {source_label('fire')}; "
            f"forecast: {source_label('forecast')}; model: "
            f"{source_label('model') if is_team_data('model') else 'none loaded'}."
        )
    else:
        render_info_notice(
            "⚠️ Backend is offline. Showing built-in offline demo data. "
            "Start the FastAPI backend server to load data from the API."
        )

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Mission Statement ─────────────────────────────────────────────────────
    _render_mission_hero()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── KPI Snapshot ──────────────────────────────────────────────────────────
    st.markdown(
        f"<h3 style='color:{PRIMARY};margin-bottom:4px'>📊 Today's Snapshot</h3>",
        unsafe_allow_html=True,
    )
    if not (is_team_data("aqi") and is_team_data("hcho")):
        render_stub_badge("Includes demo data — see the source list above")
    _render_kpi_cards()

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Module Quick Access ────────────────────────────────────────────────────
    st.markdown(
        f"<h3 style='color:{PRIMARY};margin-bottom:4px'>🧭 Platform Modules</h3>",
        unsafe_allow_html=True,
    )
    _render_module_cards()

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Sprint Progress ───────────────────────────────────────────────────────
    _render_sprint_progress()

    render_page_footer()


def _render_mission_hero() -> None:
    """Render the hero text block describing the platform mission."""
    st.markdown(
        f"""
        <div style="background:linear-gradient(135deg,{PRIMARY}22 0%,{ACCENT_ORANGE}11 100%);
                    border:1px solid {PRIMARY}44;border-radius:16px;padding:28px 32px;
                    margin-bottom:8px">
          <div style="font-size:1.6rem;font-weight:700;color:#E6EDF3;margin-bottom:8px">
            🌐 Atmospheric Knowledge · AQI from Satellite Harmonics
          </div>
          <div style="font-size:0.95rem;color:{TEXT_SECONDARY};line-height:1.7;max-width:780px">
            VAYU-DRISHTI fuses <strong style="color:{PRIMARY}">Sentinel-5P TROPOMI</strong>
            satellite measurements, <strong style="color:{PRIMARY}">MODIS/VIIRS</strong> fire
            radiative power, and <strong style="color:{PRIMARY}">CPCB ground sensors</strong>
            to estimate surface AQI with machine-learning models and explain the predictions —
            supporting evidence-based environmental policy. <em>(In development: the dashboard
            currently shows demo data and a simulated forecast.)</em>
          </div>
          <div style="margin-top:16px;display:flex;gap:12px;flex-wrap:wrap">
            <span style="background:{BG_ELEVATED};border:1px solid {BORDER_DEFAULT};
                         border-radius:20px;padding:4px 12px;font-size:0.75rem;color:{TEXT_SECONDARY}">
              🛰️ Sentinel-5P TROPOMI
            </span>
            <span style="background:{BG_ELEVATED};border:1px solid {BORDER_DEFAULT};
                         border-radius:20px;padding:4px 12px;font-size:0.75rem;color:{TEXT_SECONDARY}">
              🌍 MODIS / VIIRS
            </span>
            <span style="background:{BG_ELEVATED};border:1px solid {BORDER_DEFAULT};
                         border-radius:20px;padding:4px 12px;font-size:0.75rem;color:{TEXT_SECONDARY}">
              📡 CPCB / ERA5
            </span>
            <span style="background:{BG_ELEVATED};border:1px solid {BORDER_DEFAULT};
                         border-radius:20px;padding:4px 12px;font-size:0.75rem;color:{TEXT_SECONDARY}">
              🧠 ML + SHAP (in development)
            </span>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_kpi_cards() -> None:
    """Render top-level KPI metric cards from the backend (currently demo data)."""
    summary = surface_aqi_service.get_regional_summary()
    fires = fire_service.get_active_fires()
    alerts = fire_service.get_active_alerts()
    hotspots = hcho_service.get_hotspots()
    stations = forecast_service.get_stations()
    metrics = forecast_service.get_model_metrics(stations[0]["station_id"]) if stations else None

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric(
            label="🌫️ National Avg AQI",
            value=f"{summary.avg_aqi:.0f}",
            delta=aqi_category(summary.avg_aqi) if summary.station_count else None,
            delta_color="off",
        )
        st.caption(f"Across {summary.station_count} stations · {source_label('aqi')}")

    with c2:
        st.metric(
            label="🔥 Active Fire Events",
            value=str(len(fires)),
            delta=f"{len(alerts)} alerts",
            delta_color="inverse",
        )
        st.caption(f"Last 24 hours · {source_label('fire')}")

    with c3:
        st.metric(
            label="⚗️ HCHO Hotspots",
            value=str(len(hotspots)),
        )
        st.caption(f"Confidence ≥ 60% or unscored · {source_label('hcho')}")

    with c4:
        r2 = metrics.r_squared if metrics else None
        st.metric(
            label="🧠 Forecast R²",
            value="N/A" if r2 is None else f"{r2:.2f}",
        )
        st.caption(metrics.model_name if metrics else "Forecast unavailable")


def _render_module_cards() -> None:
    """Render clickable module quick-access cards in a 2-row grid."""
    modules = [
        {
            "name": "Surface AQI",
            "icon": "🌫️",
            "color": AQI_VERY_POOR,
            "description": "Station AQI readings with pollutant breakdown, map and category distribution. Source: " + source_label("aqi") + "; trend charts are simulated.",
            "status": "Team data" if is_team_data("aqi") else "Demo data",
        },
        {
            "name": "HCHO Hotspots",
            "icon": "⚗️",
            "color": PRIMARY,
            "description": "Formaldehyde (HCHO) hotspot map and table. Source: " + source_label("hcho") + "; source attribution and monthly trend are illustrative.",
            "status": "Team data" if is_team_data("hcho") else "Demo data",
        },
        {
            "name": "Fire Monitoring",
            "icon": "🔥",
            "color": ACCENT_ORANGE,
            "description": "Fire detections with Fire Radiative Power, filterable by region, satellite and FRP. Currently demo events and illustrative alerts.",
            "status": "Demo data",
        },
        {
            "name": "AQI Forecast",
            "icon": "📈",
            "color": AQI_GOOD,
            "description": "Up to 72-hour station AQI outlook. Simulated baseline until a forecasting model is integrated; no accuracy metrics yet.",
            "status": "Simulated",
        },
        {
            "name": "Explainable AI",
            "icon": "🧠",
            "color": STATUS_WARNING,
            "description": ("Trained-model metrics and feature importances from the model artefact, plus illustrative SHAP examples."
                            if is_team_data("model") else
                            "SHAP-style feature contributions and what-if scenarios. Currently hardcoded illustrative examples, not model output."),
            "status": "Stub",
        },
        {
            "name": "Reports",
            "icon": "📋",
            "color": AQI_MODERATE,
            "description": "Report list and generation form. Placeholder only — report generation and exports are not implemented yet.",
            "status": "Stub",
        },
    ]

    col1, col2, col3 = st.columns(3)
    cols = [col1, col2, col3]

    for idx, mod in enumerate(modules):
        with cols[idx % 3]:
            _render_single_module_card(mod)
            st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)


def _render_single_module_card(mod: dict) -> None:
    """Render a single module quick-access card."""
    color = mod["color"]
    st.markdown(
        f"""
        <div style="background:{BG_ELEVATED};border:1px solid {BORDER_DEFAULT};
                    border-top:3px solid {color};border-radius:12px;
                    padding:16px 18px;height:148px;
                    transition:transform 0.18s,box-shadow 0.18s">
          <div style="display:flex;align-items:center;gap:8px;margin-bottom:8px">
            <span style="font-size:1.4rem">{mod['icon']}</span>
            <div style="font-size:0.95rem;font-weight:600;color:#E6EDF3">{mod['name']}</div>
            <span style="margin-left:auto;font-size:0.65rem;background:{color}22;
                         color:{color};border-radius:10px;padding:2px 8px">
              {mod['status']}
            </span>
          </div>
          <div style="font-size:0.78rem;color:{TEXT_MUTED};line-height:1.55">
            {mod['description']}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if st.button(f"Open {mod['name']}", key=f"home_nav_{mod['name']}", width="stretch"):
        navigate_to(mod["name"])
        st.rerun()


def _render_sprint_progress() -> None:
    """Render the sprint/roadmap progress tracker."""
    st.markdown(
        f"<h3 style='color:{PRIMARY};margin-bottom:4px'>📅 Sprint Roadmap</h3>",
        unsafe_allow_html=True,
    )

    days = [
        ("Day 1", "Backend Foundation",    "✅ Complete", AQI_GOOD,    "FastAPI, PostgreSQL, Pydantic Settings, Health/Version endpoints"),
        ("Day 2", "Dashboard Skeleton",     "✅ Complete", AQI_GOOD,    "Streamlit layout, 7-module navigation, service interfaces, stub pages"),
        ("Day 3", "API Endpoints",          "✅ Complete", AQI_GOOD,    "REST endpoints (stub data), API client + caching"),
        ("Day 4", "Charts + GIS Maps",      "✅ Complete", AQI_GOOD,    "Plotly charts, Folium maps, raster-layer interfaces (placeholders), SHAP chart component"),
        ("Day 5", "GIS Layers + Integration", "⏳ Planned", TEXT_MUTED, "Wire real station data and trained-model output into the existing API and maps"),
        ("Day 6", "Database Integration",   "⏳ Planned",  TEXT_MUTED,  "Persist station time series and hotspot geometries in PostgreSQL/PostGIS"),
        ("Day 7", "Reports & Exports",      "⏳ Planned",  TEXT_MUTED,  "PDF summaries, CSV/GeoJSON export endpoints"),
    ]

    for day, title, status, color, detail in days:
        st.markdown(
            f"""
            <div style="display:flex;gap:12px;padding:10px 0;
                        border-bottom:1px solid {BORDER_DEFAULT};align-items:flex-start">
              <div style="min-width:56px;font-size:0.7rem;font-weight:700;color:{color};
                          background:{color}18;border-radius:6px;padding:3px 8px;
                          text-align:center;margin-top:2px">{day}</div>
              <div style="flex:1">
                <div style="font-size:0.88rem;font-weight:600;color:#E6EDF3">{title}
                  <span style="margin-left:8px;font-size:0.72rem;color:{color}">{status}</span>
                </div>
                <div style="font-size:0.75rem;color:{TEXT_MUTED};margin-top:2px">{detail}</div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
