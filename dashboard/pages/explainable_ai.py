"""
dashboard/pages/explainable_ai.py — Explainable AI (XAI) module page.

Top section: the trained model's real test-set metrics and global feature
importances, served by GET /api/v1/xai/global-importance when the backend has
a model artefact loaded. The SHAP / counterfactual sections below remain
hardcoded illustrative examples until per-prediction SHAP output exists.
"""

from __future__ import annotations

from typing import Any

import pandas as pd
import streamlit as st

from dashboard.components.empty_state import render_coming_soon, render_stub_badge
from dashboard.components.error_state import render_info_notice
from dashboard.components.footer import render_page_footer
from dashboard.components.header import render_page_header
from dashboard.components.charts import render_shap_waterfall_chart
from dashboard.core.theme import (
    ACCENT_ORANGE,
    AQI_GOOD,
    BG_ELEVATED,
    BORDER_DEFAULT,
    PRIMARY,
    STATUS_WARNING,
    TEXT_MUTED,
    TEXT_SECONDARY,
)
from dashboard.services import xai_service


def render() -> None:
    """Render the Explainable AI module page."""
    render_page_header(
        module_name="Explainable AI",
        subtitle="Trained-model metrics when a model artefact is loaded, plus illustrative explanation examples",
    )

    # ── Trained model (real artefact metadata, when loaded) ───────────────────
    st.markdown(f"<h4 style='color:{PRIMARY}'>🧠 Trained Model</h4>", unsafe_allow_html=True)
    _render_trained_model()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    render_info_notice(
        "Illustrative only: everything below this point is a hardcoded example, not output "
        "from a trained model. Per-prediction SHAP explanations will appear once a model "
        "provides them."
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── XAI Methodology Explainer ──────────────────────────────────────────────────────────────────────────────────
    _render_xai_explainer()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Prediction selector ──────────────────────────────────────────────────────────────────────────────────────────
    _render_controls()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Single data fetch for SHAP explanation ──────────────────────────────────────────────────────────────────────
    explanation = xai_service.get_shap_values("PRED-001")

    # ── SHAP Values ──────────────────────────────────────────────────────────────────────────────────────────────────
    st.markdown(f"<h4 style='color:{PRIMARY}'>🔬 SHAP Feature Contributions</h4>", unsafe_allow_html=True)
    render_stub_badge("Illustrative example — hardcoded, not model output")

    left, right = st.columns([2, 3])
    with left:
        _render_shap_table(explanation)
    with right:
        if explanation:
            render_shap_waterfall_chart(
                shap_values=explanation.shap_values,
                base_value=explanation.base_value,
                predicted_aqi=explanation.predicted_aqi,
                title=f"Illustrative SHAP Contributions — {explanation.station_id} (AQI {explanation.predicted_aqi:.0f})",
            )

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Counterfactual Scenarios ──────────────────────────────────────────────
    st.markdown(f"<h4 style='color:{PRIMARY}'>🔄 What-If Counterfactuals</h4>", unsafe_allow_html=True)
    render_stub_badge("Illustrative example — hardcoded, not model output")
    _render_counterfactuals()

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Global Feature Importance ─────────────────────────────────────────────
    st.markdown(f"<h4 style='color:{PRIMARY}'>🌍 Global Feature Importance</h4>", unsafe_allow_html=True)
    render_stub_badge("Illustrative example — hardcoded, not model output")
    _render_global_importance()

    render_page_footer()


def _render_trained_model() -> None:
    """Real metrics + importances from the model artefact; honest empty state otherwise."""
    data = xai_service.get_model_importance()
    if not data:
        render_info_notice(
            "No trained-model artefact is loaded in the backend "
            "(GET /api/v1/xai/global-importance returned no data)."
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
        f"{m.get('validation_period') or 'validation split not recorded'}"
    )

    features = data.get("feature_importances", [])
    if features:
        df = pd.DataFrame(features).rename(columns={"feature": "Feature", "importance": "Share"})
        df["Share"] = df["Share"].map(lambda x: f"{x:.1%}")
        st.dataframe(df, width="stretch", hide_index=True)
    st.caption(data.get("importance_method", ""))


def _render_xai_explainer() -> None:
    methods = [
        ("🔬 SHAP",          PRIMARY,        "SHapley Additive exPlanations — assigns each feature a contribution value for each prediction using game-theoretic principles."),
        ("🔍 LIME",          STATUS_WARNING,  "Local Interpretable Model-agnostic Explanations — fits a simple interpretable model around each prediction locally. (Not implemented.)"),
        ("🔄 Counterfactual",ACCENT_ORANGE,  "What-if analysis — shows how the prediction changes when specific input features are altered."),
    ]
    cols = st.columns(3)
    for col, (name, color, desc) in zip(cols, methods):
        with col:
            st.markdown(
                f"""
                <div style="background:{BG_ELEVATED};border:1px solid {color}44;
                            border-top:3px solid {color};border-radius:12px;
                            padding:14px 16px;height:140px">
                  <div style="font-size:0.9rem;font-weight:600;color:{color};margin-bottom:8px">{name}</div>
                  <div style="font-size:0.78rem;color:{TEXT_SECONDARY};line-height:1.55">{desc}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def _render_controls() -> None:
    c1, c2 = st.columns([3, 2])
    with c1:
        st.selectbox(
            "📌 Prediction", ["Illustrative example — Delhi – Anand Vihar (AQI 312)"],
            key="xai_prediction", disabled=True,
            help="Prediction selection becomes available once per-prediction SHAP output exists.",
        )
    with c2:
        st.selectbox(
            "⚖️ XAI Method", ["SHAP (illustrative)"], key="xai_method", disabled=True,
            help="Only an illustrative SHAP example exists today.",
        )


def _render_shap_table(explanation: Any) -> None:
    if not explanation:
        return

    rows = [
        {
            "Feature": feat,
            "Input Value": explanation.feature_values.get(feat, "—"),
            "SHAP Value": f"{val:+.1f}",
            "Direction": "↑ Increases AQI" if val > 0 else "↓ Decreases AQI",
        }
        for feat, val in sorted(
            explanation.shap_values.items(), key=lambda x: abs(x[1]), reverse=True
        )
    ]
    st.dataframe(pd.DataFrame(rows), width="stretch", hide_index=True)
    st.caption(f"Base value: {explanation.base_value:.1f} → Predicted AQI: {explanation.predicted_aqi:.0f}")


def _render_counterfactuals() -> None:
    scenarios = xai_service.get_counterfactuals("DL001")
    for sc in scenarios:
        change_color = AQI_GOOD if sc.aqi_change < 0 else ACCENT_ORANGE
        st.markdown(
            f"""
            <div style="background:{BG_ELEVATED};border:1px solid {BORDER_DEFAULT};
                        border-radius:10px;padding:14px 18px;margin-bottom:10px;
                        display:flex;gap:16px;align-items:flex-start">
              <div style="flex:1">
                <div style="font-size:0.9rem;font-weight:600;color:#E6EDF3;margin-bottom:4px">
                  🔄 {sc.scenario_name}
                </div>
                <div style="font-size:0.8rem;color:{TEXT_SECONDARY};margin-bottom:6px">{sc.description}</div>
                <div style="font-size:0.75rem;color:{TEXT_MUTED}">
                  Changes: {', '.join(f'{k}→{v}' for k, v in sc.changed_features.items())}
                </div>
              </div>
              <div style="text-align:right;min-width:120px">
                <div style="font-size:0.75rem;color:{TEXT_MUTED}">AQI Change</div>
                <div style="font-size:1.4rem;font-weight:700;color:{change_color}">
                  {sc.aqi_change:+.0f}
                </div>
                <div style="font-size:0.72rem;color:{TEXT_MUTED}">
                  {sc.original_aqi:.0f} → {sc.counterfactual_aqi:.0f}
                </div>
              </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _render_global_importance() -> None:
    items = xai_service.get_global_importance()
    df = pd.DataFrame(items).rename(columns={
        "feature": "Feature",
        "mean_abs_shap": "Mean |SHAP|",
        "rank": "Rank",
    })
    st.dataframe(df[["Rank", "Feature", "Mean |SHAP|"]], width="stretch", hide_index=True)
    st.caption("Hardcoded illustrative values — not computed from any model or dataset.")
