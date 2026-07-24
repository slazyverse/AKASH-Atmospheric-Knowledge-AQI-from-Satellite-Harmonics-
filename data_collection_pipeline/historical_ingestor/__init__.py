"""
Phase 1 — Historical Training Pipeline for AKASH / VAYU-DRISHTI.

This package orchestrates the ingestion, cleaning, feature engineering,
and baseline-model training steps over a multi-year historical date range.

It is additive: the existing real-time pipeline (main.py, scripts/run_pipeline.py)
is unaffected.  All public API surfaces in the existing modules that are called
from here accept optional kwargs with safe defaults so that the real-time path
continues to work without modification.

Public API
----------
run_historical_pipeline
    Entry point called by ``scripts/run_pipeline.py --historical``.
"""

from data_collection_pipeline.historical_ingestor.pipeline import run_historical_pipeline

__all__ = ["run_historical_pipeline"]
