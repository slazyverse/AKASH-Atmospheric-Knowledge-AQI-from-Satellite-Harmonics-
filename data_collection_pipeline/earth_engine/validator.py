"""
GEE Startup Validator.

Provides a :func:`validate_gee_startup` function that performs a four-step
health-check at startup (or on demand) to verify that Google Earth Engine is
correctly configured and accessible for this project.

Steps
-----
1. **Environment** — verify ``GEE_PROJECT_ID`` is set.
2. **Authentication** — verify Earth Engine credentials exist locally.
3. **Initialization** — call :func:`initialize_ee` and confirm it succeeds.
4. **Collection access** — query ``COPERNICUS/S5P/OFFL/L3_NO2`` for a single
   image to confirm the project can reach the GEE data catalogue.

Usage
-----
As a CLI tool::

    python -m data_collection_pipeline.earth_engine.validator

As a Python call at application startup::

    from data_collection_pipeline.earth_engine.validator import validate_gee_startup
    result = validate_gee_startup()
    if not result.success:
        raise RuntimeError(result.error_message)

Exit codes (CLI)
----------------
``0`` — all checks passed.
``1`` — one or more checks failed.
"""

from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

# Public collection used as the canary for collection-access validation.
_CANARY_COLLECTION = "COPERNICUS/S5P/OFFL/L3_NO2"
# Date range used for the canary query — recent window broad enough to always
# have at least one image in the archive.
_CANARY_START = "2024-01-01"
_CANARY_END = "2024-01-15"


@dataclass
class GeeValidationResult:
    """Result object returned by :func:`validate_gee_startup`.

    Attributes
    ----------
    success:
        ``True`` only when all four steps passed.
    project_id:
        The project ID that was used (or ``None`` if env var was missing).
    steps_passed:
        Names of validation steps that completed successfully.
    steps_failed:
        Names of validation steps that failed.
    error_message:
        Human-readable description of the first failure encountered.
    """

    success: bool = False
    project_id: Optional[str] = None
    steps_passed: List[str] = field(default_factory=list)
    steps_failed: List[str] = field(default_factory=list)
    error_message: Optional[str] = None

    def __str__(self) -> str:  # pragma: no cover
        status = "✅ PASSED" if self.success else "❌ FAILED"
        lines = [
            f"GEE Startup Validation: {status}",
            f"  Project ID : {self.project_id or '(not set)'}",
            f"  Passed     : {', '.join(self.steps_passed) or '(none)'}",
            f"  Failed     : {', '.join(self.steps_failed) or '(none)'}",
        ]
        if self.error_message:
            lines.append(f"  Error      : {self.error_message}")
        return "\n".join(lines)


