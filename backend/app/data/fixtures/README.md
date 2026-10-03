# Placeholder fixtures — NOT real data

These files let the backend and dashboard run end to end before the team's
real outputs are available. They are **deterministic placeholders**: fixed
values derived from simple formulas, never measurements, model output or
satellite detections. The API reports them as `kind: "placeholder"` in
`GET /api/v1/sources`, and the dashboard labels them PLACEHOLDER.

Each file uses the **same contract as the real source**, so swapping in the
real output only changes configuration, never the services, API or dashboard.

| File | Contract (real source) | Replaced by |
|---|---|---|
| `placeholder_station_dataset.csv` | `analysis_ready_dataset.csv` v1 (data pipeline) — 8 stations × 7 days, with deliberate gaps to exercise nullable pollutants | `DATASET_PATH`, or auto-discovered `<repo>/analysis_ready_dataset.csv` |
| `placeholder_hcho_clusters.json` | `cluster_summary.json` (`spatial_analysis/hotspot_detector.py`) — no radius / confidence / date, exactly like the real file | `HCHO_HOTSPOTS_PATH`, or auto-discovered `<repo>/reports/cluster_summary.json` |
| `placeholder_fire_events.json` | Fire-detection contract in `app/data/fires.py` (no team source exists yet) | `FIRE_EVENTS_PATH` |

There is intentionally **no placeholder model**: without a real artefact the
model / XAI capabilities report `unavailable`.

Set `ENABLE_PLACEHOLDER_DATA=false` to disable these fixtures entirely.
