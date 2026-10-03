"""
dashboard/components/source_badge.py — labels what powers a section.

Every data section shows one of:
  LIVE · LOCAL (team output) · PLACEHOLDER (not real data) · SIMULATED · UNAVAILABLE
taken from GET /api/v1/sources, so the label always matches the backend.
"""

from __future__ import annotations

import html

import streamlit as st

from dashboard.services.data_sources import get_source

_STYLE = {
    "live":        ("#00E676", "LIVE"),
    "local":       ("#58A6FF", "LOCAL · team output"),
    "placeholder": ("#FFB300", "PLACEHOLDER · not real data"),
    "simulated":   ("#B388FF", "SIMULATED · not a prediction"),
    "unavailable": ("#8B949E", "UNAVAILABLE"),
}


def render_source_badge(domain: str, what: str | None = None) -> None:
    """Render a coloured source pill plus the backend's explanation for one domain."""
    s = get_source(domain)
    color, label = _STYLE.get(s["kind"], _STYLE["unavailable"])
    name = s.get("name")
    extra = f" · {html.escape(name)}" if name and name != "none" else ""
    as_of = f" · as of {html.escape(str(s['as_of'])[:16])}" if s.get("as_of") else ""
    prefix = f"{html.escape(what)}: " if what else ""
    st.markdown(
        f"""
        <div style="display:inline-block;border:1px solid {color};border-radius:20px;
                    padding:3px 12px;margin:2px 0 6px 0;font-size:0.72rem;color:{color}"
             title="{html.escape(s.get('detail') or '')}">
          ● {prefix}<b>{label}</b>{extra}{as_of}
        </div>
        """,
        unsafe_allow_html=True,
    )
    if s["kind"] in ("placeholder", "unavailable", "simulated") and s.get("detail"):
        st.caption(s["detail"])
