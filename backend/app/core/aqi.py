"""
CPCB AQI category classification — the single source of truth for the backend.

Bands follow the CPCB National AQI scale:
  Good (0-50) | Satisfactory (51-100) | Moderate (101-200)
  Poor (201-300) | Very Poor (301-400) | Severe (401+)

Each band's upper limit is inclusive, so fractional values (e.g. a forecast of
50.4) fall into the next band only once they exceed the limit.
"""

from __future__ import annotations

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
