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
  GET /api/v1/aqi/daily     — Surface AQI daily summary + station readings (dataset or demo)
  GET /api/v1/hcho/hotspots — HCHO concentration hotspots (hotspot file or demo)
  GET /api/v1/fire          — Active fire detections + alerts (demo data)
  GET /api/v1/forecast      — Up-to-72-hour AQI forecast (simulated; no forecasting model)
  GET /api/v1/stations      — Monitoring station registry (dataset or demo)
  GET /api/v1/xai/global-importance — Trained-model metrics + importances (404 until loaded)

  Domain endpoints switch from demo data to the team's outputs when
  DATASET_PATH / HCHO_HOTSPOTS_PATH / ML_MODEL_PATH are configured.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import health, version
from app.api.v1.endpoints import aqi, fire, forecast, hcho, stations, xai

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

# ── Day 5 — Model explanation ────────────────────────────────────────────────
router.include_router(xai.router)
