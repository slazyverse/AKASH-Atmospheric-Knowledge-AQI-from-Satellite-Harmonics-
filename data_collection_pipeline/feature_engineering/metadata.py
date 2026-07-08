"""Feature dictionary and summary generation."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable

import pandas as pd

def _definition(description: str, units: str, source: str) -> Dict[str, str]:
    return {"description": description, "units": units, "source": source}


FEATURE_DEFINITIONS: Dict[str, Dict[str, str]] = {
    "PM2.5": _definition("Fine particulate matter concentration", "ug/m3", "CPCB"),
    "PM10": _definition("Coarse particulate matter concentration", "ug/m3", "CPCB"),
    "NO2": _definition("Nitrogen dioxide concentration", "ug/m3", "CPCB"),
    "SO2": _definition("Sulfur dioxide concentration", "ug/m3", "CPCB"),
    "CO": _definition("Carbon monoxide concentration", "mg/m3", "CPCB"),
    "O3": _definition("Ozone concentration", "ug/m3", "CPCB"),
    "Temperature": _definition("Near-surface air temperature", "K", "ERA5"),
    "Relative Humidity": _definition("Relative humidity", "%", "ERA5"),
    "Boundary Layer Height": _definition("Planetary boundary layer height", "m", "ERA5"),
    "Wind Speed": _definition("Wind speed derived from U/V components", "m/s", "ERA5"),
    "Wind Direction": _definition(
        "Wind direction derived from U/V components",
        "degrees",
        "ERA5",
    ),
    "Surface Pressure": _definition("Surface atmospheric pressure", "Pa", "ERA5"),
    "AOD": _definition("Aerosol optical depth", "unitless", "Satellite"),
    "HCHO": _definition("Formaldehyde vertical column density", "mol/m2", "Satellite"),
    "NO2 Column": _definition("NO2 vertical column density", "mol/m2", "Satellite"),
    "SO2 Column": _definition("SO2 vertical column density", "mol/m2", "Satellite"),
    "CO Column": _definition("CO column amount", "mol/m2", "Satellite"),
    "O3 Column": _definition("O3 column amount", "mol/m2", "Satellite"),
    "Day of Week": _definition("Day index where Monday is 0", "index", "Derived"),
    "Month": _definition("Calendar month number", "index", "Derived"),
    "Season": _definition("India-oriented meteorological season", "category", "Derived"),
    "Weekend Flag": _definition(
        "True when observation falls on Saturday or Sunday",
        "boolean",
        "Derived",
    ),
}


def write_feature_dictionary(
    df: pd.DataFrame,
    feature_columns: Iterable[str],
    output_path: Path,
) -> pd.DataFrame:
    """Write feature_dictionary.csv with missing percentages."""
    rows = []
    total_rows = len(df)
    for feature in feature_columns:
        definition = FEATURE_DEFINITIONS.get(
            feature,
            {"description": "Integrated feature", "units": "", "source": "Integrated"},
        )
        missing = 0.0
        if total_rows > 0 and feature in df.columns:
            missing = round(float(df[feature].isna().mean() * 100.0), 2)
        rows.append(
            {
                "Feature Name": feature,
                "Description": definition["description"],
                "Units": definition["units"],
                "Source": definition["source"],
                "Missing Percentage": missing,
            }
        )

    dictionary = pd.DataFrame(rows)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dictionary.to_csv(output_path, index=False)
    return dictionary


def write_feature_summary(
    df: pd.DataFrame,
    output_path: Path,
    temporal_strategy: str,
    missing_strategy: str,
    data_sources: Dict[str, str],
) -> Dict[str, object]:
    """Write feature_summary.json for integration auditing."""
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "row_count": int(len(df)),
        "station_count": int(df["Station ID"].nunique()) if "Station ID" in df else 0,
        "feature_count": int(len(df.columns)),
        "temporal_alignment": temporal_strategy,
        "missing_value_strategy": missing_strategy,
        "data_sources": data_sources,
        "missing_percentages": {
            column: round(float(df[column].isna().mean() * 100.0), 2) for column in df.columns
        },
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def write_integration_report(
    output_path: Path,
    summary: Dict[str, object],
    data_sources: Dict[str, str],
) -> None:
    """Write a compact Markdown report for Day 3 integration."""
    lines = [
        "# Day 3 Feature Engineering Integration Report",
        "",
        f"Generated at: {summary['generated_at']}",
        f"Rows: {summary['row_count']}",
        f"Stations: {summary['station_count']}",
        f"Feature columns: {summary['feature_count']}",
        f"Temporal alignment: {summary['temporal_alignment']}",
        f"Missing value strategy: {summary['missing_value_strategy']}",
        "",
        "## Data Sources",
    ]
    for source, status in data_sources.items():
        lines.append(f"- {source}: {status}")

    lines.extend(
        [
            "",
            "## Notes",
            "- Raw collection and cleaned datasets were not modified.",
            "- Satellite and ERA5 predictors are placeholder-backed when no "
            "tabular grid files are available.",
            "- No ML modelling, AQI prediction, scaling, feature selection, "
            "or train/test split was performed.",
        ]
    )
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
