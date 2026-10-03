"""
Region filter matching shared by the AQI and Fire services.

A region query matches a record when it is:
  - a national scope ("India", "All India", "All")  → every record
  - a zone ("North", "North India", "Northeast", ...) → states in that zone
  - otherwise a case-insensitive substring of the record's state or city

Zones follow the Zonal Councils of India (Ministry of Home Affairs), with the
North Eastern Council states as "Northeast".
"""

from __future__ import annotations

_NATIONAL = {"india", "all india", "all"}

_ZONES: dict[str, frozenset[str]] = {
    "north": frozenset({
        "haryana", "himachal pradesh", "punjab", "rajasthan",
        "jammu and kashmir", "ladakh", "delhi", "chandigarh",
    }),
    "central": frozenset({
        "chhattisgarh", "uttarakhand", "uttar pradesh", "madhya pradesh",
    }),
    "east": frozenset({
        "bihar", "jharkhand", "odisha", "west bengal",
    }),
    "northeast": frozenset({
        "arunachal pradesh", "assam", "manipur", "meghalaya",
        "mizoram", "nagaland", "sikkim", "tripura",
    }),
    "west": frozenset({
        "goa", "gujarat", "maharashtra",
        "dadra and nagar haveli and daman and diu",
    }),
    "south": frozenset({
        "andhra pradesh", "karnataka", "kerala", "tamil nadu",
        "telangana", "puducherry",
    }),
}


def _zone_key(region: str) -> str | None:
    key = region.strip().lower().removesuffix(" india").replace("-", "").replace(" ", "")
    return key if key in _ZONES else None


def is_national(region: str) -> bool:
    """True when the region query means 'the whole country'."""
    return region.strip().lower() in _NATIONAL


def region_matches(region: str, state: str, city: str = "") -> bool:
    """Return True if a record in `state` / `city` belongs to the queried region."""
    if is_national(region):
        return True

    zone = _zone_key(region)
    if zone is not None:
        return state.strip().lower() in _ZONES[zone]

    needle = region.strip().lower()
    return needle in state.lower() or (bool(city) and needle in city.lower())
