"""
Run the complete feature validation pipeline.
"""

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("run_feature_validation")

from data_collection_pipeline.validation.pipeline_tracer import (
    PipelineTracer, _aggregate_status,
    STATUS_PASS, STATUS_WARN_EXPECTED, STATUS_WARN_INVESTIGATE, STATUS_FAIL, STATUS_SKIP,
)
from data_collection_pipeline.validation.report_generator import ValidationReportGenerator
from data_collection_pipeline.validation.feature_schema import MAX_ADAPTIVE_LOOKBACK_DAYS, TEMPORAL_WINDOW_DAYS


def main():
    logger.info("=== AQI Feature Validation Pipeline ===")
    logger.info("Configured temporal offset window: [-%d, +%d] days", MAX_ADAPTIVE_LOOKBACK_DAYS, TEMPORAL_WINDOW_DAYS)

    tracer = PipelineTracer()
    results = tracer.run()

    counts = {STATUS_PASS: 0, STATUS_WARN_EXPECTED: 0, STATUS_WARN_INVESTIGATE: 0, STATUS_FAIL: 0, STATUS_SKIP: 0}
    for fname, stage_results in results.items():
        s = _aggregate_status(stage_results)
        counts[s] = counts.get(s, 0) + 1

    total = len(results)
    logger.info("=== Validation Summary ===")
    logger.info("  Total features validated : %d", total)
    logger.info("  PASS                     : %d", counts[STATUS_PASS])
    logger.info("  WARNING (expected)        : %d", counts[STATUS_WARN_EXPECTED])
    logger.info("  WARNING (investigate)     : %d", counts[STATUS_WARN_INVESTIGATE])
    logger.info("  FAIL                     : %d", counts[STATUS_FAIL])
    logger.info("  SKIP                     : %d", counts[STATUS_SKIP])

    for fname, stage_results in results.items():
        s = _aggregate_status(stage_results)
        if s in (STATUS_WARN_INVESTIGATE, STATUS_FAIL):
            logger.warning("  [%s] %s", s, fname)
            for sr in stage_results:
                for chk in sr.checks:
                    if chk.status in (STATUS_WARN_INVESTIGATE, STATUS_FAIL):
                        logger.warning("      [%s / %s] %s", sr.stage, chk.rule, chk.detail)

    doc_dir = Path(__file__).resolve().parent / "documentation"
    gen = ValidationReportGenerator(results, output_dir=doc_dir)
    paths = gen.write_all()
    logger.info("Report written to: %s", paths["markdown"])
    logger.info("CSV summary written to: %s", paths["csv"])

    checkpoint = {
        "current_stage": "report_generation",
        "status": "COMPLETE",
        "stages": {"schema_creation": "COMPLETE", "propagation_validation": "COMPLETE", "report_generation": "COMPLETE"},
        "findings": {
            "schema_creation": (
                "Centralized feature schema loaded from validation/feature_schema.py. "
                f"Configured temporal offset window: [-{MAX_ADAPTIVE_LOOKBACK_DAYS}, +{TEMPORAL_WINDOW_DAYS}] days. "
                "Relative Humidity valid_range tightened to (0.0, 100.0); ERA5 spectral artefact tolerance documented."
            ),
            "propagation_validation": (
                f"Validated {total} features. "
                f"{counts[STATUS_PASS]} PASS, "
                f"{counts[STATUS_WARN_EXPECTED]} WARNING (expected), "
                f"{counts[STATUS_WARN_INVESTIGATE]} WARNING (investigate), "
                f"{counts[STATUS_FAIL]} FAIL."
            ),
            "report_generation": "feature_validation_report.md and feature_validation_summary.csv written.",
        },
        "next_stage": "none",
        "last_updated": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    ckpt_path = doc_dir / "feature_validation_checkpoint.json"
    ckpt_path.write_text(json.dumps(checkpoint, indent=2), encoding="utf-8")
    logger.info("Checkpoint updated: %s", ckpt_path)

    if counts[STATUS_FAIL] > 0:
        logger.error("FAIL: %d features have hard failures.", counts[STATUS_FAIL])
        sys.exit(1)
    logger.info("Validation complete.")


if __name__ == "__main__":
    main()
