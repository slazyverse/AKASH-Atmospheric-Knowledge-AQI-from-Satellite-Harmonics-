# Historical Ground Data Ingestion Architecture

## 1. High-level System Architecture

The historical ground data ingestion layer follows an **Extract, Load, Transform (ELT)** architectural pattern designed for high throughput, reproducibility, and modularity. The system architecture consists of the following components:

- **Source Connectors:** Connect to specific APIs (OpenAQ API, CPCB CAAQMS API) and manage authentication, pagination, and retry logic.
- **Raw Landing Zone (Data Lake):** Stores raw fetched data (JSON/CSV) without any transformation, preserving the original payload for auditability and replay.
- **Parser & Standardizer:** Converts raw formats into a unified common schema, applying timestamp standardization, unit normalization, and pollutant mapping.
- **Quality Assurance (QA) Engine:** Evaluates standardized data against validation rules (bounds, completeness, duplicate detection).
- **Merger & Deduplicator:** Resolves conflicts between sources based on source priority policies and deduplicates records.
- **Structured Storage (Data Warehouse):** The final historical dataset, partitioned by year/month/station and stored in column-oriented formats (Parquet) for downstream machine learning and validation processes.
- **Orchestration & Logging:** Manages execution flow, centralized logging, and configuration injectables.

## 2. Folder Structure

```text
historical_ingestor/
├── __init__.py
├── config/
│   ├── default_config.yaml         # Base configuration (URLs, API limits, retries)
│   ├── validation_rules.yaml       # Data quality bounds for each pollutant
│   └── source_priority.yaml        # Rules for resolving overlaps (CPCB vs OpenAQ)
├── connectors/
│   ├── __init__.py
│   ├── base_connector.py           # Abstract Base Class defining `fetch_data()`
│   ├── openaq_connector.py         # OpenAQ-specific API interaction
│   └── cpcb_connector.py           # CPCB CAAQMS-specific API interaction
├── schemas/
│   ├── __init__.py
│   ├── common_data_schema.py       # Standardized observation schema definition
│   └── station_metadata_schema.py  # Standardized station schema definition
├── processors/
│   ├── __init__.py
│   ├── normalizer.py               # Unit conversion and pollutant naming standards
│   ├── time_standardizer.py        # Timestamp formatting and timezone alignment
│   └── quality_validator.py        # Validates data against bounds and rules
├── storage/
│   ├── __init__.py
│   ├── raw_writer.py               # Saves unmodified payloads to landing zone
│   ├── unified_writer.py           # Saves cleaned Parquet files
│   └── partition_manager.py        # Handles partition structures (year/month/station)
├── utils/
│   ├── __init__.py
│   ├── logger.py                   # Centralized logging configuration
│   └── error_handlers.py           # Custom exception definitions and handling
└── pipeline.py                     # Main orchestrator entry point
```

## 3. Module Responsibilities

- **`connectors/`**: Solely responsible for interacting with external APIs. They handle rate limiting, pagination, backoff, and returning raw payloads. They do *not* perform data cleaning.
- **`schemas/`**: Defines the single source of truth for how data should look internally (e.g., Pydantic or Pandera schemas). This enforces strict typing and structures.
- **`processors/`**: The core transformation layer. It maps specific source dialects to the common schema, normalizes units, standardizes time, flags missing values, and drops or imputes data based on policies.
- **`storage/`**: Manages all disk/cloud I/O operations. It enforces partitioning strategies and ensures atomic writes to prevent corrupted partial files.
- **`utils/`**: Provides horizontal services like structured logging, error definitions, and telemetry used across all modules.

## 4. Common Data Schema

The unified observation schema defines the exact structure of a single measurement after processing.

- `station_id` (String): Unique identifier linking to station metadata.
- `timestamp_utc` (Datetime): ISO-8601 formatted timestamp strictly in UTC.
- `timestamp_local` (Datetime): ISO-8601 formatted timestamp in IST (UTC+5:30).
- `pollutant` (String): Standardized parameter name (e.g., 'PM2.5', 'HCHO').
- `value` (Float): The measured concentration.
- `unit` (String): Standardized unit of measurement (e.g., 'µg/m³').
- `source_name` (String): Origin of the data (e.g., 'OpenAQ', 'CPCB').
- `qa_flag` (String/Enum): Quality indicator (e.g., 'VALID', 'SUSPECT', 'IMPUTED').

## 5. Station Metadata Schema

Station metadata is kept separate from observations to prevent data duplication.

