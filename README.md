# AKASH — Atmospheric Knowledge: AQI from Satellite Harmonics

**VAYU-DRISHTI** is a satellite-based air-quality platform for India. The goal is to estimate
surface AQI from Sentinel-5P TROPOMI, MODIS and ERA5 data trained against CPCB ground stations,
detect HCHO hotspots, monitor fires, and present the results through a FastAPI backend and a
Streamlit dashboard.

> **Read this first.** The backend and dashboard run end to end. Every domain is served from a
> resolved **source**: the team's real output when it is available, otherwise a bundled,
> clearly-labelled **placeholder fixture** that uses the exact same contract. `GET /api/v1/sources`
> reports what powers each feature, and every dashboard page shows it as a badge:
> **LIVE · LOCAL (team output) · PLACEHOLDER (not real data) · SIMULATED · UNAVAILABLE**.
> **Availability is not trust.** A team file that exists and parses is `LOCAL`, but it is only
> **PROMOTED** (trust `trusted`) after passing every check of its trust gate. Otherwise it is
> **UNVERIFIED** — used only for the features that stay safe (e.g. AQI tables) — or not used at
> all. Badges read **LOCAL — PROMOTED · LOCAL — UNVERIFIED · PLACEHOLDER · SIMULATED ·
> UNAVAILABLE** (LIVE is reserved for a live feed; none exists). Every source also reports its
> known **limitations**, and features they make misleading — such as station maps — are withheld.

## Architecture

```text
team output file  ─┐
placeholder fixture ┴─► SOURCE ADAPTER ─► NORMALISED CONTRACT ─► SERVICE ─► API ─► DASHBOARD
                         (backend/app/data)   (validated, nullable,   (backend/   (/api/v1)  (source badge,
                          rejects bad rows,    units converted,        app/services)          limitations,
                          flags limitations)   limitations + quality)                         maps withheld)
```

Resolution per domain at API startup (`backend/app/data/sources.py`):

1. **Explicit path** setting → `local`. A corrupt / unreadable file (or one whose schema cannot
   be read) **stops the API at startup**.
2. **Auto-discovered** team output at its documented repo location → `local`. If it is
   incompatible it is skipped and the reason appears in `GET /api/v1/sources`.
