"""
Report Generator: aggregates pipeline validation results into
  - documentation/feature_validation_report.md  (full narrative)
  - documentation/feature_validation_summary.csv (one row per feature)

Four status levels are rendered distinctly:
  STATUS_PASS            → ✅ PASS
  STATUS_WARN_EXPECTED   → ℹ️  WARNING (expected)  (expected operational limitation)
  STATUS_WARN_INVESTIGATE → ⚠️  WARNING (investigate) (requires investigation)
  STATUS_FAIL            → ❌ FAIL
  STATUS_SKIP            → —  SKIP (not in pipeline)
"""

from __future__ import annotations

import csv
import datetime
import logging
from pathlib import Path
from typing import Dict, List, Optional

from data_collection_pipeline import config
from data_collection_pipeline.validation.pipeline_tracer import (
    StageResult,
    STATUS_PASS,
    STATUS_WARN_EXPECTED,
    STATUS_WARN_INVESTIGATE,
    STATUS_FAIL,
    STATUS_SKIP,
    _aggregate_status,
)
from data_collection_pipeline.validation.feature_schema import (
    PIPELINE_FEATURE_SCHEMA,
    PIPELINE_STAGES,
    TEMPORAL_WINDOW_DAYS,
    MAX_ADAPTIVE_LOOKBACK_DAYS,
    FeatureSpec,
)

logger = logging.getLogger(__name__)

# Emoji legend
_EMOJI: Dict[str, str] = {
    STATUS_PASS: "✅",
    STATUS_WARN_EXPECTED: "ℹ️",
    STATUS_WARN_INVESTIGATE: "⚠️",
    STATUS_FAIL: "❌",
    STATUS_SKIP: "—",
}

_WARN_STATUSES = {STATUS_WARN_EXPECTED, STATUS_WARN_INVESTIGATE}


def _is_warn(status: str) -> bool:
    return status in _WARN_STATUSES


