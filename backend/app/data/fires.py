"""
Loader for active-fire detections (FIRE_EVENTS_PATH).

No team fire source exists yet. This module defines the normalised contract a
future source (e.g. a NASA FIRMS export) must be converted to — a JSON list of
detections:

  required  event_id, latitude, longitude, frp (MW), brightness (K),
            satellite, confidence, detected_at (ISO-8601; naive = UTC)
  optional  land_cover, state, district  (default "unknown")

Nothing is inferred: alerts are derived later by a documented FRP rule, and no
AQI-impact or smoke-trajectory value is produced (no such model exists).
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

_REQUIRED = (
    "event_id", "latitude", "longitude", "frp", "brightness",
    "satellite", "confidence", "detected_at",
)


class FireFileError(ValueError):
    """The configured fire file is missing, unreadable or violates the contract."""


@dataclass(frozen=True)
class FireRecord:
    event_id: str
    latitude: float
    longitude: float
    frp: float
    brightness: float
    satellite: str
    confidence: str
    land_cover: str
    state: str
    district: str
    detected_at: datetime


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, int | float):
        return None
    return float(value) if math.isfinite(value) else None


def _parse(item: Any, index: int) -> FireRecord:
    if not isinstance(item, dict):
        raise FireFileError(f"Detection #{index} is not an object.")
    missing = [k for k in _REQUIRED if k not in item]
    if missing:
        raise FireFileError(f"Detection #{index} is missing required keys: {missing}")

    lat, lon = _number(item["latitude"]), _number(item["longitude"])
    frp, brightness = _number(item["frp"]), _number(item["brightness"])
    if lat is None or not -90 <= lat <= 90 or lon is None or not -180 <= lon <= 180:
        raise FireFileError(f"Detection #{index} has invalid coordinates.")
    if frp is None or frp < 0:
        raise FireFileError(f"Detection #{index} has an invalid frp.")
    if brightness is None or brightness < 200:
        raise FireFileError(f"Detection #{index} has an invalid brightness (K, >= 200).")
    try:
        detected = datetime.fromisoformat(str(item["detected_at"]).replace("Z", "+00:00"))
    except ValueError as exc:
        raise FireFileError(f"Detection #{index} has an invalid detected_at.") from exc

    return FireRecord(
        event_id=str(item["event_id"]),
        latitude=lat,
        longitude=lon,
        frp=frp,
        brightness=brightness,
        satellite=str(item["satellite"]),
        confidence=str(item["confidence"]),
        land_cover=str(item.get("land_cover") or "unknown"),
        state=str(item.get("state") or "unknown"),
        district=str(item.get("district") or "unknown"),
        detected_at=detected.astimezone(UTC) if detected.tzinfo else detected.replace(tzinfo=UTC),
    )


def load_fires(path: str | Path) -> list[FireRecord]:
    """Load and validate a fire-detection file. Raises FireFileError on contract violations."""
    file = Path(path)
    if not file.is_file():
        raise FireFileError(f"Fire file not found: {file}")
    try:
        payload = json.loads(file.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FireFileError(f"Cannot read fire file {file}: {exc}") from exc
    if not isinstance(payload, list):
        raise FireFileError("Fire file must contain a JSON list of detections.")

    records = [_parse(item, i) for i, item in enumerate(payload)]
    ids = [r.event_id for r in records]
    if len(ids) != len(set(ids)):
        raise FireFileError("Fire file contains duplicate event_id values.")
    logger.info("Fire detections loaded", file=file.name, detections=len(records))
    return records