def validate_gee_startup(
    canary_collection: str = _CANARY_COLLECTION,
) -> GeeValidationResult:
    """Run four-step GEE startup validation.

    Parameters
    ----------
    canary_collection:
        GEE collection ID to query as a liveness check.
        Defaults to ``COPERNICUS/S5P/OFFL/L3_NO2``.

    Returns
    -------
    GeeValidationResult
        Structured result — inspect ``.success`` and ``.error_message``.
    """
    result = GeeValidationResult()

    # ------------------------------------------------------------------ #
    # Step 1 — Environment variable check                                  #
    # ------------------------------------------------------------------ #
    step = "environment"
    try:
        from data_collection_pipeline import config
        project_id = config.GEE_PROJECT_ID
    except EnvironmentError as e:
        result.steps_failed.append(step)
        result.error_message = str(e)
        logger.error("[GEE Validator] Step 1 FAILED — %s", result.error_message)
        return result

    result.project_id = project_id
    result.steps_passed.append(step)
    logger.info("[GEE Validator] Step 1 PASSED — GEE_PROJECT_ID=%s", project_id)

    # ------------------------------------------------------------------ #
    # Step 2 — earthengine-api importable & credentials file present       #
    # ------------------------------------------------------------------ #
    step = "authentication"
    try:
        import ee  # noqa: PLC0415
    except ImportError:
        result.steps_failed.append(step)
        result.error_message = (
            "The 'earthengine-api' package is not installed.\n"
            "\n"
            "Run: pip install earthengine-api"
        )
        logger.error("[GEE Validator] Step 2 FAILED — %s", result.error_message)
        return result

    from pathlib import Path  # noqa: PLC0415

    # Check for OAuth/user credentials or service-account env vars.
    gee_cred_path = Path.home() / ".config" / "earthengine" / "credentials"
    has_oauth = gee_cred_path.exists()
    has_sa = bool(
        os.getenv("GEE_SERVICE_ACCOUNT") and (
            os.getenv("GEE_SERVICE_ACCOUNT_KEY_FILE")
            or os.getenv("GEE_SERVICE_ACCOUNT_KEY_JSON")
        )
    )

    if not has_oauth and not has_sa:
        result.steps_failed.append(step)
        result.error_message = (
            "No Google Earth Engine credentials found.\n"
            "\n"
            "Options:\n"
            "  1. Run: earthengine authenticate\n"
            "     (stores OAuth credentials in ~/.config/earthengine/credentials)\n"
            "\n"
            "  2. Set service-account env vars:\n"
            "       GEE_SERVICE_ACCOUNT=<account@project.iam.gserviceaccount.com>\n"
            "       GEE_SERVICE_ACCOUNT_KEY_FILE=/path/to/key.json\n"
            "  or\n"
            "       GEE_SERVICE_ACCOUNT_KEY_JSON=<inline JSON string>"
        )
        logger.error("[GEE Validator] Step 2 FAILED — %s", result.error_message)
        return result

    auth_method = "OAuth credentials" if has_oauth else "service-account env vars"
    result.steps_passed.append(step)
    logger.info("[GEE Validator] Step 2 PASSED — credentials found via %s", auth_method)

    # ------------------------------------------------------------------ #
    # Step 3 — Earth Engine initialization                                 #
    # ------------------------------------------------------------------ #
    step = "initialization"
    try:
        from data_collection_pipeline.earth_engine.initializer import (  # noqa: PLC0415
            initialize_ee,
            is_ee_initialized,
        )
        if is_ee_initialized():
            logger.info(
                "[GEE Validator] Step 3 PASSED — already initialized (project=%s).",
                project_id,
            )
        else:
            ok = initialize_ee(project=project_id)
            if not ok:
                raise RuntimeError("initialize_ee() returned False — see logs above.")

        result.steps_passed.append(step)
        logger.info(
            "[GEE Validator] Step 3 PASSED — initialized successfully (project=%s).",
            project_id,
        )

    except Exception as exc:  # noqa: BLE001
        result.steps_failed.append(step)
        result.error_message = (
            f"Earth Engine initialization failed for project '{project_id}':\n"
            f"  {exc}\n"
            "\n"
            "Possible causes:\n"
            "  • The project has not been registered for Earth Engine access.\n"
            "    → Visit https://earthengine.google.com/ to register the project.\n"
            "  • The OAuth token is expired.\n"
            "    → Re-run: earthengine authenticate\n"
            "  • The service-account lacks the 'Earth Engine Resource Writer' role."
        )
        logger.error("[GEE Validator] Step 3 FAILED — %s", result.error_message)
        return result

    # ------------------------------------------------------------------ #
    # Step 4 — Collection access (canary query)                            #
    # ------------------------------------------------------------------ #
    step = "collection_access"
    try:
        collection = ee.ImageCollection(canary_collection).filterDate(
            _CANARY_START, _CANARY_END
        )
        # .size() forces server-side evaluation — catches auth / quota errors.
        size = collection.size().getInfo()
        if size == 0:
            logger.warning(
                "[GEE Validator] Step 4 WARNING — canary collection '%s' returned "
                "0 images for %s–%s. This is unexpected but not necessarily a failure.",
                canary_collection,
                _CANARY_START,
                _CANARY_END,
            )
        result.steps_passed.append(step)
        logger.info(
            "[GEE Validator] Step 4 PASSED — '%s' returned %d image(s) for "
            "%s–%s (project=%s).",
            canary_collection,
            size,
            _CANARY_START,
            _CANARY_END,
            project_id,
        )

    except Exception as exc:  # noqa: BLE001
        result.steps_failed.append(step)
        result.error_message = (
            f"Cannot query collection '{canary_collection}' under project '{project_id}':\n"
            f"  {exc}\n"
            "\n"
            "Possible causes:\n"
            "  • The project does not have access to this Earth Engine collection.\n"
            "  • The project's Earth Engine API is disabled in Google Cloud Console.\n"
            "    → Enable it at: https://console.cloud.google.com/apis/library\n"
            "  • Quota has been exceeded for this project."
        )
        logger.error("[GEE Validator] Step 4 FAILED — %s", result.error_message)
        return result

    # All four steps passed
    result.success = True
    logger.info(
        "[GEE Validator] All checks PASSED — Earth Engine is production-ready "
        "(project=%s).",
        project_id,
    )
    return result


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------

def _configure_logging() -> None:
    """Configure basic stdout logging for the CLI."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s  %(levelname)-8s  %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
        stream=sys.stdout,
    )


def main() -> None:
    """CLI entry-point for the GEE startup validator.

    Exit code ``0`` means all checks passed.
    Exit code ``1`` means at least one check failed.
    """
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
    _configure_logging()
    print("=" * 60)
    print("  AKASH — Google Earth Engine Startup Validator")
    print("=" * 60)

    result = validate_gee_startup()

    print()
    print(str(result))
    print()

    if result.success:
        print("✅  Earth Engine is production-ready. Pipeline may proceed.")
        sys.exit(0)
    else:
        print("❌  Earth Engine validation failed. Fix the error above and retry.")
        sys.exit(1)


if __name__ == "__main__":
    main()
