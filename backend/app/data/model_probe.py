"""
Isolated load probe for a trained-model artefact (opt-in: MODEL_LOAD_CHECK).

Loading a joblib file unpickles it, which executes code and needs the exact
scikit-learn / LightGBM versions the model was trained with. The API therefore
never unpickles in its own process: run_probe() executes THIS FILE as a script
in a subprocess (optionally with another interpreter, MODEL_PROBE_PYTHON, e.g.
the ML team's training environment) with a timeout, and reads one JSON report:

  loaded            the pickle loaded
  object_type       type of the loaded object
  steps             pipeline steps [{name, type}] (preprocessing + estimator)
  final_estimator   type of the last step
  feature_names_in  input columns the fitted pipeline expects
  versions          installed lightgbm / sklearn / joblib versions
  prediction        predict() on the summary's input_example: rows, outputs,
                    finite (no NaN / inf)
  error             why the probe could not complete

Only the standard library is imported at module level; joblib / scikit-learn /
lightgbm / pandas are imported inside probe(), so a missing dependency is
reported instead of crashing. The report is evidence for app.data.trust; it
never changes the artefact.
"""

from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path
from typing import Any

MODEL_FILE = "lightgbm_model.joblib"
SUMMARY_FILE = "lightgbm_training_summary.json"
PROBE_TIMEOUT_SECONDS = 120.0


def _type_name(obj: object) -> str:
    return f"{type(obj).__module__}.{type(obj).__qualname__}"


def probe(directory: Path) -> dict[str, Any]:
    """Load the artefact in THIS process and describe it (run only in a subprocess)."""
    report: dict[str, Any] = {"loaded": False, "error": None, "versions": {}}
    try:
        import joblib  # noqa: PLC0415
        import lightgbm  # noqa: PLC0415
        import pandas as pd  # noqa: PLC0415
        import sklearn  # noqa: PLC0415
    except ImportError as exc:
        report["error"] = f"dependency missing in the probe environment: {exc.name}"
        return report
    report["versions"] = {
        "lightgbm": lightgbm.__version__, "sklearn": sklearn.__version__,
        "joblib": joblib.__version__,
    }
    try:
        summary = json.loads((directory / SUMMARY_FILE).read_text(encoding="utf-8"))
        model = joblib.load(directory / MODEL_FILE)
    except Exception as exc:  # noqa: BLE001 - any load failure is reported, not raised
        report["error"] = f"cannot load artefact: {type(exc).__name__}: {exc}"
        return report

    report["loaded"] = True
    report["object_type"] = _type_name(model)
    steps = getattr(model, "steps", None) or []
    report["steps"] = [{"name": name, "type": _type_name(step)} for name, step in steps]
    report["final_estimator"] = _type_name(steps[-1][1]) if steps else _type_name(model)
    names = getattr(model, "feature_names_in_", None)
    report["feature_names_in"] = [str(n) for n in names] if names is not None else None

    example = summary.get("input_example")
    rows = example if isinstance(example, list) else [example] if example else []
    if rows:
        try:
            frame = pd.DataFrame(rows)
            if report["feature_names_in"]:
                frame = frame[report["feature_names_in"]]
            output = [float(v) for v in model.predict(frame)]
            report["prediction"] = {
                "rows": len(rows), "outputs": len(output),
                "finite": all(math.isfinite(v) for v in output),
            }
        except Exception as exc:  # noqa: BLE001
            report["prediction"] = {"rows": len(rows), "error": f"{type(exc).__name__}: {exc}"}
    return report


def run_probe(
    directory: str | Path, python: str | None = None, timeout: float = PROBE_TIMEOUT_SECONDS
) -> dict[str, Any]:
    """Run probe() in a separate interpreter and return its report (never raises)."""
    cmd = [python or sys.executable, str(Path(__file__).resolve()), str(Path(directory))]
    try:
        # Fixed argv (interpreter, this file, artefact dir) and no shell
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, check=False)  # noqa: S603
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"loaded": False, "error": f"probe could not run: {type(exc).__name__}: {exc}"}
    lines = [line for line in done.stdout.splitlines() if line.strip()]
    try:
        report = json.loads(lines[-1]) if lines else None
    except json.JSONDecodeError:
        report = None
    if not isinstance(report, dict):
        tail = (done.stderr or done.stdout).strip().splitlines()[-1:] or ["no output"]
        return {"loaded": False, "error": f"probe exited {done.returncode}: {tail[0][:200]}"}
    return report


if __name__ == "__main__":
    print(json.dumps(probe(Path(sys.argv[1]))))
