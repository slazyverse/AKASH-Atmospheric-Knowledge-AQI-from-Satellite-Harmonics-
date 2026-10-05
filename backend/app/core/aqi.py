"""
CPCB AQI category classification — the single source of truth for the backend.

Bands follow the CPCB National AQI scale:
  Good (0-50) | Satisfactory (51-100) | Moderate (101-200)
  Poor (201-300) | Very Poor (301-400) | Severe (401+)

Each band's upper limit is inclusive, so fractional values (e.g. a forecast of
50.4) fall into the next band only once they exceed the limit.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

AQI_CATEGORIES: tuple[str, ...] = (
    "Good",
    "Satisfactory",
    "Moderate",
    "Poor",
    "Very Poor",
    "Severe",
)

_UPPER_LIMITS: tuple[tuple[float, str], ...] = (
    (50, "Good"),
    (100, "Satisfactory"),
    (200, "Moderate"),
    (300, "Poor"),
    (400, "Very Poor"),
)


def aqi_category(aqi: float) -> str:
    """Return the CPCB category name for an AQI value."""
    for upper, name in _UPPER_LIMITS:
        if aqi <= upper:
            return name
    return "Severe"


# ── Data-sufficiency rule (CPCB) ───────────────────────────────────────────────
# The AQI itself is taken from the source as reported (the team pipeline owns
# the CPCB sub-index calculation); the API only checks that a reported AQI is
# admissible under the CPCB minimum-data rule and inside the AQI scale.

AQI_SCALE_MAX = 500

# The six pollutants of the dataset contract (NH3 / Pb are not part of it).
CPCB_POLLUTANTS: tuple[str, ...] = ("pm25", "pm10", "no2", "so2", "co", "o3")
_PARTICULATES: tuple[str, ...] = ("pm25", "pm10")


def meets_cpcb_minimum(pollutants: Mapping[str, float | None]) -> bool:
    """CPCB rule: an AQI needs at least three pollutants, one of them PM2.5 or PM10."""
    present = {name for name, value in pollutants.items() if value is not None}
    return len(present) >= 3 and any(p in present for p in _PARTICULATES)
