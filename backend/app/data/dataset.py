"""
Loader for the team's station dataset (analysis_ready_dataset*.csv).

Contract (verified against the data pipeline on PR #7 / PR #8):
  v1  analysis_ready_dataset.csv     "Station ID", "Station Name", "State",
                                     "City", "Latitude", "Longitude", "Date",
                                     "Time", "AQI", pollutants, "HCHO",
                                     "HCHO Obs Date", ...
  v2  analysis_ready_dataset_v2.csv  "station_id", "station_name", "state",
                                     "city", "station_latitude",
                                     "station_longitude", "timestamp_utc_str", ...

Both are mapped onto one normalised Observation. Naive timestamps are read as
UTC and offset timestamps are converted to UTC. Nothing is imputed and source
values are never altered; the adapter only accepts or rejects:

  rejected rows (counted per reason in DatasetQuality)
    missing_station_id · invalid_timestamp · invalid_coordinates ·
    outside_india · invalid_aqi (missing / outside the 0–500 AQI scale) ·
    below_cpcb_minimum (an AQI reported with fewer than three pollutants or
    without PM2.5 / PM10 is not a CPCB AQI)
  duplicates
    identical rows for the same station and timestamp are collapsed;
    conflicting rows for the same station and timestamp are all dropped
  per-value normalisation
    negative / non-finite pollutant concentrations become missing (None)

Dataset-level findings that do not justify rejecting rows (shared coordinates,
an implausible CO unit, a single date, satellite dates far from station dates)
are reported as limitations, so the API and dashboard can restrict what they
show.

Satellite HCHO samples are collected separately (HCHOSample): a satellite value
does not depend on the ground AQI, so a row rejected only for its AQI still
contributes its HCHO sample. Samples need a station ID, coordinates inside
India, a finite HCHO value and a date — the satellite overpass date when the
dataset records "HCHO Obs Date" (undated values are then excluded rather than
mixed with station dates), otherwise the station observation date.
Pure standard library — no pandas dependency.
"""

from __future__ import annotations

import csv
import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from app.core.aqi import AQI_SCALE_MAX, meets_cpcb_minimum
from app.core.geo import SHARED_COORDINATE_LIMIT, in_india
from app.core.logging import get_logger
from app.core.units import CO_PLAUSIBLE_MEDIAN_MG_M3

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
    "hcho_obs_date": ("HCHO Obs Date", "hcho_obs_date"),
    "network": ("network_source", "Source", "data_source"),
    "elevation_m": ("elevation", "Elevation"),
    "timestamp": ("timestamp_utc_str", "timestamp_utc", "ts_utc"),
    "date": ("Date",),
    "time": ("Time",),
}

_REQUIRED = ("station_id", "station_name", "state", "latitude", "longitude", "aqi")
_POLLUTANTS = ("pm25", "pm10", "no2", "so2", "co", "o3")

# Satellite values matched more than this many days away from the station date
# are reported (the team collocation window is ±3 days).
SATELLITE_DATE_TOLERANCE_DAYS = 3

REJECTION_REASONS: tuple[str, ...] = (
    "missing_station_id",
    "invalid_timestamp",
    "invalid_coordinates",
    "outside_india",
    "invalid_aqi",
    "below_cpcb_minimum",
)


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
    # Date of the satellite overpass the HCHO value comes from (None = not recorded)
    hcho_observed_on: date | None = None

    @property
    def location(self) -> tuple[float, float]:
        """Coordinate key (≈1 m precision) used to detect shared locations."""
        return _location(self.latitude, self.longitude)


def _location(latitude: float, longitude: float) -> tuple[float, float]:
    return (round(latitude, 5), round(longitude, 5))


@dataclass(frozen=True)
class HCHOSample:
    """One satellite HCHO value sampled at a station's coordinates."""

    station_id: str
    location: tuple[float, float]
    observed_on: date            # satellite overpass date (or station date if not recorded)
    value_mol_m2: float
    station_date: date | None    # station observation date, when the row has one


