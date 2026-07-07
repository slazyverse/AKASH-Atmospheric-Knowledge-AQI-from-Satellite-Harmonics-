"""
dashboard/services/api_client.py — Base HTTP client for VAYU-DRISHTI API.

This module defines:
  - APIError: typed exception hierarchy for service errors
  - APIClient: base HTTP client wrapping the `requests` library

Day 2 behaviour:
  All methods raise NotImplementedError or return stub data.
  No actual HTTP requests are made.

Day 3 behaviour:
  Replace stub bodies with actual `requests` calls.
  The interface (method signatures, return types) will NOT change.

Design decisions:
  - Client is stateless (no session stored between requests). Streamlit's
    execution model reruns the script on every interaction, so a persistent
    session object would not survive reruns anyway.
  - Typed exception hierarchy: callers catch specific subclasses
    (e.g., APITimeoutError) rather than inspecting raw HTTP status codes.
  - All methods return plain Python objects (dicts, lists, dataclasses)
    so pages are not coupled to the requests library Response type.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dashboard.core.config import dashboard_config


# ── Typed Exception Hierarchy ────────────────────────────────────────────────

class APIError(Exception):
    """Base class for all VAYU-DRISHTI API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class APIConnectionError(APIError):
    """Raised when the backend server cannot be reached."""


class APITimeoutError(APIError):
    """Raised when a request exceeds the configured timeout."""


class APINotFoundError(APIError):
    """Raised when the requested resource does not exist (HTTP 404)."""


class APIServerError(APIError):
    """Raised on unexpected backend failures (HTTP 5xx)."""


class APIValidationError(APIError):
    """Raised when the response payload fails schema validation."""


# ── Response wrapper ─────────────────────────────────────────────────────────

@dataclass
class APIResponse:
    """
    Thin wrapper around a successful API response.

    Attributes:
        status_code: HTTP status code of the response.
        data:        Parsed JSON payload as a Python dict/list.
        headers:     Selected response headers (e.g., X-Request-ID).
        latency_ms:  Round-trip latency in milliseconds.
    """
    status_code: int = 200
    data: Any = None
    headers: dict[str, str] = field(default_factory=dict)
    latency_ms: float = 0.0

    @property
    def is_ok(self) -> bool:
        return 200 <= self.status_code < 300


# ── Base API Client ───────────────────────────────────────────────────────────

class APIClient:
    """
    Base HTTP client for the VAYU-DRISHTI backend API.

    Usage (Day 3+):
        client = APIClient()
        response = client.get("/aqi/surface", params={"date": "2024-01-01"})

    Usage (Day 2 — all methods are stubs):
        client = APIClient()
        # client.get(...) will raise NotImplementedError until Day 3
    """

    def __init__(
        self,
        base_url: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self.base_url = (base_url or dashboard_config.api_v1_url).rstrip("/")
        self.timeout = timeout or dashboard_config.api_timeout_seconds

    def _build_url(self, path: str) -> str:
        """Construct the full endpoint URL from a relative path."""
        return f"{self.base_url}/{path.lstrip('/')}"

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> APIResponse:
        """
        Perform an HTTP GET request.

        Args:
            path:    API path relative to the v1 prefix (e.g., "/aqi/surface").
            params:  Query string parameters.
            headers: Additional request headers.

        Returns:
            APIResponse wrapping the parsed JSON payload.

        Raises:
            APIConnectionError: If the server is unreachable.
            APITimeoutError:    If the request exceeds `self.timeout` seconds.
            APINotFoundError:   On HTTP 404.
            APIServerError:     On HTTP 5xx.
            APIValidationError: If the response body is not valid JSON.

        Note (Day 2):
            Live HTTP requests are NOT implemented yet.
            This method returns a stub response for dashboard skeleton testing.
        """
        # ── Day 2 stub ────────────────────────────────────────────────────────
        # Replace this block in Day 3 with actual requests.get() call:
        #
        #   import requests, time
        #   url = self._build_url(path)
        #   try:
        #       t0 = time.monotonic()
        #       resp = requests.get(url, params=params, headers=headers,
        #                           timeout=self.timeout)
        #       latency = (time.monotonic() - t0) * 1000
        #       if resp.status_code == 404: raise APINotFoundError(...)
        #       if resp.status_code >= 500: raise APIServerError(...)
        #       return APIResponse(resp.status_code, resp.json(), dict(resp.headers), latency)
        #   except requests.ConnectionError: raise APIConnectionError(...)
        #   except requests.Timeout: raise APITimeoutError(...)

        return APIResponse(
            status_code=200,
            data={"stub": True, "path": path, "params": params},
            headers={"X-Request-ID": "stub-day2"},
            latency_ms=0.0,
        )

    def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> APIResponse:
        """
        Perform an HTTP POST request.

        Note (Day 2): Stub — no live request.
        """
        return APIResponse(
            status_code=201,
            data={"stub": True, "path": path},
            headers={"X-Request-ID": "stub-day2"},
            latency_ms=0.0,
        )

    def health_check(self) -> bool:
        """
        Probe the backend health endpoint.

        Returns:
            True if backend is reachable and healthy.
            False on any connection or server error.

        Note (Day 2): Always returns False (no live server expected).
        Day 3: Replace with:
            try:
                resp = self.get("/health")
                return resp.is_ok
            except APIError:
                return False
        """
        return False
