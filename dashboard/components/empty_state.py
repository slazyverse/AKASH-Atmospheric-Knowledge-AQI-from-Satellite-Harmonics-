"""
dashboard/components/empty_state.py — Empty data state UI components.

Provides styled "no data" placeholders that are shown when:
  - A module has not yet received any data (Day 2 stub state)
  - A filtered query returns zero results
  - A user has not yet configured a required parameter

Components maintain layout structure so the page does not collapse when
data is absent — critical for dashboards where layout stability signals
professionalism and reliability.
"""

from __future__ import annotations

from typing import Callable

import streamlit as st

from dashboard.core.theme import (
    BG_ELEVATED,
    BORDER_DEFAULT,
    PRIMARY,
    TEXT_MUTED,
    TEXT_SECONDARY,
)


def render_no_data(
    title: str = "No Data Available",
    message: str = "Data will appear here once the backend API is connected.",
    icon: str = "📭",
    action_label: str | None = None,
    on_action: Callable[[], None] | None = None,
) -> None:
    """
    Render a centred empty-state illustration with optional CTA.

    Args:
        title:        Short descriptive heading.
        message:      Longer explanation of why data is absent.
        icon:         Emoji or unicode character used as the illustration.
        action_label: Button label for the primary CTA (e.g., "Connect API").
        on_action:    Callback invoked when the CTA button is clicked.
    """
    st.markdown(
        f"""
        <div style="display:flex;flex-direction:column;align-items:center;
                    justify-content:center;padding:60px 20px;text-align:center;
                    background:{BG_ELEVATED};border:1px dashed {BORDER_DEFAULT};
                    border-radius:16px;margin:16px 0">
          <div style="font-size:3.5rem;margin-bottom:16px;opacity:0.7">{icon}</div>
          <div style="font-size:1.1rem;font-weight:600;color:{TEXT_SECONDARY};
                      margin-bottom:8px">{title}</div>
          <div style="font-size:0.85rem;color:{TEXT_MUTED};max-width:420px;
                      line-height:1.6">{message}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if action_label and on_action:
        col = st.columns([1, 2, 1])[1]
        with col:
            if st.button(action_label, use_container_width=True, key=f"empty_action_{title[:10]}"):
                on_action()


def render_no_results(
    query: str = "",
    suggestion: str = "Try broadening your date range or changing the region filter.",
) -> None:
    """
    Render an empty state for zero search/filter results.

    Args:
        query:      The filter/search term that produced no results.
        suggestion: Actionable hint for the user.
    """
    query_display = f'for <em>"{query}"</em>' if query else ""
    st.markdown(
        f"""
        <div style="display:flex;flex-direction:column;align-items:center;
                    justify-content:center;padding:48px 20px;text-align:center;
                    background:{BG_ELEVATED};border:1px dashed {BORDER_DEFAULT};
                    border-radius:16px;margin:16px 0">
          <div style="font-size:2.8rem;margin-bottom:12px;opacity:0.6">🔍</div>
          <div style="font-size:1rem;font-weight:600;color:{TEXT_SECONDARY};margin-bottom:6px">
            No Results {query_display}
          </div>
          <div style="font-size:0.82rem;color:{TEXT_MUTED};max-width:380px;line-height:1.5">
            {suggestion}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_coming_soon(
    module_name: str,
    planned_day: str = "Day 3",
    features: list[str] | None = None,
) -> None:
    """
    Render a "coming soon" placeholder for features not yet implemented.

    Args:
        module_name: The module this placeholder belongs to.
        planned_day: Sprint day when this feature is planned (e.g., "Day 3").
        features:    List of feature bullets to preview.
    """
    features = features or []

    feature_items = "".join([
        f'<li style="margin-bottom:4px;color:{TEXT_MUTED}">{f}</li>'
        for f in features
    ])
    feature_block = (
        f'<ul style="text-align:left;margin:12px auto;max-width:320px;padding-left:20px">'
        f'{feature_items}</ul>'
        if feature_items else ""
    )

    st.markdown(
        f"""
        <div style="display:flex;flex-direction:column;align-items:center;
                    justify-content:center;padding:56px 20px;text-align:center;
                    background:{BG_ELEVATED};border:1px solid {PRIMARY}44;
                    border-radius:16px;margin:16px 0;
                    box-shadow:0 0 20px {PRIMARY}18">
          <div style="font-size:3rem;margin-bottom:12px">🚧</div>
          <div style="font-size:1.15rem;font-weight:700;color:{PRIMARY};margin-bottom:6px">
            {module_name} — Coming {planned_day}
          </div>
          <div style="font-size:0.85rem;color:{TEXT_SECONDARY};max-width:440px;line-height:1.6">
            This module is under active development. Below is a preview of
            what will be available:
          </div>
          {feature_block}
          <div style="margin-top:16px;font-size:0.75rem;color:{TEXT_MUTED};
                      background:#21262D;border-radius:20px;padding:4px 14px;
                      border:1px solid {BORDER_DEFAULT}">
            📅 Scheduled: {planned_day} Sprint
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_stub_badge() -> None:
    """Render a small 'Day 2 Stub' badge — shown in placeholder sections."""
    st.markdown(
        f"""
        <div style="display:inline-block;background:#21262D;border:1px solid {BORDER_DEFAULT};
                    border-radius:20px;padding:3px 10px;font-size:0.7rem;color:{TEXT_MUTED};
                    margin-bottom:8px">
          🔧 Day 2 Stub — Live data in Day 3
        </div>
        """,
        unsafe_allow_html=True,
    )
