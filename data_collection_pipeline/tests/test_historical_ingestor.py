"""Tests for the historical CPCB Ground data ingestion pipeline."""

from __future__ import annotations

import numpy as np
import pandas as pd
from pathlib import Path

from data_collection_pipeline.historical_ingestor.cpcb_loader import (
    HistoricalCPCBLoader,
    standardize_station_name
)


def test_standardize_station_name():
    """Verify that station names are standardized correctly."""
    assert standardize_station_name("Anand Vihar, Delhi - DPCC") == "anandvihardelhi"
    assert standardize_station_name("Anand Vihar, Delhi (DPCC)") == "anandvihardelhidpcc"
    assert standardize_station_name("BTM Layout, Bengaluru - CPCB") == "btmlayoutbengaluru"
    assert standardize_station_name("Worli, Mumbai - MPCB") == "worlimumbai"


def test_station_metadata_mapping():
    """Verify that raw station names match registry Station IDs."""
    loader = HistoricalCPCBLoader(use_openaq=False)
    
    # Check exact matching
    stn_id, meta = loader._find_station_id("Anand Vihar, Delhi - DPCC")
    assert "anand vihar" in str(meta.get("Station Name")).lower()
    assert meta["City"] == "Delhi"
    
    # Check core fallback matching
    stn_id2, meta2 = loader._find_station_id("Anand Vihar, Delhi (DPCC)")
    assert stn_id2 == stn_id
    
    # Check dynamic fallback matching
    stn_id_unknown, meta_unknown = loader._find_station_id("ZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZZ")
    assert stn_id_unknown.startswith("STN_FLB")


def test_data_validation_and_flagging():
    """Verify bounds, stuck value, and spike QA flagging."""
    loader = HistoricalCPCBLoader(use_openaq=False)
    
    # Setup test observations dataframe
    records = [
        # Normal sequence
        {"station_id": "STN_012", "station_name": "Anand Vihar", "latitude": 28.6, "longitude": 77.3, "city": "Delhi", "state": "Delhi", "country": "IN", "timestamp_utc": pd.Timestamp("2025-01-01 00:00:00"), "timestamp_local": pd.Timestamp("2025-01-01 05:30:00"), "pollutant": "PM2.5", "value": 50.0, "unit": "ug/m3", "source": "CPCB"},
        {"station_id": "STN_012", "station_name": "Anand Vihar", "latitude": 28.6, "longitude": 77.3, "city": "Delhi", "state": "Delhi", "country": "IN", "timestamp_utc": pd.Timestamp("2025-01-01 01:00:00"), "timestamp_local": pd.Timestamp("2025-01-01 06:30:00"), "pollutant": "PM2.5", "value": 60.0, "unit": "ug/m3", "source": "CPCB"},
        # Spike value (from 60 to 400 is > 500% change where base > 10)
        {"station_id": "STN_012", "station_name": "Anand Vihar", "latitude": 28.6, "longitude": 77.3, "city": "Delhi", "state": "Delhi", "country": "IN", "timestamp_utc": pd.Timestamp("2025-01-01 02:00:00"), "timestamp_local": pd.Timestamp("2025-01-01 07:30:00"), "pollutant": "PM2.5", "value": 400.0, "unit": "ug/m3", "source": "CPCB"},
        # Out of bounds value (PM2.5 max is 1000)
        {"station_id": "STN_012", "station_name": "Anand Vihar", "latitude": 28.6, "longitude": 77.3, "city": "Delhi", "state": "Delhi", "country": "IN", "timestamp_utc": pd.Timestamp("2025-01-01 03:00:00"), "timestamp_local": pd.Timestamp("2025-01-01 08:30:00"), "pollutant": "PM2.5", "value": 1500.0, "unit": "ug/m3", "source": "CPCB"}
    ]
    df = pd.DataFrame(records)
    
    flagged = loader._validate_and_flag_observations(df)
    
    # Assert spike check flagged
    assert flagged.iloc[2]["qa_flag"] == "SUSPECT_SPIKE"
    
    # Assert bounds check set out of range to NaN and INVALID
    assert pd.isna(flagged.iloc[3]["value"])
    assert flagged.iloc[3]["qa_flag"] == "INVALID"


def test_merge_and_deduplicate():
    """Verify source priority: CPCB overrides OpenAQ on duplicate keys."""
    loader = HistoricalCPCBLoader(use_openaq=False)
    
    cpcb_records = [
        {"station_id": "STN_012", "timestamp_utc": pd.Timestamp("2025-01-01 00:00:00"), "pollutant": "PM2.5", "value": 50.0, "source": "CPCB"}
    ]
    openaq_records = [
        # Same key, different value
        {"station_id": "STN_012", "timestamp_utc": pd.Timestamp("2025-01-01 00:00:00"), "pollutant": "PM2.5", "value": 55.0, "source": "OpenAQ"},
        # Unique key
        {"station_id": "STN_012", "timestamp_utc": pd.Timestamp("2025-01-01 01:00:00"), "pollutant": "PM2.5", "value": 60.0, "source": "OpenAQ"}
    ]
    
    df_cpcb = pd.DataFrame(cpcb_records)
    df_openaq = pd.DataFrame(openaq_records)
    
    merged = loader._merge_and_deduplicate(df_cpcb, df_openaq)
    
    assert len(merged) == 2
    
    # Verify that the CPCB record value (50.0) is kept for the duplicate key
    dup_row = merged[merged["timestamp_utc"] == pd.Timestamp("2025-01-01 00:00:00")]
    assert len(dup_row) == 1
    assert dup_row.iloc[0]["value"] == 50.0
    assert dup_row.iloc[0]["source"] == "CPCB"
