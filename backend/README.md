# VAYU-DRISHTI Backend API

> **Version:** 0.1.0 | **Status:** Day 1 — Foundation + Audit Fixes Applied | **Runtime:** Python 3.11+

Air quality monitoring and geospatial analytics platform — FastAPI backend.

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Directory Structure](#directory-structure)
3. [Prerequisites](#prerequisites)
4. [Local Setup (Without Docker)](#local-setup-without-docker)
5. [Local Setup (With Docker)](#local-setup-with-docker)
6. [Environment Variables](#environment-variables)
7. [Running the API](#running-the-api)
8. [Database Migrations](#database-migrations)
9. [Running Tests](#running-tests)
10. [API Endpoints](#api-endpoints)
11. [Code Quality](#code-quality)
12. [Architectural Decisions](#architectural-decisions)

---

## Architecture Overview

```
HTTP Request
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│  FastAPI Application (app/main.py)                          │
│  ┌─────────────────┐   ┌─────────────────────────────────┐  │
│  │  CORS Middleware │   │  Request-ID Middleware          │  │
│  └─────────────────┘   └─────────────────────────────────┘  │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  API Router  /api/v1/                               │    │
│  │  ├── /health   → endpoints/health.py                │    │
│  │  └── /version  → endpoints/version.py               │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────┐   │
│  │  core/config  │  │ core/logging  │  │core/exceptions│   │
│  └───────────────┘  └───────────────┘  └───────────────┘   │
│                                                             │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Database Layer                                     │    │
│  │  db/session.py → AsyncEngine → asyncpg → PostgreSQL │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## Directory Structure

```
backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── router.py              # Aggregated v1 router
│   │       └── endpoints/
│   │           ├── health.py          # GET /api/v1/health
│   │           └── version.py         # GET /api/v1/version
│   ├── core/
│   │   ├── config.py                  # Pydantic Settings (env vars)
│   │   ├── logging.py                 # structlog JSON configuration
│   │   └── exceptions.py             # Domain exceptions + handlers
│   ├── db/
│   │   ├── base.py                    # SQLAlchemy declarative base
│   │   ├── session.py                 # Async engine + session factory
│   │   └── models/                    # ORM models (Day 2+)
│   ├── schemas/
│   │   ├── health.py                  # HealthResponse schema
│   │   └── version.py                 # VersionResponse schema
│   ├── services/
│   │   └── base.py                    # Abstract service interface
│   └── main.py                        # FastAPI application factory
├── alembic/
│   ├── env.py                         # Async Alembic environment
│   └── versions/                      # Migration scripts (generated)
├── docker/
│   └── init-db.sql                    # PostGIS extension init
├── tests/
│   ├── conftest.py                    # Shared pytest fixtures
│   └── test_health.py                 # Health + version tests
├── alembic.ini                        # Alembic configuration
├── docker-compose.yml                 # Local development stack
├── Dockerfile                         # Multi-stage production image
├── pyproject.toml                     # Build + lint + test config
├── requirements.txt                   # Production dependencies
├── requirements-dev.txt               # Development dependencies
└── .env.example                       # Environment variable template
```

---

## Prerequisites

| Tool | Version | Purpose |
|------|---------|---------|
| Python | ≥ 3.11 | Runtime |
| pip | ≥ 23.0 | Dependency management |
| Docker Desktop | ≥ 24.0 | Container runtime |
| Docker Compose | v2 (bundled with Docker Desktop) | Local stack orchestration |
| PostgreSQL + PostGIS | 16 + 3.4 (via Docker) | Database |

---

## Local Setup (Without Docker)

### 1. Create a virtual environment

```bash
cd backend/
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt -r requirements-dev.txt
```

### 3. Configure environment

```bash
cp .env.example .env
# Edit .env and fill in POSTGRES_PASSWORD and SECRET_KEY
```

Generate a SECRET_KEY:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 4. Start PostgreSQL + PostGIS locally (requires Docker)

```bash
docker compose up db -d
```

### 5. Run database migrations

```bash
alembic upgrade head
```

### 6. Start the API server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API is now available at **http://localhost:8000**

---

## Local Setup (With Docker)

### 1. Configure environment

```bash
cp .env.example .env
# Edit .env — at minimum set POSTGRES_PASSWORD and SECRET_KEY
```

### 2. Start the full stack

```bash
docker compose up -d
```

This starts:
- `vayu_db` — PostgreSQL 16 + PostGIS 3.4 on port **5432**
- `vayu_api` — FastAPI API on port **8000**

### 3. Apply migrations

```bash
docker compose exec api alembic upgrade head
```

### 4. View logs

```bash
docker compose logs -f api
docker compose logs -f db
```

### 5. Stop the stack

```bash
docker compose down        # Stop containers, preserve data volume
docker compose down -v     # Stop containers AND delete data volume
```

---

## Environment Variables

All variables are documented in [`.env.example`](.env.example). Key variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | ✅ | — | Min 32-char secret. Generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `POSTGRES_PASSWORD` | ✅ | — | Database user password. Special characters are URL-encoded automatically. |
| `ENVIRONMENT` | — | `development` | `development` \| `staging` \| `production` |
| `DEBUG` | — | `false` | Enable SQLAlchemy query logging. Must be `false` in production |
| `LOG_FORMAT` | — | `json` | `json` for aggregators; `console` for local development |
| `LOG_LEVEL` | — | `INFO` | `DEBUG` \| `INFO` \| `WARNING` \| `ERROR` \| `CRITICAL` |
| `PORT` | — | `8000` | API server port |
| `POSTGRES_HOST` | — | `localhost` | Use `db` when running with docker-compose |
| `RUN_MIGRATIONS` | — | `false` | Set to `true` to run `alembic upgrade head` before server starts (entrypoint.sh) |

---

## Running the API

### Development (with auto-reload)

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production (multi-worker)

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4 --no-access-log
```

### Interactive API Documentation

Available only in `development` and `staging` environments:

| URL | Description |
|-----|-------------|
| http://localhost:8000/docs | Swagger UI (interactive) |
| http://localhost:8000/redoc | ReDoc (read-only) |
| http://localhost:8000/openapi.json | Raw OpenAPI schema |

---

## Database Migrations

VAYU-DRISHTI uses Alembic for schema-as-code database migrations.
Alembic runs via an **async engine** (asyncpg) — no psycopg2 is required.

```bash
# Apply all pending migrations (includes PostGIS extension setup)
alembic upgrade head

# Roll back the last migration
alembic downgrade -1

# Generate a new migration from ORM model changes
alembic revision --autogenerate -m "add sensors table"

# Show migration history
alembic history

# Show currently applied revision
alembic current

# Preview the SQL without applying (offline mode)
alembic upgrade head --sql
```

> **PostGIS:** Extensions (`postgis`, `postgis_topology`, `uuid-ossp`) are enabled by the
> first migration (`alembic/versions/20260706_0000_*_enable_postgis_extensions.py`).
> This is idempotent (`IF NOT EXISTS`) and replaces the previous `docker/init-db.sql` approach.
>
> **Important:** After creating new ORM models in `app/db/models/`, import them in
> `alembic/env.py` before running `--autogenerate`.

### Startup sequence

1. Start the database: `docker compose up db -d`
2. Wait for the DB healthcheck to pass (or `docker compose up -d`)
3. Run migrations: `docker compose exec api alembic upgrade head`
4. The API is ready to serve traffic.

Alternatively, set `RUN_MIGRATIONS=true` in `.env` and the entrypoint script
will run `alembic upgrade head` automatically before starting uvicorn.

---

## Running Tests

```bash
# Run all unit tests (no live DB required)
pytest

# Run with coverage report
pytest --cov=app --cov-report=term-missing

# Run only unit tests (exclude integration tests)
pytest -m "not integration"

# Run integration tests (requires live PostgreSQL)
pytest -m integration

# Run a specific test file
pytest tests/test_health.py -v
```

---

## API Endpoints

### Day 1 (Available Now)

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `GET` | `/` | Service discovery metadata | None |
| `GET` | `/api/v1/health` | Service health check | None |
| `GET` | `/api/v1/version` | Application version metadata | None |

### Example Responses

**GET /api/v1/health**
```json
{
  "status": "healthy",
  "timestamp": "2026-07-06T18:00:00Z",
  "environment": "development",
  "components": {
    "api": {
      "status": "healthy",
      "detail": "Request handler reachable."
    },
    "database": {
      "status": "healthy",
      "latency_ms": 3.2,
      "detail": "Connection pool healthy."
    }
  }
}
```

**GET /api/v1/version**
```json
{
  "name": "VAYU-DRISHTI",
  "version": "0.1.0",
  "api_version": "v1",
  "environment": "development",
  "python_version": "3.11.9"
}
```

---

## Code Quality

```bash
# Lint (ruff)
ruff check app/ tests/

# Auto-fix lint issues
ruff check --fix app/ tests/

# Format (black)
black app/ tests/

# Type check (mypy)
mypy app/

# Run all quality checks
ruff check app/ tests/ && black --check app/ tests/ && mypy app/
```

---

## Architectural Decisions

| Decision | Rationale |
|----------|-----------|
| **FastAPI** | Async-native, OpenAPI auto-docs, Pydantic v2 integration, DI container |
| **asyncpg only** | Single PostgreSQL driver for runtime AND Alembic migrations (via async env.py). psycopg2 eliminated. |
| **PostGIS** | Geospatial sensor data requires geography types, spatial indexes, ST_ functions |
| **Pydantic Settings + quote_plus** | Type-safe env vars; `urllib.parse.quote_plus` encodes credentials to prevent URL corruption from special characters |
| **structlog + uvicorn unification** | Uvicorn handlers cleared; `propagate=True` routes all logs (app + server) through one structlog JSON pipeline |
| **Alembic async env** | `asyncio.run()` + `create_async_engine` + `connection.run_sync()` — migrations use asyncpg, NullPool for CLI safety |
| **PostGIS in Alembic migration** | Extension setup is version-controlled, idempotent (`IF NOT EXISTS`), and runs in all environments identically |
| **RequestValidationError handler** | Normalises FastAPI's default 422 body into our RFC 7807 error envelope for consistent client parsing |
| **entrypoint.sh + exec** | Shell `exec` replaces itself with uvicorn, making uvicorn PID 1. SIGTERM from Docker/Kubernetes goes directly to uvicorn for graceful shutdown |
| **`init: true` in Compose** | Docker's tini init (PID 1) reaps zombies and forwards signals — belt-and-suspenders with the `exec` entrypoint |
| **Multi-stage Docker** | Builder compiles asyncpg (C extension); runtime image has no build tools |
| **API versioning `/api/v1/`** | Breaking changes can be added as `/api/v2/` without disrupting consumers |
| **Non-root Docker user (1001)** | Limits blast radius of a container escape |
| **`expire_on_commit=False`** | Prevents lazy-load errors in async SQLAlchemy sessions after commit |
| **`pool_pre_ping=True`** | Detects and discards stale DB connections before use |
| **Health via `engine.connect()`** | Direct engine probe catches all failure modes (pool, host, auth) inside the handler — no more unhandled 500s |
| **Application factory pattern** | Separates construction from module-level app; enables isolated test instances |
| **`services/base.py`** | SOLID abstract service interface for ML, sensor, and analytics services (Day 4+) |

---

*Maintained by the VAYU-DRISHTI Engineering Team.*
*Last updated: 2026-07-07 — Day 1 Audit Fixes Applied.*
