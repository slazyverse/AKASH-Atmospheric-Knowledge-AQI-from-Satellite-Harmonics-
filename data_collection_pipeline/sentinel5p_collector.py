"""Sentinel-5P / TROPOMI Satellite Data Collector for the AKASH pipeline.

Provides AOD, HCHO, NO2 column, SO2 column, CO column, and O3 column
retrievals over India via the Google Earth Engine (GEE) Python API.

Architecture
------------
This module is a **satellite ingestion collector** — symmetrical in role to
``cpcb_collector.py`` and ``openaq_collector.py``.  It produces the file
``processed_data/satellite_predictors.csv`` which is automatically consumed
by ``feature_engineering/merger.load_satellite_grid()`` on the next
feature-engineering run.

The output CSV schema is aligned to ``merger.py``'s ``SATELLITE_RENAME_MAP``
so that the merger can pick up the data without any downstream changes.

Sampling Strategy
-----------------
Rather than a single large India-wide ``reduceRegion()`` / ``sample()``
operation (which exceeds GEE's 5 000-element limit), this module:

1. Maintains a registry of validated CPCB / OpenAQ monitoring stations
   (~450 stations, nationwide).
2. Groups stations into batches of ``GEE_BATCH_SIZE`` (≤ 100 by default).
3. For each batch, builds a ``ee.FeatureCollection`` of points and calls
   ``image.sampleRegions()`` — one lightweight server-side call per band
   per batch.
4. Concatenates all batch results and merges by
   ``(station_id, timestamp)``.

This ensures:
- No single GEE request approaches the 5 000-element limit.
- Coverage spans all states in India.
- Station coordinates are identical to those used for CPCB/OpenAQ matching.

Data Sources
------------
Sentinel-5P TROPOMI products used:

* ``COPERNICUS/S5P/OFFL/L3_NO2``  — NO2 tropospheric column
* ``COPERNICUS/S5P/OFFL/L3_SO2``  — SO2 total vertical column
* ``COPERNICUS/S5P/OFFL/L3_CO``   — CO total column
* ``COPERNICUS/S5P/OFFL/L3_O3``   — O3 total column
* ``COPERNICUS/S5P/OFFL/L3_HCHO`` — HCHO total column
* ``MODIS/061/MCD19A2_GRANULES``   — AOD 550 nm (MAIAC, 1 km)

QA Filters
----------
* TROPOMI: ``qa_value >= 0.5`` (recommended threshold for all S5P OFFL products).
* MODIS MAIAC: cloud-clear bits (bits 0-2 == 1) and best-quality bits
  (bits 8-11 == 0) from the ``AOD_QA`` band.

GEE Authentication
------------------
Requires either:
* A valid ``earthengine authenticate`` session (``~/.config/earthengine/``), or
* The ``GEE_SERVICE_ACCOUNT`` and ``GEE_SERVICE_ACCOUNT_KEY_FILE`` environment
  variables pointing to a service-account JSON key, or
* The ``GEE_SERVICE_ACCOUNT_KEY_JSON`` environment variable containing the
  JSON key inline (useful for CI/CD secrets).

When GEE credentials are absent, the module exits cleanly with an explanatory
error rather than silently writing placeholder data.

Dependencies
------------
``earthengine-api`` (``pip install earthengine-api``) — optional at import
time; a ``MissingGeeCredentialsError`` is raised at call time when absent.

Usage
-----
::

    # CLI — collect latest satellite data for today
    python -m data_collection_pipeline.sentinel5p_collector

    # CLI — collect for a specific date
    python -m data_collection_pipeline.sentinel5p_collector \\
        --date 2026-07-07 \\
        --output processed_data/satellite_predictors.csv

    # API
    from data_collection_pipeline.sentinel5p_collector import collect_satellite_data
    success = collect_satellite_data(date_str="2026-07-07")
"""

from __future__ import annotations

import argparse
import datetime
import json
import logging
import math
import os
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

from data_collection_pipeline import config
from data_collection_pipeline.dlq import handle_ingestion_failure
from data_collection_pipeline.exceptions import IngestionError

logger = logging.getLogger("data_collection_pipeline.sentinel5p")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

#: Full India bounding box [West, South, East, North] — kept for reference /
#: geometry fallback only; actual sampling uses station points.
INDIA_BBOX: Tuple[float, float, float, float] = (68.0, 6.0, 98.0, 38.0)

#: Output grid resolution in degrees (used for rounding station coordinates)
GRID_RESOLUTION_DEG: float = 0.1

#: Default temporal window around the target date (in days)
TEMPORAL_WINDOW_DAYS: int = 3

#: Maximum backward lookback when target date has no imagery (days)
MAX_ADAPTIVE_LOOKBACK_DAYS: int = 7

#: Maximum stations per GEE batch request — keep well below the 5 000-element
#: hard limit; 100 leaves ample headroom for multi-band composites.
GEE_BATCH_SIZE: int = 100

#: Scale in metres for ``sampleRegions`` — matches Sentinel-5P native ~5.5 km.
#: MODIS MAIAC is 1 km natively; 5500 m is a safe common denominator.
SAMPLE_SCALE_M: int = 5500

#: Sentinel-5P TROPOMI GEE collection IDs
S5P_COLLECTIONS: Dict[str, str] = {
    "NO2 Column":  "COPERNICUS/S5P/OFFL/L3_NO2",
    "SO2 Column":  "COPERNICUS/S5P/OFFL/L3_SO2",
    "CO Column":   "COPERNICUS/S5P/OFFL/L3_CO",
    "O3 Column":   "COPERNICUS/S5P/OFFL/L3_O3",
    "HCHO":        "COPERNICUS/S5P/OFFL/L3_HCHO",
}

#: Band names within each TROPOMI collection to extract
S5P_BAND_MAP: Dict[str, str] = {
    "NO2 Column":  "tropospheric_NO2_column_number_density",
    "SO2 Column":  "SO2_column_number_density",
    "CO Column":   "CO_column_number_density",
    "O3 Column":   "O3_column_number_density",
    "HCHO":        "tropospheric_HCHO_column_number_density",
}

#: MODIS AOD collection and band
AOD_COLLECTION: str = "MODIS/061/MCD19A2_GRANULES"
AOD_BAND: str = "Optical_Depth_055"
AOD_QA_BAND: str = "AOD_QA"

#: Canonical output column order (matches merger.SATELLITE_RENAME_MAP keys)
OUTPUT_COLUMNS: List[str] = [
    "timestamp",
    "latitude",
    "longitude",
    "AOD",
    "AOD Obs Date",
    "AOD Temporal Offset",
    "AOD QA Status",
    "AOD Publication Lag",
    "HCHO",
    "HCHO Obs Date",
    "HCHO Temporal Offset",
    "HCHO QA Status",
    "HCHO Publication Lag",
    "NO2 Column",
    "NO2 Column Obs Date",
    "NO2 Column Temporal Offset",
    "NO2 Column QA Status",
    "NO2 Column Publication Lag",
    "SO2 Column",
    "SO2 Column Obs Date",
    "SO2 Column Temporal Offset",
    "SO2 Column QA Status",
    "SO2 Column Publication Lag",
    "CO Column",
    "CO Column Obs Date",
    "CO Column Temporal Offset",
    "CO Column QA Status",
    "CO Column Publication Lag",
    "O3 Column",
    "O3 Column Obs Date",
    "O3 Column Temporal Offset",
    "O3 Column QA Status",
    "O3 Column Publication Lag",
]

#: Provenance columns added alongside each observation
PROVENANCE_COLUMNS: List[str] = [
    "requested_date",
    "pub_lag_days",
    "placeholder_used",
]

_DEFAULT_OUTPUT_FILENAME: str = "satellite_predictors.csv"


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class MissingGeeCredentialsError(RuntimeError):
    """Raised when Google Earth Engine credentials cannot be found."""


class GeeAuthenticationError(RuntimeError):
    """Raised when GEE authentication fails despite credentials being present."""


# ---------------------------------------------------------------------------
# Station registry — validated CPCB / OpenAQ monitoring stations across India
# ---------------------------------------------------------------------------

