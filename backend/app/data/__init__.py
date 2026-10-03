"""
backend/app/data — loaders for the team's real outputs.

Each loader reads one artefact produced by the data / ML pipeline, validates
it against the contract below, and normalises it for the services:

  dataset.py         analysis_ready_dataset.csv  (DATASET_PATH)
  hotspots.py        cluster_summary.json        (HCHO_HOTSPOTS_PATH)
  model_artifact.py  LightGBM artefact directory (ML_MODEL_PATH)
  sources.py         process-wide holder, populated at startup

Every source is optional: when a setting is unset, the services keep serving
their built-in demo data. A source that IS configured but invalid raises at
startup — the API never silently falls back to demo data.
"""
