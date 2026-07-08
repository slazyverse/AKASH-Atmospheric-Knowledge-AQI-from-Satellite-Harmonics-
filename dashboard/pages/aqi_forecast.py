"""
dashboard/pages/aqi_forecast.py — AQI Forecast module page.

Displays 72-hour AQI predictions with confidence intervals and model accuracy.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components import (
    render_forecast_line_chart,
    render_forecast_coverage_map,
    render_info_notice,
    render_page_header,
    render_page_footer,
    render_no_data,
)
from dashboard.core.theme import (
    PRIMARY,
    TEXT_MUTED,
)
from dashboard.services import forecast_service, surface_aqi_service

# Map station display names to their service station IDs
_STATION_IDS = {
    "Delhi – Anand Vihar": "DL001",
    "Mumbai – Bandra Kurla": "MU001",
    "Bengaluru – Silk Board": "BL001",
}


def render() -> None:
    """Render the AQI Forecast module page."""
    render_page_header(
        module_name="AQI Forecast",
        subtitle="72-hour AQI predictions with calibrated confidence intervals",
        show_refresh_button=True,
    )

    # ── Forecast Controls ─────────────────────────────────────────────────────
    _render_controls()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # Resolve active selected station ID
    selected_name = st.session_state.get("fc_station", "Delhi – Anand Vihar")
    selected_id = _STATION_IDS.get(selected_name, "DL001")
    
    # Resolve horizon hours
    horizon_sel = st.session_state.get("fc_horizon", "72 hours")
    horizon_hours = 72
    if "24" in horizon_sel:
        horizon_hours = 24
    elif "48" in horizon_sel:
        horizon_hours = 48

    # ── Single Data Fetch ─────────────────────────────────────────────────────
    forecast_steps = forecast_service.get_station_forecast(
        station_id=selected_id,
        horizon_hours=horizon_hours
    )
    readings = surface_aqi_service.get_latest_readings()

    # ── Model Performance KPIs ────────────────────────────────────────────────
    st.markdown(f"<h4 style='color:{PRIMARY}'>📊 Model Performance</h4>", unsafe_allow_html=True)
    _render_model_metrics()

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Forecast chart ────────────────────────────────────────────────────────
    st.markdown(f"<h4 style='color:{PRIMARY}'>📈 {horizon_hours}-Hour AQI Forecast</h4>", unsafe_allow_html=True)
    render_forecast_line_chart(forecast_steps, title=f"Predictions: {selected_name}")

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Feature Importance and Coverage Map ───────────────────────────────────
    left, right = st.columns([3, 2])

    with left:
        st.markdown(f"<h4 style='color:{PRIMARY}'>🔬 Feature Importance</h4>", unsafe_allow_html=True)
        _render_feature_importance()

    with right:
        st.markdown(f"<h4 style='color:{PRIMARY}'>🗺️ Forecast Coverage Map</h4>", unsafe_allow_html=True)
        render_forecast_coverage_map(readings, key="forecast_coverage_map_widget")

    render_page_footer()


def _render_controls() -> None:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.selectbox("📍 Station", ["Delhi – Anand Vihar", "Mumbai – Bandra Kurla", "Bengaluru – Silk Board"], key="fc_station")
    with c2:
        st.selectbox("⏱ Horizon", ["24 hours", "48 hours", "72 hours"], index=2, key="fc_horizon")
    with c3:
        st.selectbox("🧠 Model", ["XGBoost v1 (Active)", "LSTM v0.2 (Experimental)"], key="fc_model")


def _render_model_metrics() -> None:
    metrics = forecast_service.get_model_metrics()
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("🧠 Model", "XGBoost v1", "Active")
    with c2:
        st.metric("📉 RMSE", f"{metrics.rmse:.1f}", "AQI units")
    with c3:
        st.metric("📉 MAE", f"{metrics.mae:.1f}", "AQI units")
    with c4:
        st.metric("📊 R²", f"{metrics.r_squared:.2f}", "Fit quality")
    with c5:
        st.metric("📅 Last Trained", "2026-06-01", "Model Registry")


def _render_feature_importance() -> None:
    features = forecast_service.get_feature_importances()
    df = pd.DataFrame(features).rename(columns={"feature": "Feature", "importance": "Importance"})
    df["Importance %"] = df["Importance"].map(lambda x: f"{x:.0%}")
    df = df.sort_values("Importance", ascending=False).reset_index(drop=True)
    st.dataframe(
        df[["Feature", "Importance %"]],
        use_container_width=True,
        hide_index=True,
    )
    st.caption("SHAP global feature importances calculated across validation dataset.")