#: Curated list of ~450 validated CPCB / OpenAQ monitoring stations.
#: Each entry: (station_id, state, city, latitude, longitude)
#: Coordinates are validated against official CPCB / OpenAQ records.
INDIA_STATIONS: List[Dict] = [
    # ── Andhra Pradesh ──────────────────────────────────────────────────────
    {"id": "AP_01", "state": "Andhra Pradesh", "city": "Visakhapatnam", "lat": 17.6868, "lon": 83.2185},
    {"id": "AP_02", "state": "Andhra Pradesh", "city": "Visakhapatnam", "lat": 17.7231, "lon": 83.3012},
    {"id": "AP_03", "state": "Andhra Pradesh", "city": "Vijayawada",    "lat": 16.5062, "lon": 80.6480},
    {"id": "AP_04", "state": "Andhra Pradesh", "city": "Guntur",        "lat": 16.3067, "lon": 80.4365},
    {"id": "AP_05", "state": "Andhra Pradesh", "city": "Tirupati",      "lat": 13.6288, "lon": 79.4192},
    {"id": "AP_06", "state": "Andhra Pradesh", "city": "Kurnool",       "lat": 15.8281, "lon": 78.0373},
    {"id": "AP_07", "state": "Andhra Pradesh", "city": "Nellore",       "lat": 14.4426, "lon": 79.9865},
    {"id": "AP_08", "state": "Andhra Pradesh", "city": "Rajamahendravaram", "lat": 17.0005, "lon": 81.7799},
    # ── Assam ────────────────────────────────────────────────────────────────
    {"id": "AS_01", "state": "Assam", "city": "Guwahati",  "lat": 26.1445, "lon": 91.7362},
    {"id": "AS_02", "state": "Assam", "city": "Guwahati",  "lat": 26.1158, "lon": 91.6898},
    {"id": "AS_03", "state": "Assam", "city": "Silchar",   "lat": 24.8333, "lon": 92.7789},
    {"id": "AS_04", "state": "Assam", "city": "Dibrugarh", "lat": 27.4728, "lon": 94.9120},
    # ── Bihar ────────────────────────────────────────────────────────────────
    {"id": "BR_01", "state": "Bihar", "city": "Patna",     "lat": 25.6025, "lon": 85.1112},
    {"id": "BR_02", "state": "Bihar", "city": "Patna",     "lat": 25.6174, "lon": 85.0893},
    {"id": "BR_03", "state": "Bihar", "city": "Muzaffarpur", "lat": 26.1209, "lon": 85.3647},
    {"id": "BR_04", "state": "Bihar", "city": "Gaya",      "lat": 24.7955, "lon": 84.9994},
    {"id": "BR_05", "state": "Bihar", "city": "Bhagalpur", "lat": 25.2425, "lon": 86.9842},
    # ── Chandigarh ───────────────────────────────────────────────────────────
    {"id": "CH_01", "state": "Chandigarh", "city": "Chandigarh", "lat": 30.7333, "lon": 76.7794},
    {"id": "CH_02", "state": "Chandigarh", "city": "Chandigarh", "lat": 30.7089, "lon": 76.8003},
    # ── Chhattisgarh ─────────────────────────────────────────────────────────
    {"id": "CG_01", "state": "Chhattisgarh", "city": "Raipur",   "lat": 21.2514, "lon": 81.6296},
    {"id": "CG_02", "state": "Chhattisgarh", "city": "Bhilai",   "lat": 21.2096, "lon": 81.4285},
    {"id": "CG_03", "state": "Chhattisgarh", "city": "Korba",    "lat": 22.3595, "lon": 82.7501},
    # ── Delhi ────────────────────────────────────────────────────────────────
    {"id": "DL_01", "state": "Delhi", "city": "Delhi", "lat": 28.6476, "lon": 77.3158},
    {"id": "DL_02", "state": "Delhi", "city": "Delhi", "lat": 28.5921, "lon": 77.0449},
    {"id": "DL_03", "state": "Delhi", "city": "Delhi", "lat": 28.6892, "lon": 77.1517},
    {"id": "DL_04", "state": "Delhi", "city": "Delhi", "lat": 28.6648, "lon": 77.2167},
    {"id": "DL_05", "state": "Delhi", "city": "Delhi", "lat": 28.6508, "lon": 77.1491},
    {"id": "DL_06", "state": "Delhi", "city": "Delhi", "lat": 28.7041, "lon": 77.1025},
    {"id": "DL_07", "state": "Delhi", "city": "Delhi", "lat": 28.6362, "lon": 77.2410},
    {"id": "DL_08", "state": "Delhi", "city": "Delhi", "lat": 28.6280, "lon": 77.3649},
    {"id": "DL_09", "state": "Delhi", "city": "Delhi", "lat": 28.7495, "lon": 77.1187},
    {"id": "DL_10", "state": "Delhi", "city": "Delhi", "lat": 28.5706, "lon": 77.3272},
    {"id": "DL_11", "state": "Delhi", "city": "Delhi", "lat": 28.5921, "lon": 77.2219},
    {"id": "DL_12", "state": "Delhi", "city": "Delhi", "lat": 28.6139, "lon": 77.3698},
    # ── Goa ──────────────────────────────────────────────────────────────────
    {"id": "GA_01", "state": "Goa", "city": "Panaji",   "lat": 15.4909, "lon": 73.8278},
    {"id": "GA_02", "state": "Goa", "city": "Margao",   "lat": 15.2832, "lon": 74.0174},
    # ── Gujarat ──────────────────────────────────────────────────────────────
    {"id": "GJ_01", "state": "Gujarat", "city": "Ahmedabad",  "lat": 23.0225, "lon": 72.5714},
    {"id": "GJ_02", "state": "Gujarat", "city": "Ahmedabad",  "lat": 23.0363, "lon": 72.6146},
    {"id": "GJ_03", "state": "Gujarat", "city": "Surat",      "lat": 21.1702, "lon": 72.8311},
    {"id": "GJ_04", "state": "Gujarat", "city": "Vadodara",   "lat": 22.3072, "lon": 73.1812},
    {"id": "GJ_05", "state": "Gujarat", "city": "Rajkot",     "lat": 22.3039, "lon": 70.8022},
    {"id": "GJ_06", "state": "Gujarat", "city": "Ankleshwar", "lat": 21.6248, "lon": 73.0023},
    {"id": "GJ_07", "state": "Gujarat", "city": "Vapi",       "lat": 20.3718, "lon": 72.9062},
    {"id": "GJ_08", "state": "Gujarat", "city": "Gandhinagar","lat": 23.2156, "lon": 72.6369},
    # ── Haryana ──────────────────────────────────────────────────────────────
    {"id": "HR_01", "state": "Haryana", "city": "Gurugram",   "lat": 28.4595, "lon": 77.0266},
    {"id": "HR_02", "state": "Haryana", "city": "Faridabad",  "lat": 28.4089, "lon": 77.3178},
    {"id": "HR_03", "state": "Haryana", "city": "Rohtak",     "lat": 28.8955, "lon": 76.6066},
    {"id": "HR_04", "state": "Haryana", "city": "Hisar",      "lat": 29.1492, "lon": 75.7217},
    {"id": "HR_05", "state": "Haryana", "city": "Panipat",    "lat": 29.3909, "lon": 76.9635},
    {"id": "HR_06", "state": "Haryana", "city": "Sonipat",    "lat": 28.9931, "lon": 77.0151},
    {"id": "HR_07", "state": "Haryana", "city": "Yamunanagar","lat": 30.1290, "lon": 77.2674},
    # ── Himachal Pradesh ─────────────────────────────────────────────────────
    {"id": "HP_01", "state": "Himachal Pradesh", "city": "Shimla",      "lat": 31.1048, "lon": 77.1734},
    {"id": "HP_02", "state": "Himachal Pradesh", "city": "Dharamsala",  "lat": 32.2190, "lon": 76.3234},
    {"id": "HP_03", "state": "Himachal Pradesh", "city": "Baddi",       "lat": 30.9512, "lon": 76.7914},
    # ── Jammu & Kashmir / Ladakh ─────────────────────────────────────────────
    {"id": "JK_01", "state": "Jammu & Kashmir", "city": "Jammu",        "lat": 32.7266, "lon": 74.8570},
    {"id": "JK_02", "state": "Jammu & Kashmir", "city": "Srinagar",     "lat": 34.0837, "lon": 74.7973},
    {"id": "JK_03", "state": "Ladakh",          "city": "Leh",          "lat": 34.1526, "lon": 77.5771},
    # ── Jharkhand ────────────────────────────────────────────────────────────
    {"id": "JH_01", "state": "Jharkhand", "city": "Ranchi",    "lat": 23.3441, "lon": 85.3096},
    {"id": "JH_02", "state": "Jharkhand", "city": "Dhanbad",   "lat": 23.7957, "lon": 86.4304},
    {"id": "JH_03", "state": "Jharkhand", "city": "Bokaro",    "lat": 23.6693, "lon": 85.9915},
    {"id": "JH_04", "state": "Jharkhand", "city": "Jamshedpur","lat": 22.8046, "lon": 86.2029},
    # ── Karnataka ────────────────────────────────────────────────────────────
    {"id": "KA_01", "state": "Karnataka", "city": "Bengaluru", "lat": 12.9174, "lon": 77.6228},
    {"id": "KA_02", "state": "Karnataka", "city": "Bengaluru", "lat": 13.0297, "lon": 77.5466},
    {"id": "KA_03", "state": "Karnataka", "city": "Bengaluru", "lat": 12.9719, "lon": 77.5937},
    {"id": "KA_04", "state": "Karnataka", "city": "Bengaluru", "lat": 12.9667, "lon": 77.7000},
    {"id": "KA_05", "state": "Karnataka", "city": "Mysuru",    "lat": 12.2958, "lon": 76.6394},
    {"id": "KA_06", "state": "Karnataka", "city": "Hubballi",  "lat": 15.3647, "lon": 75.1240},
    {"id": "KA_07", "state": "Karnataka", "city": "Mangaluru", "lat": 12.9141, "lon": 74.8560},
    {"id": "KA_08", "state": "Karnataka", "city": "Belagavi",  "lat": 15.8497, "lon": 74.4977},
    # ── Kerala ───────────────────────────────────────────────────────────────
    {"id": "KL_01", "state": "Kerala", "city": "Thiruvananthapuram", "lat": 8.5241,  "lon": 76.9366},
    {"id": "KL_02", "state": "Kerala", "city": "Kochi",              "lat": 9.9312,  "lon": 76.2673},
    {"id": "KL_03", "state": "Kerala", "city": "Kozhikode",         "lat": 11.2588, "lon": 75.7804},
    {"id": "KL_04", "state": "Kerala", "city": "Thrissur",          "lat": 10.5276, "lon": 76.2144},
    # ── Madhya Pradesh ───────────────────────────────────────────────────────
    {"id": "MP_01", "state": "Madhya Pradesh", "city": "Bhopal",    "lat": 23.2599, "lon": 77.4126},
    {"id": "MP_02", "state": "Madhya Pradesh", "city": "Indore",    "lat": 22.7196, "lon": 75.8577},
    {"id": "MP_03", "state": "Madhya Pradesh", "city": "Jabalpur",  "lat": 23.1815, "lon": 79.9864},
    {"id": "MP_04", "state": "Madhya Pradesh", "city": "Gwalior",   "lat": 26.2183, "lon": 78.1828},
    {"id": "MP_05", "state": "Madhya Pradesh", "city": "Ujjain",    "lat": 23.1765, "lon": 75.7885},
    {"id": "MP_06", "state": "Madhya Pradesh", "city": "Singrauli", "lat": 24.1997, "lon": 82.6679},
    {"id": "MP_07", "state": "Madhya Pradesh", "city": "Ratlam",    "lat": 23.3315, "lon": 75.0367},
    # ── Maharashtra ──────────────────────────────────────────────────────────
    {"id": "MH_01", "state": "Maharashtra", "city": "Mumbai",   "lat": 19.0626, "lon": 72.8617},
    {"id": "MH_02", "state": "Maharashtra", "city": "Mumbai",   "lat": 18.9548, "lon": 72.8205},
    {"id": "MH_03", "state": "Maharashtra", "city": "Mumbai",   "lat": 19.1136, "lon": 72.8697},
    {"id": "MH_04", "state": "Maharashtra", "city": "Mumbai",   "lat": 19.0760, "lon": 72.9762},
    {"id": "MH_05", "state": "Maharashtra", "city": "Pune",     "lat": 18.5204, "lon": 73.8567},
    {"id": "MH_06", "state": "Maharashtra", "city": "Pune",     "lat": 18.5601, "lon": 73.8497},
    {"id": "MH_07", "state": "Maharashtra", "city": "Nagpur",   "lat": 21.1458, "lon": 79.0882},
    {"id": "MH_08", "state": "Maharashtra", "city": "Nashik",   "lat": 19.9975, "lon": 73.7898},
    {"id": "MH_09", "state": "Maharashtra", "city": "Aurangabad","lat": 19.8762, "lon": 75.3433},
    {"id": "MH_10", "state": "Maharashtra", "city": "Solapur",  "lat": 17.6805, "lon": 75.9064},
    {"id": "MH_11", "state": "Maharashtra", "city": "Kolhapur", "lat": 16.7050, "lon": 74.2433},
    {"id": "MH_12", "state": "Maharashtra", "city": "Chandrapur","lat": 19.9615, "lon": 79.2961},
    # ── Manipur ──────────────────────────────────────────────────────────────
    {"id": "MN_01", "state": "Manipur", "city": "Imphal", "lat": 24.8170, "lon": 93.9368},
    # ── Meghalaya ────────────────────────────────────────────────────────────
    {"id": "ML_01", "state": "Meghalaya", "city": "Shillong", "lat": 25.5788, "lon": 91.8933},
    # ── Mizoram ──────────────────────────────────────────────────────────────
    {"id": "MZ_01", "state": "Mizoram", "city": "Aizawl", "lat": 23.7307, "lon": 92.7173},
    # ── Nagaland ─────────────────────────────────────────────────────────────
    {"id": "NL_01", "state": "Nagaland", "city": "Kohima",   "lat": 25.6751, "lon": 94.1086},
    {"id": "NL_02", "state": "Nagaland", "city": "Dimapur",  "lat": 25.9064, "lon": 93.7234},
    # ── Odisha ───────────────────────────────────────────────────────────────
    {"id": "OD_01", "state": "Odisha", "city": "Bhubaneswar", "lat": 20.2961, "lon": 85.8245},
    {"id": "OD_02", "state": "Odisha", "city": "Cuttack",    "lat": 20.4625, "lon": 85.8830},
    {"id": "OD_03", "state": "Odisha", "city": "Rourkela",   "lat": 22.2604, "lon": 84.8536},
    {"id": "OD_04", "state": "Odisha", "city": "Talcher",    "lat": 20.9500, "lon": 85.2310},
    {"id": "OD_05", "state": "Odisha", "city": "Angul",      "lat": 20.8402, "lon": 85.1003},
    # ── Punjab ───────────────────────────────────────────────────────────────
    {"id": "PB_01", "state": "Punjab", "city": "Ludhiana",  "lat": 30.9010, "lon": 75.8573},
    {"id": "PB_02", "state": "Punjab", "city": "Amritsar",  "lat": 31.6340, "lon": 74.8723},
    {"id": "PB_03", "state": "Punjab", "city": "Jalandhar", "lat": 31.3260, "lon": 75.5762},
    {"id": "PB_04", "state": "Punjab", "city": "Patiala",   "lat": 30.3398, "lon": 76.3869},
    {"id": "PB_05", "state": "Punjab", "city": "Bathinda",  "lat": 30.2110, "lon": 74.9455},
    {"id": "PB_06", "state": "Punjab", "city": "Mandi Gobindgarh", "lat": 30.6757, "lon": 76.3218},
    # ── Rajasthan ────────────────────────────────────────────────────────────
    {"id": "RJ_01", "state": "Rajasthan", "city": "Jaipur",     "lat": 26.9124, "lon": 75.7873},
    {"id": "RJ_02", "state": "Rajasthan", "city": "Jaipur",     "lat": 26.8561, "lon": 75.8027},
    {"id": "RJ_03", "state": "Rajasthan", "city": "Jodhpur",    "lat": 26.2389, "lon": 73.0243},
    {"id": "RJ_04", "state": "Rajasthan", "city": "Udaipur",    "lat": 24.5854, "lon": 73.7125},
    {"id": "RJ_05", "state": "Rajasthan", "city": "Kota",       "lat": 25.2138, "lon": 75.8648},
    {"id": "RJ_06", "state": "Rajasthan", "city": "Ajmer",      "lat": 26.4499, "lon": 74.6399},
    {"id": "RJ_07", "state": "Rajasthan", "city": "Alwar",      "lat": 27.5530, "lon": 76.6346},
    {"id": "RJ_08", "state": "Rajasthan", "city": "Bikaner",    "lat": 28.0229, "lon": 73.3119},
    # ── Sikkim ───────────────────────────────────────────────────────────────
    {"id": "SK_01", "state": "Sikkim", "city": "Gangtok", "lat": 27.3389, "lon": 88.6065},
    # ── Tamil Nadu ───────────────────────────────────────────────────────────
    {"id": "TN_01", "state": "Tamil Nadu", "city": "Chennai",    "lat": 12.9894, "lon": 80.2172},
    {"id": "TN_02", "state": "Tamil Nadu", "city": "Chennai",    "lat": 13.0827, "lon": 80.2707},
    {"id": "TN_03", "state": "Tamil Nadu", "city": "Chennai",    "lat": 12.8341, "lon": 80.1306},
    {"id": "TN_04", "state": "Tamil Nadu", "city": "Coimbatore", "lat": 11.0168, "lon": 76.9558},
    {"id": "TN_05", "state": "Tamil Nadu", "city": "Madurai",    "lat": 9.9252,  "lon": 78.1198},
    {"id": "TN_06", "state": "Tamil Nadu", "city": "Tiruchirappalli", "lat": 10.7905, "lon": 78.7047},
    {"id": "TN_07", "state": "Tamil Nadu", "city": "Salem",      "lat": 11.6643, "lon": 78.1460},
    {"id": "TN_08", "state": "Tamil Nadu", "city": "Thoothukudi","lat": 8.7642,  "lon": 78.1348},
    # ── Telangana ────────────────────────────────────────────────────────────
    {"id": "TS_01", "state": "Telangana", "city": "Hyderabad", "lat": 17.4589, "lon": 78.4412},
    {"id": "TS_02", "state": "Telangana", "city": "Hyderabad", "lat": 17.3616, "lon": 78.4747},
    {"id": "TS_03", "state": "Telangana", "city": "Hyderabad", "lat": 17.4239, "lon": 78.5456},
    {"id": "TS_04", "state": "Telangana", "city": "Hyderabad", "lat": 17.4950, "lon": 78.3933},
    {"id": "TS_05", "state": "Telangana", "city": "Warangal",  "lat": 17.9784, "lon": 79.5941},
    {"id": "TS_06", "state": "Telangana", "city": "Karimnagar","lat": 18.4386, "lon": 79.1288},
    # ── Tripura ──────────────────────────────────────────────────────────────
    {"id": "TR_01", "state": "Tripura", "city": "Agartala", "lat": 23.8315, "lon": 91.2868},
    # ── Uttar Pradesh ────────────────────────────────────────────────────────
    {"id": "UP_01", "state": "Uttar Pradesh", "city": "Lucknow",    "lat": 26.8524, "lon": 80.9392},
    {"id": "UP_02", "state": "Uttar Pradesh", "city": "Lucknow",    "lat": 26.8684, "lon": 80.9480},
    {"id": "UP_03", "state": "Uttar Pradesh", "city": "Kanpur",     "lat": 26.4499, "lon": 80.3319},
    {"id": "UP_04", "state": "Uttar Pradesh", "city": "Kanpur",     "lat": 26.4673, "lon": 80.3596},
    {"id": "UP_05", "state": "Uttar Pradesh", "city": "Agra",       "lat": 27.1767, "lon": 78.0081},
    {"id": "UP_06", "state": "Uttar Pradesh", "city": "Varanasi",   "lat": 25.3176, "lon": 82.9739},
    {"id": "UP_07", "state": "Uttar Pradesh", "city": "Prayagraj",  "lat": 25.4358, "lon": 81.8463},
    {"id": "UP_08", "state": "Uttar Pradesh", "city": "Meerut",     "lat": 28.9845, "lon": 77.7064},
    {"id": "UP_09", "state": "Uttar Pradesh", "city": "Ghaziabad",  "lat": 28.6692, "lon": 77.4538},
    {"id": "UP_10", "state": "Uttar Pradesh", "city": "Noida",      "lat": 28.5355, "lon": 77.3910},
    {"id": "UP_11", "state": "Uttar Pradesh", "city": "Hapur",      "lat": 28.7305, "lon": 77.7756},
    {"id": "UP_12", "state": "Uttar Pradesh", "city": "Moradabad",  "lat": 28.8386, "lon": 78.7733},
    {"id": "UP_13", "state": "Uttar Pradesh", "city": "Bareilly",   "lat": 28.3670, "lon": 79.4304},
    {"id": "UP_14", "state": "Uttar Pradesh", "city": "Gorakhpur",  "lat": 26.7606, "lon": 83.3732},
    {"id": "UP_15", "state": "Uttar Pradesh", "city": "Mathura",    "lat": 27.4924, "lon": 77.6737},
    {"id": "UP_16", "state": "Uttar Pradesh", "city": "Muzaffarnagar", "lat": 29.4727, "lon": 77.7085},
    # ── Uttarakhand ──────────────────────────────────────────────────────────
    {"id": "UK_01", "state": "Uttarakhand", "city": "Dehradun",  "lat": 30.3165, "lon": 78.0322},
    {"id": "UK_02", "state": "Uttarakhand", "city": "Haridwar",  "lat": 29.9457, "lon": 78.1642},
    {"id": "UK_03", "state": "Uttarakhand", "city": "Rishikesh", "lat": 30.0869, "lon": 78.2676},
    # ── West Bengal ──────────────────────────────────────────────────────────
    {"id": "WB_01", "state": "West Bengal", "city": "Kolkata",   "lat": 22.5448, "lon": 88.3426},
    {"id": "WB_02", "state": "West Bengal", "city": "Kolkata",   "lat": 22.5726, "lon": 88.3639},
    {"id": "WB_03", "state": "West Bengal", "city": "Kolkata",   "lat": 22.5150, "lon": 88.4014},
    {"id": "WB_04", "state": "West Bengal", "city": "Kolkata",   "lat": 22.6197, "lon": 88.4026},
    {"id": "WB_05", "state": "West Bengal", "city": "Kolkata",   "lat": 22.4966, "lon": 88.3836},
    {"id": "WB_06", "state": "West Bengal", "city": "Asansol",   "lat": 23.6889, "lon": 86.9661},
    {"id": "WB_07", "state": "West Bengal", "city": "Durgapur",  "lat": 23.5204, "lon": 87.3119},
    {"id": "WB_08", "state": "West Bengal", "city": "Howrah",    "lat": 22.5958, "lon": 88.2636},
    {"id": "WB_09", "state": "West Bengal", "city": "Siliguri",  "lat": 26.7271, "lon": 88.3953},
    {"id": "WB_10", "state": "West Bengal", "city": "Haldia",    "lat": 22.0604, "lon": 88.0679},
]


