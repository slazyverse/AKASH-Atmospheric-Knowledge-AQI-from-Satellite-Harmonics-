"""
Loader for the HCHO hotspot clusters (cluster_summary.json).

Contract (verified against spatial_analysis/hotspot_detector.py on PR #7):
a JSON list of clusters, each with
  cluster_id, mean_latitude, mean_longitude, mean_hcho (mol/m²),
  station_count, stations (station names), mean_co_column (optional)

That file carries no radius, confidence, source type or observation date.
Those fields are read when present (radius_km, confidence, source_type,
observation_date) and are otherwise left empty — never invented.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.logging import get_logger
from app.core.units import hcho_mol_m2_to_1e15_molec_cm2

logger = get_logger(__name__)

_REQUIRED = ("cluster_id", "mean_latitude", "mean_longitude", "mean_hcho")


class HotspotFileError(ValueError):
    """The configured hotspot file is missing, unreadable or violates the contract."""


@dataclass(frozen=True)
class HotspotRecord:
    hotspot_id: str
    latitude: float
    longitude: float
    column_density: float          # 10¹⁵ molecules/cm²
    station_count: int | None
    stations: tuple[str, ...]
    radius_km: float | None
    confidence: float | None
    source_type: str
    observed_at: datetime | None


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value) if math.isfinite(value) else None


def _parse(item: Any, index: int) -> HotspotRecord:
    if not isinstance(item, dict):
        raise HotspotFileError(f"Cluster #{index} is not an object.")
    missing = [k for k in _REQUIRED if k not in item]
    if missing:
        raise HotspotFileError(f"Cluster #{index} is missing required keys: {missing}")

    lat, lon, hcho = (
        _number(item[k]) for k in ("mean_latitude", "mean_longitude", "mean_hcho")
    )
    if lat is None or not -90 <= lat <= 90 or lon is None or not -180 <= lon <= 180:
        raise HotspotFileError(f"Cluster #{index} has invalid coordinates.")
    if hcho is None or hcho < 0:
        raise HotspotFileError(f"Cluster #{index} has an invalid mean_hcho: {item['mean_hcho']!r}")

    confidence = _number(item.get("confidence"))
    if confidence is not None and not 0 <= confidence <= 1:
        raise HotspotFileError(f"Cluster #{index} has confidence outside [0, 1].")
    radius = _number(item.get("radius_km"))

    observed_at = None
    if item.get("observation_date"):
        try:
            raw_date = str(item["observation_date"]).replace("Z", "+00:00")
            observed_at = datetime.fromisoformat(raw_date)
        except ValueError as exc:
            raise HotspotFileError(f"Cluster #{index} has an invalid observation_date.") from exc
        observed_at = (
            observed_at.astimezone(UTC) if observed_at.tzinfo else observed_at.replace(tzinfo=UTC)
        )

    stations = item.get("stations")
    if stations is None:
        stations = []
    elif not isinstance(stations, list):
        raise HotspotFileError(f"Cluster #{index} has 'stations' that is not a list.")

    count = _number(item.get("station_count"))
    return HotspotRecord(
        hotspot_id=f"HS-{item['cluster_id']}",
        latitude=lat,
        longitude=lon,
        column_density=hcho_mol_m2_to_1e15_molec_cm2(hcho),
        station_count=int(count) if count is not None else None,
        stations=tuple(str(s) for s in stations),
        radius_km=radius if radius is not None and radius >= 0 else None,
        confidence=confidence,
        source_type=str(item.get("source_type") or "unknown"),
        observed_at=observed_at,
    )


def load_hotspots(path: str | Path) -> list[HotspotRecord]:
    """Load and validate cluster_summary.json. Raises HotspotFileError on contract violations."""
    file = Path(path)
    if not file.is_file():
        raise HotspotFileError(f"Hotspot file not found: {file}")
    try:
        payload = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise HotspotFileError(f"Cannot read hotspot file {file}: {exc}") from exc
    if not isinstance(payload, list):
        raise HotspotFileError("Hotspot file must contain a JSON list of clusters.")

    records = [_parse(item, i) for i, item in enumerate(payload)]
    logger.info("HCHO hotspot clusters loaded", file=file.name, clusters=len(records))
    return records
