"""
dashboard/services/data_sources.py — what powers each domain (GET /api/v1/sources).

The backend reports, per domain, a source `kind`:
  live         live external feed
  local        team output file (the team's data — not scientifically validated;
               its known limitations are listed per domain)
  placeholder  bundled deterministic fixture — NOT real data
  simulated    synthetic algorithm (forecast)
  unavailable  no source
When the backend itself is unreachable every domain is reported as
"unavailable" with detail "Backend unreachable" — the dashboard keeps no
hardcoded data of its own.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

from dashboard.services.api_client import APIClient, APIError

_REAL_KINDS = {"live", "local"}
_SPATIAL_CODES = {"approximate_coordinates", "unverified_coordinates"}
_OFFLINE = {"kind": "unavailable", "name": "none", "detail": "Backend unreachable.",
            "records": None, "as_of": None}


@st.cache_data(ttl=60)
def get_sources() -> dict[str, dict[str, Any]]:
    """Source status per domain from the backend; {} when the backend is unreachable."""
    try:
        items = APIClient().get("/sources").data.get("sources") or []
        return {s["domain"]: s for s in items if isinstance(s, dict) and "domain" in s}
    except (APIError, AttributeError, TypeError, KeyError):
        return {}


def get_source(domain: str) -> dict[str, Any]:
    """Status dict for one domain (kind, name, detail, records, as_of)."""
    sources = get_sources()
    if not sources:
        return {"domain": domain, **_OFFLINE}
    return sources.get(domain) or {"domain": domain, **_OFFLINE, "detail": "Not reported."}


def source_kind(domain: str) -> str:
    return get_source(domain)["kind"]


def is_team_data(domain: str) -> bool:
    """True when the domain is served from real data (team output or live feed)."""
    return source_kind(domain) in _REAL_KINDS


def limitations(domain: str) -> list[dict[str, str]]:
    """Known limitations of a domain's source ([{code, message}], [] if none / offline)."""
    items = get_source(domain).get("limitations") or []
    return [i for i in items if isinstance(i, dict) and "code" in i]


def has_limitation(domain: str, code: str) -> bool:
    return any(i["code"] == code for i in limitations(domain))


def spatial_restriction(domain: str) -> str | None:
    """
    Why positions in this domain must not be mapped, or None when mapping is fine.

    The backend reports `approximate_coordinates` (shared fallback coordinates)
    or `unverified_coordinates` (precision cannot be checked); either way a map
    would suggest locations that are not known.
    """
    for item in limitations(domain):
        if item["code"] in _SPATIAL_CODES:
            return item.get("message") or item["code"]
    return None


def source_label(domain: str) -> str:
    """Short label, e.g. 'PLACEHOLDER (placeholder_station_dataset.csv)'."""
    s = get_source(domain)
    kind = s["kind"].upper()
    if s["kind"] in ("local", "live", "placeholder") and s.get("name") not in (None, "none"):
        return f"{kind} ({s['name']})"
    return kind
