# AKASH — Atmospheric Knowledge: AQI from Satellite Harmonics

**VAYU-DRISHTI** is a production-grade air quality monitoring system for India that fuses ground-station observations (CPCB, OpenAQ), satellite data (Sentinel-5P TROPOMI, MODIS MAIAC), and meteorological reanalysis (ERA5) into a unified ML pipeline for AQI prediction.

---

## 🏗️ Repository Layout

```text
AKASH/
├── backend/                    # FastAPI backend service
├── dashboard/                  # Streamlit dashboard
├── data_collection_pipeline/   # Data ingestion, feature engineering & ML pipeline
│   ├── earth_engine/           # Google Earth Engine satellite data pipeline
│   └── ...
├── docs/                       # Technical documentation
└── PROJECT_CONFIG.yaml         # Project-level configuration
```

---

## ⚡ Quick Start

### 1. Install dependencies

```bash
pip install -r data_collection_pipeline/requirements.txt
```

### 2. Configure environment variables

Copy and edit the example environment file:

```bash
cp backend/.env.example backend/.env
```

The following variables are required to run the full pipeline:

| Variable | Required | Description |
|----------|----------|-------------|
| `GEE_PROJECT_ID` | **Yes** | Google Cloud Project ID registered for Earth Engine. Set to `aqi-satellite`. |
| `DATA_GOV_API_KEY` | Recommended | API key for CPCB data via data.gov.in |
| `OPENAQ_API_KEY` | Recommended | API key for OpenAQ |
| `EE_SA_KEY_PATH` | CI/CD only | Path to service-account JSON key (headless auth) |

Minimum `.env` for the satellite pipeline:

```env
GEE_PROJECT_ID=aqi-satellite
```

### 3. Authenticate with Earth Engine

```bash
earthengine authenticate
```

### 4. Validate Earth Engine setup

```bash
python -m data_collection_pipeline.earth_engine.validator
```

This runs a four-step health check (env var → credentials → initialization → collection query) and exits with code `0` if everything is production-ready.

### 5. Run the data collection pipeline

```bash
python data_collection_pipeline/scripts/run_pipeline.py
```

---

## 📚 Documentation

- [Earth Engine Pipeline](docs/earth_engine.md) — GEE package layout, datasets, auth, and startup validation.
- [Data Collection Pipeline README](data_collection_pipeline/README.md) — Full pipeline usage and configuration reference.
- [Backend README](backend/README.md) — FastAPI service setup.