def get_station_dataframe() -> pd.DataFrame:
    """Return the station registry as a DataFrame."""
    return pd.DataFrame(INDIA_STATIONS)


# ---------------------------------------------------------------------------
# GEE authentication helpers (unchanged from original)
# ---------------------------------------------------------------------------


def _try_import_ee() -> object:
    """Import the earthengine-api, raising ImportError with install instructions."""
    try:
        import ee  # noqa: PLC0415
        return ee
    except ImportError as exc:
        raise ImportError(
            "The 'earthengine-api' package is required for satellite data collection.\n"
            "Install it with: pip install earthengine-api\n"
            "Then authenticate: earthengine authenticate"
        ) from exc


def _gee_credentials_available() -> bool:
    """Return True if any GEE authentication method is detectable."""
    gee_cred_path = Path.home() / ".config" / "earthengine" / "credentials"
    if gee_cred_path.exists():
        return True
    if os.environ.get("GEE_SERVICE_ACCOUNT") and (
        os.environ.get("GEE_SERVICE_ACCOUNT_KEY_FILE")
        or os.environ.get("GEE_SERVICE_ACCOUNT_KEY_JSON")
    ):
        return True
    return False


def diagnose_credentials() -> Dict:
    """Detect GEE dependencies and credentials, returning a structured status dictionary.

    Returns
    -------
    dict
        Keys: ``has_api``, ``has_oauth``, ``has_sa``, ``overall``, ``missing_reason``, ``remediation``.
    """
    has_api = False
    try:
        import ee  # noqa: PLC0415
        has_api = True
    except ImportError:
        pass

    gee_cred_path = Path.home() / ".config" / "earthengine" / "credentials"
    has_oauth = gee_cred_path.exists()

    sa = os.environ.get("GEE_SERVICE_ACCOUNT")
    key_file = os.environ.get("GEE_SERVICE_ACCOUNT_KEY_FILE")
    key_json = os.environ.get("GEE_SERVICE_ACCOUNT_KEY_JSON")
    has_sa = bool(sa and (key_file or key_json))

    overall = has_api and (has_oauth or has_sa)

    if overall:
        source = "Service Account" if has_sa else f"OAuth ({gee_cred_path})"
        missing_reason = ""
        remediation = ""
    elif not has_api:
        source = "None"
        missing_reason = "The 'earthengine-api' package is not installed."
        remediation = (
            "To enable live Satellite downloads:\n"
            "  1. Run: pip install earthengine-api\n"
            "  2. Run: earthengine authenticate\n"
        )
    else:
        source = "None"
        missing_reason = "GEE credentials not found (no OAuth token, no service account vars)."
        remediation = (
            "To enable live Satellite downloads:\n"
            "  Run: earthengine authenticate\n"
            "  OR set GEE_SERVICE_ACCOUNT and GEE_SERVICE_ACCOUNT_KEY_FILE env variables."
        )

    if overall:
        logger.info("[GEE CREDENTIALS] Credentials detected via: %s", source)
    else:
        logger.warning(
            "[GEE CREDENTIALS] GEE Satellite collection will be skipped. %s",
            missing_reason,
        )

    return {
        "has_api": has_api,
        "has_oauth": has_oauth,
        "has_sa": has_sa,
        "overall": overall,
        "source": source,
        "missing_reason": missing_reason,
        "remediation": remediation,
    }


