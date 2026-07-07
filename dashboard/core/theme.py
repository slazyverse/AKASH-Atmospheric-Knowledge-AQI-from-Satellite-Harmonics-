"""
VAYU-DRISHTI Dashboard — Core design system constants.

All visual tokens (colours, spacing, typography) live here.
A single edit to this file reskins the entire application.

Design philosophy:
  - Dark-mode first: reduces eye strain during long monitoring sessions.
  - Teal/cyan primary: conveys air, clarity, and scientific precision.
  - AQI severity palette: follows WHO/CPCB standard colour conventions
    so domain experts immediately recognise risk levels.
  - Accent orange: used exclusively for fire/alert states to invoke urgency.
"""

from __future__ import annotations

# ── Primary Palette ─────────────────────────────────────────────────────────
PRIMARY          = "#00BFA5"   # Teal-cyan — brand identity, interactive elements
PRIMARY_DARK     = "#00897B"   # Darker teal — hover states, active nav items
PRIMARY_LIGHT    = "#B2DFDB"   # Light teal — subtle highlights, borders
ACCENT_ORANGE    = "#FF6D00"   # Alert orange — fire monitoring, critical alerts
ACCENT_YELLOW    = "#FFD600"   # Caution yellow — moderate AQI, warnings

# ── Surface Palette ─────────────────────────────────────────────────────────
BG_DEEP          = "#0D1117"   # Page background (matches .streamlit/config.toml)
BG_SURFACE       = "#161B22"   # Card / sidebar surface
BG_ELEVATED      = "#21262D"   # Elevated card (hover), tooltip backgrounds
BORDER_DEFAULT   = "#30363D"   # Subtle borders for cards and dividers
BORDER_FOCUS     = PRIMARY     # Focus ring colour for interactive elements

# ── Text Palette ─────────────────────────────────────────────────────────────
TEXT_PRIMARY     = "#E6EDF3"   # Main readable text
TEXT_SECONDARY   = "#8B949E"   # Labels, metadata, secondary info
TEXT_MUTED       = "#484F58"   # Placeholder, disabled states
TEXT_INVERSE     = "#0D1117"   # Text on coloured backgrounds

# ── AQI Severity Palette (CPCB / WHO standard mapping) ──────────────────────
AQI_GOOD         = "#00E676"   # 0–50:   Good
AQI_SATISFACTORY = "#69F0AE"   # 51–100: Satisfactory
AQI_MODERATE     = "#FFD600"   # 101–200: Moderate
AQI_POOR         = "#FF9100"   # 201–300: Poor
AQI_VERY_POOR    = "#FF3D00"   # 301–400: Very Poor
AQI_SEVERE       = "#B71C1C"   # 401–500: Severe / Hazardous

# ── Status Indicators ────────────────────────────────────────────────────────
STATUS_OK        = AQI_GOOD
STATUS_WARNING   = AQI_MODERATE
STATUS_ERROR     = "#CF6679"   # Error red (accessible on dark backgrounds)
STATUS_INFO      = "#58A6FF"   # Info blue

# ── Typography ───────────────────────────────────────────────────────────────
FONT_FAMILY      = "Inter, 'Segoe UI', Arial, sans-serif"
FONT_SIZE_XS     = "0.75rem"
FONT_SIZE_SM     = "0.875rem"
FONT_SIZE_BASE   = "1rem"
FONT_SIZE_LG     = "1.25rem"
FONT_SIZE_XL     = "1.5rem"
FONT_SIZE_2XL    = "2rem"
FONT_SIZE_3XL    = "2.5rem"

# ── Spacing ──────────────────────────────────────────────────────────────────
SPACE_XS         = "4px"
SPACE_SM         = "8px"
SPACE_MD         = "16px"
SPACE_LG         = "24px"
SPACE_XL         = "40px"

# ── Icon Map (emoji fallbacks — replaced by SVG in Day 4+) ──────────────────
MODULE_ICONS: dict[str, str] = {
    "Home":             "🏠",
    "Surface AQI":      "🌫️",
    "HCHO Hotspots":    "⚗️",
    "Fire Monitoring":  "🔥",
    "AQI Forecast":     "📈",
    "Explainable AI":   "🧠",
    "Reports":          "📋",
}

# ── CSS Injection Helper ──────────────────────────────────────────────────────
CUSTOM_CSS = f"""
<style>
  /* Import Inter from Google Fonts */
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

  /* Override Streamlit's root font */
  html, body, [class*="css"] {{
    font-family: {FONT_FAMILY};
  }}

  /* Metric card hover lift effect */
  [data-testid="metric-container"] {{
    background-color: {BG_SURFACE};
    border: 1px solid {BORDER_DEFAULT};
    border-radius: 12px;
    padding: 16px 20px;
    transition: transform 0.18s ease, box-shadow 0.18s ease;
  }}
  [data-testid="metric-container"]:hover {{
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(0,191,165,0.15);
  }}

  /* Sidebar brand strip */
  [data-testid="stSidebar"] > div:first-child {{
    background: linear-gradient(180deg, {BG_ELEVATED} 0%, {BG_SURFACE} 100%);
    border-right: 1px solid {BORDER_DEFAULT};
  }}

  /* Radio buttons styled as nav links */
  [data-testid="stSidebar"] .stRadio > div {{
    gap: 2px;
  }}
  [data-testid="stSidebar"] .stRadio label {{
    border-radius: 8px;
    padding: 8px 12px;
    transition: background 0.15s ease;
    cursor: pointer;
  }}
  [data-testid="stSidebar"] .stRadio label:hover {{
    background-color: {BG_ELEVATED};
  }}

  /* Divider colour */
  hr {{
    border-color: {BORDER_DEFAULT} !important;
  }}

  /* Scrollbar styling */
  ::-webkit-scrollbar {{ width: 6px; }}
  ::-webkit-scrollbar-track {{ background: {BG_DEEP}; }}
  ::-webkit-scrollbar-thumb {{ background: {BORDER_DEFAULT}; border-radius: 3px; }}
  ::-webkit-scrollbar-thumb:hover {{ background: {TEXT_SECONDARY}; }}
</style>
"""
