"""
backend/app/services — Business-logic service layer.

One module per domain. Endpoints import from here to keep coupling explicit.

Day 1 services: BaseService (abstract contract)
Day 3 services: AQIService, HCHOService, FireService, ForecastService, StationService
"""

# ── Day 1 — Abstract base contract ────────────────────────────────────────────
from app.services.base import BaseService

# ── Day 3 — Concrete domain services ──────────────────────────────────────────
from app.services.aqi_service import AQIService, aqi_service
from app.services.fire_service import FireService, fire_service
from app.services.forecast_service import ForecastService, forecast_service
from app.services.hcho_service import HCHOService, hcho_service
from app.services.station_service import StationService, station_service

__all__ = [
    # Abstract base
    "BaseService",
    # Service classes (for DI / testing)
    "AQIService",
    "HCHOService",
    "FireService",
    "ForecastService",
    "StationService",
    # Module-level singletons
    "aqi_service",
    "hcho_service",
    "fire_service",
    "forecast_service",
    "station_service",
]