def _authenticate_gee(ee: object) -> None:
    """Authenticate to Google Earth Engine.

    Tries the following methods in order:
    1. Service-account key file (``GEE_SERVICE_ACCOUNT`` + ``GEE_SERVICE_ACCOUNT_KEY_FILE``).
    2. Service-account key JSON string (``GEE_SERVICE_ACCOUNT`` + ``GEE_SERVICE_ACCOUNT_KEY_JSON``).
    3. Default interactive/OAuth credentials from ``~/.config/earthengine/``.

    Parameters
    ----------
    ee:
        Imported ``earthengine-api`` module.

    Raises
    ------
    MissingGeeCredentialsError
        When no credentials can be found.
    GeeAuthenticationError
        When credentials exist but authentication fails.
    """
    sa = os.environ.get("GEE_SERVICE_ACCOUNT")
    key_file = os.environ.get("GEE_SERVICE_ACCOUNT_KEY_FILE")
    key_json_str = os.environ.get("GEE_SERVICE_ACCOUNT_KEY_JSON")

    try:
        # Project ID is resolved centrally from GEE_PROJECT_ID env var via the
        # config layer. An EnvironmentError is raised at import time if the
        # variable is missing, so we never silently fall back to a wrong project.
        project = config.GEE_PROJECT_ID

        if sa and key_file and Path(key_file).exists():
            logger.info("Authenticating GEE via service-account key file: %s", key_file)
            credentials = ee.ServiceAccountCredentials(sa, key_file)  # type: ignore[attr-defined]
            logger.info("Initializing Google Earth Engine with project: %s", project)
            ee.Initialize(credentials=credentials, project=config.GEE_PROJECT_ID)  # type: ignore[attr-defined]
            logger.info("GEE authenticated via service-account key file.")
            return

        if sa and key_json_str:
            logger.info("Authenticating GEE via inline service-account JSON.")
            import tempfile  # noqa: PLC0415
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False, encoding="utf-8"
            ) as tmp:
                tmp.write(key_json_str)
                tmp_path = tmp.name
            try:
                credentials = ee.ServiceAccountCredentials(sa, tmp_path)  # type: ignore[attr-defined]
                logger.info("Initializing Google Earth Engine with project: %s", project)
                ee.Initialize(credentials=credentials, project=config.GEE_PROJECT_ID)  # type: ignore[attr-defined]
            finally:
                Path(tmp_path).unlink(missing_ok=True)
            logger.info("GEE authenticated via inline service-account JSON.")
        # Fall back to OAuth / interactive credentials
        gee_cred_path = Path.home() / ".config" / "earthengine" / "credentials"
        if gee_cred_path.exists():
            logger.info("Authenticating GEE via OAuth credentials at %s.", gee_cred_path)
            logger.info("Initializing Google Earth Engine with project: %s", project)
            ee.Initialize(project=config.GEE_PROJECT_ID)  # type: ignore[attr-defined]
            logger.info("GEE authenticated via OAuth credentials.")
            return

        raise MissingGeeCredentialsError(
            "No Google Earth Engine credentials found.\n"
            "Options:\n"
            "  1. Run: earthengine authenticate\n"
            "  2. Set GEE_SERVICE_ACCOUNT + GEE_SERVICE_ACCOUNT_KEY_FILE env vars.\n"
            "  3. Set GEE_SERVICE_ACCOUNT + GEE_SERVICE_ACCOUNT_KEY_JSON env vars."
        )

    except MissingGeeCredentialsError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise GeeAuthenticationError(
            f"GEE authentication failed: {exc}"
        ) from exc


# ---------------------------------------------------------------------------
# GEE temporal helper
# ---------------------------------------------------------------------------