- `station_id` (String): Primary key (e.g., `IN-DL-001`).
- `source_station_id` (String): The original ID from the data provider.
- `station_name` (String): Human-readable name.
- `latitude` (Float): Decimal degrees (WGS84).
- `longitude` (Float): Decimal degrees (WGS84).
- `elevation_m` (Float): Elevation in meters above sea level (if available).
- `city` (String): Mapped city name.
- `state` (String): Mapped state name.
- `country` (String): 'India' (ISO code 'IN').
- `status` (String/Enum): 'ACTIVE', 'INACTIVE'.

## 6. Pollutant Naming Standards

To ensure consistency across differing source conventions (e.g., OpenAQ uses 'pm25', CPCB uses 'PM2.5'), the ingestion layer enforces a strict internal taxonomy:

- **PM2.5**: Particulate Matter < 2.5 µm (Mapped from 'pm25', 'PM 2.5', 'pm-2-5')
- **PM10**: Particulate Matter < 10 µm (Mapped from 'pm10', 'PM 10')
- **NO2**: Nitrogen Dioxide (Mapped from 'no2', 'Nitrogen Dioxide')
- **SO2**: Sulfur Dioxide (Mapped from 'so2', 'Sulphur Dioxide')
- **CO**: Carbon Monoxide (Mapped from 'co')
- **O3**: Ozone (Mapped from 'o3', 'Ozone')
- **HCHO**: Formaldehyde (For future satellite ground-truth matching)

*Rationale:* A hardcoded mapping dictionary in the configuration ensures all downstream models query a single, predictable parameter name.

## 7. Unit Normalization Strategy

Different sources report in different units (e.g., ppb, ppm, µg/m³, mg/m³).

- **Standard Units:**
  - Particulates (PM2.5, PM10): `µg/m³`
  - Gases (NO2, SO2, O3, HCHO): `µg/m³`
  - CO: `mg/m³`
- **Conversion Policy:** The `normalizer.py` module will use standard environmental temperature (25°C) and pressure (1 atm) formulas for volumetric (ppb/ppm) to mass density (µg/m³) conversions where required.
- *Rationale:* Machine learning models require homogenous scale distributions. Normalizing at ingestion prevents complex, error-prone conversions during the feature engineering phase.

## 8. Timestamp Standardization Strategy

- **Resolution:** Hourly. Sub-hourly data will be aggregated (mean) to the top of the hour.
- **Timezone:** All internal storage will use strictly UTC for `timestamp_utc`. A secondary `timestamp_local` (IST, UTC+5:30) is stored to simplify diurnal pattern analysis.
- **Format:** ISO-8601 string format in temporary stages, strictly cast to Pandas/PyArrow Datetime objects upon Parquet write.
- *Rationale:* Satellites (MODIS, Sentinel-5P) pass over in UTC. Standardizing ground data to UTC ensures seamless temporal joins without timezone shift bugs.

## 9. Missing-Value Handling Policy

- **Ingestion Phase (No Imputation):** The ingestion layer will **not** impute missing values. If a sensor did not report an hour, the row is either dropped or explicitly stored as `NaN`.
- **Negative Values:** Treated as missing (`NaN`) unless specific instrument calibration documentation states otherwise.
- **Consecutive Missing:** Not flagged at ingestion, handled in the ML feature pipeline.
- *Rationale:* Imputation is a modeling decision, not a data extraction decision. The ingestion layer's duty is to accurately reflect reality, including outages.

## 10. Data Quality Validation Framework

The `quality_validator.py` applies rules against the common schema.

- **Range Checks:** Values outside physical bounds (e.g., PM2.5 < 0 or > 2000 µg/m³) are flagged as `INVALID`.
- **Rate of Change (Spike Detection):** Changes > 500% in a single hour without surrounding context are flagged as `SUSPECT`.
- **Stuck Values:** Exact same float value repeating for > 12 hours is flagged as `SUSPECT` (likely a frozen sensor).
- *Rationale:* Bad sensor data is common in CAAQMS. Flagging instead of deleting preserves the audit trail while allowing the ML pipeline to filter by `qa_flag == VALID`.

## 11. Duplicate Detection Strategy

Duplicates arise from overlapping paginations or overlapping sources (e.g., OpenAQ aggregating CPCB data).

- **Composite Key:** `[station_id, timestamp_utc, pollutant]`
- **Resolution:** The `Merger & Deduplicator` groups by the composite key.
- **Tie-Breaker:** If values are identical, keep the first. If values differ, defer to the **Source Priority Policy**.

## 12. Source Priority Policy (OpenAQ vs CPCB)

