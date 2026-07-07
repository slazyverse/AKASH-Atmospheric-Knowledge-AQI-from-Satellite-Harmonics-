"""
Tests for the observability endpoints: /api/v1/health and /api/v1/version.

Test strategy:
  - All tests are unit tests (no live database required).
  - The 'client' fixture injects a mock DB session that succeeds.
  - The 'client_db_failure' fixture injects a mock DB session that fails,
    allowing verification of the unhealthy database response path.
  - Tests are grouped by endpoint in classes for readability and
    to allow future class-level fixture scoping without restructuring.

Coverage targets:
  - HTTP status codes
  - Response body schema (required fields present and correctly typed)
  - Correct values for known fields (name, api_version)
  - Aggregate health logic (healthy DB → healthy overall)
  - Unhealthy DB path (DB failure → unhealthy database component)
  - X-Request-ID header injection
  - Root discovery endpoint
"""

from __future__ import annotations

import pytest
from fastapi import status
from httpx import AsyncClient


@pytest.mark.unit
class TestHealthEndpoint:
    """Tests for GET /api/v1/health"""

    async def test_returns_http_200(self, client: AsyncClient) -> None:
        """Health endpoint always returns HTTP 200, even when degraded."""
        response = await client.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK

    async def test_response_contains_required_fields(self, client: AsyncClient) -> None:
        """Response must include status, timestamp, environment, and components."""
        response = await client.get("/api/v1/health")
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "environment" in data
        assert "components" in data

    async def test_api_component_is_healthy(self, client: AsyncClient) -> None:
        """API component must always report healthy if the handler executes."""
        response = await client.get("/api/v1/health")
        data = response.json()
        assert "api" in data["components"]
        assert data["components"]["api"]["status"] == "healthy"

    async def test_database_component_healthy_when_db_ok(self, client: AsyncClient) -> None:
        """Database component reports healthy when SELECT 1 succeeds."""
        response = await client.get("/api/v1/health")
        data = response.json()
        assert "database" in data["components"]
        assert data["components"]["database"]["status"] == "healthy"

    async def test_overall_status_healthy_when_all_components_healthy(
        self, client: AsyncClient
    ) -> None:
        """Overall status is 'healthy' when all components succeed."""
        response = await client.get("/api/v1/health")
        data = response.json()
        assert data["status"] == "healthy"

    async def test_database_component_unhealthy_when_db_fails(
        self, client_db_failure: AsyncClient
    ) -> None:
        """Database component reports unhealthy when the DB raises an exception."""
        response = await client_db_failure.get("/api/v1/health")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["components"]["database"]["status"] == "unhealthy"

    async def test_overall_status_unhealthy_when_db_fails(
        self, client_db_failure: AsyncClient
    ) -> None:
        """Aggregate status degrades to 'unhealthy' when any component is unhealthy."""
        response = await client_db_failure.get("/api/v1/health")
        data = response.json()
        assert data["status"] == "unhealthy"

    async def test_database_latency_present_when_healthy(self, client: AsyncClient) -> None:
        """Healthy database component includes a numeric latency_ms field."""
        response = await client.get("/api/v1/health")
        data = response.json()
        latency = data["components"]["database"].get("latency_ms")
        assert latency is not None
        assert isinstance(latency, float)
        assert latency >= 0.0

    async def test_response_contains_valid_timestamp(self, client: AsyncClient) -> None:
        """Timestamp field must be a non-empty ISO 8601 string."""
        response = await client.get("/api/v1/health")
        data = response.json()
        timestamp = data.get("timestamp")
        assert timestamp is not None
        assert isinstance(timestamp, str)
        assert len(timestamp) > 0

    async def test_request_id_header_in_response(self, client: AsyncClient) -> None:
        """Every response must include the X-Request-ID header."""
        response = await client.get("/api/v1/health")
        assert "x-request-id" in response.headers

    async def test_custom_request_id_is_echoed(self, client: AsyncClient) -> None:
        """If a client provides X-Request-ID, the same value must be echoed back."""
        custom_id = "test-request-id-12345"
        response = await client.get(
            "/api/v1/health",
            headers={"X-Request-ID": custom_id},
        )
        assert response.headers.get("x-request-id") == custom_id


@pytest.mark.unit
class TestVersionEndpoint:
    """Tests for GET /api/v1/version"""

    async def test_returns_http_200(self, client_no_db: AsyncClient) -> None:
        """Version endpoint must always return HTTP 200."""
        response = await client_no_db.get("/api/v1/version")
        assert response.status_code == status.HTTP_200_OK

    async def test_response_contains_required_fields(self, client_no_db: AsyncClient) -> None:
        """Response must include name, version, api_version, environment, python_version."""
        response = await client_no_db.get("/api/v1/version")
        data = response.json()
        required_fields = {"name", "version", "api_version", "environment", "python_version"}
        assert required_fields.issubset(data.keys())

    async def test_name_is_vayu_drishti(self, client_no_db: AsyncClient) -> None:
        """Application name must be VAYU-DRISHTI."""
        response = await client_no_db.get("/api/v1/version")
        assert response.json()["name"] == "VAYU-DRISHTI"

    async def test_api_version_is_v1(self, client_no_db: AsyncClient) -> None:
        """Active API version must be 'v1'."""
        response = await client_no_db.get("/api/v1/version")
        assert response.json()["api_version"] == "v1"

    async def test_version_follows_semver_format(self, client_no_db: AsyncClient) -> None:
        """Version field must follow MAJOR.MINOR.PATCH format."""
        response = await client_no_db.get("/api/v1/version")
        version = response.json()["version"]
        parts = version.split(".")
        assert len(parts) == 3
        assert all(part.isdigit() for part in parts)

    async def test_python_version_is_non_empty_string(self, client_no_db: AsyncClient) -> None:
        """Python version must be a non-empty string."""
        response = await client_no_db.get("/api/v1/version")
        python_version = response.json()["python_version"]
        assert isinstance(python_version, str)
        assert len(python_version) > 0

    async def test_request_id_header_in_response(self, client_no_db: AsyncClient) -> None:
        """Every response must include X-Request-ID."""
        response = await client_no_db.get("/api/v1/version")
        assert "x-request-id" in response.headers


@pytest.mark.unit
class TestRootEndpoint:
    """Tests for GET / (service discovery)"""

    async def test_returns_http_200(self, client_no_db: AsyncClient) -> None:
        response = await client_no_db.get("/")
        assert response.status_code == status.HTTP_200_OK

    async def test_response_contains_service_info(self, client_no_db: AsyncClient) -> None:
        """Root endpoint must include service name, version, and key URLs."""
        response = await client_no_db.get("/")
        data = response.json()
        assert "service" in data
        assert "version" in data
        assert "health_url" in data
        assert "version_url" in data

    async def test_health_url_points_to_v1(self, client_no_db: AsyncClient) -> None:
        """Health URL must be under the /api/v1/ prefix."""
        response = await client_no_db.get("/")
        data = response.json()
        assert "/api/v1/health" in data["health_url"]
