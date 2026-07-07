"""
API v1 master router.

This module is the single registration point for all v1 endpoint routers.
Adding a new domain to the API requires only:
  1. Create app/api/v1/endpoints/<domain>.py with a module-level APIRouter.
  2. Import it here and call router.include_router().

Router tags and prefixes can be overridden at include time to keep
individual endpoint modules free of URL path concerns.

Current v1 endpoints:
  GET /api/v1/health        — Service health check (observability)
  GET /api/v1/version       — Application version metadata (observability)
  GET /api/v1/aqi/daily     — Surface AQI daily summary + station readings
  GET /api/v1/hcho/hotspots — HCHO concentration hotspots (Sentinel-5P)
  GET /api/v1/fire          — Active fire detections + alerts (MODIS/VIIRS)
  GET /api/v1/forecast      — 72-hour AQI forecast with confidence intervals
  GET /api/v1/stations      — CPCB monitoring station registry
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health, version
from app.api.v1.endpoints import aqi, fire, forecast, hcho, stations

router = APIRouter()

# ── Day 1 — Observability ─────────────────────────────────────────────────────
router.include_router(health.router)
router.include_router(version.router)

# ── Day 3 — Domain Data Endpoints ─────────────────────────────────────────────
router.include_router(aqi.router)
router.include_router(hcho.router)
router.include_router(fire.router)
router.include_router(forecast.router)
router.include_router(stations.router)
