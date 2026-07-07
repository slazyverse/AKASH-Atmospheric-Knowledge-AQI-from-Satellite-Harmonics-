"""
dashboard/pages/explainable_ai.py — Explainable AI (XAI) module page.

Makes ML forecast decisions interpretable through SHAP, LIME, and what-if analysis.

Day 2 Scope: Stub SHAP values table, counterfactual scenarios, XAI methodology explanation.
Day 3/4 Scope: Plotly SHAP waterfall chart, LIME explanation, interactive what-if sliders.
"""

from __future__ import annotations

import pandas as pd
import streamlit as st

from dashboard.components.empty_state import render_coming_soon, render_stub_badge
from dashboard.components.error_state import render_info_notice
from dashboard.components.footer import render_page_footer
from dashboard.components.header import render_page_header
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
        subtitle="Transparent ML decisions via SHAP values, LIME, and counterfactual scenarios",
    )

    render_info_notice(
        "XAI features require the ML model (Day 4). "
        "SHAP and counterfactual displays show stub data today."
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── XAI Methodology Explainer ─────────────────────────────────────────────
    _render_xai_explainer()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Prediction selector ───────────────────────────────────────────────────
    _render_controls()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── SHAP Values ───────────────────────────────────────────────────────────
    st.markdown(f"<h4 style='color:{PRIMARY}'>🔬 SHAP Feature Contributions</h4>", unsafe_allow_html=True)
    render_stub_badge()

    left, right = st.columns([2, 3])
    with left:
        _render_shap_table()
    with right:
        render_coming_soon(
            "SHAP Waterfall Chart",
            planned_day="Day 4",
            features=[
                "Waterfall plot showing each feature's AQI contribution",
                "Positive contributions (red) vs. negative (blue)",
                "Base value + individual SHAP sum = final prediction",
            ],
        )

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Counterfactual Scenarios ──────────────────────────────────────────────
    st.markdown(f"<h4 style='color:{PRIMARY}'>🔄 What-If Counterfactuals</h4>", unsafe_allow_html=True)
    render_stub_badge()
    _render_counterfactuals()

    st.markdown("<div style='height:20px'></div>", unsafe_allow_html=True)

    # ── Global Feature Importance ─────────────────────────────────────────────
    st.markdown(f"<h4 style='color:{PRIMARY}'>🌍 Global Feature Importance</h4>", unsafe_allow_html=True)
    render_stub_badge()
    _render_global_importance()

    render_page_footer()


def _render_xai_explainer() -> None:
    methods = [
        ("🔬 SHAP",          PRIMARY,        "SHapley Additive exPlanations — assigns each feature a contribution value for each prediction using game-theoretic principles."),
        ("🔍 LIME",          STATUS_WARNING,  "Local Interpretable Model-agnostic Explanations — fits a simple interpretable model around each prediction locally."),
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
        st.selectbox("📍 Prediction", ["Delhi – Anand Vihar (AQI 312, 2024-01-15 14:00)"], key="xai_prediction")
    with c2:
        st.selectbox("🔬 XAI Method", ["SHAP", "LIME", "Counterfactual"], key="xai_method")


def _render_shap_table() -> None:
    explanation = xai_service.get_shap_values("PRED-001")
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
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
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
    st.dataframe(df[["Rank", "Feature", "Mean |SHAP|"]], use_container_width=True, hide_index=True)
    st.caption("Averaged over all predictions in the validation set (stub values)")
