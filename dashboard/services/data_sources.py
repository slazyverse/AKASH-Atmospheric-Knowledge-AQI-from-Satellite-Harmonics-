"""
dashboard/services/data_sources.py — which backend source is live per domain.

Reads `data_sources` from GET /api/v1/version (e.g. {"aqi": "dataset:analysis_ready_dataset.csv",
"hcho": "demo", "forecast": "simulated", "model": "none"}) so pages label demo
data vs the team's real outputs from what the backend reports, not hardcoded text.
"""

from __future__ import annotations

import streamlit as st

from dashboard.services.api_client import APIClient, APIError

_TEAM_KINDS = {"dataset", "hotspot_file", "artifact"}


@st.cache_data(ttl=60)
def get_data_sources() -> dict[str, str]:
    """Backend-reported source per domain; {} when the backend is unreachable."""
    try:
        return dict(APIClient().get("/version").data.get("data_sources") or {})
    except (APIError, AttributeError, TypeError):
        return {}


def is_team_data(domain: str) -> bool:
    """True when the domain is served from the team's dataset / hotspot file / model artefact."""
    return get_data_sources().get(domain, "demo").partition(":")[0] in _TEAM_KINDS


def source_label(domain: str) -> str:
    """Short human-readable label for a domain's data source."""
    kind, _, name = get_data_sources().get(domain, "demo").partition(":")
    if kind == "dataset":
        return f"team dataset ({name})"
    if kind == "hotspot_file":
        return "team hotspot clusters"
    if kind == "artifact":
        return f"trained-model artefact ({name})"
    if kind == "simulated":
        return "simulated"
    return "demo data"
