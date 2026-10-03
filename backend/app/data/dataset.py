"""
Loader for the team's station dataset (analysis_ready_dataset*.csv).

Contract (verified against the data pipeline):
  v1  analysis_ready_dataset.csv     "Station ID", "Station Name", "State",
                                     "City", "Latitude", "Longitude", "Date",
                                     "Time", "AQI", pollutants, "HCHO", ...
  v2  analysis_ready_dataset_v2.csv  "station_id", "station_name", "state",
                                     "city", "station_latitude",
                                     "station_longitude", "timestamp_utc_str", ...

Both are mapped onto one normalised Observation. Naive timestamps are read as
UTC and offset timestamps are converted to UTC. Rows without a usable station
ID, coordinates or AQI are skipped and counted; nothing is imputed.
Pure standard library — no pandas dependency.
"""

from __future__ import annotations

import csv
import math
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from app.core.logging import get_logger

logger = get_logger(__name__)


class DatasetError(ValueError):
    """The configured dataset is missing, unreadable or violates the contract."""


# Canonical field → accepted column names (first match wins).
_ALIASES: dict[str, tuple[str, ...]] = {
    "station_id": ("Station ID", "station_id"),
    "station_name": ("Station Name", "station_name", "station"),
    "state": ("State", "state"),
    "city": ("City", "city"),
    "latitude": ("Latitude", "station_latitude", "latitude"),
    "longitude": ("Longitude", "station_longitude", "longitude"),
    "aqi": ("AQI",),
    "pm25": ("PM2.5",),
    "pm10": ("PM10",),
    "no2": ("NO2",),
    "so2": ("SO2",),
    "co": ("CO",),
    "o3": ("O3",),
    "hcho": ("HCHO",),
    "network": ("network_source", "Source", "data_source"),
    "elevation_m": ("elevation", "Elevation"),
    "timestamp": ("timestamp_utc_str", "timestamp_utc", "ts_utc"),
    "date": ("Date",),
    "time": ("Time",),
}

_REQUIRED = ("station_id", "station_name", "state", "latitude", "longitude", "aqi")
_POLLUTANTS = ("pm25", "pm10", "no2", "so2", "co", "o3")


@dataclass(frozen=True)
class Observation:
    """One station observation, normalised from either dataset version."""

    station_id: str
    station_name: str
    state: str
    city: str
    latitude: float
    longitude: float
    network: str | None
    elevation_m: float | None
    observed_at: datetime
    aqi: int
    pm25: float | None
    pm10: float | None
    no2: float | None
    so2: float | None
    co: float | None
    o3: float | None
    hcho_mol_m2: float | None


def _resolve_columns(header: list[str]) -> dict[str, str]:
    present = set(header)
    resolved = {}
    for field, candidates in _ALIASES.items():
        for name in candidates:
            if name in present:
                resolved[field] = name
                break
    return resolved


def _float(raw: str | None) -> float | None:
    if raw is None or raw.strip() == "":
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _timestamp(row: dict[str, str], cols: dict[str, str]) -> datetime | None:
    if "timestamp" in cols:
        text = row.get(cols["timestamp"], "").strip()
    else:
        text = row.get(cols["date"], "").strip()
        if text and "time" in cols and row.get(cols["time"], "").strip():
            text = f"{text}T{row[cols['time']].strip()}"
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    # Normalise to UTC so date filters compare UTC calendar dates
    return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _parse_row(row: dict[str, str], cols: dict[str, str]) -> Observation | None:
    def get(field: str) -> str:
        return row.get(cols[field], "").strip() if field in cols else ""

    station_id = get("station_id")
    lat, lon = _float(get("latitude")), _float(get("longitude"))
    aqi = _float(get("aqi"))
    observed_at = _timestamp(row, cols)
    if (
        not station_id
        or lat is None or not -90 <= lat <= 90
        or lon is None or not -180 <= lon <= 180
        or aqi is None or not 0 <= aqi <= 1000
        or observed_at is None
    ):
        return None

    pollutants = {}
    for field in _POLLUTANTS:
        value = _float(get(field))
        pollutants[field] = value if value is not None and value >= 0 else None

    return Observation(
        station_id=station_id,
        station_name=get("station_name") or station_id,
        state=get("state"),
        city=get("city"),
        latitude=lat,
        longitude=lon,
        network=get("network") or None,
        elevation_m=_float(get("elevation_m")),
        observed_at=observed_at,
        aqi=round(aqi),
        hcho_mol_m2=_float(get("hcho")),
        **pollutants,
    )


class StationDataset:
    """Read-only, query-friendly view over the loaded observations."""

    def __init__(self, observations: list[Observation], source_name: str) -> None:
        if not observations:
            raise DatasetError("Dataset contains no valid observations.")
        self.source_name = source_name
        self._observations = observations

    def __len__(self) -> int:
        return len(self._observations)

    @property
    def latest_date(self) -> date:
        return max(o.observed_at.date() for o in self._observations)

    def latest_per_station(self, on_date: date | None = None) -> list[Observation]:
        """Latest observation for each station (optionally restricted to one UTC date)."""
        latest: dict[str, Observation] = {}
        for o in self._observations:
            if on_date is not None and o.observed_at.date() != on_date:
                continue
            current = latest.get(o.station_id)
            if current is None or o.observed_at > current.observed_at:
                latest[o.station_id] = o
        return list(latest.values())

    @property
    def observations(self) -> tuple[Observation, ...]:
        return tuple(self._observations)

    def observations_for(self, station_id: str) -> list[Observation]:
        """All observations of one station, oldest first."""
        return sorted(
            (o for o in self._observations if o.station_id == station_id),
            key=lambda o: o.observed_at,
        )

    def latest_for(self, station_id: str) -> Observation | None:
        matches = [o for o in self._observations if o.station_id == station_id]
        return max(matches, key=lambda o: o.observed_at, default=None)


def load_dataset(path: str | Path) -> StationDataset:
    """Load and validate a station dataset CSV. Raises DatasetError on contract violations."""
    file = Path(path)
    if not file.is_file():
        raise DatasetError(f"Dataset file not found: {file}")

    try:
        with file.open(newline="", encoding="utf-8-sig") as fh:
            reader = csv.DictReader(fh)
            header = reader.fieldnames or []
            cols = _resolve_columns(header)
            missing = [f for f in _REQUIRED if f not in cols]
            if "timestamp" not in cols and "date" not in cols:
                missing.append("timestamp|date")
            if missing:
                raise DatasetError(
                    f"Dataset {file.name} is missing required columns: {missing}. "
                    f"Accepted names: { {f: _ALIASES[f.split('|')[0]] for f in missing} }"
                )
            rows = list(reader)
    except (OSError, UnicodeDecodeError, csv.Error) as exc:
        raise DatasetError(f"Cannot read dataset {file}: {exc}") from exc

    observations = [obs for row in rows if (obs := _parse_row(row, cols)) is not None]
    skipped = len(rows) - len(observations)
    if not rows:
        raise DatasetError(f"Dataset {file.name} has a header but no rows.")

    logger.info(
        "Station dataset loaded",
        file=file.name,
        rows=len(rows),
        observations=len(observations),
        skipped_rows=skipped,
    )
    return StationDataset(observations, source_name=file.name)
