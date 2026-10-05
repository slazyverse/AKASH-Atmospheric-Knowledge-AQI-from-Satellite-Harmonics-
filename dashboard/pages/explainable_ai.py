"""
dashboard/pages/explainable_ai.py — Explainable AI (XAI) module page.

Shows only genuine explanation data:
  - the trained model's test-set metrics and global feature importances
    (GET /api/v1/xai/global-importance) when a model artefact is loaded;
  - a capability table from GET /api/v1/sources stating what is unavailable.
No illustrative or hardcoded explanations are displayed. Per-prediction SHAP
and counterfactuals will appear here once a model provides them.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from dashboard.components import (
    render_info_notice,
    render_page_footer,
    render_page_header,
    render_source_badge,
)
from dashboard.core.theme import PRIMARY
from dashboard.services import xai_service
from dashboard.services.data_sources import get_source

_CAPABILITIES = [
    ("Global feature importance", "xai_global"),
    ("Per-prediction SHAP explanations", "xai_local"),
    ("Trained-model artefact", "model"),
    ("AQI forecasting model", "forecast"),
]


def render() -> None:
    """Render the Explainable AI module page."""
    render_page_header(
        module_name="Explainable AI",
        subtitle="Trained-model metrics and explanations — only what a real model artefact provides",
    )

    st.markdown(f"<h4 style='color:{PRIMARY}'>🧠 Trained Model</h4>", unsafe_allow_html=True)
    render_source_badge("model", "Model artefact")
    _render_trained_model()

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    st.markdown(f"<h4 style='color:{PRIMARY}'>🧭 Explanation Capabilities</h4>", unsafe_allow_html=True)
    _render_capabilities()

    render_page_footer()


def _render_trained_model() -> None:
    """Real metrics + importances from the model artefact; honest empty state otherwise."""
    data = xai_service.get_model_importance()
    if not data:
        render_info_notice(
            "No validated trained-model artefact is loaded, so no model metrics or feature "
            "importances are shown. Nothing is substituted. An artefact that exists but lacks "
            "the required training metadata is listed above as not validated."
        )
        return

    m = data.get("model_metrics", {})

    def fmt(value: Any, spec: str) -> str:
        return "N/A" if value is None else format(value, spec)

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        st.metric("📊 R²", fmt(m.get("r_squared"), ".3f"))
    with c2:
        st.metric("📉 RMSE", fmt(m.get("rmse"), ".1f"))
    with c3:
        st.metric("📉 MAE", fmt(m.get("mae"), ".1f"))
    with c4:
        st.metric("⚖️ Mean Bias", fmt(data.get("mean_bias_error"), "+.1f"))
    with c5:
        st.metric("🎯 Target", data.get("target_column") or "N/A")
    st.caption(
        f"{m.get('model_name', 'Model')} · {m.get('model_version', '')} · "
        f"{m.get('validation_period') or 'validation split not recorded'}. "
        "This is a same-day AQI estimator, not a forecaster."
    )

    features = data.get("feature_importances", [])
    if features:
        df = pd.DataFrame(features).rename(columns={"feature": "Feature", "importance": "Share"})
        df["Share"] = df["Share"].map(lambda x: f"{x:.1%}")
        st.dataframe(df, width="stretch", hide_index=True)
    st.caption(data.get("importance_method", ""))


def _render_capabilities() -> None:
    rows = []
    for label, domain in _CAPABILITIES:
        s = get_source(domain)
        rows.append({"Capability": label, "Status": s["kind"].upper(), "Detail": s.get("detail", "")})
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.caption(
        "Counterfactual (what-if) analysis and LIME are not implemented. Statuses come from "
        "GET /api/v1/sources."
    )
