"""
backend/app/schemas — Pydantic v2 request and response models.

One module per domain.  Import from here rather than from sub-modules
to keep consumers decoupled from internal organisation.

Day 1 schemas: health, version
Day 3 schemas: aqi, hcho, fire, forecast, stations
"""

# ── Observability (Day 1) ─────────────────────────────────────────────────────
from app.schemas.health import (
    ComponentHealth,
    ComponentStatus,
    HealthResponse,
    OverallStatus,
)
from app.schemas.version import VersionResponse

# ── AQI (Day 3) ───────────────────────────────────────────────────────────────
from app.schemas.aqi import (
    AQIDailyListResponse,
    AQIDailySummary,
    StationReading,
)

# ── HCHO (Day 3) ──────────────────────────────────────────────────────────────
from app.schemas.hcho import (
    HCHOHotspotItem,
    HCHOHotspotsResponse,
)

# ── Fire (Day 3) ──────────────────────────────────────────────────────────────
from app.schemas.fire import (
    FireAlertItem,
    FireEventItem,
    FireResponse,
)

# ── Forecast (Day 3) ──────────────────────────────────────────────────────────
from app.schemas.forecast import (
    FeatureImportance,
    ForecastResponse,
    ForecastStep,
    ModelMetrics,
)

# ── Stations (Day 3) ──────────────────────────────────────────────────────────
from app.schemas.stations import (
    StationItem,
    StationsResponse,
)

__all__ = [
    # Observability
    "ComponentHealth", "ComponentStatus", "HealthResponse", "OverallStatus",
    "VersionResponse",
    # AQI
    "StationReading", "AQIDailySummary", "AQIDailyListResponse",
    # HCHO
    "HCHOHotspotItem", "HCHOHotspotsResponse",
    # Fire
    "FireEventItem", "FireAlertItem", "FireResponse",
    # Forecast
    "ForecastStep", "ModelMetrics", "FeatureImportance", "ForecastResponse",
    # Stations
    "StationItem", "StationsResponse",
]
