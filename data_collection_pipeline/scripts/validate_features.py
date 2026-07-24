"""
Feature Validation CLI entry point.

Usage:
    python -m data_collection_pipeline.scripts.validate_features
    python -m data_collection_pipeline.scripts.validate_features --base-dir /path/to/pipeline

Outputs:
    documentation/feature_validation_report.md
    documentation/feature_validation_summary.csv

Exit codes:
    0 — success (PASS or WARN only)
    1 — hard failures present (when --fail-on-error is set)
"""

from __future__ import annotations

import argparse
import logging
import sys
import json
import datetime
import shutil
from pathlib import Path

# Ensure the pipeline root is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from data_collection_pipeline.validation.pipeline_tracer import (
    PipelineTracer,
    STATUS_FAIL,
    STATUS_WARN_EXPECTED,
    STATUS_WARN_INVESTIGATE,
    STATUS_PASS,
    STATUS_SKIP,
    _aggregate_status,
)
from data_collection_pipeline.validation.report_generator import ValidationReportGenerator
from data_collection_pipeline import config

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s [%(name)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("data_collection_pipeline.validate_features")


def update_checkpoint(stage: str, status: str, findings: str, next_stage: str, base_dir: Path):
    """Write progress checkpoint to JSON for resumability."""
    root_doc_dir = base_dir.parent / "documentation"
    pipeline_doc_dir = base_dir / "documentation"

    for doc_dir in [root_doc_dir, pipeline_doc_dir]:
        doc_dir.mkdir(parents=True, exist_ok=True)
        checkpoint_path = doc_dir / "feature_validation_checkpoint.json"

        data: dict = {}
        if checkpoint_path.exists():
            try:
                with open(checkpoint_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass

        data["current_stage"] = stage
        data["status"] = status
        data.setdefault("stages", {})[stage] = status
        data.setdefault("findings", {})[stage] = findings
        data["next_stage"] = next_stage
        data["last_updated"] = datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

        try:
            with open(checkpoint_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as exc:
            logger.error("Failed to write checkpoint to %s: %s", checkpoint_path, exc)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run AQI pipeline feature validation and generate reports.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--base-dir",
        type=Path,
        default=None,
        help="Path to data_collection_pipeline/ directory. Defaults to config.BASE_DIR.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=None,
        help="Directory to write reports to. Defaults to <base-dir>/documentation/.",
    )
    parser.add_argument(
        "--fail-on-error",
        action="store_true",
        default=False,
        help="Exit with code 1 if any feature has FAIL status.",
    )
    args = parser.parse_args()
    base_dir = args.base_dir if args.base_dir else Path(config.BASE_DIR)

    update_checkpoint(
        stage="schema_creation",
        status="COMPLETE",
        findings="Centralized feature schema loaded from validation/feature_schema.py.",
        next_stage="propagation_validation",
        base_dir=base_dir,
    )

    logger.info("Starting AQI pipeline feature validation...")

    # Run tracer
    tracer = PipelineTracer(base_dir=args.base_dir)
    results = tracer.run()

    # Count by all four status levels
    overall_statuses = [_aggregate_status(r) for r in results.values()]
    n_pass = overall_statuses.count(STATUS_PASS)
    n_we   = overall_statuses.count(STATUS_WARN_EXPECTED)
    n_wi   = overall_statuses.count(STATUS_WARN_INVESTIGATE)
    n_fail = overall_statuses.count(STATUS_FAIL)
    n_skip = overall_statuses.count(STATUS_SKIP)
    n_total = len(overall_statuses)

    logger.info(
        "Validation complete: %d PASS | %d WARN_EXPECTED | %d WARN_INVESTIGATE | %d FAIL | %d total",
        n_pass, n_we, n_wi, n_fail, n_total,
    )

    update_checkpoint(
        stage="propagation_validation",
        status="COMPLETE",
        findings=(
            f"Validated {n_total} features. "
            f"{n_pass} PASS, {n_we} WARN_EXPECTED, {n_wi} WARN_INVESTIGATE, {n_fail} FAIL."
        ),
        next_stage="report_generation",
        base_dir=base_dir,
    )

    # Write reports
    report_dir = args.output_dir
    gen = ValidationReportGenerator(results, output_dir=report_dir)
    paths = gen.write_all()

    # Mirror to root documentation folder
    root_doc_dir = base_dir.parent / "documentation"
    if root_doc_dir.resolve() != Path(paths["markdown"]).parent.resolve():
        root_doc_dir.mkdir(parents=True, exist_ok=True)
        try:
            shutil.copy2(paths["markdown"], root_doc_dir / "feature_validation_report.md")
            shutil.copy2(paths["csv"], root_doc_dir / "feature_validation_summary.csv")
            logger.info("Mirrored reports to %s", root_doc_dir)
        except Exception as exc:
            logger.error("Failed to mirror reports: %s", exc)

    update_checkpoint(
        stage="report_generation",
        status="COMPLETE",
        findings="feature_validation_report.md and feature_validation_summary.csv written.",
        next_stage="none",
        base_dir=base_dir,
    )

    logger.info("Feature validation report: %s", paths["markdown"])
    logger.info("Feature validation summary CSV: %s", paths["csv"])

    # ── Console summary ───────────────────────────────────────────────────────
    print("\n" + "=" * 66)
    print("  AQI Pipeline Feature Validation Summary")
    print("=" * 66)
    print(f"  [PASS]             : {n_pass:4d}  (meets all expectations)")
    print(f"  [WARN_EXPECTED]    : {n_we:4d}  (expected operational limitation)")
    print(f"  [WARN_INVESTIGATE] : {n_wi:4d}  (unexpected — requires investigation)")
    print(f"  [FAIL]             : {n_fail:4d}  (hard failure — must fix)")
    print(f"  Total              : {n_total:4d}")
    print("=" * 66)

    if n_fail > 0:
        print(f"\n[FAIL] {n_fail} feature(s) FAILED validation:")
        for fname, stage_results in results.items():
            if _aggregate_status(stage_results) == STATUS_FAIL:
                for sr in stage_results:
                    for chk in sr.checks:
                        if chk.status == STATUS_FAIL:
                            print(f"  * {fname} [{sr.stage}/{chk.rule}]: {chk.detail[:100]}")
                            break

    if n_wi > 0:
        print(f"\n[WARN_INVESTIGATE] {n_wi} feature(s) require investigation:")
        for fname, stage_results in results.items():
            if _aggregate_status(stage_results) == STATUS_WARN_INVESTIGATE:
                for sr in stage_results:
                    for chk in sr.checks:
                        if chk.status == STATUS_WARN_INVESTIGATE:
                            print(f"  * {fname} [{sr.stage}/{chk.rule}]: {chk.detail[:100]}")
                            break

    if n_we > 0:
        print(f"\n[WARN_EXPECTED] {n_we} feature(s) have expected operational limitations:")
        for fname, stage_results in results.items():
            if _aggregate_status(stage_results) == STATUS_WARN_EXPECTED:
                # Only print first expected warning per feature
                for sr in stage_results:
                    for chk in sr.checks:
                        if chk.status == STATUS_WARN_EXPECTED:
                            print(f"  ~ {fname} [{sr.stage}/{chk.rule}]: {chk.detail[:80]}...")
                            break
                    else:
                        continue
                    break

    print(f"\nReports written to:")
    print(f"  {paths['markdown']}")
    print(f"  {paths['csv']}")
    print()

    if args.fail_on_error and n_fail > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
