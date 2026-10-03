# AKASH — Atmospheric Knowledge: AQI from Satellite Harmonics

**VAYU-DRISHTI** is a satellite-based air-quality platform for India. The goal is to estimate
surface AQI from Sentinel-5P TROPOMI, MODIS and ERA5 data trained against CPCB ground stations,
detect HCHO hotspots, monitor fires, and present the results through a FastAPI backend and a
Streamlit dashboard.

> **Development status — read this first.** The backend and dashboard work end to end. By
> default every domain endpoint serves **static demo data** and the forecast is a **simulated
> baseline**. The backend can load the team's real outputs (station dataset, HCHO hotspot
> clusters, trained-model metadata) through optional settings — see
> [Connecting the team's outputs](#connecting-the-teams-outputs). `GET /api/v1/version` reports
> which source is live, and the dashboard labels demo / simulated / team data accordingly.

## What is real today

| Area | Status | Notes |
|---|---|---|
| Backend API (FastAPI) | ✅ Working | Health, version, AQI, HCHO, fire, forecast and station endpoints; filters and validation are tested |
| AQI / stations data | 🟡 Demo by default | Team dataset when `DATASET_PATH` is set; otherwise 8 demo AQI stations / 12 registry stations |
| HCHO hotspots | 🟡 Demo by default | Team `cluster_summary.json` when `HCHO_HOTSPOTS_PATH` is set; otherwise 5 demo hotspots |
| Fire data | 🟡 Demo data | 5 demo events, 2 illustrative alerts (no fire-detection source exists yet) |
| Forecast | 🟡 Simulated | Deterministic diurnal curve seeded from the station's demo reading; metrics are `null`, no feature importances |
| Dashboard (Streamlit, 7 modules) | ✅ Working | Every page renders against the API; offline demo fallback when the backend is unreachable |
| Surface AQI / HCHO trend charts | 🟡 Simulated | Generated in the page (random walk / seasonal sine); clearly labelled |
| Explainable AI page | 🟡 Partly real | Trained-model metrics + importances when a model artefact is loaded; SHAP / counterfactual sections are hardcoded examples |
| Reports page | ⚪ Placeholder | List and form only; no report generation |
| Raster map overlays (AQI / HCHO / fire) | ⚪ Placeholder | Layer slots exist; no raster data source |
| Database (PostgreSQL / PostGIS) | ⚪ Configured only | Engine, health probe and PostGIS migration; no tables or queries yet |
| Data collection & ML pipeline | Separate | `data_collection_pipeline/` (data and ML team); the API consumes its output files, it does not import its code |

## Repository layout

```text
AKASH/
├── backend/                   # FastAPI service (app/, tests/, alembic/, Dockerfile, docker-compose.yml)
├── dashboard/                 # Streamlit dashboard (app.py, pages/, components/, services/, core/)
├── data_collection_pipeline/  # Data collection, cleaning, feature engineering and ML pipeline
└── PROJECT_CONFIG.yaml        # Project metadata read by the dashboard
```

## Prerequisites

- Python 3.11+ (verified with 3.12)
- PostgreSQL 16 + PostGIS — optional; only `/api/v1/health` uses the database today

## Backend

```bash
python -m venv .venv
```

Activate it (`.venv\Scripts\activate` on Windows, `source .venv/bin/activate` elsewhere), then:

```bash
pip install -r backend/requirements.txt -r backend/requirements-dev.txt
```

```bash
cp backend/.env.example backend/.env
```

Run the API from the `backend/` directory (settings load `.env` from the working directory):

```bash
cd backend && uvicorn app.main:app --reload --port 8000
```

- Swagger UI: http://localhost:8000/docs (disabled when `ENVIRONMENT=production`)
- Without a database, `GET /api/v1/health` returns **503** with `DATABASE_ERROR`. That is
  expected; every other endpoint works without a database.
- With Docker, `backend/docker-compose.yml` starts PostGIS and the API together
  (`cd backend && docker compose up`).

### Backend environment variables (`backend/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `ENVIRONMENT` | `development` | `development` / `staging` / `production` (production disables `/docs` and enforces the checks below) |
| `DEBUG` | `false` | Must be `false` in production |
| `SECRET_KEY` | placeholder | Must be changed in production (min 32 chars) |
| `ALLOWED_ORIGINS` | localhost:3000, :5173 | CORS origins; no localhost or `*` in production |
| `POSTGRES_HOST` / `PORT` / `USER` / `PASSWORD` / `DB` | `localhost` / `5432` / `vayu` / `vayu_password` / `vayu_drishti` | Database connection |
| `LOG_LEVEL` / `LOG_FORMAT` | `INFO` / `json` | Structured logging |
| `DATASET_PATH` | empty | Team station dataset CSV (see below); empty → demo data |
| `HCHO_HOTSPOTS_PATH` | empty | Team `cluster_summary.json`; empty → demo hotspots |
| `ML_MODEL_PATH`, `ENABLE_ML_ENDPOINTS` | empty / `false` | Trained-model artefact directory; loaded only when both are set |

### API endpoints (`/api/v1`)

| Endpoint | Data source today | Notes |
|---|---|---|
| `GET /health` | DB ping | 200 healthy, 503 if the database is unreachable |
| `GET /version` | Settings | App name, version and `data_sources` (which source backs each domain) |
| `GET /aqi/daily` | Dataset or demo | `region`: `India`, a zone (`North India`, `Central India`, `East India`, `Northeast India`, `West India`, `South India`), or a state / city. `date` defaults to the latest available date; dates without data → 404, invalid dates → 422. Unreported pollutants are `null` |
| `GET /stations` | Dataset or demo | `state`, `network`, `active_only`, `limit` filters |
| `GET /forecast` | Simulated | Any active station from `/stations`; `horizon_hours` 1–72; metrics `null` (also when a model artefact is loaded — that model is not a forecaster) |
| `GET /hcho/hotspots` | Hotspot file or demo | `min_confidence` (unscored clusters are kept); `date` optional. From the team file, radius / confidence / date are `null` |
| `GET /fire` | Demo data | `region` (zone / state / district), `min_frp`, `hours`; alerts follow the returned events |
| `GET /xai/global-importance` | Model artefact | Test-set metrics + normalised LightGBM importances; 404 until an artefact is loaded |

Zones follow the Zonal Councils of India (Ministry of Home Affairs).

### Tests

```bash
cd backend && python -m pytest
```

The suite covers health and version, AQI categories, region and date filters, station and
forecast consistency, HCHO and fire filters, 422/404 validation, and the data / hotspot /
model-artefact loaders against synthetic fixtures. No database or real data is needed.

Dashboard compatibility tests (fake API client, no backend needed), from the repository root:

```bash
python -m pytest dashboard/tests
```

## Connecting the team's outputs

Set any of these in `backend/.env` and restart the API. A configured file that is missing or
violates its contract stops the API at startup — it never silently falls back to demo data.

| Setting | Expected input (produced by `data_collection_pipeline/`) |
|---|---|
| `DATASET_PATH` | `analysis_ready_dataset.csv` (v1: `Station ID`, `Station Name`, `State`, `City`, `Latitude`, `Longitude`, `Date`, `Time`, `AQI`, pollutants) or `analysis_ready_dataset_v2.csv` (v2: `station_id`, `station_name`, `state`, `city`, `station_latitude`, `station_longitude`, `timestamp_utc_str`, …). Rows without station ID, coordinates or AQI are skipped and counted; nothing is imputed |
| `HCHO_HOTSPOTS_PATH` | `cluster_summary.json`: list of `{cluster_id, mean_latitude, mean_longitude, mean_hcho (mol/m²), station_count, stations}`; optional `radius_km`, `confidence`, `source_type`, `observation_date` are used when present. HCHO is converted to 10¹⁵ molecules/cm² |
| `ML_MODEL_PATH` + `ENABLE_ML_ENDPOINTS=true` | Directory with `lightgbm_model.joblib` (presence checked, not loaded), `lightgbm_evaluation_metrics.json` (`R2`, `RMSE`, `MAE`, `MBE`), `lightgbm_feature_importances.json`, optional `lightgbm_training_summary.json` |

The model binary is not unpickled: that needs the exact scikit-learn / LightGBM versions it was
trained with, and no endpoint serves its predictions yet.

## Dashboard

```bash
pip install -r dashboard/requirements.txt
```

Run from the repository root while the backend is running:

```bash
streamlit run dashboard/app.py
```

Then open http://localhost:8501.

### Dashboard environment variables (shell or `dashboard/.env`)

| Variable | Default | Purpose |
|---|---|---|
| `VAYU_API_URL` | `http://localhost:8000` | Backend base URL |
| `VAYU_API_V1_PREFIX` | `/api/v1` | API prefix |
| `VAYU_API_TIMEOUT` | `30` | Request timeout in seconds |
| `VAYU_APP_NAME`, `VAYU_APP_VERSION`, `VAYU_STATUS` | from `PROJECT_CONFIG.yaml` | Display metadata |

If the backend is unreachable, pages show built-in offline demo data (the forecast page shows
"unavailable"). A filter that legitimately matches nothing shows an empty state, never demo data.

## Current limitations

- Without the settings above, all domain data is demo data. Fire data is always demo data.
- No model predictions are served; forecasts are simulated and forecast metrics are `null`.
- Trend charts, SHAP / counterfactual examples, HCHO source attribution and fire-alert impact
  scores are illustrative.
- `dominant_pollutant` is not computed (`N/A` with the team dataset).
- No database tables, persistence, authentication, report generation or raster layers yet.

## Next integration steps

1. Point `DATASET_PATH`, `HCHO_HOTSPOTS_PATH` and `ML_MODEL_PATH` at the team's delivered
   outputs (the loaders, adapters and dashboard handling are in place).
2. Serve model predictions once a forecasting model (or an agreed estimate endpoint) and its
   exact library versions are delivered.
3. Persist time series and geometries in PostgreSQL / PostGIS.
