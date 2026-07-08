"""
dashboard/services/api_client.py — Base HTTP client for VAYU-DRISHTI API.

This module defines:
  - APIError: typed exception hierarchy for service errors
  - APIClient: production HTTP client wrapping the `requests` library

Day 3 behaviour (this file):
  All methods perform real HTTP requests against the VAYU-DRISHTI FastAPI backend.
  Every known failure mode (connection refused, timeout, 404, 5xx, bad JSON)
  is caught and mapped to the typed exception hierarchy defined below.
  The interface (method signatures, return types) is identical to the Day 2 stubs
  so all callers require zero changes.

Design decisions:
  - Client is stateless (no session stored between requests). Streamlit's
    execution model reruns the script on every interaction, so a persistent
    session object would not survive reruns anyway. requests.get() creates a
    fresh connection each call (connection pooling is handled at the OS level).
  - Typed exception hierarchy: callers catch specific subclasses
    (e.g., APITimeoutError) rather than inspecting raw HTTP status codes.
  - All methods return plain Python objects (dicts, lists, dataclasses)
    so pages are not coupled to the requests library Response type.
  - health_check() is intentionally lightweight — it calls GET /health and
    returns True/False without raising. The sidebar calls this on every
    Streamlit rerun so it must never crash the app.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any

import requests

from dashboard.core.config import dashboard_config


# ── Typed Exception Hierarchy ────────────────────────────────────────────────

class APIError(Exception):
    """Base class for all VAYU-DRISHTI API errors."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class APIConnectionError(APIError):
    """Raised when the backend server cannot be reached (connection refused, DNS failure)."""


class APITimeoutError(APIError):
    """Raised when a request exceeds the configured timeout."""


class APINotFoundError(APIError):
    """Raised when the requested resource does not exist (HTTP 404)."""


class APIServerError(APIError):
    """Raised on unexpected backend failures (HTTP 5xx)."""


