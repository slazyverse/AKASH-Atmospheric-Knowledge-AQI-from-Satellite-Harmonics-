"""dashboard/services — Service layer providing typed API interfaces."""

from dashboard.services.api_client import (
    APIClient,
    APIConnectionError,
    APIError,
    APINotFoundError,
    APIResponse,
    APIServerError,
    APITimeoutError,
    APIValidationError,
)
from dashboard.services.aqi_service import SurfaceAQIService, surface_aqi_service
from dashboard.services.fire_service import FireMonitoringService, fire_service
from dashboard.services.forecast_service import ForecastService, forecast_service
from dashboard.services.hcho_service import HCHOService, hcho_service
from dashboard.services.report_service import ReportService, report_service
from dashboard.services.xai_service import XAIService, xai_service

__all__ = [
    # Base client + errors
    "APIClient", "APIResponse",
    "APIError", "APIConnectionError", "APITimeoutError",
    "APINotFoundError", "APIServerError", "APIValidationError",
    # Service singletons
    "surface_aqi_service",
    "hcho_service",
    "fire_service",
    "forecast_service",
    "xai_service",
    "report_service",
    # Service classes (for DI in tests)
    "SurfaceAQIService",
    "HCHOService",
    "FireMonitoringService",
    "ForecastService",
    "XAIService",
    "ReportService",
]