3. Every loaded team source then passes its **trust gate** (`backend/app/data/trust.py`, see
   [Data trust and promotion](#data-trust-and-promotion)): contract failure → not used (the
   domain falls back, naming the rejected `candidate`); contract only → **unverified**; every
   check → **promoted**.
4. **Placeholder fixture** (`backend/app/data/fixtures/`) → `placeholder` (if `ENABLE_PLACEHOLDER_DATA`).
5. Otherwise → `unavailable`.

Placeholders use the same contract as the real source, so plugging in a teammate's artefact is
a **configuration change only** — no service, API or dashboard change.

Adapters never alter or "fix" source values. Per row they **accept or reject** (with a counted
reason); per dataset they report **limitations** in `GET /api/v1/sources` (`limitations` +
`quality`), which the API and dashboard use to restrict what they present.

## Data trust and promotion

**Availability ≠ trust.** `kind` / `status` say what is serving (`local` team file, `placeholder`,
…; `available`, `withheld`, `unavailable`). `trust` and `promoted` say whether it may be relied on:

| Trust | Meaning | Dashboard badge |
|---|---|---|
| `trusted` | Team source that passed **every** blocking and restricting check — promoted | LOCAL — PROMOTED |
| `unverified` | Team source that passed the contract but failed a scientific check; used only for the capabilities whose checks pass, never presented as validated | LOCAL — UNVERIFIED |
| `placeholder` | Bundled deterministic fixture — not real data (also used when a team source failed its contract) | PLACEHOLDER |
| `simulated` | Synthetic algorithm (the forecast) | SIMULATED |
| `unavailable` | Nothing served (an unverified model is `withheld`: found, not served) | UNAVAILABLE |

Each gate is a list of checks: **blocking** (the contract — failure means the source is not used),
**restricting** (scientific quality — failure blocks promotion and the affected capabilities) and
**info** (reported only). `GET /api/v1/sources` returns the checks, the per-feature
`capabilities` (e.g. `station_maps`, `hotspot_map`, `model_metrics`), a one-line `reason` such as
"Team dataset in use but not promoted: 60 of 502 rows rejected; coordinate quality insufficient
for spatial maps; CO unit unverified (+1 more)", and the rejected team `candidate` if any.

| Source | Blocking (contract) | Restricting (promotion) | Capabilities |
|---|---|---|---|
| Station dataset | required columns / schema; ≤ 25 % of rows rejected (malformed rows, missing / invalid IDs, invalid or future timestamps, missing / invalid / non-Indian coordinates, AQI outside 0–500 or violating the CPCB minimum-data rule, conflicting duplicates) | ≤ 1 % rows rejected; coordinates are distinct station positions (not shared by > 10 % of stations, no point shared by different cities); CO plausible in mg/m³; PM2.5 ≤ PM10 in ≥ 95 % of rows; consistent station metadata; no unusable numeric cells | `aqi_tables`, `station_history` (contract) · `station_maps` (coordinate check) |
| HCHO trend (satellite samples in the dataset) | ≥ 1 dated sample | numeric values; satellite overpass dates recorded; satellite date within 3 days of the station date; no conflicting values at one location-date; sampled at distinct station positions | `hcho_trend` — samples are independent of the ground-AQI row rejection |
| HCHO clusters | the `cluster_summary.json` contract (unique `cluster_id`, coordinates, `mean_hcho`) | consistent member counts; members found in the station dataset; no single-point clusters / approximate centroids; observation date present | `hotspot_table` (contract) · `hotspot_map` (coordinate checks) |
| Fire file | the fire contract | provenance — no rule exists yet, so a fire file is never promoted | `fire_alerts` |
| Model artefact | files + JSON metadata | `model_type` LGBMRegressor; target AQI; task `same_day_estimation`; `feature_names`; no leaky inputs; importances match features; `trained_at`; time-based `split_strategy`; held-out metrics + test size; library versions; `input_example`; **isolated load probe** (`MODEL_LOAD_CHECK`): loads as a preprocessing pipeline ending in LGBMRegressor, input columns = `feature_names`, installed lightgbm / scikit-learn = training major.minor, finite prediction for `input_example` | `model_metrics`, `global_importance` (all checks) · `model_forecast` never |

**Why local team outputs can stay unverified.** The gates measure the data; they never repair it.
The current PR #7 / #8 dataset passes the contract (12 % of rows rejected) but fails promotion:
its stations sit on shared city / registry fallback coordinates, CO is not in mg/m³, PM2.5
exceeds PM10 in 15 % of rows and satellite values are 13–20 days from the station date. It is
therefore served as **UNVERIFIED** for AQI tables and history, while **station and hotspot maps
stay withheld** — plotting stations at fallback points would invent locations.

**How a corrected team dataset becomes promotable.** Deliver per-station coordinates, AQI only
where the CPCB minimum-data rule holds, CO in mg/m³, consistent PM values and satellite values
matched to the station date. On the next API start the same gate promotes it automatically and
`station_maps` re-enables — no code change.

**How the model becomes validated.** The training summary must record every field listed above
(nothing is ever filled in or guessed), and the operator enables the isolated load probe
(`MODEL_LOAD_CHECK=true`, optionally `MODEL_PROBE_PYTHON` = the training environment's
interpreter). A model that merely loads, or has complete metadata but was never load-checked,
stays unverified and is not served. Even a promoted model is a same-day estimator: the forecast
stays simulated.

`REQUIRE_TRUSTED_TEAM_DATA=true` turns UNVERIFIED use off: only promoted team sources are used and
the other domains keep their placeholder / unavailable state.

## What powers each feature today

| Feature | Source today | Real source (when delivered) |
|---|---|---|
| AQI / stations | PLACEHOLDER — 8 stations × 7 days, deterministic | Team `analysis_ready_dataset.csv` (PR #7/#8, not yet on `main`) |
| HCHO hotspot clusters | PLACEHOLDER — 4 clusters in the `cluster_summary.json` contract | Team `cluster_summary.json` (PR #7 hotspot step) |
| HCHO daily trend | Derived from the station dataset (placeholder today) | Same, from the team dataset |
| Fire detections & alerts | PLACEHOLDER — 5 detections; alerts by FRP rule | A fire file in the `app/data/fires.py` contract (no team source yet) |
| Forecast | SIMULATED — deterministic diurnal baseline | A real forecasting model behind the `Forecaster` interface |
| Model metrics / global importance | UNAVAILABLE | Team LightGBM artefact (`ML_MODEL_PATH`) |
| Per-prediction SHAP | UNAVAILABLE | Not produced by any team output yet |
| GIS rasters (interpolation, Gi*/LISA, HYSPLIT) | UNAVAILABLE — no layer shown | XYZ tile source via `VAYU_*_RASTER_TILES` |
| Database (PostgreSQL / PostGIS) | Configured only (health probe, PostGIS migration) | Planned |

## Team outputs (PR #7 / PR #8): integration status

Verified against the actual branch contents and by simulating `main` + this integration + PR #7
+ PR #8. Neither PR is merged yet, so `main` serves placeholders until they are; after the merge
the outputs below are picked up automatically (or via the path settings).

| Team output | Found in | Integration | Why / limitations reported by `/sources` |
|---|---|---|---|
| `analysis_ready_dataset.csv` (502 rows, one date) | Repo root on PR #7 and PR #8 (identical file) | **Consumed as UNVERIFIED** for AQI tables, stations, history and the HCHO trend — not promoted; station maps withheld | 60 rows rejected: AQI reported without PM2.5/PM10 or with fewer than 3 pollutants (violates the CPCB minimum-data rule). The remaining 442 stations sit on only **46 distinct coordinates**, 429 of them shared (`approximate_coordinates`; in the file one point carries 69 stations from 29 cities) → station maps withheld, tables kept. CO median 27 is implausible in the contract unit mg/m³ (`co_unit_unverified`). Single date (`single_date`). Satellite HCHO observed 13–20 days before the station date (`satellite_date_mismatch`) → trend dated by `HCHO Obs Date`; the satellite samples of AQI-rejected rows still count (all 48 distinct location-date samples). AQI served as reported (not recomputed) |
| `cluster_summary.json` (`spatial_analysis/hotspot_detector.py`) | Not committed; written to `<repo>/reports/` by `scripts/run_sprint07_pipeline.py` | **Consumed when present as UNVERIFIED** — table only, hotspot map withheld | DBSCAN runs on the shared fallback coordinates: on the team dataset 2 of its 4 clusters are 38 and 10 stations on a single point. `approximate_coordinates` (or `unverified_coordinates` when members cannot be matched to the station dataset) → hotspot map withheld; no date / radius / confidence / attribution (`no_observation_date`, …) |
| LightGBM artefact (`model_training/lightgbm_model.py`) | Not committed (`*.joblib` is git-ignored); default output is the repo root | **Withheld as UNVERIFIED** | The trainer's `lightgbm_training_summary.json` records no `model_type`, `task`, `feature_names`, `trained_at`, `split_strategy` (it falls back to a random split) or `input_example`, so an artefact is "found but not validated", not served, and `/xai/global-importance` stays 404 |
| `analysis_ready_dataset_v2.csv` (`dataset_merger.py`) | Not committed (`processed_data/` is git-ignored) | **Consumed when present** if the v1 file is absent or incompatible | Same adapter rules; different station IDs (`ST_<hash>` vs `STN_xxx`) |
| Root `feature_importances.json` (PR #8) | Repo root on PR #8 | **Not consumed** | Random-Forest baseline output with no metrics, run metadata or model; "Day of Week" = 0.58 on a single-date dataset is not explainable |
| Day-5 explainer / SHAP outputs | `data_collection_pipeline` | **Not consumed** | Use PM2.5 / PM10 as features → target leakage |
| `predictions.csv`, `india_aqi_map*.png` (`inference/`, `spatial_mapper.py`) | Not committed | **Not consumed** | In-sample same-day estimates of a Random-Forest model on a path outside the repo; never a forecast |
| `historical_data/openaq/*.csv` | PR #8 | **Not consumed** | Raw hourly PM2.5 for 3 stations — not the analysis-ready contract (no AQI) |
| Audit CSVs / reports | PR #8 repo root | **Not consumed** | Documentation, not service data |

## What this build does NOT claim

- Placeholder fixtures are **not measurements, detections or model output** — they exist so the
  system runs and can be tested before the team's artefacts land.
- The forecast is **not a prediction**: no forecasting model exists. The team's LightGBM model is a
  **same-day AQI estimator**, not a 72-hour forecaster, and is never presented as one.
- No model accuracy (R², RMSE, …) is shown unless it comes from a real model artefact.
- HCHO clusters have no radius, confidence, source attribution or date in the team contract;
  these stay null / "unknown" and are never invented.
- Fire alerts are a documented FRP threshold rule; no AQI-impact or smoke-trajectory value exists.
- No Kriging, Gi*/LISA, HYSPLIT or counterfactual output exists; none is displayed.
- `dominant_pollutant` is not computed (`N/A`).
- Team data served as `local` is **not scientifically validated** by this application: AQI is
  taken as reported, coordinates are only as good as the pipeline's lookup, and every known
  defect is listed in the source's `limitations`.
- No corrected coordinates, recomputed AQI or rescaled CO values are produced — restricted
  features are withheld instead.

## Repository layout

```text
AKASH/
├── backend/                   # FastAPI service (app/, tests/, alembic/, Dockerfile, docker-compose.yml)
│   └── app/data/              # source adapters, resolver, placeholder fixtures
├── dashboard/                 # Streamlit dashboard (app.py, pages/, components/, services/, core/, tests/)
├── data_collection_pipeline/  # Data collection, cleaning, feature engineering and ML (data/ML team)
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
| `DATASET_PATH` | empty | Team station dataset CSV (explicit → strict) |
| `HCHO_HOTSPOTS_PATH` | empty | Team `cluster_summary.json` (explicit → strict) |
| `FIRE_EVENTS_PATH` | empty | Fire-detection JSON (explicit → strict) |
| `AUTO_DISCOVER_TEAM_OUTPUTS` | `true` | Use the team outputs at their documented locations when present: `<repo>/analysis_ready_dataset.csv` (then `data_collection_pipeline/processed_data/analysis_ready_dataset_v2.csv`), `<repo>/reports/cluster_summary.json`, and (with `ENABLE_ML_ENDPOINTS`) a LightGBM artefact in `<repo>/` |
| `ENABLE_PLACEHOLDER_DATA` | `true` | Fall back to the placeholder fixtures; `false` → those domains report `unavailable` |
| `ML_MODEL_PATH`, `ENABLE_ML_ENDPOINTS` | empty / `false` | Trained-model artefact directory. Served only when `ENABLE_ML_ENDPOINTS=true` **and** the model trust gate promotes it |
| `REQUIRE_TRUSTED_TEAM_DATA` | `false` | `true` → only **promoted** team sources are used; unverified ones are reported as rejected candidates |
| `MODEL_LOAD_CHECK` | `false` | Opt-in isolated load probe (unpickles the artefact in a subprocess). Without it a model can never be promoted |
| `MODEL_PROBE_PYTHON` | empty | Interpreter for the probe (e.g. the ML training environment with the exact lightgbm / scikit-learn versions); default: the API's own |

### API endpoints (`/api/v1`)

| Endpoint | Notes |
|---|---|
| `GET /health` | 200 healthy, 503 if the database is unreachable |
| `GET /version` | App name, version and compact `data_sources` |
| `GET /sources` | Source and trust status per domain: `kind`, `name`, `detail`, `records`, `as_of`, `limitations`, the adapter's `quality` report (incl. a `spatial` summary), plus `status` (available / withheld / unavailable), `origin` (configured / discovered / bundled / generated), `location` (repo-relative, never absolute), `trust`, `promoted`, one-line `reason`, `validation` (status + checks), `capabilities` and the rejected team `candidate` |
| `GET /aqi/daily` | `region`: `India`, a zone (`North India`, `Central India`, `East India`, `Northeast India`, `West India`, `South India`) or a state / city. `date` defaults to the source's latest date; no data → 404; invalid date → 422. Unreported pollutants are `null` |
| `GET /aqi/history` | One station's observations (never simulated), `days` window ending at the source's latest date; unknown station → 404 |
| `GET /stations` | Registry derived from the station source; `state`, `network`, `active_only`, `limit`; `location_quality` = `approximate` when coordinates are shared fallbacks (also on `/aqi` readings) |
| `GET /forecast` | Any station from `/stations`; `horizon_hours` 1–72; `forecast_kind` = `simulated`; `based_on_observation_at`; metrics `null` |
| `GET /hcho/hotspots` | Clusters, column density in 10¹⁵ molecules/cm²; `min_confidence` keeps unscored clusters; `date` optional; `station_count`, `member_locations` (distinct station locations behind the cluster) and `location_quality` |
| `GET /hcho/trend` | Daily mean satellite HCHO column at the dataset's sampling locations; dated by the satellite overpass (`date_basis`) when recorded (undated values are then excluded); stations sharing a coordinate count once (`location_count`); rows rejected only for their AQI still contribute their satellite sample; negative retrievals kept |
| `GET /fire` | `region` (zone / state / district), `min_frp`, `hours` (window ends at `as_of`, the latest detection); FRP-rule alerts, `aqi_impact_score` null |
| `GET /xai/global-importance` | Validated model artefact metrics + normalised LightGBM importances; 404 (with the reason) until a validated artefact is loaded |

Zones follow the Zonal Councils of India (Ministry of Home Affairs). HCHO unit conversion
(mol/m² → 10¹⁵ molecules/cm², ×6.02214076e4) lives only in `backend/app/core/units.py`; CPCB AQI
categories only in `backend/app/core/aqi.py` (mirrored for display in `dashboard/core/theme.py`).

### Tests

```bash
cd backend && python -m pytest
```

```bash
python -m pytest dashboard/tests
```

Backend tests cover every source path (explicit, auto-discovered, incompatible, placeholder,
disabled, invalid, v1/v2 priority), the adapters' contracts and rejection rules, team-shaped
fixtures reproducing the known defects (shared coordinates, AQI without PM, CO unit, satellite
dates), the model production gate (validated, team-trainer format, leakage, random split,
forecasting task), filters, dates, nullable values, unit conversion, history / trend, forecast
and model states, and `/sources`. The trust-gate tests cover a clean team-shaped source that is
promoted, partially valid / malformed / mostly-rejected sources (unverified, fallback, explicit
without crash), coordinate and PM checks, HCHO dating / conflicts / independence from AQI,
cluster structure, `REQUIRE_TRUSTED_TEAM_DATA`, the model gate (metadata contract and load-probe
outcomes) and the isolated probe subprocess. Dashboard tests cover the data layer, trust labels,
capabilities, map restrictions and badge rendering. No database, network or real data is needed.

## Connecting the team's outputs

| Team output | Contract | How to plug in |
|---|---|---|
| Station dataset (data pipeline) | `analysis_ready_dataset.csv` v1 (`Station ID`, `Station Name`, `State`, `City`, `Latitude`, `Longitude`, `Date`, `Time`, `AQI`, pollutants, `HCHO`, optional `HCHO Obs Date`) or `analysis_ready_dataset_v2.csv` (`station_id`, `station_latitude`, `timestamp_utc_str`, …). Rows are rejected for: missing station ID / timestamp, invalid or non-Indian coordinates, AQI outside 0–500, AQI violating the CPCB minimum-data rule; conflicting duplicates are dropped | Merge it to the repo root (auto-discovered), write v2 to `processed_data/`, or set `DATASET_PATH` |
| HCHO hotspot clusters (`spatial_analysis/hotspot_detector.py`) | `cluster_summary.json`: `{cluster_id, mean_latitude, mean_longitude, mean_hcho (mol/m²), station_count, stations}`; optional `radius_km`, `confidence`, `source_type`, `observation_date` are used when present | Write it to `<repo>/reports/cluster_summary.json` or set `HCHO_HOTSPOTS_PATH` |
| LightGBM artefact (`model_training/lightgbm_model.py`) | `lightgbm_model.joblib` (never unpickled in the API process), `lightgbm_evaluation_metrics.json` (`R2`, `RMSE`, `MAE`, `MBE`), `lightgbm_feature_importances.json`, `lightgbm_training_summary.json` with `model_type`, `task: "same_day_estimation"`, `target_column: "AQI"`, `feature_names`, `trained_at`, `split_strategy: "temporal"`, `test_samples`, `reproducibility.lightgbm_version` + `sklearn_version` and an `input_example` row; no AQI / PM2.5 / PM10 / NO2 / SO2 / CO / O3 inputs (see [Data trust and promotion](#data-trust-and-promotion)) | Set `ML_MODEL_PATH` (or leave the trainer's default output in `<repo>/`), `ENABLE_ML_ENDPOINTS=true` and `MODEL_LOAD_CHECK=true` |
| Fire detections | JSON list in `backend/app/data/fires.py` (`event_id`, `latitude`, `longitude`, `frp`, `brightness`, `satellite`, `confidence`, `detected_at`, …) | Set `FIRE_EVENTS_PATH` |
| Forecasting model | Implement `Forecaster` in `backend/app/services/forecast_service.py` (`kind = "model"`) | Register it in `ForecastService`; API and dashboard already carry `forecast_kind` |
| Raster layers | XYZ tile template (e.g. TiTiler over team COGs) | `VAYU_AQI_RASTER_TILES`, `VAYU_HCHO_RASTER_TILES`, `VAYU_FIRE_RASTER_TILES` (dashboard env) |

After restarting the API, `GET /api/v1/sources` must show `local` for the domain; the dashboard
badges follow automatically.

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
| `VAYU_AQI_RASTER_TILES` etc. | empty | Optional real raster tile sources (no layer is shown without them) |

The dashboard keeps **no hardcoded data**. If the backend is unreachable every section shows
UNAVAILABLE; a filter that matches nothing shows an empty state.

## Remaining external dependencies

- Team dataset with per-station coordinates (the PR #7/#8 file puts 502 stations on 48
  coordinates), AQI only where the CPCB minimum-data rule holds, CO in mg/m³, and satellite
  values matched to the station date — station maps then re-enable automatically.
- `cluster_summary.json` computed on real station coordinates, with an observation date.
- LightGBM artefact whose training summary passes the model trust gate (model type, task,
  feature names, training date, time-based split, library versions, input example) and that
  loads in the probe environment.
- A forecasting model; per-prediction SHAP output from a non-leaky model; a fire-detection
  source; raster tiles.
- Database persistence (PostgreSQL / PostGIS) and PDF reports — planned on our side.
