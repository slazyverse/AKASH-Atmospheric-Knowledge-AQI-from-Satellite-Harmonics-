"""
dashboard/services/data_sources.py — what powers each domain and how far it is
trusted (GET /api/v1/sources).

Availability is not trust. The backend reports, per domain:
  kind      live · local (team output file) · placeholder (NOT real data) ·
            simulated · unavailable
  trust     trusted (promoted: passed every validation check) · unverified
            (team output used only for its safe capabilities) · placeholder ·
            simulated · unavailable
  reason    one-line explanation, capabilities (what the source may be used
            for, e.g. station maps) and a rejected team `candidate`
A `local` source is never treated as trusted unless the backend says
`trust: trusted`. When the backend itself is unreachable every domain is
reported as "unavailable" with reason "Backend unreachable" — the dashboard
keeps no hardcoded data of its own.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from dashboard.services.api_client import APIClient, APIError

_REAL_KINDS = {"live", "local"}
_SPATIAL_CODES = {"approximate_coordinates", "unverified_coordinates"}
# Capability that governs mapping positions, per domain
_MAP_CAPABILITY = {"aqi": "station_maps", "stations": "station_maps", "hcho": "hotspot_map"}
_OFFLINE = {"kind": "unavailable", "name": "none", "detail": "Backend unreachable.",
            "records": None, "as_of": None, "trust": "unavailable", "status": "unavailable",
            "promoted": False, "reason": "Backend unreachable."}
# Older backends do not report trust: derive it, never as "trusted"
_TRUST_FROM_KIND = {"live": "unverified", "local": "unverified", "placeholder": "placeholder",
                    "simulated": "simulated", "unavailable": "unavailable"}


@st.cache_data(ttl=60)
def get_sources() -> dict[str, dict[str, Any]]:
    """Source status per domain from the backend; {} when the backend is unreachable."""
    try:
        items = APIClient().get("/sources").data.get("sources") or []
        return {s["domain"]: s for s in items if isinstance(s, dict) and "domain" in s}
    except (APIError, AttributeError, TypeError, KeyError):
        return {}


def get_source(domain: str) -> dict[str, Any]:
    """Status dict for one domain (kind, trust, reason, capabilities, limitations, …)."""
    sources = get_sources()
    if not sources:
        return {"domain": domain, **_OFFLINE}
    return sources.get(domain) or {"domain": domain, **_OFFLINE, "detail": "Not reported.",
                                   "reason": "Not reported by the backend."}


def source_kind(domain: str) -> str:
    return get_source(domain)["kind"]


def trust_level(domain: str) -> str:
    s = get_source(domain)
    trust = s.get("trust") or _TRUST_FROM_KIND.get(s["kind"], "unavailable")
    # Defensive: "trusted" requires the backend's explicit promotion
    return "unverified" if trust == "trusted" and not s.get("promoted") else trust


def is_promoted(domain: str) -> bool:
    return trust_level(domain) == "trusted"


def is_team_data(domain: str) -> bool:
    """True when the domain is served from a team output / live feed (trusted or not)."""
    return source_kind(domain) in _REAL_KINDS


def trust_label(domain: str) -> str:
    """User-facing label, e.g. 'LOCAL — PROMOTED', 'LOCAL — UNVERIFIED', 'PLACEHOLDER'."""
    s = get_source(domain)
    kind, trust = s["kind"], trust_level(domain)
    if kind in _REAL_KINDS:
        prefix = "LIVE" if kind == "live" else "LOCAL"
        if trust == "trusted":
            return f"{prefix} — PROMOTED"
        return f"{prefix} — UNVERIFIED" + (" · not served" if s.get("status") == "withheld"
                                          else "")
    return trust.upper() if trust in ("placeholder", "simulated") else "UNAVAILABLE"


def trust_reason(domain: str) -> str:
    s = get_source(domain)
    return s.get("reason") or s.get("detail") or ""


def candidate(domain: str) -> dict[str, Any] | None:
    """A team source that exists but is not used, with the reason ({} → None)."""
    c = get_source(domain).get("candidate")
    return c if isinstance(c, dict) and c.get("reason") else None


def capabilities(domain: str) -> dict[str, dict[str, Any]]:
    caps = get_source(domain).get("capabilities") or {}
    return {k: v for k, v in caps.items() if isinstance(v, dict) and "enabled" in v}


def capability(domain: str, name: str) -> dict[str, Any] | None:
    return capabilities(domain).get(name)


def limitations(domain: str) -> list[dict[str, str]]:
    """Known limitations of a domain's source ([{code, message}], [] if none / offline)."""
    items = get_source(domain).get("limitations") or []
    return [i for i in items if isinstance(i, dict) and "code" in i]


def failed_checks(domain: str) -> list[dict[str, Any]]:
    """Failed blocking / restricting validation checks ([] if none / no gate)."""
    checks = (get_source(domain).get("validation") or {}).get("checks") or []
    return [c for c in checks if isinstance(c, dict) and not c.get("passed")
            and c.get("severity") in ("blocking", "restricting")]


def has_limitation(domain: str, code: str) -> bool:
    return any(i["code"] == code for i in limitations(domain))


def spatial_restriction(domain: str) -> str | None:
    """
    Why positions in this domain must not be mapped, or None when mapping is fine.

    Uses the backend's map capability (station_maps / hotspot_map) when reported,
    otherwise the `approximate_coordinates` / `unverified_coordinates` limitations;
    either way a map would suggest locations that are not known.
    """
    cap = capability(domain, _MAP_CAPABILITY.get(domain, ""))
    if cap is not None and not cap["enabled"]:
        spatial = next((i.get("message") for i in limitations(domain)
                        if i["code"] in _SPATIAL_CODES), None)
        return spatial or cap.get("reason") or "Map withheld by the backend."
    if cap is not None:
        return None
    for item in limitations(domain):
        if item["code"] in _SPATIAL_CODES:
            return item.get("message") or item["code"]
    return None


def source_label(domain: str) -> str:
    """Short label, e.g. 'LOCAL — UNVERIFIED (analysis_ready_dataset.csv)'."""
    s = get_source(domain)
    label = trust_label(domain)
    if s["kind"] in ("local", "live", "placeholder") and s.get("name") not in (None, "none"):
        return f"{label} ({s['name']})"
    return label
