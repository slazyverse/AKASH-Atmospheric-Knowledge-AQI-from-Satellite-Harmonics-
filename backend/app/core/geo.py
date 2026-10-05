"""
Geographic plausibility rules shared by the adapters (single source of truth).

INDIA_BOUNDS is a generous bounding box around India (incl. Andaman & Nicobar
and Ladakh). A station outside it cannot belong to the national network and is
rejected at the adapter boundary rather than plotted somewhere wrong.

SHARED_COORDINATE_LIMIT: physical monitoring stations practically never share
identical coordinates. When more than this fraction of a dataset's stations
share their exact coordinates with another station, the coordinates are city /
registry fallbacks rather than station locations, so the whole dataset is
treated as having approximate locations (maps are withheld; tables remain).
"""

from __future__ import annotations

INDIA_BOUNDS: tuple[tuple[float, float], tuple[float, float]] = ((6.0, 38.0), (68.0, 98.0))
SHARED_COORDINATE_LIMIT = 0.10


def in_india(latitude: float, longitude: float) -> bool:
    """True when the point lies inside India's bounding box."""
    (lat_lo, lat_hi), (lon_lo, lon_hi) = INDIA_BOUNDS
    return lat_lo <= latitude <= lat_hi and lon_lo <= longitude <= lon_hi