class APIValidationError(APIError):
    """Raised when the response payload fails JSON parsing or schema validation."""


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
    Production HTTP client for the VAYU-DRISHTI backend API.

    Usage:
        client = APIClient()
        response = client.get("/aqi/daily", params={"region": "India"})
        data = response.data

    All network errors are mapped to the typed APIError hierarchy.
    Callers should catch the specific subclass they care about:

        try:
            resp = client.get("/aqi/daily")
        except APITimeoutError:
            st.warning("Backend timed out — retrying...")
        except APIConnectionError:
            st.error("Backend offline.")
        except APIError as e:
            st.error(str(e))
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

    def _parse_json(self, response: requests.Response, url: str) -> Any:
        """
        Parse JSON from a requests Response.

        Raises:
            APIValidationError: if the body is not valid JSON.
        """
        try:
            return response.json()
        except (json.JSONDecodeError, ValueError) as exc:
            raise APIValidationError(
                f"Backend returned non-JSON response from {url}: {exc}",
                status_code=response.status_code,
            ) from exc

    def get(
        self,
        path: str,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
        timeout: float | None = None,
    ) -> APIResponse:
        """
        Perform an HTTP GET request against the VAYU-DRISHTI backend.

        Args:
            path:    API path relative to the v1 prefix (e.g., "/aqi/daily").
            params:  Query string parameters.
            headers: Additional request headers merged with defaults.

        Returns:
            APIResponse wrapping the parsed JSON payload.

        Raises:
            APIConnectionError: If the server is unreachable (refused / DNS failure).
            APITimeoutError:    If the request exceeds `self.timeout` seconds.
            APINotFoundError:   On HTTP 404.
            APIServerError:     On HTTP 5xx.
            APIValidationError: If the response body is not valid JSON.
        """
        url = self._build_url(path)
        request_headers: dict[str, str] = {"Accept": "application/json"}
        if headers:
            request_headers.update(headers)

        req_timeout = timeout if timeout is not None else self.timeout
        try:
            t0 = time.monotonic()
            resp = requests.get(
                url,
                params=params,
                headers=request_headers,
                timeout=req_timeout,
            )
            latency_ms = (time.monotonic() - t0) * 1000

        except requests.exceptions.ConnectionError as exc:
            raise APIConnectionError(
                f"Cannot reach VAYU-DRISHTI backend at {url}. "
                f"Is the server running? ({type(exc).__name__})"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise APITimeoutError(
                f"Request to {url} timed out after {req_timeout}s.",
            ) from exc
        except requests.exceptions.RequestException as exc:
            # Catch-all for any other requests library error (SSL, proxy, etc.)
            raise APIConnectionError(
                f"Unexpected network error reaching {url}: {exc}",
            ) from exc

        # ── HTTP error mapping ────────────────────────────────────────────────
        if resp.status_code == 404:
            data = self._parse_json(resp, url)
            error_msg = data.get("error", {}).get("message", "Resource not found.")
            raise APINotFoundError(
                f"[404] {error_msg} — {url}",
                status_code=404,
            )

        if resp.status_code >= 500:
            raise APIServerError(
                f"Backend error {resp.status_code} from {url}. "
                "The server encountered an unexpected condition.",
                status_code=resp.status_code,
            )

        if not resp.ok:
            # 4xx other than 404 (e.g., 422 validation error)
            data = self._parse_json(resp, url)
            msg = data.get("error", {}).get("message", f"HTTP {resp.status_code}")
            raise APIValidationError(
                f"[{resp.status_code}] {msg} — {url}",
                status_code=resp.status_code,
            )

        # ── Successful response ───────────────────────────────────────────────
        parsed_data = self._parse_json(resp, url)

        return APIResponse(
            status_code=resp.status_code,
            data=parsed_data,
            headers={
                "X-Request-ID": resp.headers.get("X-Request-ID", ""),
                "Content-Type": resp.headers.get("Content-Type", ""),
            },
            latency_ms=round(latency_ms, 2),
        )

    def post(
        self,
        path: str,
        json: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> APIResponse:
        """
        Perform an HTTP POST request against the VAYU-DRISHTI backend.

        Args:
            path:    API path relative to the v1 prefix.
            json:    Request body as a Python dict (serialised to JSON).
            headers: Additional request headers.

        Returns:
            APIResponse wrapping the parsed JSON payload.

        Raises:
            APIConnectionError, APITimeoutError, APIServerError, APIValidationError.
        """
        url = self._build_url(path)
        request_headers: dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if headers:
            request_headers.update(headers)

        try:
            t0 = time.monotonic()
            resp = requests.post(
                url,
                json=json,
                headers=request_headers,
                timeout=self.timeout,
            )
            latency_ms = (time.monotonic() - t0) * 1000
        except requests.exceptions.ConnectionError as exc:
            raise APIConnectionError(
                f"Cannot reach VAYU-DRISHTI backend at {url}.",
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise APITimeoutError(
                f"POST to {url} timed out after {self.timeout}s.",
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise APIConnectionError(str(exc)) from exc

        if resp.status_code >= 500:
            raise APIServerError(
                f"Backend error {resp.status_code} from {url}.",
                status_code=resp.status_code,
            )

        parsed_data = self._parse_json(resp, url)

        return APIResponse(
            status_code=resp.status_code,
            data=parsed_data,
            headers={"X-Request-ID": resp.headers.get("X-Request-ID", "")},
            latency_ms=round(latency_ms, 2),
        )

    def health_check(self, timeout: float | None = None) -> bool:
        """
        Probe the backend health/version endpoint and return True if reachable and healthy.

        This method is intentionally silent — it never raises. The sidebar
        calls it on every Streamlit rerun and must not crash the app if the
        backend is offline.

        Returns:
            True  — backend is reachable and returned a 200 OK response.
            False — any network error, timeout, or non-2xx response.
        """
        try:
            # Query /version instead of /health because /health returns 503 when the local 
            # database is down, even though the backend service is fully alive and serving mock data.
            resp = self.get("/version", timeout=timeout)
            return resp.is_ok
        except APIError:
            return False
        except Exception:  # pragma: no cover — belt-and-suspenders catch-all
            return False