@dataclass(frozen=True)
class DatasetQuality:
    """What the adapter accepted, rejected and found — reported by GET /sources."""

    rows_read: int
    rows_accepted: int
    rejected: dict[str, int]
    duplicates_collapsed: int
    conflicting_duplicates_dropped: int
    station_metadata_conflicts: int
    stations: int
    distinct_locations: int
    stations_sharing_coordinates: int
    first_date: date
    last_date: date
    co_median: float | None
    hcho_dates: tuple[date, date] | None
    max_satellite_offset_days: int | None
    pollutant_columns: tuple[str, ...] = field(default_factory=tuple)
    hcho_samples: int = 0
    hcho_satellite_dated: bool = False

    @property
    def approximate_coordinates(self) -> bool:
        return self.stations_sharing_coordinates > SHARED_COORDINATE_LIMIT * self.stations

    @property
    def co_unit_unverified(self) -> bool:
        return self.co_median is not None and self.co_median > CO_PLAUSIBLE_MEDIAN_MG_M3

    @property
    def satellite_date_mismatch(self) -> bool:
        return (
            self.max_satellite_offset_days is not None
            and self.max_satellite_offset_days > SATELLITE_DATE_TOLERANCE_DAYS
        )

    def station_limitations(self) -> list[tuple[str, str]]:
        """(code, message) findings for the station / AQI domains."""
        out: list[tuple[str, str]] = []
        if self.approximate_coordinates:
            out.append((
                "approximate_coordinates",
                f"{self.stations_sharing_coordinates} of {self.stations} stations share their "
                f"exact coordinates ({self.distinct_locations} distinct locations): the "
                "coordinates are city / registry fallbacks, not station positions. Station "
                "maps are withheld; tables and AQI values remain available.",
            ))
        rejected = sum(self.rejected.values())
        if rejected or self.conflicting_duplicates_dropped:
            reasons = ", ".join(f"{k}: {v}" for k, v in self.rejected.items() if v)
            if self.conflicting_duplicates_dropped:
                reasons = ", ".join(filter(None, [
                    reasons, f"conflicting_duplicates: {self.conflicting_duplicates_dropped}",
                ]))
            out.append((
                "rows_rejected",
                f"{rejected + self.conflicting_duplicates_dropped} of {self.rows_read} rows "
                f"rejected at the adapter ({reasons}).",
            ))
        if self.co_unit_unverified:
            out.append((
                "co_unit_unverified",
                f"CO median {self.co_median:g} is implausible in the contract unit mg/m³ "
                f"(CPCB 'Poor' starts at {CO_PLAUSIBLE_MEDIAN_MG_M3:g} mg/m³); CO is shown as "
                "reported, unit unverified.",
            ))
        if self.first_date == self.last_date:
            out.append((
                "single_date",
                f"The source covers a single date ({self.last_date}); station history has "
                "one point per station.",
            ))
        if self.station_metadata_conflicts:
            out.append((
                "station_metadata_conflicts",
                f"{self.station_metadata_conflicts} station IDs carry differing names or "
                "coordinates across rows; the latest row's metadata is used.",
            ))
        return out

    def hcho_limitations(self) -> list[tuple[str, str]]:
        """(code, message) findings for the station-collocated HCHO trend."""
        out: list[tuple[str, str]] = []
        if self.satellite_date_mismatch and self.hcho_dates:
            out.append((
                "satellite_date_mismatch",
                f"Satellite HCHO was observed {self.hcho_dates[0]}…{self.hcho_dates[1]}, up to "
                f"{self.max_satellite_offset_days} days from the station observation dates "
                f"({self.first_date}…{self.last_date}); the trend is dated by satellite "
                "observation date.",
            ))
        if self.approximate_coordinates:
            out.append((
                "approximate_coordinates",
                "HCHO was sampled at approximate (shared) station coordinates; each distinct "
                "location is counted once in the daily mean.",
            ))
        return out

    def as_dict(self) -> dict[str, Any]:
        return {
            "rows_read": self.rows_read,
            "rows_accepted": self.rows_accepted,
            **{f"rejected_{k}": v for k, v in self.rejected.items() if v},
            "duplicates_collapsed": self.duplicates_collapsed,
            "conflicting_duplicates_dropped": self.conflicting_duplicates_dropped,
            "station_metadata_conflicts": self.station_metadata_conflicts,
            "stations": self.stations,
            "distinct_locations": self.distinct_locations,
            "stations_sharing_coordinates": self.stations_sharing_coordinates,
            "coordinate_quality": "approximate" if self.approximate_coordinates else "reported",
            "first_date": str(self.first_date),
            "last_date": str(self.last_date),
            "co_median": self.co_median,
            "hcho_samples": self.hcho_samples,
            "hcho_date_basis": (
                "satellite_observation_date" if self.hcho_satellite_dated
                else "station_observation_date"
            ),
        }


def _resolve_columns(header: list[str]) -> dict[str, str]:
    present = set(header)
    resolved = {}
    for field_name, candidates in _ALIASES.items():
        for name in candidates:
            if name in present:
                resolved[field_name] = name
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


