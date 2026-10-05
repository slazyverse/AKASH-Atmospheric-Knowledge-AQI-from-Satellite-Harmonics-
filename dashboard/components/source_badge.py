"""
dashboard/components/source_badge.py — labels what powers a section.

Every data section shows one of:
  LIVE · LOCAL (team output) · PLACEHOLDER (not real data) · SIMULATED · UNAVAILABLE
taken from GET /api/v1/sources, so the label always matches the backend.
LOCAL means "the team's output", not "validated": the source's known
limitations are listed under the badge, and maps are withheld when the
backend reports that its coordinates are not station positions.
"""

from __future__ import annotations

import html

import streamlit as st

from dashboard.services.data_sources import get_source, limitations, spatial_restriction

_STYLE = {
    "live":        ("#00E676", "LIVE"),
    "local":       ("#58A6FF", "LOCAL · team output"),
    "placeholder": ("#FFB300", "PLACEHOLDER · not real data"),
    "simulated":   ("#B388FF", "SIMULATED · not a prediction"),
    "unavailable": ("#8B949E", "UNAVAILABLE"),
}
_WARN = "#FFB300"


def render_source_badge(domain: str, what: str | None = None, compact: bool = False) -> None:
    """
    Render a coloured source pill plus the backend's explanation for one domain.

    compact=True (overview pages) lists limitation codes in one line instead of
    the full explanations.
    """
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

    known = limitations(domain)
    if not known:
        return
    if compact:
        codes = ", ".join(i["code"].replace("_", " ") for i in known)
        st.caption(f"⚠️ {len(known)} known limitation(s): {codes}")
        return
    items = "".join(
        f"<li><b>{html.escape(i['code'].replace('_', ' '))}</b> — "
        f"{html.escape(i.get('message', ''))}</li>"
        for i in known
    )
    st.markdown(
        f"""
        <div style="border-left:3px solid {_WARN};padding:4px 10px;margin:0 0 8px 0;
                    font-size:0.74rem;color:#C9D1D9">
          <span style="color:{_WARN};font-weight:600">⚠️ Known limitations of this source</span>
          <ul style="margin:4px 0 0 0;padding-left:18px">{items}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_map_withheld(domain: str, what: str = "Map") -> bool:
    """
    If the domain's coordinates must not be mapped, render why and return True.

    Pages call this before drawing a map; nothing is plotted at positions the
    backend reports as approximate or unverified, and no corrected positions
    are invented.
    """
    reason = spatial_restriction(domain)
    if reason is None:
        return False
    st.markdown(
        f"""
        <div style="border:1px dashed {_WARN};border-radius:10px;padding:18px 20px;
                    margin:4px 0 8px 0;color:#C9D1D9;font-size:0.82rem;line-height:1.55">
          <div style="color:{_WARN};font-weight:600;margin-bottom:6px">
            🗺️ {html.escape(what)} withheld — locations are not known precisely
          </div>
          {html.escape(reason)}
          <div style="margin-top:6px;color:#8B949E;font-size:0.74rem">
            The data stays available in the tables. Corrected per-station coordinates must
            come from the data pipeline; the dashboard never estimates them.
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    return True
