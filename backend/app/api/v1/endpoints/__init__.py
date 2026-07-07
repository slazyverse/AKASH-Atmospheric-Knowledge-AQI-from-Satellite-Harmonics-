"""
backend/app/api/v1/endpoints — Route handler modules.

One file per API domain. Each module exposes a single `router = APIRouter()`
that is registered in the parent `router.py`.

Day 1: health, version  (observability)
Day 3: aqi, hcho, fire, forecast, stations  (domain data)
"""