- **Priority 1: CPCB CAAQMS (Direct).** Considered the authoritative primary source.
- **Priority 2: OpenAQ.** Considered an aggregator.
- *Rationale:* OpenAQ can sometimes have ingestion lags or unit conversion rounding errors. If a composite key exists in both, the CPCB value strictly overrides the OpenAQ value.

## 13. Unified Historical Dataset Specification

The final output is a strictly defined tabular dataset.

- **Grain:** 1 Row = 1 Station + 1 Hour + 1 Pollutant.
- **Completeness:** Ensures a continuous hourly time grid. If a station exists, a complete hourly index is generated for the target year (2025), with missing hours filled as `NaN` explicitly (Time Series padding).
- *Rationale:* Explicit `NaN` padding forces downstream pipelines to actively handle missingness rather than silently ignoring sparse sensor days.

## 14. File Format Recommendations (CSV vs Parquet)

- **Format:** Apache Parquet with Snappy compression.
- **Why not CSV?** Parquet provides columnar compression, reducing storage costs by ~70-80%. It preserves data types natively (no date parsing overhead) and allows predicate pushdown (e.g., efficiently querying only 'PM2.5' columns without reading the whole file).
- **Partitioning:** `year=YYYY/month=MM/station=ID/data.parquet`
- *Rationale:* Maximizes I/O performance during model training where specific months or regions are loaded repeatedly.

## 15. Logging Architecture

- **Structured Logging:** JSON-formatted logs via Python's `logging` or `structlog`.
- **Fields:** `timestamp`, `level`, `module`, `source`, `records_processed`, `status`.
- **Destinations:** Standard output (stdout) for container orchestration, and rotating file logs (`ingestion_YYYYMMDD.log`) for local audits.
- *Rationale:* JSON logs are easily ingested by log aggregators (ELK/Datadog) and parsed for pipeline health metrics.

## 16. Configuration Management Strategy

- **Implementation:** YAML-based configuration loaded via a singleton configuration manager (`config.py`).
- **Environment Variables:** Used for sensitive overrides (API keys, database URLs).
- **Separation:** Logic parameters (URLs, timeouts) are separate from Business rules (Quality bound thresholds).
- *Rationale:* Allows researchers to tweak QA bounds or add API endpoints without touching Python code.

## 17. Error Handling Strategy

- **Transient Errors (e.g., HTTP 500, 429 Timeout):** Caught by Connectors. Exponential backoff (e.g., 2s, 4s, 8s) implemented via `tenacity` library.
- **Permanent Errors (e.g., HTTP 404, Schema validation fail):** Logged as `ERROR` and skipped. The pipeline continues processing other stations.
- **Data Integrity Errors:** Caught by QA Engine. The row is tagged `INVALID` but not crashed.
- *Rationale:* Ingestion pipelines must be resilient. One offline CPCB station should not crash the job for the other 9.

## 18. Scalability Considerations

- **Current State:** 10 stations for 1 year is trivially small.
- **Future State (All of India, multi-year):**
  - **Asynchronous I/O:** Connectors should utilize `asyncio` and `aiohttp` to fetch hundreds of stations concurrently without thread-blocking.
  - **Chunked Processing:** Memory constraints are mitigated by processing and writing to Parquet in chunks (e.g., 1 month per station at a time) rather than loading everything into a single Pandas DataFrame.

## 19. Future Integration Points for Satellite Datasets

- **Spatial Indexing:** The Station Metadata Schema includes precise Lat/Lon. Future modules will use this to generate bounding boxes or perform nearest-neighbor queries against raster grids (MODIS, Sentinel-5P).
- **Temporal Alignment:** The strict enforcement of `timestamp_utc` ensures satellite overpass times (which are always UTC) can be joined exactly with the closest hourly ground observation.
- *Rationale:* Designing the ground layer with explicit spatial and temporal coordinates decouples it from the satellite layer, allowing the satellite layer to treat ground data as an independent, reliable lookup table.

## 20. Risks and Mitigation Strategies

- **Risk 1: CPCB API Rate Limits / Bans.**
  - *Mitigation:* Implement strict token bucket rate limiting in the base connector. Cache successful raw responses to disk to prevent re-fetching during development.
- **Risk 2: Sudden Data Schema Changes from Providers.**
  - *Mitigation:* The Raw Landing Zone saves the original payload. If the schema changes, the pipeline fails safely at the Parser level. The raw data is saved, and parsing logic can be updated and re-run locally without losing data.
- **Risk 3: Silent Data Corruption (Drifting sensors).**
  - *Mitigation:* The QA Engine's stuck-value and extreme-range rules flag obvious corruption. Subtle drift requires cross-validation with neighboring sensors (planned for future ML phase).