def _cell(row: dict[str, str | None], column: str) -> str:
    # csv.DictReader fills the missing cells of a short (ragged) row with None
    return (row.get(column) or "").strip()


def _timestamp(row: dict[str, str | None], cols: dict[str, str]) -> datetime | None:
    if "timestamp" in cols:
        text = _cell(row, cols["timestamp"])
    else:
        text = _cell(row, cols["date"])
        time_text = _cell(row, cols["time"]) if "time" in cols else ""
        if text and time_text:
            text = f"{text}T{time_text}"
    if not text:
        return None
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None
    # Normalise to UTC so date filters compare UTC calendar dates
    return parsed.astimezone(UTC) if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _date(text: str) -> date | None:
    try:
        return date.fromisoformat(text[:10]) if text else None
    except ValueError:
        return None


def _parse_row(row: dict[str, str | None], cols: dict[str, str]) -> Observation | str:
    """An Observation, or the rejection reason."""
    def get(field_name: str) -> str:
        return _cell(row, cols[field_name]) if field_name in cols else ""

    station_id = get("station_id")
    if not station_id:
        return "missing_station_id"
    observed_at = _timestamp(row, cols)
    if observed_at is None:
        return "invalid_timestamp"
    lat, lon = _float(get("latitude")), _float(get("longitude"))
    if lat is None or lon is None or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        return "invalid_coordinates"
    if not in_india(lat, lon):
        return "outside_india"
    aqi = _float(get("aqi"))
    if aqi is None or not 0 <= aqi <= AQI_SCALE_MAX:
        return "invalid_aqi"

    pollutants = {}
    for field_name in _POLLUTANTS:
        value = _float(get(field_name))
        pollutants[field_name] = value if value is not None and value >= 0 else None
    # The rule can only be checked when the source carries pollutant columns
    if any(p in cols for p in _POLLUTANTS) and not meets_cpcb_minimum(pollutants):
        return "below_cpcb_minimum"

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
        hcho_observed_on=_date(get("hcho_obs_date")),
        **pollutants,
    )


def _hcho_sample(row: dict[str, str | None], cols: dict[str, str]) -> HCHOSample | None:
    """The row's satellite HCHO sample, judged independently of its ground AQI."""
    if "hcho" not in cols:
        return None

    def get(field_name: str) -> str:
        return _cell(row, cols[field_name]) if field_name in cols else ""

    station_id, value = get("station_id"), _float(get("hcho"))
    lat, lon = _float(get("latitude")), _float(get("longitude"))
    if not station_id or value is None or lat is None or lon is None or not in_india(lat, lon):
        return None
    observed_at = _timestamp(row, cols)
    station_day = observed_at.date() if observed_at else None
    day = _date(get("hcho_obs_date")) if "hcho_obs_date" in cols else station_day
    if day is None:
        return None
    return HCHOSample(station_id, _location(lat, lon), day, value, station_day)


def _samples_from(observations: list[Observation]) -> list[HCHOSample]:
    return [
        HCHOSample(o.station_id, o.location, o.hcho_observed_on or o.observed_at.date(),
                   o.hcho_mol_m2, o.observed_at.date())
        for o in observations if o.hcho_mol_m2 is not None
    ]


def _deduplicate(observations: list[Observation]) -> tuple[list[Observation], int, int]:
    """Collapse identical duplicates; drop every row of a conflicting duplicate key."""
    groups: dict[tuple[str, datetime], list[Observation]] = defaultdict(list)
    for o in observations:
        groups[(o.station_id, o.observed_at)].append(o)
    kept: list[Observation] = []
    collapsed = conflicting = 0
    for group in groups.values():
        if len(group) == 1:
            kept.append(group[0])
        elif all(o == group[0] for o in group):
            kept.append(group[0])
            collapsed += len(group) - 1
        else:
            conflicting += len(group)
    return kept, collapsed, conflicting


