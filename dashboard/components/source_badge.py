"""
dashboard/components/source_badge.py — labels what powers a section and how
far it is trusted.

Every data section shows one of:
  LIVE — PROMOTED · LOCAL — PROMOTED · LOCAL — UNVERIFIED · PLACEHOLDER ·
  SIMULATED · UNAVAILABLE
taken from GET /api/v1/sources, so the label always matches the backend.
LOCAL means "the team's output"; only PROMOTED means it passed every
validation check. Under the pill: one concise reason, the features a source
is NOT allowed to power, and — folded away — the failed checks and known
limitations. Maps are withheld when the backend says positions are unsafe.
"""

from __future__ import annotations

import html

import streamlit as st

from dashboard.services.data_sources import (
    candidate,
    capabilities,
    failed_checks,
    get_source,
    limitations,
    spatial_restriction,
    trust_label,
    trust_level,
    trust_reason,
)

# trust level → pill colour (LIVE is reserved for kind "live")
_COLOR = {
    "trusted": "#3FB950",
    "unverified": "#F0883E",
    "placeholder": "#FFB300",
    "simulated": "#B388FF",
    "unavailable": "#8B949E",
}
_SUFFIX = {"placeholder": " · not real data", "simulated": " · not a prediction"}
_WARN = "#FFB300"


def render_source_badge(domain: str, what: str | None = None, compact: bool = False) -> None:
    """
    Render the trust pill, a one-line reason and (unless compact) the disabled
    capabilities plus an expander with failed checks and limitations.
    """
    s = get_source(domain)
    trust = trust_level(domain)
    color = "#00E676" if s["kind"] == "live" and trust == "trusted" else _COLOR[trust]
    label = trust_label(domain) + _SUFFIX.get(trust, "")
    name = s.get("name")
    extra = f" · {html.escape(name)}" if name and name != "none" else ""
    as_of = f" · as of {html.escape(str(s['as_of'])[:16])}" if s.get("as_of") else ""
    prefix = f"{html.escape(what)}: " if what else ""
    st.markdown(
        f"""
        <div style="display:inline-block;border:1px solid {color};border-radius:20px;
                    padding:3px 12px;margin:2px 0 4px 0;font-size:0.72rem;color:{color}"
             title="{html.escape(s.get('detail') or '')}">
          ● {prefix}<b>{html.escape(label)}</b>{extra}{as_of}
        </div>
        """,
        unsafe_allow_html=True,
    )
    reason = trust_reason(domain)
    if reason:
        st.caption(reason)
    if compact:
        return

    off = [(n, c) for n, c in capabilities(domain).items() if not c["enabled"]]
    if off and s["kind"] != "unavailable":
        chips = " · ".join(f"✗ {html.escape(n.replace('_', ' '))}" for n, _ in off)
        st.markdown(
            f"<div style='font-size:0.72rem;color:{_WARN};margin:0 0 4px 0'>Not enabled: "
            f"{chips}</div>",
            unsafe_allow_html=True,
        )

    cand = candidate(domain)
    # A placeholder is never a promotion candidate: list its limitations, not checks
    checks = failed_checks(domain) if trust in ("trusted", "unverified") else []
    known = limitations(domain)
    if not (cand or checks or known):
        return
    with st.expander("Validation details", expanded=False):
        if cand:
            st.markdown(
                f"**Team source not used** — `{html.escape(str(cand.get('location')))}` "
                f"({html.escape(str(cand.get('origin')))}): {html.escape(cand['reason'])}"
            )
        for c in checks:
            st.markdown(f"- ✗ **{html.escape(c['name'].replace('_', ' '))}** "
                        f"({c['severity']}) — {html.escape(c.get('detail', ''))}")
        for i in known:
            st.markdown(f"- ⚠️ **{html.escape(i['code'].replace('_', ' '))}** — "
                        f"{html.escape(i.get('message', ''))}")


def render_map_withheld(domain: str, what: str = "Map") -> bool:
    """
    If the domain's coordinates must not be mapped, render why and return True.

    Pages call this before drawing a map; nothing is plotted at positions the
    backend reports as unsafe, and no corrected positions are invented.
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
