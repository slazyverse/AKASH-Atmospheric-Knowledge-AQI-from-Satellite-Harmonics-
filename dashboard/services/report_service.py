"""
dashboard/services/report_service.py — Report generation service interface.

Provides access to generated analytical reports: PDF bulletins, CSV exports,
and scheduled summary emails.

Day 2: All methods return typed stub data.
Day 3: Replace stub bodies with APIClient calls.

API endpoints this service will consume (Day 3+):
  GET  /api/v1/reports              — List available reports with metadata
  GET  /api/v1/reports/{id}         — Download a specific report
  POST /api/v1/reports/generate     — Trigger on-demand report generation
  GET  /api/v1/reports/templates    — List report templates
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from dashboard.services.api_client import APIClient


@dataclass
class ReportMetadata:
    """Metadata for a generated report document."""
    report_id: str
    title: str
    report_type: str                # daily_bulletin | weekly_summary | custom
    format: str                     # pdf | csv | json
    size_kb: int
    generated_at: datetime = field(default_factory=datetime.utcnow)
    status: str = "ready"           # ready | generating | failed


class ReportService:
    """Manages report generation and retrieval."""

    def __init__(self, client: APIClient | None = None) -> None:
        self._client = client or APIClient()

    def list_reports(
        self,
        report_type: str | None = None,
        limit: int = 20,
    ) -> list[ReportMetadata]:
        """
        List available reports.

        Day 2: Returns 4 stub report entries.
        Day 3: resp = self._client.get("/reports", params={"type": report_type, "limit": limit})
        """
        return [
            ReportMetadata("RPT-001", "India AQI Daily Bulletin — 2024-01-15", "daily_bulletin",  "pdf", 824),
            ReportMetadata("RPT-002", "HCHO Hotspot Analysis — Week 3, 2024",  "weekly_summary",  "pdf", 1240),
            ReportMetadata("RPT-003", "Fire Season 2024 — Q1 Summary",         "custom",          "pdf", 3412),
            ReportMetadata("RPT-004", "Station Data Export — January 2024",    "custom",          "csv",  512),
        ]

    def generate_report(
        self,
        template_id: str,
        parameters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Trigger on-demand report generation.

        Day 2: Returns stub job ID.
        Day 3: resp = self._client.post("/reports/generate", json={"template_id": template_id, "parameters": parameters})
        """
        return {
            "job_id": "stub-job-001",
            "status": "queued",
            "estimated_seconds": 30,
            "stub": True,
        }

    def get_report_templates(self) -> list[dict[str, Any]]:
        """
        Return available report templates.

        Day 2: Returns stub template list.
        Day 3: resp = self._client.get("/reports/templates")
        """
        return [
            {"id": "daily_bulletin",  "name": "Daily AQI Bulletin",      "description": "24-hour summary with station table and trend chart"},
            {"id": "weekly_summary",  "name": "Weekly Summary",          "description": "7-day overview with hotspot map and fire events"},
            {"id": "hcho_analysis",   "name": "HCHO Hotspot Report",     "description": "Detailed HCHO source attribution and trend analysis"},
            {"id": "forecast_accuracy","name": "Forecast Accuracy Report","description": "Model performance metrics and residual diagnostics"},
        ]


report_service = ReportService()
