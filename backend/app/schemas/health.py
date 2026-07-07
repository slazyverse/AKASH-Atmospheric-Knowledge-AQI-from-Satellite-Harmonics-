"""
Health check response schema.

Inspired by the IETF Health Check Response Format for HTTP APIs
(draft-inadarei-api-health-check). The 'components' field allows
monitoring systems to pinpoint which subsystem is degraded without
needing to parse free-text messages.

Status semantics:
  - healthy:   The component is operating normally.
  - degraded:  The component is functioning but with reduced performance
               or intermittent errors. Traffic should continue but the
               issue warrants investigation.
  - unhealthy: The component has failed. Dependent operations will fail.
               Traffic may need to be redirected.

Aggregate status follows the worst-case rule:
  - Any 'unhealthy' component → overall 'unhealthy'.
  - Any 'degraded' (but no 'unhealthy') → overall 'degraded'.
  - All 'healthy' → overall 'healthy'.
"""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ComponentStatus(StrEnum):
    """Health status for an individual service component."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class OverallStatus(StrEnum):
    """Aggregate health status for the entire service."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ComponentHealth(BaseModel):
    """Health status report for a single service component."""

    status: ComponentStatus = Field(description="Operational status of this component.")
    latency_ms: float | None = Field(
        default=None,
        description="Round-trip latency in milliseconds, if measurable.",
    )
    detail: str | None = Field(
        default=None,
        description="Human-readable status detail or error description.",
    )


class HealthResponse(BaseModel):
    """Complete health check response returned by GET /api/v1/health."""

    status: OverallStatus = Field(
        description="Aggregate health status. 'healthy' means all components are operational."
    )
    timestamp: datetime = Field(description="UTC timestamp when this health check was performed.")
    environment: str = Field(description="Deployment environment (development | staging | production).")
    components: dict[str, ComponentHealth] = Field(
        description=(
            "Per-component health breakdown. Keys are component names "
            "(e.g., 'database', 'cache', 'ml_engine'). "
            "Additional components are added as new dependencies are introduced."
        )
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "timestamp": "2026-07-06T18:00:00Z",
                "environment": "development",
                "components": {
                    "api": {
                        "status": "healthy",
                        "detail": "Request handler reachable.",
                    },
                    "database": {
                        "status": "healthy",
                        "latency_ms": 3.2,
                        "detail": "Connection pool healthy.",
                    },
                },
            }
        }
    }
