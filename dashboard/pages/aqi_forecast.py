"""
dashboard/pages/aqi_forecast.py — AQI Forecast module page.

Displays 72-hour AQI predictions with confidence intervals and model accuracy.

Day 2 Scope: Stub model metrics, feature importance table, forecast chart skeleton.
Day 3 Scope: Live station selection, Plotly forecast chart with confidence bands.
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
    BG_ELEVATED,
    BORDER_DEFAULT,
    PRIMARY,
    TEXT_MUTED,
    TEXT_SECONDARY,
)
from dashboard.services import forecast_service


def render() -> None:
    """Render the AQI Forecast module page."""
    render_page_header(
        module_name="AQI Forecast",
        subtitle="72-hour AQI predictions with calibrated confidence intervals",
        show_refresh_button=True,
    )

    render_info_notice(
        "ML forecasting model integration arrives in Day 4. "
        "Currently showing stub model metrics and feature importances."
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Forecast Controls ─────────────────────────────────────────────────────
    _render_controls()

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Model Performance KPIs ────────────────────────────────────────────────
    st.markdown(f"<h4 style='color:{PRIMARY}'>📊 Model Performance</h4>", unsafe_allow_html=True)
    render_stub_badge()
    _render_model_metrics()

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Forecast chart placeholder ────────────────────────────────────────────
    st.markdown(f"<h4 style='color:{PRIMARY}'>📈 72-Hour AQI Forecast</h4>", unsafe_allow_html=True)
    render_coming_soon(
        "72-Hour Forecast Chart",
        planned_day="Day 4",
        features=[
            "Multi-step ahead AQI line chart",
            "95% confidence interval shaded bands",
            "Actual vs. predicted overlay for past 24h",
            "Per-hour tooltip with pollutant breakdown",
            "Categorical AQI band background colouring",
        ],
    )

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Feature Importance ────────────────────────────────────────────────────
    left, right = st.columns([3, 2])

    with left:
        st.markdown(f"<h4 style='color:{PRIMARY}'>🔬 Feature Importance</h4>", unsafe_allow_html=True)
        render_stub_badge()
        _render_feature_importance()

    with right:
        st.markdown(f"<h4 style='color:{PRIMARY}'>🗺️ Forecast Coverage Map</h4>", unsafe_allow_html=True)
        render_coming_soon(
            "Forecast Coverage Map",
            planned_day="Day 4",
            features=[
                "Station markers with forecast AQI category colour",
                "Region aggregation toggle",
            ],
        )

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
        st.metric("📅 Last Trained", "—", "Awaiting Day 4")


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
    st.caption("Feature importances from stub data — real SHAP values in Day 4")