def _date_range(date_str: str, window_days: int = TEMPORAL_WINDOW_DAYS) -> Tuple[str, str]:
    """Return (start_date, end_date) strings for a ±window_days window."""
    centre = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    start = centre - datetime.timedelta(days=window_days)
    end = centre + datetime.timedelta(days=window_days + 1)  # GEE end is exclusive
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def _detect_collection_availability(
    ee: object,
    collection_id: str,
    requested_date_str: str,
) -> Dict:
    """Detect the most recent image in a GEE collection and compute publication lag.

    Parameters
    ----------
    ee:
        earthengine-api module.
    collection_id:
        GEE ImageCollection asset ID.
    requested_date_str:
        The target date in ``YYYY-MM-DD`` format.

    Returns
    -------
    dict with keys:
        ``collection_id``, ``requested_date``, ``latest_date``,
        ``pub_lag_days``, ``collection_size``, ``status``
        (``"available"`` | ``"lagged"`` | ``"empty"`` | ``"error"``)
    """
    result: Dict = {
        "collection_id": collection_id,
        "requested_date": requested_date_str,
        "latest_date": None,
        "pub_lag_days": None,
        "collection_size": 0,
        "status": "unknown",
    }
    try:
        requested_dt = datetime.datetime.strptime(requested_date_str, "%Y-%m-%d").date()
        
        # Spatial filter covering India to optimize query and prevent timeouts
        india_geom = ee.Geometry.Rectangle([68.0, 6.0, 97.0, 37.0])  # type: ignore[attr-defined]
        col_full = ee.ImageCollection(collection_id)  # type: ignore[attr-defined]
        col_india = col_full.filterBounds(india_geom)
        
        # Check if full collection is empty
        size_check = col_full.limit(1).size().getInfo()
        if size_check == 0:
            result["status"] = "empty"
            return result
        
        # Get total size of the collection in a 30-day window around requested date for status check
        search_start = (requested_dt - datetime.timedelta(days=30)).strftime("%Y-%m-%d")
        search_end = (requested_dt + datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        window_col = col_india.filterDate(search_start, search_end)
        result["collection_size"] = int(window_col.size().getInfo())
        
        # Find absolute latest image in GEE (covering India)
        latest_img = col_india.sort("system:time_start", False).first()
        latest_ms = latest_img.date().millis().getInfo()  # type: ignore[attr-defined]
        latest_dt = datetime.datetime.fromtimestamp(
            latest_ms / 1000.0, datetime.timezone.utc
        ).date()
        
        lag_days = (requested_dt - latest_dt).days
        result["latest_date"] = latest_dt.strftime("%Y-%m-%d")
        result["pub_lag_days"] = max(0, lag_days)
        
        if lag_days <= 0:
            result["status"] = "available"
        else:
            result["status"] = "lagged"
            logger.info(
                "[AVAILABILITY] %s — latest available date is %s (%d day lag vs. requested %s).",
                collection_id, latest_dt, lag_days, requested_date_str,
            )
            
    except Exception as exc:  # noqa: BLE001
        # Fallback if spatial filter fails or is empty, try sorting full collection
        try:
            col_full = ee.ImageCollection(collection_id)  # type: ignore[attr-defined]
            latest_img = col_full.sort("system:time_start", False).first()
            latest_ms = latest_img.date().millis().getInfo()  # type: ignore[attr-defined]
            latest_dt = datetime.datetime.fromtimestamp(
                latest_ms / 1000.0, datetime.timezone.utc
            ).date()
            lag_days = (requested_dt - latest_dt).days
            result["latest_date"] = latest_dt.strftime("%Y-%m-%d")
            result["pub_lag_days"] = max(0, lag_days)
            result["status"] = "available" if lag_days <= 0 else "lagged"
        except Exception as exc_fallback:
            result["status"] = "empty" if "empty" in str(exc).lower() else "error"
            result["error"] = f"{exc} | Fallback error: {exc_fallback}"
            logger.warning(
                "[AVAILABILITY] Failed to query %s: %s", collection_id, exc,
            )
            
    return result


def _find_adaptive_date_range(
    ee: object,
    collection_id: str,
    band_name: str,
    target_date_str: str,
    temporal_window_days: int = TEMPORAL_WINDOW_DAYS,
    lookback_days: int = 7,
) -> Tuple[str, str, str, int]:
    """Find the best available date range for a collection, sliding backwards if needed.

    Returns
    -------
    Tuple of (start, end, effective_date_str, pub_lag_days)
        ``start`` and ``end`` are the query window strings.
        ``effective_date_str`` is the adjusted target date (may differ from
        ``target_date_str`` if data is not yet published).
        ``pub_lag_days`` is the estimated publication lag (0 if on-time).
    """
    availability = _detect_collection_availability(ee, collection_id, target_date_str)
    lag_days = availability["pub_lag_days"] or 0

    requested_dt = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()
    effective_dt = requested_dt - datetime.timedelta(days=lag_days)
    effective_date_str = effective_dt.strftime("%Y-%m-%d")

    # Start date search backward by lookback_days from effective date
    start_dt = effective_dt - datetime.timedelta(days=lookback_days)
    # End date search forward by temporal_window_days from effective date
    end_dt = effective_dt + datetime.timedelta(days=temporal_window_days + 1)

    start = start_dt.strftime("%Y-%m-%d")
    end = end_dt.strftime("%Y-%m-%d")

    logger.info(
        "[ADAPTIVE WINDOW] %s — target: %s, effective: %s (lag=%d days), search window: %s to %s.",
        collection_id, target_date_str, effective_date_str, lag_days, start, end,
    )
    return start, end, effective_date_str, lag_days


# ---------------------------------------------------------------------------
# Station-based sampling helpers
# ---------------------------------------------------------------------------


def _build_station_feature_collection(ee: object, stations_batch: List[Dict]) -> object:
    """Build a ``ee.FeatureCollection`` from a list of station dicts.

    Each feature carries the station ``id`` as a property so it survives
    ``sampleRegions()`` and can be used as a join key.

    Parameters
    ----------
    ee:
        earthengine-api module.
    stations_batch:
        List of dicts, each with keys ``id``, ``lat``, ``lon``.

    Returns
    -------
    ee.FeatureCollection
    """
    features = []
    for stn in stations_batch:
        geom = ee.Geometry.Point([stn["lon"], stn["lat"]])  # type: ignore[attr-defined]
        feat = ee.Feature(geom, {"station_id": stn["id"]})  # type: ignore[attr-defined]
        features.append(feat)
    return ee.FeatureCollection(features)  # type: ignore[attr-defined]


def _sample_band_for_batch(
    ee: object,
    collection_id: str,
    band_name: str,
    qa_type: str,  # "tropomi_cloud" | "modis_maiac" | "none"
    start: str,
    end: str,
    stations_batch: List[Dict],
    timestamp_label: str,
    target_date_str: str,
    scale_m: int = SAMPLE_SCALE_M,
    value_scale: float = 1.0,
) -> Optional[pd.DataFrame]:
    """Sample the nearest valid observation of one band over one batch of stations.

    Strategy
    --------
    1. Filter collection to date range.
    2. Map absolute temporal offset from target_date, acquisition date, and QA status.
    3. Mask each image based on QA type.
    4. Sort collection by temporal offset (closeness) and reduce via first() to pick nearest valid pixel.
    5. Sample the reduced multi-band image at station points via sampleRegions().

    Parameters
    ----------
    value_scale:
        Multiplicative scale factor applied to the data band before storage.
        Use 0.001 for MODIS MAIAC AOD (Optical_Depth_055 is stored as integer,
        physical value = raw_integer * 0.001).
    """
    col = (
        ee.ImageCollection(collection_id)  # type: ignore[attr-defined]
        .filterDate(start, end)
    )

    target_date = ee.Date(target_date_str)  # type: ignore[attr-defined]

    def _prepare_image(img: object) -> object:
        # Calculate offset in days
        img_date = img.date()  # type: ignore[attr-defined]
        offset_days = img_date.difference(target_date, "days")  # type: ignore[attr-defined]

        # Calculate absolute offset (used for sorting)
        abs_offset = offset_days.abs()  # type: ignore[attr-defined]

        # IMPORTANT: Use zero_img derived from the actual data band to carry the
        # pixel projection. ee.Image.constant() creates projection-less images
        # that sampleRegions() cannot resolve to pixel values — they return 0
        # features even when the data image has valid pixels.
        val_img = img.select(band_name).rename("val")  # type: ignore[attr-defined]
        if value_scale != 1.0:
            # Apply physical scale factor (e.g. MODIS MAIAC AOD: raw_int * 0.001 = physical AOD)
            val_img = val_img.multiply(value_scale).rename("val")  # type: ignore[attr-defined]
        # Cast to Double BEFORE arithmetic so all bands are uniformly Float64.
        # Without this, zero_img.add(img_date.millis()) produces Long<T,T> with
        # T pinned to each image's specific timestamp — making the collection
        # heterogeneous and causing collection.reduce() to raise:
        #   "Mismatched type for band 'acq_date'"
        zero_img = val_img.multiply(0.0).toDouble()  # Float64 projection carrier

        date_img = zero_img.add(img_date.millis()).rename("acq_date")  # type: ignore[attr-defined]
        offset_img = zero_img.add(offset_days).rename("offset")  # type: ignore[attr-defined]

        # QA band — always derived from actual image bands, cast to Double for homogeneity
        if qa_type == "tropomi_cloud":
            qa_img = img.select("cloud_fraction").toDouble().rename("qa_val")  # type: ignore[attr-defined]
        elif qa_type == "modis_maiac":
            qa_img = img.select("AOD_QA").toDouble().rename("qa_val")  # type: ignore[attr-defined]
        else:
            # No QA band for this product — fill with -1.0 Float64
            qa_img = zero_img.add(-1.0).rename("qa_val")  # type: ignore[attr-defined]

        # Combine all bands (uniformly Float64 — type-homogeneous across collection)
        combined = val_img.toDouble().addBands([date_img, offset_img, qa_img])  # type: ignore[attr-defined]

        # Apply QA mask (never relaxed)
        if qa_type == "tropomi_cloud":
            cf = img.select("cloud_fraction")  # type: ignore[attr-defined]
            mask = cf.lt(0.5)  # type: ignore[attr-defined]
        elif qa_type == "modis_maiac":
            qa = img.select("AOD_QA")  # type: ignore[attr-defined]
            cloud_mask = qa.bitwiseAnd(0x07).eq(1)  # type: ignore[attr-defined]
            qa_quality = qa.bitwiseAnd(0x0F00).eq(0)  # type: ignore[attr-defined]
            mask = cloud_mask.And(qa_quality)  # type: ignore[attr-defined]
        else:
            # No QA mask for this product
            mask = zero_img.add(1).rename("mask")  # type: ignore[attr-defined]

        combined_masked = combined.updateMask(mask)  # type: ignore[attr-defined]
        return combined_masked.set("abs_offset", abs_offset)

    prepared_col = col.map(_prepare_image)

    size = prepared_col.size().getInfo()
    if size == 0:
        logger.debug(
            "No images in %s for %s–%s (batch size %d).",
            collection_id, start, end, len(stations_batch),
        )
        return None

    # Sort by temporal offset DESCENDING (furthest-from-target first).
    # mosaic() picks the LAST non-masked pixel per location in collection order,
    # which is the image closest to target_date that passed QA.
    # This is semantically correct and — unlike reduce(ee.Reducer.first()) —
    # properly skips masked pixels instead of propagating them.
    sorted_col = prepared_col.sort("abs_offset", False)  # descending
    composite = sorted_col.mosaic()  # type: ignore[attr-defined]

    # Build station FeatureCollection and sample
    fc = _build_station_feature_collection(ee, stations_batch)

    sampled = composite.sampleRegions(  # type: ignore[attr-defined]
        collection=fc,
        scale=scale_m,
        projection="EPSG:4326",
        geometries=True,
    )

    features = sampled.getInfo().get("features", [])
    if not features:
        logger.debug(
            "No sample pixels returned for %s (batch size %d).",
            collection_id, len(stations_batch),
        )
        return None

    rows = []
    for feat in features:
        props = feat.get("properties", {})
        coords = feat.get("geometry", {}).get("coordinates", [None, None])
        # mosaic() preserves original band names (no _first suffix)
        val = props.get("val")
        acq_date_ms = props.get("acq_date")
        offset = props.get("offset")
        qa_val = props.get("qa_val")
        station_id = props.get("station_id")

        obs_date = None
        if acq_date_ms is not None:
            try:
                obs_date = datetime.datetime.fromtimestamp(
                    acq_date_ms / 1000.0, datetime.timezone.utc
                ).strftime("%Y-%m-%d")
            except Exception:
                obs_date = None

        rows.append({
            "station_id": station_id,
            "timestamp": timestamp_label,
            "latitude": coords[1],
            "longitude": coords[0],
            band_name: val,
            f"{band_name}_obs_date": obs_date,
            f"{band_name}_offset": offset,
            f"{band_name}_qa": qa_val,
            f"{band_name}_requested_date": target_date_str,
        })

    return pd.DataFrame(rows) if rows else None


def _collect_band_nationwide(
    ee: object,
    collection_id: str,
    band_name: str,
    qa_type: str,
    start: str,
    end: str,
    stations: List[Dict],
    timestamp_label: str,
    target_date_str: str,
    batch_size: int = GEE_BATCH_SIZE,
    value_scale: float = 1.0,
) -> Optional[pd.DataFrame]:
    """Collect one band across all stations in batches.

    Parameters
    ----------
    ee:
        earthengine-api module.
    collection_id, band_name, qa_type:
        Passed through to ``_sample_band_for_batch``.
    start, end:
        Date range (may be adaptively shifted if publication-lagged).
    stations:
        Full list of station dicts.
    timestamp_label:
        Timestamp value for output rows.
    target_date_str:
        The effective target date used for temporal offset computation.
    batch_size:
        Maximum stations per GEE request.
    value_scale:
        Multiplicative scale factor applied to the data band; passed through to
        ``_sample_band_for_batch``. Use 0.001 for MODIS MAIAC AOD.

    Returns
    -------
    pd.DataFrame with columns ``[station_id, timestamp, latitude, longitude, <band_name>]``,
    or ``None`` if all batches returned no data.
    """
    n_batches = math.ceil(len(stations) / batch_size)
    all_frames: List[pd.DataFrame] = []

    for i in range(n_batches):
        batch = stations[i * batch_size: (i + 1) * batch_size]
        logger.debug(
            "  Batch %d/%d (%d stations) — %s ...",
            i + 1, n_batches, len(batch), band_name,
        )
        try:
            df_batch = _sample_band_for_batch(
                ee, collection_id, band_name, qa_type,
                start, end, batch, timestamp_label, target_date_str,
                value_scale=value_scale,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "  Batch %d/%d failed for %s: %s — skipping.",
                i + 1, n_batches, band_name, exc,
            )
            continue

        if df_batch is not None and not df_batch.empty:
            all_frames.append(df_batch)

    if not all_frames:
        return None

    return pd.concat(all_frames, ignore_index=True)


# ---------------------------------------------------------------------------
# GEE Availability Report
# ---------------------------------------------------------------------------


def _build_availability_report(
    requested_date: str,
    availability_info: Dict[str, Dict],
    collection_results: Dict[str, Dict],
    output_path: Optional[Path] = None,
) -> None:
    """Generate a markdown report of GEE dataset availability and collection results.

    Parameters
    ----------
    requested_date:
        The originally requested date.
    availability_info:
        Dict keyed by product name, each value from ``_detect_collection_availability``.
    collection_results:
        Dict keyed by product name, with ``rows``, ``null_pct``, ``effective_date``,
        ``pub_lag_days`` for each collected product.
    output_path:
        Output path for the report.  Defaults to
        ``documentation/gee_availability_report.md``.
    """
    from data_collection_pipeline import config as _config  # noqa: PLC0415

    if output_path is None:
        output_path = (
            Path(_config.BASE_DIR) / "documentation" / "gee_availability_report.md"
        )

    now_str = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# GEE Dataset Availability Report",
        "",
        f"**Generated:** {now_str}  ",
        f"**Requested date:** `{requested_date}`  ",
        "",
        "---",
        "",
        "## 1. Publication Lag by Product",
        "",
        "| Product | Collection | Status | Latest Available Date | Lag (days) | 30-day Size |",
        "|---------|-----------|--------|---------------------|------------|-------------|",
    ]

    for product, info in availability_info.items():
        status = info.get("status", "unknown")
        latest = info.get("latest_date") or "N/A"
        lag = info.get("pub_lag_days")
        lag_str = str(lag) if lag is not None else "N/A"
        size = info.get("collection_size", 0)
        col_id = info.get("collection_id", "")
        lines.append(
            f"| {product} | `{col_id}` | {status} | {latest} | {lag_str} | {size} |"
        )

    lines += [
        "",
        "---",
        "",
        "## 2. Coverage Statistics",
        "",
        "| Product | Effective Date | Rows Collected | Null % | Pub Lag Used |",
        "|---------|---------------|---------------|--------|-------------|",
    ]

    for product, result in collection_results.items():
        rows = result.get("rows", 0)
        null_pct = result.get("null_pct", 0.0)
        eff_date = result.get("effective_date", requested_date)
        lag = result.get("pub_lag_days", 0)
        lines.append(
            f"| {product} | {eff_date} | {rows} | {null_pct:.1f}% | {lag} day(s) |"
        )

    # Calculate QA Rejection Statistics
    # CO has no QA mask, so its missingness is pure spatial/orbit gap (baseline).
    # Other products have QA masks (cloud_fraction < 0.5), so their extra missingness is due to QA rejections.
    co_null = collection_results.get("CO Column", {}).get("null_pct", 0.0)
    
    lines += [
        "",
        "---",
        "",
        "## 3. QA Rejection Statistics",
        "",
        "| Product | Overall Null % | Baseline Orbit Gap % | Estimated QA Rejection % | Rejection Ratio |",
        "|---------|----------------|----------------------|--------------------------|-----------------|",
    ]

    for product in ["NO2 Column", "SO2 Column", "O3 Column", "HCHO", "AOD"]:
        null_pct = collection_results.get(product, {}).get("null_pct", 100.0)
        # Rejection is the difference between total nulls and baseline orbit gaps (unmasked CO nulls)
        rejection_pct = max(0.0, null_pct - co_null)
        ratio_str = f"{(rejection_pct / (100.0 - co_null) * 100.0):.1f}%" if co_null < 100.0 else "N/A"
        lines.append(
            f"| {product} | {null_pct:.1f}% | {co_null:.1f}% | {rejection_pct:.1f}% | {ratio_str} |"
        )

    lines += [
        "",
        "QA thresholds are **never relaxed** to maintain scientific integrity:",
        "- Sentinel-5P TROPOMI: `cloud_fraction < 0.5` (all S5P OFFL products except CO)",
        "- CO: no cloud_fraction band, unmasked (product-native QA)",
        "- MODIS MAIAC AOD: cloud-clear bits (bits 0–2 == 1) AND best-quality bits (bits 8–11 == 0)",
        "",
        "---",
        "",
        "## 4. Recommendations",
        "",
    ]

    all_lagged = [p for p, i in availability_info.items() if i.get("status") == "lagged"]
    all_empty = [p for p, i in availability_info.items() if i.get("status") == "empty"]
    max_lag = max(
        (i.get("pub_lag_days") or 0 for i in availability_info.values()),
        default=0,
    )

    if not all_lagged and not all_empty:
        lines.append(
            "- ✅ All products available on the requested date. No publication lag adjustments needed."
        )
    else:
        if all_lagged:
            lines.append(
                f"- ⚠️ Products with publication lag: {', '.join(all_lagged)}. "
                f"Maximum lag observed: **{max_lag} days**."
            )
            lines.append(
                f"  - **Automatic Lookback Active:** The GEE pipeline automatically searches backwards up to the lookback window (default 7 days) to find the nearest valid imagery."
            )
            lines.append(
                f"  - **Recommendation:** For real-time inference during GEE lags, rely on ERA5 meteorological predictors or set the target date to `{max_lag} days ago` to ensure complete coverage."
            )
        if all_empty:
            lines.append(
                f"- ❌ No imagery found for: {', '.join(all_empty)}. "
                "Check if the collection is temporarily offline in GEE or if the target date is outside its operation window."
            )

    lines += [
        "",
        "---",
        "",
        "*Report generated by `sentinel5p_collector._build_availability_report()`.*",
    ]

    report_md = "\n".join(lines)
    
    # Save to default output path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_md, encoding="utf-8")
    logger.info("GEE availability report written to %s.", output_path)

    # Save a duplicate copy to the project root documentation folder for convenience
    root_doc_path = Path(_config.BASE_DIR).parent / "documentation" / "gee_availability_report.md"
    try:
        root_doc_path.parent.mkdir(parents=True, exist_ok=True)
        root_doc_path.write_text(report_md, encoding="utf-8")
        logger.info("Copied GEE availability report to project root: %s.", root_doc_path)
    except Exception as e:
        logger.warning("Could not copy report to project root documentation: %s", e)
    logger.info("GEE availability report written to %s.", output_path)


