"""
dashboard/components/loading.py — Loading state components.

Provides reusable loading indicators used while:
  - API requests are in-flight (Day 3+)
  - Computationally expensive operations are running
  - Data is being parsed or transformed

Components:
  - render_spinner()        — Full-page spinner overlay with message
  - render_skeleton_card()  — Animated skeleton placeholder for metric cards
  - render_skeleton_chart() — Animated skeleton placeholder for chart areas
  - render_skeleton_table() — Animated skeleton for data tables

Design decision:
  Skeleton screens are preferred over spinners for known content shapes (cards,
  charts, tables) because they prevent layout shift and give users a sense of
  how data will appear — reducing perceived load time.
"""

from __future__ import annotations

import time

import streamlit as st

from dashboard.core.theme import BG_ELEVATED, BORDER_DEFAULT, PRIMARY, TEXT_MUTED


def render_spinner(message: str = "Loading data…") -> None:
    """
    Display a centred spinner with a descriptive message.

    Args:
        message: Human-readable description of what is loading.
    """
    st.markdown(
        f"""
        <div style="display:flex;flex-direction:column;align-items:center;
                    justify-content:center;padding:60px 20px;gap:16px">
          <div style="width:48px;height:48px;border:4px solid {BORDER_DEFAULT};
                      border-top-color:{PRIMARY};border-radius:50%;
                      animation:spin 0.8s linear infinite"></div>
          <div style="font-size:0.9rem;color:{TEXT_MUTED}">{message}</div>
        </div>
        <style>
          @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_skeleton_card(n_cards: int = 4) -> None:
    """
    Render N animated skeleton placeholders styled as metric cards.

    Args:
        n_cards: Number of skeleton cards to display in a row.
    """
    cols = st.columns(n_cards)
    for col in cols:
        with col:
            st.markdown(
                f"""
                <div style="background:{BG_ELEVATED};border:1px solid {BORDER_DEFAULT};
                            border-radius:12px;padding:20px;height:100px;
                            position:relative;overflow:hidden">
                  <div style="height:12px;background:{BORDER_DEFAULT};
                              border-radius:4px;width:60%;margin-bottom:12px"></div>
                  <div style="height:28px;background:{BORDER_DEFAULT};
                              border-radius:4px;width:40%;margin-bottom:8px"></div>
                  <div style="height:10px;background:{BORDER_DEFAULT};
                              border-radius:4px;width:80%"></div>
                  <div style="position:absolute;top:0;left:-100%;width:100%;height:100%;
                              background:linear-gradient(90deg,transparent,rgba(255,255,255,0.04),transparent);
                              animation:shimmer 1.5s infinite"></div>
                </div>
                <style>
                  @keyframes shimmer {{ to {{ left: 200%; }} }}
                </style>
                """,
                unsafe_allow_html=True,
            )


def render_skeleton_chart(height_px: int = 300) -> None:
    """
    Render an animated skeleton placeholder for a chart area.

    Args:
        height_px: Height of the skeleton area in pixels.
    """
    st.markdown(
        f"""
        <div style="background:{BG_ELEVATED};border:1px solid {BORDER_DEFAULT};
                    border-radius:12px;padding:20px;height:{height_px}px;
                    position:relative;overflow:hidden;
                    display:flex;align-items:flex-end;gap:8px">
          {''.join([
              f'<div style="background:{BORDER_DEFAULT};border-radius:4px 4px 0 0;'
              f'width:calc((100% - {i*3}px) / 12);'
              f'height:{30 + (i * 17) % 60}%;flex-shrink:0"></div>'
              for i in range(12)
          ])}
          <div style="position:absolute;top:0;left:-100%;width:100%;height:100%;
                      background:linear-gradient(90deg,transparent,rgba(255,255,255,0.04),transparent);
                      animation:shimmer 1.5s infinite"></div>
        </div>
        <style>
          @keyframes shimmer {{ to {{ left: 200%; }} }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_skeleton_table(n_rows: int = 6) -> None:
    """
    Render an animated skeleton placeholder for a data table.

    Args:
        n_rows: Number of skeleton rows to display.
    """
    widths = ["20%", "35%", "15%", "15%", "15%"]

    header_html = "".join([
        f'<div style="background:{PRIMARY}22;border-radius:4px;height:12px;width:{w};flex:0 0 {w}"></div>'
        for w in widths
    ])
    row_html_template = "".join([
        f'<div style="background:{BORDER_DEFAULT};border-radius:4px;height:10px;width:{w};flex:0 0 {w}"></div>'
        for w in widths
    ])

    rows_html = ""
    for i in range(n_rows):
        opacity = 1 - (i * 0.1)
        rows_html += f"""
        <div style="display:flex;gap:12px;padding:10px 0;
                    border-bottom:1px solid {BORDER_DEFAULT};opacity:{opacity:.1f}">
          {row_html_template}
        </div>
        """

    st.markdown(
        f"""
        <div style="background:{BG_ELEVATED};border:1px solid {BORDER_DEFAULT};
                    border-radius:12px;padding:16px;position:relative;overflow:hidden">
          <div style="display:flex;gap:12px;padding:0 0 12px;
                      border-bottom:2px solid {BORDER_DEFAULT};margin-bottom:4px">
            {header_html}
          </div>
          {rows_html}
          <div style="position:absolute;top:0;left:-100%;width:100%;height:100%;
                      background:linear-gradient(90deg,transparent,rgba(255,255,255,0.04),transparent);
                      animation:shimmer 1.5s infinite"></div>
        </div>
        <style>
          @keyframes shimmer {{ to {{ left: 200%; }} }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def with_loading(message: str = "Loading…"):
    """
    Context manager that shows a spinner while the body executes.

    Usage:
        with with_loading("Fetching AQI data…"):
            data = api_service.get_data()

    Note: Uses st.spinner (native) for compatibility with Streamlit's async model.
    """
    return st.spinner(message)
