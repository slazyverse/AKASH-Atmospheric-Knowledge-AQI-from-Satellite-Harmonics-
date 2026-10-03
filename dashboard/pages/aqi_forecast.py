"""
dashboard/pages/aqi_forecast.py — AQI Forecast module page.

Displays the backend's AQI forecast for any registered station. No trained
model is integrated yet, so the backend returns a SIMULATED baseline; this page
labels it as such and shows N/A for metrics that do not exist.
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
    render_source_badge,
)
from dashboard.core.theme import PRIMARY
from dashboard.services import forecast_service, surface_aqi_service
from dashboard.services.data_sources import source_label
from dashboard.services.forecast_service import ModelMetrics

_HORIZONS = {"24 hours": 24, "48 hours": 48, "72 hours": 72}


def render() -> None:
    """Render the AQI Forecast module page."""
    render_page_header(
        module_name="AQI Forecast",
        subtitle="Station AQI outlook — simulated until a forecasting model is integrated",
        show_refresh_button=True,
    )

    stations = forecast_service.get_stations()
    if not stations:
        render_no_data(
            title="Station List Unavailable",
            message="Could not load stations from the backend (GET /api/v1/stations). "
                    "Start the FastAPI backend to view forecasts.",
            icon="📡",
        )
        render_page_footer()
        return

    names = {s["station_id"]: s["station_name"] for s in stations}

    # ── Forecast Controls ─────────────────────────────────────────────────────
    selected_id, horizon_hours = _render_controls(names)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ── Single Data Fetch (one cached GET /forecast) ──────────────────────────
    forecast_steps = forecast_service.get_station_forecast(selected_id, horizon_hours)
    metrics = forecast_service.get_model_metrics(selected_id, horizon_hours)
    info = forecast_service.get_forecast_info(selected_id, horizon_hours)
    readings = surface_aqi_service.get_latest_readings()

    render_source_badge("forecast", "Forecast")
    if info.get("based_on_observation_at"):
        st.caption(
            f"Seeded from the station observation at {info['based_on_observation_at'][:16]} UTC "
            f"(station data: {source_label('aqi')})."
        )
    if info.get("forecast_kind", "simulated") == "simulated":
        render_info_notice(
            "Simulated forecast: no forecasting model is integrated yet. The curve is a "
            "deterministic diurnal baseline seeded from the station's latest AQI reading, "
            "and the shaded band is illustrative — not a calibrated confidence interval."
        )

    # ── Model Performance KPIs ────────────────────────────────────────────────
    st.markdown(f"<h4 style='color:{PRIMARY}'>📊 Model Performance</h4>", unsafe_allow_html=True)
    _render_model_metrics(metrics)

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Forecast chart ────────────────────────────────────────────────────────
    st.markdown(f"<h4 style='color:{PRIMARY}'>📈 {horizon_hours}-Hour AQI Outlook</h4>", unsafe_allow_html=True)
    render_forecast_line_chart(
        forecast_steps,
        title=f"Simulated forecast: {names[selected_id]} ({selected_id})",
    )

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Feature Importance and Coverage Map ───────────────────────────────────
    left, right = st.columns([3, 2])

    with left:
        st.markdown(f"<h4 style='color:{PRIMARY}'>🔬 Feature Importance</h4>", unsafe_allow_html=True)
        _render_feature_importance(selected_id, horizon_hours)

    with right:
        st.markdown(f"<h4 style='color:{PRIMARY}'>🗺️ Station Coverage Map</h4>", unsafe_allow_html=True)
        render_source_badge("aqi", "Stations")
        render_forecast_coverage_map(readings, key="forecast_coverage_map_widget")

    render_page_footer()


def _render_controls(names: dict[str, str]) -> tuple[str, int]:
    """Render station / horizon / model controls; return (station_id, horizon_hours)."""
    station_ids = list(names)
    # Drop a stale selection (e.g. a station that no longer exists) instead of
    # silently substituting another station.
    if st.session_state.get("fc_station") not in station_ids:
        st.session_state.pop("fc_station", None)

    c1, c2, c3 = st.columns(3)
    with c1:
        selected_id = st.selectbox(
            "📍 Station",
            station_ids,
            format_func=lambda sid: f"{names[sid]} ({sid})",
            key="fc_station",
        )
    with c2:
        horizon_label = st.selectbox("⏱ Horizon", list(_HORIZONS), index=2, key="fc_horizon")
    with c3:
        st.selectbox(
            "🧠 Model",
            ["Simulated baseline (no forecasting model)"],
            disabled=True,
            help="Model selection becomes available once forecasting models are integrated.",
        )
    return selected_id, _HORIZONS[horizon_label]


def _fmt(value: float | None, spec: str) -> str:
    return "N/A" if value is None else format(value, spec)


def _render_model_metrics(metrics: ModelMetrics | None) -> None:
    if metrics is None:
        render_no_data(
            title="Model Metadata Unavailable",
            message="The backend did not return forecast metadata.",
            icon="🧠",
        )
        return

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("🧠 Model", metrics.model_version, help=metrics.model_name)
        st.caption(metrics.model_name)
    with c2:
        st.metric("📉 RMSE", _fmt(metrics.rmse, ".1f"))
    with c3:
        st.metric("📉 MAE", _fmt(metrics.mae, ".1f"))
    with c4:
        st.metric("📊 R²", _fmt(metrics.r_squared, ".2f"))
    with c5:
        st.metric("📅 Last Trained", metrics.training_date or "N/A")
    if metrics.r_squared is None:
        st.caption("Metrics are N/A: no forecasting model has been validated yet.")


def _render_feature_importance(station_id: str, horizon_hours: int) -> None:
    features = forecast_service.get_feature_importances(station_id, horizon_hours)
    if not features:
        render_no_data(
            title="No Feature Importances",
            message="Available once a forecasting model is integrated.",
            icon="🔬",
        )
        return
    df = pd.DataFrame(features).rename(columns={"feature": "Feature", "importance": "Importance"})
    df["Importance %"] = df["Importance"].map(lambda x: f"{x:.0%}")
    df = df.sort_values("Importance", ascending=False).reset_index(drop=True)
    st.dataframe(df[["Feature", "Importance %"]], width="stretch", hide_index=True)
    st.caption("Global feature importances reported by the forecast model.")