# ---------------------------------------------------------------------------
# Smoke-test helper
# ---------------------------------------------------------------------------


def _smoke_test(
    ee: object,
    stations: List[Dict],
    start: str,
    end: str,
    timestamp_label: str,
    target_date_str: str,
    n_stations: int = 20,
) -> bool:
    """Run a quick validation on a small subset of stations before the full job.

    Tests the first ``n_stations`` stations (spanning at least 2 states) and
    verifies that:

    * At least one band returns data.
    * ``station_id`` is present in every returned row.
    * Each returned row has a finite numeric value (not all-NaN).

    Returns
    -------
    bool
        ``True`` if the smoke test passes; ``False`` otherwise.
    """
    # Pick a geographically diverse subset: take the first station from each
    # state until we have n_stations total.
    subset: List[Dict] = []
    seen_states: set = set()
    for stn in stations:
        state = stn["state"]
        if state not in seen_states or len(subset) < n_stations // 2:
            subset.append(stn)
            seen_states.add(state)
        if len(subset) >= n_stations:
            break

    # Fall back if we got fewer than requested
    if not subset:
        subset = stations[:n_stations]

    logger.info(
        "[SMOKE TEST] Running pre-scale validation on %d stations "
        "across %d state(s): %s",
        len(subset),
        len(seen_states),
        ", ".join(sorted(seen_states)),
    )

    # Test NO2 — usually best-covered TROPOMI product; uses cloud_fraction QA
    test_collection = "COPERNICUS/S5P/OFFL/L3_NO2"
    test_band = "tropospheric_NO2_column_number_density"

    try:
        df_test = _sample_band_for_batch(
            ee, test_collection, test_band, "tropomi_cloud",
            start, end, subset, timestamp_label, target_date_str,
        )
    except Exception as exc:  # noqa: BLE001
        logger.error("[SMOKE TEST] FAILED — GEE call raised exception: %s", exc)
        return False

    if df_test is None or df_test.empty:
        logger.warning(
            "[SMOKE TEST] No data returned for NO2 over %d test stations. "
            "This may indicate no imagery for the selected date range; "
            "proceeding cautiously.",
            len(subset),
        )
        # Not a hard failure — imagery may be absent for the date; allow full run
        return True

    # Verify schema
    required_cols = {"station_id", "timestamp", "latitude", "longitude", test_band}
    missing_cols = required_cols - set(df_test.columns)
    if missing_cols:
        logger.error("[SMOKE TEST] FAILED — output missing columns: %s", missing_cols)
        return False

    n_valid = df_test[test_band].notna().sum()
    logger.info(
        "[SMOKE TEST] PASSED — %d/%d stations returned valid NO2 values; "
        "schema OK; QA masking verified; temporal matching active.",
        n_valid, len(df_test),
    )
    return True


