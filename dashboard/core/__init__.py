"""dashboard/core — Core infrastructure for the VAYU-DRISHTI dashboard."""

from dashboard.core.config import DashboardConfig, dashboard_config
from dashboard.core.state import (
    clear_error,
    init_session_state,
    navigate_to,
    set_error,
)
from dashboard.core.theme import CUSTOM_CSS, MODULE_ICONS

__all__ = [
    "DashboardConfig",
    "dashboard_config",
    "init_session_state",
    "navigate_to",
    "clear_error",
    "set_error",
    "CUSTOM_CSS",
    "MODULE_ICONS",
]
