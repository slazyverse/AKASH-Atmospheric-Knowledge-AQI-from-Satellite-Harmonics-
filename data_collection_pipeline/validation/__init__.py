"""
Feature Validation Package.

Provides end-to-end feature validation for the AQI pipeline:
- Centralized feature schema with per-stage unit expectations
- Unit, range, dtype, null, and provenance field validation
- Pipeline-stage propagation tracing (Collector → ML model)
- Report generation (Markdown + CSV)
"""

from data_collection_pipeline.validation.feature_schema import (
    PIPELINE_FEATURE_SCHEMA,
    FeatureSpec,
    StageSpec,
    PIPELINE_STAGES,
    ML_MODEL_GROUPS,
)
from data_collection_pipeline.validation.pipeline_tracer import PipelineTracer
from data_collection_pipeline.validation.report_generator import ValidationReportGenerator

__all__ = [
    "PIPELINE_FEATURE_SCHEMA",
    "FeatureSpec",
    "StageSpec",
    "PIPELINE_STAGES",
    "ML_MODEL_GROUPS",
    "PipelineTracer",
    "ValidationReportGenerator",
]