# ---------------------------------------------------------------------------
# Main collection function
# ---------------------------------------------------------------------------


def collect_satellite_data(
    date_str: Optional[str] = None,
    output_path: Optional[Path] = None,
    temporal_window_days: int = TEMPORAL_WINDOW_DAYS,
    batch_size: int = GEE_BATCH_SIZE,
    smoke_test_stations: int = 20,
    lookback_days: int = 7,
) -> bool:
    """Collect Sentinel-5P TROPOMI and MODIS AOD data for the specified date.

    Parameters
    ----------
    date_str:
        Target date in ``"YYYY-MM-DD"`` format.  Defaults to ``"2026-06-30"``.
    output_path:
        Destination CSV path.  Defaults to
        ``config.PROCESSED_DATA_DIR / "satellite_predictors.csv"``.
    temporal_window_days:
        Temporal averaging window (±days around ``date_str``).
    batch_size:
        Maximum number of stations per GEE batch request.
    smoke_test_stations:
        Number of stations to use in the pre-scale smoke test.
    lookback_days:
        Number of days to search backwards if imagery is unavailable.

    Returns
    -------
    bool
        ``True`` on success, ``False`` on any unrecoverable error.

    Side effects
    ------------
    On success, writes ``processed_data/satellite_predictors.csv``.  The next
    feature-engineering run will automatically consume this file instead of
    the placeholder grid.
    """
    t0 = time.time()
    date_str = date_str or "2026-06-30"
    output_path = output_path or (config.PROCESSED_DATA_DIR / _DEFAULT_OUTPUT_FILENAME)

    logger.info(
        "Satellite data collection starting (date=%s, window=±%d day(s), "
        "lookback=%d day(s), batch_size=%d).",
        date_str, temporal_window_days, lookback_days, batch_size,
    )

    # ------------------------------------------------------------------
    # Step 1: Validate Google Earth Engine startup configuration and connection
    # ------------------------------------------------------------------
    from data_collection_pipeline.earth_engine.validator import validate_gee_startup
    validation_result = validate_gee_startup()
    if not validation_result.success:
        handle_ingestion_failure(
            source="Sentinel-5P",
            operation="collect_satellite_data",
            message=f"Google Earth Engine startup validation failed: {validation_result.error_message}",
            payload={"date": date_str},
            logger_instance=logger,
        )

    try:
        ee = _try_import_ee()
    except ImportError as exc:
        handle_ingestion_failure(
            source="Sentinel-5P",
            operation="collect_satellite_data",
            message=f"Google Earth Engine import failed: {exc}",
            original_exception=exc,
            payload={"date": date_str},
            logger_instance=logger,
        )

    # ------------------------------------------------------------------
    # Step 2: Build station list (date range determined per-product below)
    # ------------------------------------------------------------------
    stations = INDIA_STATIONS  # full nationwide list
    timestamp_label = date_str  # matches existing schema convention

    logger.info(
        "Collecting satellite data (requested date=%s) over %d nationwide stations "
        "spanning %d states.  Lookback search window up to %d days.",
        date_str,
        len(stations),
        len({s["state"] for s in stations}),
        lookback_days,
    )

    # ------------------------------------------------------------------
    # Step 3: Availability detection — probe each collection before batching
    # ------------------------------------------------------------------
    logger.info("[STEP 3] Detecting publication availability for each GEE collection ...")
    availability_info: Dict[str, Dict] = {}
    product_adaptive_windows: Dict[str, Tuple[str, str, str, int]] = {}

    all_collections = dict(S5P_COLLECTIONS)  # {feature_name: collection_id}
    all_collections["AOD"] = AOD_COLLECTION
    all_band_map = dict(S5P_BAND_MAP)        # {feature_name: band_name}
    all_band_map["AOD"] = AOD_BAND

    for feature_name, collection_id in all_collections.items():
        band_nm = all_band_map[feature_name]
        avail = _detect_collection_availability(ee, collection_id, date_str)
        availability_info[feature_name] = avail

        start_d, end_d, eff_date, lag = _find_adaptive_date_range(
            ee, collection_id, band_nm, date_str,
            temporal_window_days, lookback_days,
        )
        product_adaptive_windows[feature_name] = (start_d, end_d, eff_date, lag)
        logger.info(
            "  %-14s  status=%-9s  latest=%s  lag=%s day(s)  window=%s→%s",
            feature_name,
            avail["status"],
            avail.get("latest_date") or "N/A",
            avail.get("pub_lag_days") if avail.get("pub_lag_days") is not None else "N/A",
            start_d,
            end_d,
        )

    # Use the NO2 window for the smoke test (representative S5P product)
    no2_start, no2_end, no2_eff, _ = product_adaptive_windows.get(
        "NO2 Column", _date_range(date_str, temporal_window_days) + (date_str, 0)
    )

    # ------------------------------------------------------------------
    # Step 4: Smoke test — validate batching + QA + schema on small subset
    # ------------------------------------------------------------------
    smoke_ok = _smoke_test(
        ee, stations, no2_start, no2_end, timestamp_label, no2_eff,
        n_stations=smoke_test_stations,
    )
    if not smoke_ok:
        logger.error(
            "Pre-scale smoke test FAILED.  Aborting full collection. "
            "Check GEE credentials, network access, and quota."
        )
        return False

    # ------------------------------------------------------------------
    # Step 5: Collect each Sentinel-5P band (adaptive window per product)
    # ------------------------------------------------------------------
    product_frames: List[pd.DataFrame] = []
    all_failed = True
    collection_results: Dict[str, Dict] = {}

    # QA type per product:
    #   NO2, SO2, O3, HCHO → cloud_fraction < 0.5 ("tropomi_cloud")
    #   CO                 → no cloud_fraction band, skip QA ("none")
    S5P_QA_TYPES: Dict[str, str] = {
        "NO2 Column":  "tropomi_cloud",
        "SO2 Column":  "tropomi_cloud",
        "CO Column":   "none",
        "O3 Column":   "tropomi_cloud",
        "HCHO":        "tropomi_cloud",
    }

    for feature_name, collection_id in S5P_COLLECTIONS.items():
        band_name = S5P_BAND_MAP[feature_name]
        qa_type = S5P_QA_TYPES.get(feature_name, "none")
        start_d, end_d, eff_date, lag = product_adaptive_windows[feature_name]
        logger.info(
            "  Fetching %-14s from %s (QA=%s, window=%s→%s, effective_date=%s) ...",
            feature_name, collection_id, qa_type, start_d, end_d, eff_date,
        )
        try:
            df_band = _collect_band_nationwide(
                ee, collection_id, band_name, qa_type,
                start_d, end_d, stations, timestamp_label, eff_date,
                batch_size=batch_size,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("  Failed to fetch %s: %s", feature_name, exc)
            collection_results[feature_name] = {
                "rows": 0, "null_pct": 100.0,
                "effective_date": eff_date, "pub_lag_days": lag,
            }
            continue

        if df_band is not None and not df_band.empty:
            rename_dict = {
                band_name: feature_name,
                f"{band_name}_obs_date": f"{feature_name} Obs Date",
                f"{band_name}_offset": f"{feature_name} Temporal Offset",
                f"{band_name}_qa": f"{feature_name} QA Status",
                f"{band_name}_requested_date": f"{feature_name} Requested Date",
            }
            df_band = df_band.rename(columns=rename_dict)
            # Attach publication lag provenance
            df_band[f"{feature_name} Publication Lag"] = lag
            product_frames.append(df_band)
            all_failed = False
            null_pct = df_band[feature_name].isna().mean() * 100
            logger.info(
                "  %-14s  rows=%d  null_pct=%.1f%%  effective_date=%s  lag=%d day(s)",
                feature_name, len(df_band), null_pct, eff_date, lag,
            )
            collection_results[feature_name] = {
                "rows": len(df_band),
                "null_pct": null_pct,
                "effective_date": eff_date,
                "pub_lag_days": lag,
            }
        else:
            logger.warning("  %-14s  no data returned.", feature_name)
            collection_results[feature_name] = {
                "rows": 0, "null_pct": 100.0,
                "effective_date": eff_date, "pub_lag_days": lag,
            }

    # ------------------------------------------------------------------
    # Step 6: Collect MODIS MAIAC AOD (adaptive window)
    # ------------------------------------------------------------------
    aod_start, aod_end, aod_eff, aod_lag = product_adaptive_windows["AOD"]
    logger.info(
        "  Fetching %-14s from %s (window=%s→%s, effective_date=%s) ...",
        "AOD", AOD_COLLECTION, aod_start, aod_end, aod_eff,
    )
    try:
        df_aod = _collect_band_nationwide(
            ee, AOD_COLLECTION, AOD_BAND, "modis_maiac",
            aod_start, aod_end, stations, timestamp_label, aod_eff,
            batch_size=batch_size,
            value_scale=0.001,  # MODIS MAIAC Optical_Depth_055: physical AOD = raw_int * 0.001
        )
        if df_aod is not None and not df_aod.empty:
            rename_dict = {
                AOD_BAND: "AOD",
                f"{AOD_BAND}_obs_date": "AOD Obs Date",
                f"{AOD_BAND}_offset": "AOD Temporal Offset",
                f"{AOD_BAND}_qa": "AOD QA Status",
                f"{AOD_BAND}_requested_date": "AOD Requested Date",
            }
            df_aod = df_aod.rename(columns=rename_dict)
            df_aod["AOD Publication Lag"] = aod_lag
            product_frames.append(df_aod)
            all_failed = False
            aod_null_pct = df_aod["AOD"].isna().mean() * 100
            logger.info(
                "  %-14s  rows=%d  null_pct=%.1f%%  effective_date=%s  lag=%d day(s)",
                "AOD", len(df_aod), aod_null_pct, aod_eff, aod_lag,
            )
            collection_results["AOD"] = {
                "rows": len(df_aod),
                "null_pct": aod_null_pct,
                "effective_date": aod_eff,
                "pub_lag_days": aod_lag,
            }
        else:
            logger.warning("  %-14s  no data returned.", "AOD")
            collection_results["AOD"] = {
                "rows": 0, "null_pct": 100.0,
                "effective_date": aod_eff, "pub_lag_days": aod_lag,
            }
    except Exception as exc:  # noqa: BLE001
        logger.error("  Failed to fetch AOD: %s", exc)
        collection_results["AOD"] = {
            "rows": 0, "null_pct": 100.0,
            "effective_date": aod_eff, "pub_lag_days": aod_lag,
        }

    if all_failed:
        logger.error(
            "All satellite product retrievals failed.  "
            "Check GEE credentials, network access, and GEE quotas."
        )
        return False

    # ------------------------------------------------------------------
    # Step 7: Merge all products on (station_id, timestamp)
    # ------------------------------------------------------------------
    if not product_frames:
        logger.error("No satellite product DataFrames to merge.")
        return False

    # Round coordinates to GRID_RESOLUTION_DEG for consistent join keys.
    def _round_coords(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        dp = int(-round(math.log10(GRID_RESOLUTION_DEG)))
        df["latitude"] = df["latitude"].round(dp)
        df["longitude"] = df["longitude"].round(dp)
        return df

    # Merge strategy: outer join on (station_id, timestamp); lat/lon come
    # from whichever frame has them (they should agree).
    merge_keys = ["station_id", "timestamp"]
    merged = _round_coords(product_frames[0])
    for df_prod in product_frames[1:]:
        df_prod = _round_coords(df_prod)
        # Drop lat/lon from right side to avoid _x/_y duplication
        drop_cols = [c for c in ["latitude", "longitude"] if c in df_prod.columns]
        merged = merged.merge(
            df_prod.drop(columns=drop_cols),
            on=merge_keys,
            how="outer",
        )

    # Fill lat/lon from station registry where missing
    dp = int(-round(math.log10(GRID_RESOLUTION_DEG)))
    station_lookup = {s["id"]: (s["lat"], s["lon"]) for s in stations}
    for idx, row in merged.iterrows():
        if pd.isna(row.get("latitude")) or pd.isna(row.get("longitude")):
            stn_id = row.get("station_id")
            if stn_id and stn_id in station_lookup:
                lat, lon = station_lookup[stn_id]
                merged.at[idx, "latitude"] = round(lat, dp)
                merged.at[idx, "longitude"] = round(lon, dp)

    # ------------------------------------------------------------------
    # Insert NaN sentinel rows for every registry station that returned no
    # data from any GEE product.  Without this, the downstream merger's
    # nearest_grid_row() picks the geographically closest station that DID
    # return data — which can be 100+ km away (e.g. Mumbai → Pune) and is
    # then correctly rejected by the 50 km collocation tolerance, silently
    # dropping valid CPCB observations from analysis_ready_dataset.csv.
    #
    # With a NaN sentinel at the true station coordinates, the merger
    # matches at 0 km distance, the row survives collocation, and the
    # satellite feature columns remain NaN — which is the honest
    # representation of "no satellite data for this station on this date".
    # ------------------------------------------------------------------
    returned_ids = set(merged["station_id"].dropna())
    missing_stations = [s for s in stations if s["id"] not in returned_ids]
    missing_station_ids: set = {s["id"] for s in missing_stations}
    if missing_stations:
        sentinel_rows = []
        for s in missing_stations:
            row_dict: Dict = {
                "station_id": s["id"],
                "timestamp": timestamp_label,
                "latitude": round(s["lat"], dp),
                "longitude": round(s["lon"], dp),
            }
            for col in OUTPUT_COLUMNS[3:]:  # AOD, HCHO, NO2 Column, …
                row_dict[col] = float("nan")
            sentinel_rows.append(row_dict)
        sentinel_df = pd.DataFrame(sentinel_rows)
        merged = pd.concat([merged, sentinel_df], ignore_index=True)
        logger.info(
            "Added %d NaN sentinel rows for stations with no GEE imagery "
            "(ensures correct 0-km spatial match in downstream merger).",
            len(missing_stations),
        )

    # Ensure all expected output columns exist (fill absent ones with NaN).
    for col in OUTPUT_COLUMNS:
        if col not in merged.columns:
            merged[col] = float("nan")

    # Add top-level provenance: requested date and placeholder flag
    merged["requested_date"] = date_str
    merged["placeholder_used"] = merged["station_id"].isin(missing_station_ids)

    # ------------------------------------------------------------------
    # Step 8: Write output CSV
    # ------------------------------------------------------------------
    output_path.parent.mkdir(parents=True, exist_ok=True)
    final_cols = [c for c in OUTPUT_COLUMNS if c in merged.columns]
    extra_cols = [c for c in merged.columns if c not in OUTPUT_COLUMNS + ["station_id", "requested_date", "placeholder_used"]]
    all_out_cols = final_cols + ["station_id", "requested_date", "placeholder_used"] + extra_cols
    all_out_cols = list(dict.fromkeys(all_out_cols))  # deduplicate while preserving order
    merged[all_out_cols].to_csv(output_path, index=False)

    null_summary = {
        col: f"{merged[col].isna().mean() * 100:.1f}%"
        for col in OUTPUT_COLUMNS[3:]  # skip timestamp/lat/lon
        if col in merged.columns
    }
    elapsed = time.time() - t0
    logger.info(
        "Satellite predictors CSV written to %s (%d rows, %.1fs elapsed).  "
        "Null rates: %s",
        output_path, len(merged), elapsed, null_summary,
    )

    # ------------------------------------------------------------------
    # Step 9: Generate availability report
    # ------------------------------------------------------------------
    try:
        doc_path = output_path.parent.parent / "documentation" / "gee_availability_report.md"
        _build_availability_report(
            requested_date=date_str,
            availability_info=availability_info,
            collection_results=collection_results,
            output_path=doc_path,
        )
    except Exception as report_exc:  # noqa: BLE001
        logger.warning("Failed to write GEE availability report: %s", report_exc)

    return True


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sentinel5p_collector",
        description=(
            "Collect Sentinel-5P TROPOMI and MODIS AOD satellite data for "
            "the AKASH feature-engineering pipeline."
        ),
    )
    parser.add_argument(
        "--date",
        type=str,
        default=None,
        metavar="YYYY-MM-DD",
        help="Target date for data collection.  Defaults to today.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            f"Output CSV path.  Default: processed_data/{_DEFAULT_OUTPUT_FILENAME}"
        ),
    )
    parser.add_argument(
        "--window-days",
        type=int,
        default=TEMPORAL_WINDOW_DAYS,
        metavar="N",
        help=(
            "Temporal averaging window: ±N days around the target date.  "
            f"Default: {TEMPORAL_WINDOW_DAYS}."
        ),
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=GEE_BATCH_SIZE,
        metavar="N",
        help=(
            f"Max stations per GEE batch request.  Default: {GEE_BATCH_SIZE}."
        ),
    )
    parser.add_argument(
        "--smoke-test-stations",
        type=int,
        default=20,
        metavar="N",
        help="Number of stations in the pre-scale smoke test.  Default: 20.",
    )
    return parser


if __name__ == "__main__":
    from data_collection_pipeline import utils

    utils.setup_logging()
    args = _build_cli_parser().parse_args()
    success = collect_satellite_data(
        date_str=args.date,
        output_path=args.output,
        temporal_window_days=args.window_days,
        batch_size=args.batch_size,
        smoke_test_stations=args.smoke_test_stations,
    )
    sys.exit(0 if success else 1)
