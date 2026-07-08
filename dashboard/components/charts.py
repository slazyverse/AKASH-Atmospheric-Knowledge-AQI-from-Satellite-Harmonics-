"""
dashboard/components/charts.py — Reusable Plotly Visualisations for VAYU-DRISHTI.

This module provides production-quality, responsive Plotly charts styled to match
the platform's dark-mode design system. All charts support hover tooltips,
legends, and gracefully fall back to empty state components when empty data is provided.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from dashboard.components.empty_state import render_no_data
from dashboard.core.theme import (
    AQI_GOOD,
    AQI_MODERATE,
    AQI_POOR,
    AQI_SATISFACTORY,
    AQI_SEVERE,
    AQI_VERY_POOR,
    BG_ELEVATED,
    BG_SURFACE,
    BORDER_DEFAULT,
    PRIMARY,
    TEXT_PRIMARY,
    TEXT_SECONDARY,
)


def _apply_dark_theme(fig: go.Figure, title: str = "") -> None:
    """Helper to apply the uniform VAYU-DRISHTI dark-theme layout to any Plotly figure."""
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(color=TEXT_PRIMARY, size=15),
            x=0.02,
            y=0.95,
        ),
        paper_bgcolor="rgba(0,0,0,0)",  # Transparent background to let Streamlit container style shine
        plot_bgcolor="rgba(0,0,0,0)",   # Transparent plot background
        font=dict(color=TEXT_PRIMARY, family="Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif"),
        legend=dict(
            font=dict(color=TEXT_SECONDARY, size=10),
            bgcolor=BG_SURFACE,
            bordercolor=BORDER_DEFAULT,
            borderwidth=1,
            orientation="h",
            yanchor="bottom",
            y=-0.25,
            xanchor="center",
            x=0.5,
        ),
        margin=dict(l=40, r=20, t=50, b=50),
        hoverlabel=dict(
            bgcolor=BG_ELEVATED,
            font_color=TEXT_PRIMARY,
            font_size=11,
            bordercolor=BORDER_DEFAULT,
        ),
        hovermode="x unified",
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor=BORDER_DEFAULT,
        linecolor=BORDER_DEFAULT,
        tickfont=dict(color=TEXT_SECONDARY, size=10),
        title_font=dict(color=TEXT_SECONDARY, size=11),
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=BORDER_DEFAULT,
        linecolor=BORDER_DEFAULT,
        tickfont=dict(color=TEXT_SECONDARY, size=10),
        title_font=dict(color=TEXT_SECONDARY, size=11),
    )


# ── Chart 1: AQI Time Series ──────────────────────────────────────────────────

def render_aqi_time_series(df: pd.DataFrame, title: str = "AQI Trend Over Time") -> None:
    """
    Render a line chart for AQI values over time.
    Expects df with columns: 'recorded_at' (datetime/string) and 'aqi_value' (numeric).
    """
    if df is None or df.empty or "recorded_at" not in df.columns or "aqi_value" not in df.columns:
        render_no_data(
            title="AQI Trend Unavailable",
            message="No time-series recordings found for the active station.",
            icon="📈",
        )
        return

    # Ensure sorted by date
    df = df.sort_values("recorded_at")

    fig = go.Figure()

    # Base line trace
    fig.add_trace(
        go.Scatter(
            x=df["recorded_at"],
            y=df["aqi_value"],
            mode="lines+markers",
            name="AQI Value",
            line=dict(color=PRIMARY, width=2.5),
            marker=dict(size=6, color=PRIMARY, symbol="circle"),
            hovertemplate="AQI: <b>%{y}</b><extra></extra>",
            fill="tozeroy",
            fillcolor="rgba(0, 191, 165, 0.1)",  # Subtle teal shading underneath line
        )
    )

    _apply_dark_theme(fig, title)
    fig.update_layout(yaxis_title="AQI Units")
    st.plotly_chart(fig, use_container_width=True, key=f"plotly_ts_{hash(title) % 10000}")


# ── Chart 2: Pollutant Trend Comparison ───────────────────────────────────────

def render_pollutant_trend_comparison(
    df: pd.DataFrame,
    pollutants: list[str] | None = None,
    title: str = "Pollutant Comparison (µg/m³)",
) -> None:
    """
    Render a multi-line comparison chart for different pollutants.
    Expects df with columns: 'recorded_at' and the pollutant parameter names.
    """
    if pollutants is None:
        pollutants = ["PM2.5", "PM10", "NO2", "O3", "SO2"]

    if df is None or df.empty or "recorded_at" not in df.columns:
        render_no_data(
            title="Pollutant Trends Unavailable",
            message="No individual pollutant parameters matched in the selected records.",
            icon="💨",
        )
        return

    available_pollutants = [p for p in pollutants if p in df.columns]
    if not available_pollutants:
        render_no_data(
            title="Pollutant Trends Unavailable",
            message="No individual pollutant parameters matched in the selected records.",
            icon="💨",
        )
        return

    df = df.sort_values("recorded_at")

    # Define color scheme for various pollutants
    colors = {
        "PM2.5": "#FF3D00",  # Red
        "PM10": "#FF9100",   # Orange
        "NO2": "#58A6FF",    # Blue
        "O3": "#00E676",     # Green
        "SO2": "#FFD600",    # Yellow
        "CO": "#B2DFDB",     # Light Teal
    }

    fig = go.Figure()

    for col in available_pollutants:
        fig.add_trace(
            go.Scatter(
                x=df["recorded_at"],
                y=df[col],
                mode="lines",
                name=col,
                line=dict(color=colors.get(col, PRIMARY), width=2),
                hovertemplate=f"{col}: <b>%{{y}} µg/m³</b><extra></extra>",
            )
        )

    _apply_dark_theme(fig, title)
    fig.update_layout(yaxis_title="Concentration (µg/m³)")
    st.plotly_chart(fig, use_container_width=True, key=f"plotly_pollutants_{hash(title) % 10000}")


# ── Chart 3: AQI Category Distribution ────────────────────────────────────────

def render_aqi_category_distribution(
    df: pd.DataFrame,
    category_col: str = "Category",
    title: str = "AQI Category Distribution Across Stations",
) -> None:
    """
    Render a bar chart of the AQI categories distribution.
    Expects a DataFrame containing AQI categories to count.
    """
    if df is None or df.empty or category_col not in df.columns:
        render_no_data(
            title="Distribution Unavailable",
            message="No readings available to calculate AQI categories distribution.",
            icon="📊",
        )
        return

    counts = df[category_col].value_counts()
    categories_order = ["Good", "Satisfactory", "Moderate", "Poor", "Very Poor", "Severe"]
    colors_map = {
        "Good": AQI_GOOD,
        "Satisfactory": AQI_SATISFACTORY,
        "Moderate": AQI_MODERATE,
        "Poor": AQI_POOR,
        "Very Poor": AQI_VERY_POOR,
        "Severe": AQI_SEVERE,
    }

    x_labels = [cat for cat in categories_order if cat in counts.index]
    y_values = [counts[cat] for cat in x_labels]
    bar_colors = [colors_map.get(cat, PRIMARY) for cat in x_labels]

    if not y_values:
        # Fallback if categories are named differently or mismatch
        x_labels = list(counts.index)
        y_values = list(counts.values)
        bar_colors = [PRIMARY] * len(x_labels)

    fig = go.Figure()
    fig.add_trace(
        go.Bar(
            x=x_labels,
            y=y_values,
            marker_color=bar_colors,
            marker_line=dict(color=BORDER_DEFAULT, width=1),
            hovertemplate="Count: <b>%{y} stations</b><extra></extra>",
            showlegend=False,
        )
    )

    _apply_dark_theme(fig, title)
    fig.update_layout(
        yaxis_title="Station Count",
        margin=dict(l=40, r=20, t=50, b=40),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"plotly_cat_dist_{hash(title) % 10000}")


# ── Chart 4: Daily HCHO Trend ─────────────────────────────────────────────────

def render_daily_hcho_trend(df: pd.DataFrame, title: str = "HCHO Column Density Trend") -> None:
    """
    Render a line chart showing daily HCHO column density.
    Expects df with: 'year_month' or 'date' and 'column_density' (numeric).
    """
    if df is None or df.empty or ("date" not in df.columns and "year_month" not in df.columns):
        render_no_data(
            title="HCHO Trend Unavailable",
            message="No Sentinel-5P HCHO temporal measurements found.",
            icon="⚗️",
        )
        return

    time_col = "date" if "date" in df.columns else "year_month"
    if "column_density" not in df.columns:
        render_no_data(
            title="HCHO Trend Unavailable",
            message="No Sentinel-5P HCHO temporal measurements found.",
            icon="⚗️",
        )
        return

    df = df.sort_values(time_col)

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=df[time_col],
            y=df["column_density"],
            mode="lines+markers",
            line=dict(color="#D3436C", width=2.5),  # Distinct Magenta/Red color for HCHO
            marker=dict(size=6, color="#D3436C"),
            name="Mean Density",
            hovertemplate="Density: <b>%{y:.2f} ×10¹⁵ mol/cm²</b><extra></extra>",
            fill="tozeroy",
            fillcolor="rgba(211, 67, 108, 0.1)",
        )
    )

    _apply_dark_theme(fig, title)
    fig.update_layout(yaxis_title="Density (×10¹⁵ molecules/cm²)")
    st.plotly_chart(fig, use_container_width=True, key=f"plotly_hcho_trend_{hash(title) % 10000}")


# ── Chart 5: Forecast Line Chart (with Confidence Intervals) ──────────────────

def render_forecast_line_chart(forecast_steps: list[Any], title: str = "72-Hour AQI Forecast") -> None:
    """
    Render forecast line with shaded 95% confidence interval bounds and horizontal category bands.
    Expects a list of ForecastStep objects.
    """
    if not forecast_steps:
        render_no_data(
            title="Forecast Data Unavailable",
            message="No ML forecast predictions returned for this station.",
            icon="📈",
        )
        return

    # Extract lists
    times = [step.forecast_at for step in forecast_steps]
    predicted = [step.predicted_aqi for step in forecast_steps]
    lower = [step.lower_bound for step in forecast_steps]
    upper = [step.upper_bound for step in forecast_steps]

    fig = go.Figure()

    # Category Horizontal Background Bands
    # Standard CPCB ranges: 0-50 (Good), 50-100 (Satisfactory), 100-200 (Moderate), 200-300 (Poor), 300-400 (Very Poor), 400-500 (Severe)
    max_forecast = max(max(upper), 350)
    bands = [
        ("Good", 0, 50, AQI_GOOD),
        ("Satisfactory", 50, 100, AQI_SATISFACTORY),
        ("Moderate", 100, 200, AQI_MODERATE),
        ("Poor", 200, 300, AQI_POOR),
        ("Very Poor", 300, 400, AQI_VERY_POOR),
        ("Severe", 400, max(max_forecast + 50, 500), AQI_SEVERE),
    ]

    # Upper bound line (invisible, used to fill down to lower bound)
    fig.add_trace(
        go.Scatter(
            x=times,
            y=upper,
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    # Shaded confidence band (fill='tonexty' fills between upper and lower)
    fig.add_trace(
        go.Scatter(
            x=times,
            y=lower,
            mode="lines",
            fill="tonexty",
            fillcolor="rgba(0, 191, 165, 0.15)",  # Translucent teal-cyan
            line=dict(width=0),
            name="95% Confidence Interval",
            hovertemplate="95% CI Range: <b>%{y} - " + "</b><extra></extra>",  # Modified by hover unified
        )
    )

    # Point Predictions Line
    fig.add_trace(
        go.Scatter(
            x=times,
            y=predicted,
            mode="lines+markers",
            line=dict(color=PRIMARY, width=2.5),
            marker=dict(size=5, color=PRIMARY),
            name="Predicted AQI",
            hovertemplate="Predicted AQI: <b>%{y:.1f}</b><extra></extra>",
        )
    )

    # Add shapes for background bands (horizontal lines or rectangles)
    # We add transparent shapes to denote CPCB AQI bands
    for name, min_val, max_val, color in bands:
        if min_val <= max_forecast:
            fig.add_hrect(
                y0=min_val,
                y1=min(max_val, max_forecast + 20),
                fillcolor=color,
                opacity=0.03,  # Very subtle background coloring to prevent visual clutter
                layer="below",
                line_width=0,
            )

    _apply_dark_theme(fig, title)
    fig.update_layout(
        yaxis_title="AQI Units",
        hovermode="x unified",
        legend=dict(y=-0.2),
    )
    # Adjust Y-axis scale to fit the data comfortably
    fig.update_yaxes(range=[0, max_forecast + 20])
    st.plotly_chart(fig, use_container_width=True, key="plotly_aqi_forecast")


# ── Chart 6: Fire Count & FRP Timeline ────────────────────────────────────────

def render_fire_count_timeline(fire_events: list[Any], title: str = "Active Fire & FRP Timeline") -> None:
    """
    Render a dual-axis timeline chart: count of fire events and total FRP.
    Expects a list of FireEvent objects.
    """
    if not fire_events:
        render_no_data(
            title="Fire Timeline Unavailable",
            message="No active fire occurrences recorded in the selection window.",
            icon="🔥",
        )
        return

    # Aggregate by hour/date of detection. Since fires are in past 24h, let's group by Hour.
    data = []
    for e in fire_events:
        # Round datetime to nearest hour
        dt_hour = e.detected_at.replace(minute=0, second=0, microsecond=0)
        data.append({"hour": dt_hour, "frp": e.frp})

    df = pd.DataFrame(data)
    if df.empty:
        render_no_data(
            title="Fire Timeline Unavailable",
            message="Error formatting fire event timeline data.",
            icon="🔥",
        )
        return

    grouped = df.groupby("hour").agg(
        fire_count=("frp", "count"),
        total_frp=("frp", "sum")
    ).reset_index().sort_values("hour")

    fig = go.Figure()

    # Bar chart for Fire counts (Left Y-Axis)
    fig.add_trace(
        go.Bar(
            x=grouped["hour"],
            y=grouped["fire_count"],
            name="Fire Count",
            marker_color="#FF6D00",  # Accent Orange
            opacity=0.6,
            marker_line=dict(color=BORDER_DEFAULT, width=1),
            yaxis="y1",
            hovertemplate="Fires: <b>%{y}</b><extra></extra>",
        )
    )

    # Line chart for Cumulative FRP (Right Y-Axis)
    fig.add_trace(
        go.Scatter(
            x=grouped["hour"],
            y=grouped["total_frp"],
            name="Total FRP (MW)",
            mode="lines+markers",
            line=dict(color="#FFD600", width=2),  # Caution Yellow
            marker=dict(size=5, color="#FFD600"),
            yaxis="y2",
            hovertemplate="Total FRP: <b>%{y:.1f} MW</b><extra></extra>",
        )
    )

    _apply_dark_theme(fig, title)
    fig.update_layout(
        yaxis=dict(
            title=dict(text="Active Fire Detections", font=dict(color="#FF6D00")),
            tickfont=dict(color="#FF6D00"),
        ),
        yaxis2=dict(
            title=dict(text="Radiative Power (MW)", font=dict(color="#FFD600")),
            tickfont=dict(color="#FFD600"),
            overlaying="y",
            side="right",
            showgrid=False,  # Prevent grid lines from clashing
        ),
        legend=dict(y=-0.2),
    )
    st.plotly_chart(fig, use_container_width=True, key="plotly_fire_timeline")


# ── Chart 7: Source Attribution Donut ─────────────────────────────────────────

def render_source_attribution_donut(attribution: dict[str, float], title: str = "Emission Source Attribution") -> None:
    """
    Render a donut chart showing HCHO source attribution percentage.
    Expects attribution dict like {'industrial': 0.55, 'biogenic': 0.3, ...}.
    """
    if not attribution or not any(attribution.values()):
        render_no_data(
            title="Source Attribution Unavailable",
            message="No attribution profile generated for this hotspot.",
            icon="🍩",
        )
        return

    labels = [k.replace("_", " ").title() for k in attribution.keys() if k != "hotspot_id"]
    values = [attribution[k] for k in attribution.keys() if k != "hotspot_id"]

    # Color scheme matching source categories
    source_colors = {
        "Industrial": PRIMARY,
        "Biogenic": "#00E676",         # Green
        "Biomass Burning": "#FF6D00",  # Orange
        "Unknown": TEXT_SECONDARY,
    }
    colors = [source_colors.get(label, PRIMARY) for label in labels]

    fig = go.Figure()
    fig.add_trace(
        go.Pie(
            labels=labels,
            values=values,
            hole=0.45,
            marker=dict(colors=colors, line=dict(color=BORDER_DEFAULT, width=1.5)),
            textinfo="percent",
            hovertemplate="Source: <b>%{label}</b><br>Share: <b>%{percent}</b><extra></extra>",
        )
    )

    _apply_dark_theme(fig, title)
    # Hide pie chart grid/axes
    fig.update_layout(
        showlegend=True,
        margin=dict(l=20, r=20, t=50, b=20),
    )
    st.plotly_chart(fig, use_container_width=True, key=f"plotly_donut_{hash(title) % 10000}")


# ── Chart 8: SHAP Waterfall Chart ────────────────────────────────────────────

def render_shap_waterfall_chart(
    shap_values: dict[str, float],
    base_value: float,
    predicted_aqi: float,
    title: str = "SHAP Feature Contributions (Waterfall)",
) -> None:
    """
    Render a SHAP waterfall chart showing how each feature pushes the prediction
    above or below the model baseline.

    Positive SHAP values push AQI higher (shown in red/orange tones).
    Negative SHAP values reduce AQI (shown in teal/green tones).
    The chart reads bottom-to-top: base_value → each feature delta → final prediction.

    Args:
        shap_values: Dict mapping feature name → SHAP value (positive increases AQI, negative decreases).
        base_value:  The model's average prediction (starting point for the waterfall).
        predicted_aqi: Final predicted AQI (base + sum of all SHAP values).
        title: Chart title.
    """
    if not shap_values:
        render_no_data(
            title="SHAP Data Unavailable",
            message="No SHAP explanation data found for this prediction.",
            icon="🔬",
        )
        return

    # Sort by absolute magnitude descending so largest contributors are at top
    sorted_features = sorted(shap_values.items(), key=lambda x: abs(x[1]), reverse=True)
    features = [f for f, _ in sorted_features]
    values   = [v for _, v in sorted_features]

    # Color coding: positive SHAP = AQI_POOR (orange-red), negative = PRIMARY (teal)
    colors = [AQI_POOR if v > 0 else PRIMARY for v in values]

    # Build measure array for Plotly waterfall:
    # "relative" for each feature, "total" for base and final
    measures = ["absolute"] + ["relative"] * len(features) + ["total"]
    x_labels = ["Base Value"] + features + ["Predicted AQI"]
    y_values  = [base_value] + values + [predicted_aqi]

    # Colors list: base (neutral), feature contributions, total (neutral)
    bar_colors = [TEXT_SECONDARY] + colors + [PRIMARY]

    fig = go.Figure(
        go.Waterfall(
            name="SHAP Values",
            orientation="v",
            measure=measures,
            x=x_labels,
            y=y_values,
            text=[f"{v:+.1f}" if i not in (0, len(x_labels) - 1) else f"{v:.1f}"
                  for i, v in enumerate(y_values)],
            textposition="outside",
            connector=dict(
                line=dict(color=BORDER_DEFAULT, width=1, dash="dot")
            ),
            increasing=dict(marker=dict(color=AQI_POOR)),
            decreasing=dict(marker=dict(color=PRIMARY)),
            totals=dict(marker=dict(color=BG_ELEVATED, line=dict(color=PRIMARY, width=2))),
            hovertemplate="%{x}: <b>%{y:+.1f}</b><extra></extra>",
        )
    )

    # Add a horizontal reference line at the base value
    fig.add_hline(
        y=base_value,
        line=dict(color=TEXT_SECONDARY, width=1, dash="dash"),
        annotation_text=f"Baseline: {base_value:.1f}",
        annotation_position="top right",
        annotation_font=dict(color=TEXT_SECONDARY, size=10),
    )

    _apply_dark_theme(fig, title)
    fig.update_layout(
        yaxis_title="AQI Units",
        showlegend=False,
        margin=dict(l=40, r=20, t=60, b=60),
    )
    fig.update_xaxes(tickangle=-30)
    st.plotly_chart(fig, use_container_width=True, key=f"plotly_shap_{hash(title) % 10000}")
