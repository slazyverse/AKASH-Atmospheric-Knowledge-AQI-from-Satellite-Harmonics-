"""
Version endpoint response schema.

Provides deployment metadata that is useful for:
  - Confirming which version is running after a deployment.
  - Canary deployment comparison (two instances reporting different versions).
  - Feature flag auditing (ENABLE_ML_ENDPOINTS field).
  - Support and incident investigations.
"""

from pydantic import BaseModel, Field


class VersionResponse(BaseModel):
    """Application version and deployment metadata."""

    name: str = Field(description="Application name.")
    version: str = Field(description="Semantic version string (MAJOR.MINOR.PATCH).")
    api_version: str = Field(description="Active API version prefix (e.g., 'v1').")
    environment: str = Field(
        description="Deployment environment (development | staging | production)."
    )
    python_version: str = Field(description="Python runtime version string.")
    data_sources: dict[str, str] = Field(
        default_factory=dict,
        description=(
            "Which source backs each domain: 'demo', 'dataset:<file>', 'hotspot_file', "
            "'simulated', 'artifact:<dir>' or 'none'. Lets clients label demo vs real data."
        ),
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "VAYU-DRISHTI",
                "version": "0.1.0",
                "api_version": "v1",
                "environment": "development",
                "python_version": "3.11.9",
                "data_sources": {
                    "stations": "demo", "aqi": "demo", "hcho": "demo",
                    "fire": "demo", "forecast": "simulated", "model": "none",
                },
            }
        }
    }
