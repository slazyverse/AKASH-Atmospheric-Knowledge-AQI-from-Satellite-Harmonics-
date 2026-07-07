"""
dashboard/pages/reports.py — Reports module page.

Provides access to generated analytical reports and on-demand export tools.

Day 2 Scope: Report list table, template selector, generation form placeholder.
Day 3 Scope: Actual PDF download links, scheduled report configuration.
"""

from __future__ import annotations

from datetime import datetime

import pandas as pd
import streamlit as st

from dashboard.components.empty_state import render_coming_soon, render_stub_badge
from dashboard.components.error_state import render_info_notice
from dashboard.components.footer import render_page_footer
from dashboard.components.header import render_page_header
from dashboard.core.theme import (
    BG_ELEVATED,
    BORDER_DEFAULT,
    PRIMARY,
    TEXT_MUTED,
    TEXT_SECONDARY,
)
from dashboard.services import report_service


def render() -> None:
    """Render the Reports module page."""
    render_page_header(
        module_name="Reports",
        subtitle="On-demand and scheduled analytical reports for AQI monitoring",
        show_export_button=False,
    )

    render_info_notice(
        "Report generation requires live API (Day 3). "
        "Currently displaying stub report list and templates."
    )

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Report Stats ──────────────────────────────────────────────────────────
    _render_report_stats()

    st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

    # ── Tab layout ────────────────────────────────────────────────────────────
    tab1, tab2, tab3 = st.tabs(["📄 Available Reports", "🛠️ Generate Report", "⏰ Scheduled Reports"])

    with tab1:
        _render_report_list()

    with tab2:
        _render_generate_form()

    with tab3:
        render_coming_soon(
            "Scheduled Reports",
            planned_day="Day 6",
            features=[
                "Daily AQI bulletin — auto-sent at 08:00 IST",
                "Weekly summary — every Monday",
                "Alert-triggered reports on fire events",
                "Email recipients configuration",
            ],
        )

    render_page_footer(show_data_sources=False)


def _render_report_stats() -> None:
    reports = report_service.list_reports()
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("📄 Total Reports", str(len(reports)), "Available")
    with c2:
        pdf_count = sum(1 for r in reports if r.format == "pdf")
        st.metric("📕 PDF Reports", str(pdf_count), "")
    with c3:
        csv_count = sum(1 for r in reports if r.format == "csv")
        st.metric("📊 CSV Exports", str(csv_count), "")
    with c4:
        st.metric("⏰ Scheduled", "0", "Awaiting Day 6")


def _render_report_list() -> None:
    st.markdown(f"<h4 style='color:{PRIMARY}'>📋 Report Library</h4>", unsafe_allow_html=True)
    render_stub_badge()

    reports = report_service.list_reports()
    rows = [
        {
            "ID": r.report_id,
            "Title": r.title,
            "Type": r.report_type,
            "Format": r.format.upper(),
            "Size": f"{r.size_kb} KB",
            "Status": r.status.title(),
            "Generated": r.generated_at.strftime("%Y-%m-%d %H:%M"),
        }
        for r in reports
    ]
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    render_coming_soon(
        "Report Download",
        planned_day="Day 3",
        features=[
            "One-click PDF download from the table",
            "Preview modal for report content",
            "Share link generation",
        ],
    )


def _render_generate_form() -> None:
    st.markdown(f"<h4 style='color:{PRIMARY}'>🛠️ Generate On-Demand Report</h4>", unsafe_allow_html=True)
    render_stub_badge()

    templates = report_service.get_report_templates()

    template_options = {t["name"]: t["id"] for t in templates}
    selected_name = st.selectbox("📄 Report Template", list(template_options.keys()), key="report_template")
    selected_template = next(t for t in templates if t["name"] == selected_name)
    st.caption(selected_template["description"])

    c1, c2 = st.columns(2)
    with c1:
        st.date_input("📅 From Date", key="report_from")
    with c2:
        st.date_input("📅 To Date", key="report_to")

    st.selectbox(
        "🌍 Region",
        ["All India", "North India", "South India", "East India", "West India"],
        key="report_region",
    )
    st.selectbox("📁 Output Format", ["PDF", "CSV", "JSON"], key="report_format")

    if st.button("⚙️ Generate Report", key="btn_generate_report", use_container_width=False):
        result = report_service.generate_report(
            template_id=template_options[selected_name],
        )
        st.success(f"✅ Report queued (Job ID: {result['job_id']}). Live generation available in Day 3.")

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    render_info_notice("Report generation is a stub in Day 2. The form captures parameters but does not call the API.")
