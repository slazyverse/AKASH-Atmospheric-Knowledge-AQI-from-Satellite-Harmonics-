"""dashboard/components — Shared UI component library for VAYU-DRISHTI."""

from dashboard.components.empty_state import (
    render_coming_soon,
    render_no_data,
    render_no_results,
    render_stub_badge,
)
from dashboard.components.error_state import (
    render_api_error,
    render_critical_alert,
    render_data_error,
    render_info_notice,
    render_inline_warning,
)
from dashboard.components.footer import render_page_footer
from dashboard.components.header import render_page_header
from dashboard.components.loading import (
    render_skeleton_card,
    render_skeleton_chart,
    render_skeleton_table,
    render_spinner,
    with_loading,
)
from dashboard.components.sidebar import render_sidebar

# GIS Maps
from dashboard.components.map import (
    render_aqi_spatial_map,
    render_hcho_spatial_map,
    render_fire_spatial_map,
    render_forecast_coverage_map,
)

# Plotly Charts
from dashboard.components.charts import (
    render_aqi_time_series,
    render_pollutant_trend_comparison,
    render_aqi_category_distribution,
    render_daily_hcho_trend,
    render_forecast_line_chart,
    render_fire_count_timeline,
    render_source_attribution_donut,
    render_shap_waterfall_chart,
)

__all__ = [
    # Sidebar
    "render_sidebar",
    # Header / Footer
    "render_page_header",
    "render_page_footer",
    # Loading
    "render_spinner",
    "render_skeleton_card",
    "render_skeleton_chart",
    "render_skeleton_table",
    "with_loading",
    # Error
    "render_api_error",
    "render_data_error",
    "render_inline_warning",
    "render_info_notice",
    "render_critical_alert",
    # Empty state
    "render_no_data",
    "render_no_results",
    "render_coming_soon",
    "render_stub_badge",
    # GIS Maps
    "render_aqi_spatial_map",
    "render_hcho_spatial_map",
    "render_fire_spatial_map",
    "render_forecast_coverage_map",
    # Plotly Charts
    "render_aqi_time_series",
    "render_pollutant_trend_comparison",
    "render_aqi_category_distribution",
    "render_daily_hcho_trend",
    "render_forecast_line_chart",
    "render_fire_count_timeline",
    "render_source_attribution_donut",
    "render_shap_waterfall_chart",
]