def _assess(
    rows_read: int,
    rejected: Counter[str],
    observations: list[Observation],
    collapsed: int,
    conflicting: int,
    cols: dict[str, str],
    samples: list[HCHOSample],
) -> DatasetQuality:
    metadata: dict[str, set[tuple[str, tuple[float, float]]]] = defaultdict(set)
    latest: dict[str, Observation] = {}
    for o in observations:
        metadata[o.station_id].add((o.station_name, o.location))
        if o.station_id not in latest or o.observed_at > latest[o.station_id].observed_at:
            latest[o.station_id] = o
    per_location = Counter(o.location for o in latest.values())
    sharing = sum(n for n in per_location.values() if n > 1)

    co_values = [o.co for o in observations if o.co is not None]
    hcho_dates = sorted({s.observed_on for s in samples})
    offsets = [
        abs((s.observed_on - s.station_date).days) for s in samples if s.station_date
    ]
    days = [o.observed_at.date() for o in observations]
    return DatasetQuality(
        rows_read=rows_read,
        rows_accepted=len(observations),
        rejected={reason: rejected.get(reason, 0) for reason in REJECTION_REASONS},
        duplicates_collapsed=collapsed,
        conflicting_duplicates_dropped=conflicting,
        station_metadata_conflicts=sum(1 for v in metadata.values() if len(v) > 1),
        stations=len(latest),
        distinct_locations=len(per_location),
        stations_sharing_coordinates=sharing,
        first_date=min(days),
        last_date=max(days),
        co_median=round(statistics.median(co_values), 3) if co_values else None,
        hcho_dates=(hcho_dates[0], hcho_dates[-1]) if hcho_dates else None,
        max_satellite_offset_days=max(offsets) if offsets else None,
        pollutant_columns=tuple(p for p in _POLLUTANTS if p in cols),
        hcho_samples=len(samples),
        hcho_satellite_dated="hcho_obs_date" in cols,
    )


class StationDataset:
    """Read-only, query-friendly view over the loaded observations."""

    def __init__(
        self,
        observations: list[Observation],
        source_name: str,
        quality: DatasetQuality | None = None,
        hcho_samples: list[HCHOSample] | None = None,
    ) -> None:
        if not observations:
            raise DatasetError("Dataset contains no valid observations.")
        self.source_name = source_name
        self._observations = observations
        self._hcho_samples = (
            hcho_samples if hcho_samples is not None else _samples_from(observations)
        )
        self.quality = quality or _assess(
            len(observations), Counter(), observations, 0, 0, {}, self._hcho_samples
        )

    def __len__(self) -> int:
        return len(self._observations)

    @property
    def latest_date(self) -> date:
        return max(o.observed_at.date() for o in self._observations)

    @property
    def location_quality(self) -> str:
        """'approximate' when the dataset's coordinates are shared fallbacks, else 'reported'."""
        return "approximate" if self.quality.approximate_coordinates else "reported"

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

    @property
    def hcho_samples(self) -> tuple[HCHOSample, ...]:
        """Satellite HCHO samples (incl. rows rejected only for their ground AQI)."""
        return tuple(self._hcho_samples)

    @property
    def hcho_date_basis(self) -> str:
        return (
            "satellite_observation_date" if self.quality.hcho_satellite_dated
            else "station_observation_date"
        )

    def observations_for(self, station_id: str) -> list[Observation]:
        """All observations of one station, oldest first."""
        return sorted(
            (o for o in self._observations if o.station_id == station_id),
            key=lambda o: o.observed_at,
        )

    def latest_for(self, station_id: str) -> Observation | None:
        matches = [o for o in self._observations if o.station_id == station_id]
        return max(matches, key=lambda o: o.observed_at, default=None)

    def locations_by_name(self) -> dict[str, tuple[float, float]]:
        """Station name → coordinate key (latest row), for cross-checking derived outputs."""
        return {o.station_name: o.location for o in self.latest_per_station()}


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
    if not rows:
        raise DatasetError(f"Dataset {file.name} has a header but no rows.")

    parsed: list[Observation] = []
    rejected: Counter[str] = Counter()
    samples = [s for row in rows if (s := _hcho_sample(row, cols)) is not None]
    for row in rows:
        result = _parse_row(row, cols)
        if isinstance(result, str):
            rejected[result] += 1
        else:
            parsed.append(result)
    observations, collapsed, conflicting = _deduplicate(parsed)
    if not observations:
        raise DatasetError(
            f"Dataset {file.name} contains no valid observations "
            f"(rejected: {dict(rejected)}, conflicting duplicates: {conflicting})."
        )

    quality = _assess(len(rows), rejected, observations, collapsed, conflicting, cols, samples)
    logger.info(
        "Station dataset loaded",
        file=file.name,
        rows=len(rows),
        observations=len(observations),
        rejected=sum(rejected.values()),
        stations=quality.stations,
        distinct_locations=quality.distinct_locations,
    )
    return StationDataset(
        observations, source_name=file.name, quality=quality, hcho_samples=samples
    )