class ValidationReportGenerator:
    """Writes the feature validation Markdown report and CSV summary."""

    def __init__(
        self,
        results: Dict[str, List[StageResult]],
        output_dir: Optional[Path] = None,
    ):
        self.results = results
        self.output_dir = Path(output_dir) if output_dir else (
            Path(config.BASE_DIR) / "documentation"
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.timestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _overall_status(self, feature_name: str) -> str:
        return _aggregate_status(self.results[feature_name])

    def _stage_result(self, feature_name: str, stage: str) -> Optional[StageResult]:
        for r in self.results[feature_name]:
            if r.stage == stage:
                return r
        return None

    def _emoji(self, status: str) -> str:
        return _EMOJI.get(status, "?")

    # ------------------------------------------------------------------
    # CSV summary
    # ------------------------------------------------------------------

    def write_csv_summary(self) -> Path:
        path = self.output_dir / "feature_validation_summary.csv"

        stage_cols = [f"{s}_status" for s in PIPELINE_STAGES]

        target_stages = [
            ("collector", "Collector"),
            ("merger", "Merger"),
            ("dataset_builder", "Dataset Builder"),
            ("analysis_dataset", "analysis_ready_dataset.csv"),
            ("train_dataset", "train_dataset.csv"),
        ]

        stats_cols = []
        for label, _ in target_stages:
            stats_cols.extend([
                f"{label}_non_null",
                f"{label}_null_pct",
                f"{label}_placeholder_pct",
                f"{label}_min",
                f"{label}_median",
                f"{label}_max",
                f"{label}_std",
                f"{label}_samples",
                f"{label}_expected_unit",
                f"{label}_observed_unit",
                f"{label}_unit_verification",
                f"{label}_unique_values",
                f"{label}_unique_ratio",
                f"{label}_variance",
                f"{label}_std_dev",
                f"{label}_coefficient_of_variation",
            ])

        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=[
                "feature_name", "group", "dtype", "unit", "source",
                "overall_status",
                *stage_cols,
                *stats_cols,
                "null_pct_merged", "null_pct_analysis", "null_pct_train",
                "observed_min", "observed_max",
                "unique_non_null_values",
                "unique_ratio",
                "variance",
                "std_dev",
                "coefficient_of_variation",
                "range_violation_pct",
                "in_model",
                "issues_fail",
                "issues_warn_investigate",
                "issues_warn_expected",
            ])
            writer.writeheader()

            for fname, spec in PIPELINE_FEATURE_SCHEMA.items():
                stage_results = self.results.get(fname, [])
                overall = _aggregate_status(stage_results)

                row: dict = {
                    "feature_name": fname,
                    "group": spec.group,
                    "dtype": spec.dtype,
                    "unit": spec.unit,
                    "source": spec.source,
                    "overall_status": overall,
                    "in_model": spec.in_model,
                }

                # Per-stage statuses
                for stage in PIPELINE_STAGES:
                    sr = self._stage_result(fname, stage)
                    row[f"{stage}_status"] = sr.status if sr else STATUS_SKIP

                # Per-stage detailed stats
                for label, stage in target_stages:
                    sr = self._stage_result(fname, stage)
                    if sr is not None and sr.status != STATUS_SKIP:
                        row[f"{label}_non_null"] = f"{sr.non_null_count}/{sr.total_count}" if sr.non_null_count is not None and sr.total_count is not None else ""
                        row[f"{label}_null_pct"] = f"{sr.null_pct:.2f}" if sr.null_pct is not None else ""
                        row[f"{label}_placeholder_pct"] = f"{sr.placeholder_pct:.2f}" if sr.placeholder_pct is not None else ""
                        row[f"{label}_min"] = f"{sr.observed_min:.6g}" if sr.observed_min is not None else ""
                        row[f"{label}_median"] = f"{sr.observed_median:.6g}" if sr.observed_median is not None else ""
                        row[f"{label}_max"] = f"{sr.observed_max:.6g}" if sr.observed_max is not None else ""
                        row[f"{label}_std"] = f"{sr.observed_std:.6g}" if sr.observed_std is not None else ""
                        row[f"{label}_samples"] = str(sr.sample_values) if sr.sample_values else ""
                        row[f"{label}_expected_unit"] = sr.unit_expected
                        row[f"{label}_observed_unit"] = sr.unit_observed if sr.unit_observed is not None else ""
                        row[f"{label}_unit_verification"] = sr.unit_verification_status
                        row[f"{label}_unique_values"] = f"{sr.unique_non_null_values}" if sr.unique_non_null_values is not None else ""
                        row[f"{label}_unique_ratio"] = f"{sr.unique_ratio:.4f}" if sr.unique_ratio is not None else ""
                        row[f"{label}_variance"] = f"{sr.variance:.6g}" if sr.variance is not None else ""
                        row[f"{label}_std_dev"] = f"{sr.std_dev:.6g}" if sr.std_dev is not None else ""
                        row[f"{label}_coefficient_of_variation"] = f"{sr.coefficient_of_variation:.6g}" if sr.coefficient_of_variation is not None else ""
                    else:
                        row[f"{label}_non_null"] = ""
                        row[f"{label}_null_pct"] = ""
                        row[f"{label}_placeholder_pct"] = ""
                        row[f"{label}_min"] = ""
                        row[f"{label}_median"] = ""
                        row[f"{label}_max"] = ""
                        row[f"{label}_std"] = ""
                        row[f"{label}_samples"] = ""
                        row[f"{label}_expected_unit"] = ""
                        row[f"{label}_observed_unit"] = ""
                        row[f"{label}_unit_verification"] = ""
                        row[f"{label}_unique_values"] = ""
                        row[f"{label}_unique_ratio"] = ""
                        row[f"{label}_variance"] = ""
                        row[f"{label}_std_dev"] = ""
                        row[f"{label}_coefficient_of_variation"] = ""

                # Null rates at key stages
                for label, stage in [
                    ("null_pct_merged", "merged_feature_table.csv"),
                    ("null_pct_analysis", "analysis_ready_dataset.csv"),
                    ("null_pct_train", "train_dataset.csv"),
                ]:
                    sr = self._stage_result(fname, stage)
                    row[label] = f"{sr.null_pct:.1f}" if sr and sr.null_pct is not None else ""

                # Min / max (from merged_feature_table.csv or Collector)
                sr_merged = self._stage_result(fname, "merged_feature_table.csv")
                if sr_merged is None or sr_merged.observed_min is None:
                    sr_merged = self._stage_result(fname, "Collector")
                row["observed_min"] = (
                    f"{sr_merged.observed_min:.4g}"
                    if sr_merged and sr_merged.observed_min is not None else ""
                )
                row["observed_max"] = (
                    f"{sr_merged.observed_max:.4g}"
                    if sr_merged and sr_merged.observed_max is not None else ""
                )

                sr_stats = self._stage_result(fname, "merged_feature_table.csv")
                if sr_stats is None or sr_stats.unique_non_null_values is None:
                    sr_stats = self._stage_result(fname, "Collector")
                if sr_stats is None or sr_stats.unique_non_null_values is None:
                    for stage in PIPELINE_STAGES:
                        candidate = self._stage_result(fname, stage)
                        if candidate and candidate.unique_non_null_values is not None:
                            sr_stats = candidate
                            break

                row["unique_non_null_values"] = (
                    f"{sr_stats.unique_non_null_values}"
                    if sr_stats and sr_stats.unique_non_null_values is not None else ""
                )
                row["unique_ratio"] = (
                    f"{sr_stats.unique_ratio:.4f}"
                    if sr_stats and sr_stats.unique_ratio is not None else ""
                )
                row["variance"] = (
                    f"{sr_stats.variance:.6g}"
                    if sr_stats and sr_stats.variance is not None else ""
                )
                row["std_dev"] = (
                    f"{sr_stats.std_dev:.6g}"
                    if sr_stats and sr_stats.std_dev is not None else ""
                )
                row["coefficient_of_variation"] = (
                    f"{sr_stats.coefficient_of_variation:.6g}"
                    if sr_stats and sr_stats.coefficient_of_variation is not None else ""
                )

                row["range_violation_pct"] = (
                    f"{sr_merged.range_violation_pct:.1f}"
                    if sr_merged and sr_merged.range_violation_pct is not None else ""
                )

                # Separate issue columns by severity
                issues_fail, issues_wi, issues_we = [], [], []
                for sr in stage_results:
                    for chk in sr.checks:
                        detail_clean = chk.detail.replace("\n", "; ").replace("    ", "").replace("  - ", "- ")
                        item = f"[{sr.stage}:{chk.rule}] {detail_clean}"
                        if chk.status == STATUS_FAIL:
                            issues_fail.append(item)
                        elif chk.status == STATUS_WARN_INVESTIGATE:
                            issues_wi.append(item)
                        elif chk.status == STATUS_WARN_EXPECTED:
                            issues_we.append(item)
                row["issues_fail"] = " | ".join(issues_fail)
                row["issues_warn_investigate"] = " | ".join(issues_wi)
                row["issues_warn_expected"] = " | ".join(issues_we)

                writer.writerow(row)

        logger.info("CSV summary written to %s", path)
        return path

    # ------------------------------------------------------------------
    # Markdown report
    # ------------------------------------------------------------------

    def write_markdown_report(self) -> Path:
        path = self.output_dir / "feature_validation_report.md"

        # Count totals by four categories
        total = len(self.results)
        status_counts: Dict[str, int] = {
            STATUS_PASS: 0,
            STATUS_WARN_EXPECTED: 0,
            STATUS_WARN_INVESTIGATE: 0,
            STATUS_FAIL: 0,
            STATUS_SKIP: 0,
        }
        for fname in self.results:
            s = self._overall_status(fname)
            status_counts[s] = status_counts.get(s, 0) + 1

        lines: List[str] = []

        # Header
        lines += [
            "# AQI Pipeline — Feature Validation Report",
            "",
            f"*Generated: {self.timestamp}*",
            "",
            "## Executive Summary",
            "",
            "| Status | Meaning | Count |",
            "|--------|---------|-------|",
            f"| {_EMOJI[STATUS_PASS]} PASS | Meets all expectations | {status_counts[STATUS_PASS]} |",
            f"| {_EMOJI[STATUS_WARN_EXPECTED]} WARNING (expected) | Expected operational limitation (no action required) | {status_counts[STATUS_WARN_EXPECTED]} |",
            f"| {_EMOJI[STATUS_WARN_INVESTIGATE]} WARNING (investigate) | Unexpected condition (requires investigation) | {status_counts[STATUS_WARN_INVESTIGATE]} |",
            f"| {_EMOJI[STATUS_FAIL]} FAIL | Hard failure (must fix) | {status_counts[STATUS_FAIL]} |",
            f"| — SKIP | Not in pipeline yet | {status_counts.get(STATUS_SKIP, 0)} |",
            f"| **Total** | | **{total}** |",
            "",
            "### Configured Temporal Offset Window",
            "",
            f"| Parameter | Value |",
            f"|-----------|-------|",
            f"| `TEMPORAL_WINDOW_DAYS` | {TEMPORAL_WINDOW_DAYS} days |",
            f"| `MAX_ADAPTIVE_LOOKBACK_DAYS` | {MAX_ADAPTIVE_LOOKBACK_DAYS} days |",
            f"| **Valid offset range** | **[−{MAX_ADAPTIVE_LOOKBACK_DAYS}, +{TEMPORAL_WINDOW_DAYS}] days** |",
            "",
            "> [!NOTE]",
            "> Temporal offsets within the configured window are **PASS**.",
            "> Offsets outside the window are **WARNING (investigate)** (the contributing",
            "> observation falls outside the adaptive collection window).",
            "",
            "",
            "### Scientific Terminology & Validation Context",
            "",
            "The data collection pipeline explicitly distinguishes between satellite products to apply accurate QA filtering context:",
            "",
            "**Sentinel-5P Products (NO2, SO2, HCHO, CO, O3):**",
            "- **Processing**: Level-2 retrieval to Level-3 gridding.",
            "- **Quality Metric**: Standard `qa_value` constraints.",
            "- **Validation References**: Sentinel-5P ATBDs and Product Readmes.",
            "- **Context**: Google Earth Engine ingests Level-3 Sentinel-5P data, with standard `qa_value` masking pre-applied. The pipeline subsequently applies a secondary cloud fraction filter.",
            "",
            "**MODIS MAIAC Products (AOD):**",
            "- **Processing**: Level-2 (MCD19A2).",
            "- **Quality Metric**: MAIAC `AOD_QA` bits and quality flags.",
            "- **Validation References**: MODIS MAIAC ATBD and User Guide.",
            "- **Context**: AOD relies on complex surface reflectance and cloud masking specific to MAIAC, inherently distinct from UV/DOAS logic.",
            "",
        ]

        # Feature overview table
        lines += [
            "## Feature Status Overview",
            "",
            "| Feature | Group | Unit | Overall | "
            + " | ".join(s.replace("_", "<br>") for s in PIPELINE_STAGES)
            + " |",
            "|---------|-------|------|---------|"
            + "|".join("---" for _ in PIPELINE_STAGES)
            + "|",
        ]
        for fname, spec in PIPELINE_FEATURE_SCHEMA.items():
            overall = self._overall_status(fname)
            stage_cells = []
            for stage in PIPELINE_STAGES:
                sr = self._stage_result(fname, stage)
                cell_status = sr.status if sr else STATUS_SKIP
                stage_cells.append(self._emoji(cell_status))
            lines.append(
                f"| {fname} | {spec.group} | {spec.unit} "
                f"| {self._emoji(overall)} {overall} | "
                + " | ".join(stage_cells) + " |"
            )
        lines += [""]

        # ── Failure section ──────────────────────────────────────────────────
        fail_items = [
            (fname, self.results[fname])
            for fname in self.results
            if self._overall_status(fname) == STATUS_FAIL
        ]
        if fail_items:
            lines += ["## ❌ Failures (must fix before production)", ""]
            for fname, stage_results in fail_items:
                lines.append(f"### `{fname}`")
                for sr in stage_results:
                    for chk in sr.checks:
                        if chk.status == STATUS_FAIL:
                            lines.append(f"- **[{sr.stage} / {chk.rule}]** {chk.detail}")
                lines.append("")

        # ── WARN_INVESTIGATE section ─────────────────────────────────────────
        wi_items = [
            (fname, self.results[fname])
            for fname in self.results
            if self._overall_status(fname) == STATUS_WARN_INVESTIGATE
        ]
        if wi_items:
            lines += [
                "## ⚠️ WARN_INVESTIGATE (unexpected conditions — requires investigation)",
                "",
                "> [!WARNING]",
                "> These features have values or null rates that fall outside",
                "> the configured pipeline parameters. Investigate before production use.",
                "",
            ]
            for fname, stage_results in wi_items:
                lines.append(f"### `{fname}`")
                for sr in stage_results:
                    for chk in sr.checks:
                        if chk.status == STATUS_WARN_INVESTIGATE:
                            lines.append(f"- **[{sr.stage} / {chk.rule}]** {chk.detail}")
                lines.append("")

        # ── WARN_EXPECTED section ────────────────────────────────────────────
        we_items = [
            (fname, self.results[fname])
            for fname in self.results
            if self._overall_status(fname) == STATUS_WARN_EXPECTED
        ]
        if we_items:
            lines += [
                "## ℹ️ WARN_EXPECTED (expected operational limitations — no action required)",
                "",
                "> [!NOTE]",
                "> These conditions are scientifically expected and consistent with",
                "> the pipeline configuration. No code change is required.",
                "",
            ]
            for fname, stage_results in we_items:
                lines.append(f"### `{fname}`")
                for sr in stage_results:
                    for chk in sr.checks:
                        if chk.status == STATUS_WARN_EXPECTED:
                            lines.append(f"- **[{sr.stage} / {chk.rule}]** {chk.detail}")
                lines.append("")

        # ── Detailed per-group breakdown ──────────────────────────────────────
        groups_seen = sorted({spec.group for spec in PIPELINE_FEATURE_SCHEMA.values()})
        lines += ["## Detailed Validation Results", ""]

        for group in groups_seen:
            lines += [f"### Group: `{group}`", ""]
            group_features = [
                (fname, spec)
                for fname, spec in PIPELINE_FEATURE_SCHEMA.items()
                if spec.group == group
            ]
            for fname, spec in group_features:
                overall = self._overall_status(fname)
                lines += [
                    f"#### {self._emoji(overall)} `{fname}` ({overall})",
                    "",
                    f"- **Unit:** {spec.unit}",
                    f"- **Source:** {spec.source}",
                    f"- **In ML model:** {'Yes' if spec.in_model else 'No'}",
                    f"- **Valid range:** {spec.valid_range if spec.valid_range else 'N/A'}",
                    f"- **Description:** {spec.description}",
                    "",
                ]
                # Per-stage table
                lines += [
                    "| Stage | Status | Exp Unit | Obs Unit | Unit Verif | Non-null | Null % | Placeholder % | Min | Median | Max | Std | Unique | Uniq % | Var | CV | Sample Values |",
                    "|-------|--------|----------|----------|------------|----------|--------|---------------|-----|--------|-----|-----|--------|--------|-----|----|---------------|",
                ]
                for stage in PIPELINE_STAGES:
                    sr = self._stage_result(fname, stage)
                    if sr is None or sr.status == STATUS_SKIP:
                        lines.append(f"| {stage} | {_EMOJI[STATUS_SKIP]} — | — | — | — | — | — | — | — | — | — | — | — | — | — | — | — |")
                        continue
                    non_null_str = f"{sr.non_null_count}/{sr.total_count}" if sr.non_null_count is not None and sr.total_count is not None else "—"
                    null_pct_str = f"{sr.null_pct:.1f}%" if sr.null_pct is not None else "—"
                    ph_pct_str = f"{sr.placeholder_pct:.1f}%" if sr.placeholder_pct is not None else "—"
                    min_str = f"{sr.observed_min:.4g}" if sr.observed_min is not None else "—"
                    median_str = f"{sr.observed_median:.4g}" if sr.observed_median is not None else "—"
                    max_str = f"{sr.observed_max:.4g}" if sr.observed_max is not None else "—"
                    std_str = f"{sr.std_dev:.4g}" if sr.std_dev is not None else "—"
                    uniq_str = f"{sr.unique_non_null_values}" if sr.unique_non_null_values is not None else "—"
                    uniq_ratio_str = f"{sr.unique_ratio:.1%}" if sr.unique_ratio is not None else "—"
                    var_str = f"{sr.variance:.4g}" if sr.variance is not None else "—"
                    cv_str = f"{sr.coefficient_of_variation:.4g}" if sr.coefficient_of_variation is not None else "—"
                    obs_unit_str = sr.unit_observed if sr.unit_observed is not None else "—"
                    unit_verif_str = sr.unit_verification_status
                    lines.append(
                        f"| {stage} "
                        f"| {self._emoji(sr.status)} {sr.status} "
                        f"| {sr.unit_expected} "
                        f"| {obs_unit_str} "
                        f"| {unit_verif_str} "
                        f"| {non_null_str} "
                        f"| {null_pct_str} "
                        f"| {ph_pct_str} "
                        f"| {min_str} "
                        f"| {median_str} "
                        f"| {max_str} "
                        f"| {std_str} "
                        f"| {uniq_str} "
                        f"| {uniq_ratio_str} "
                        f"| {var_str} "
                        f"| {cv_str} "
                        f"| {_fmt_samples(sr.sample_values)} |"
                    )
                lines.append("")

                # Check-level details
                for stage in PIPELINE_STAGES:
                    sr = self._stage_result(fname, stage)
                    if sr is None:
                        continue
                    checks_to_show = [
                        c for c in sr.checks
                        if c.status in (STATUS_FAIL, STATUS_WARN_INVESTIGATE, STATUS_WARN_EXPECTED)
                        or (c.status == STATUS_PASS and c.rule in ("null_rate", "scientific_validation"))
                        or (c.status == STATUS_SKIP and c.rule == "low_variance_check")
                    ]
                    if checks_to_show:
                        for chk in checks_to_show:
                            emoji = "ℹ️" if chk.status == STATUS_SKIP else self._emoji(chk.status)
                            lines.append(
                                f"  - {emoji} **{stage}/{chk.rule}:** {chk.detail}"
                            )
                        lines.append("")

        # Appendix
        lines += [
            "## Appendix: Pipeline Stage File Locations",
            "",
            "| Stage | File / Source |",
            "|-------|------|",
            "| `Collector` | CPCB / ERA5 / MODIS / TROPOMI raw outputs |",
            "| `Merger` | `data_collection_pipeline/features/merged_feature_table.csv` |",
            "| `Dataset Builder` | `analysis_ready_dataset.csv` |",
            "| `merged_feature_table.csv` | `data_collection_pipeline/features/merged_feature_table.csv` |",
            "| `analysis_ready_dataset.csv` | `analysis_ready_dataset.csv` |",
            "| `train_dataset.csv` | `train_dataset.csv` |",
            "| `FeatureGroupManager` | `FeatureGroupManager` model features registry |",
            "",
            "## Appendix: Unit Key",
            "",
            "| Abbreviation | Meaning |",
            "|-------------|---------|",
            "| µg/m³ | micrograms per cubic metre |",
            "| mg/m³ | milligrams per cubic metre |",
            "| mol/m² | moles per square metre |",
            "| K | Kelvin |",
            "| °C | Celsius |",
            "| Pa | Pascals |",
            "| m/s | metres per second |",
            "",
            "## Appendix: Validation Status Definitions",
            "",
            "| Status | Symbol | Meaning |",
            "|--------|--------|---------|",
            "| PASS | ✅ | Feature meets all schema expectations |",
            "| WARN_EXPECTED | ℹ️ | Expected operational limitation (e.g. AOD null during monsoon, provenance null when science feature is null due to cloud cover, Relative Humidity 100.0–100.5% from ERA5 spectral artefacts). No code change required. |",
            f"| WARN_INVESTIGATE | ⚠️ | Unexpected condition that should be investigated (e.g. temporal offset outside configured lookback window [−{MAX_ADAPTIVE_LOOKBACK_DAYS}, +{TEMPORAL_WINDOW_DAYS}] days, provenance null when science feature is present, unexpectedly high null rate without documented cause). |",
            "| FAIL | ❌ | Hard failure: feature missing, 100% null, values outside physical range. Must be fixed before production use. |",
            "| SKIP | — | Feature not expected in this pipeline stage. |",
            "",
            "*Report generated by `data_collection_pipeline.validation`.*",
        ]

        path.write_text("\n".join(lines), encoding="utf-8")
        logger.info("Markdown report written to %s", path)
        return path

    # ------------------------------------------------------------------
    # Combined write
    # ------------------------------------------------------------------

    def write_all(self) -> Dict[str, Path]:
        return {
            "markdown": self.write_markdown_report(),
            "csv": self.write_csv_summary(),
        }


def _fmt_samples(samples: list) -> str:
    if not samples:
        return "—"
    formatted = []
    for s in samples[:3]:
        if isinstance(s, float):
            formatted.append(f"{s:.4g}")
        else:
            formatted.append(str(s)[:20])
    return ", ".join(formatted)
