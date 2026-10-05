"""
backend/app/data — loaders for the team's real outputs.

Each adapter reads one artefact, validates it against its contract and
normalises it for the services (source → adapter → normalised contract →
service → API → dashboard):

  dataset.py         analysis_ready_dataset.csv  (DATASET_PATH)
  hotspots.py        cluster_summary.json        (HCHO_HOTSPOTS_PATH)
  fires.py           fire-detection JSON         (FIRE_EVENTS_PATH)
  model_artifact.py  LightGBM artefact directory (ML_MODEL_PATH)
  sources.py         resolves each domain: explicit path → auto-discovered team
                     output → bundled placeholder fixture (fixtures/) →
                     unavailable; exposes the status via GET /api/v1/sources

Placeholders use the same contract as the real source, so plugging in the
team's output is a configuration change only. An explicitly configured but
invalid source raises at startup — the API never silently serves other data.
"""
