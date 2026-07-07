# ──────────────────────────────────────────────────────────────────────────────
# VAYU-DRISHTI Backend — Multi-Stage Dockerfile
#
# Stage 1 (builder): Installs all Python dependencies into a virtual environment.
#   Using a dedicated builder stage prevents build tools (pip, gcc, etc.) from
#   appearing in the final image, reducing the attack surface and image size.
#
# Stage 2 (runtime): Copies only the virtual environment and application code
#   from the builder. The runtime image is based on python:3.11-slim (Debian
#   Bookworm), which is minimal but includes the libc needed by asyncpg.
#
# asyncpg requires libpq-dev at compile time (builder) and libpq5 at runtime.
# psycopg2-binary has been removed — Alembic now uses asyncpg via async engine.
#
# Security hardening:
#   - Runs as a non-root user (vayu, UID 1001) to limit container escape blast radius.
#   - No package manager cache is retained in the final image.
#   - PYTHONDONTWRITEBYTECODE prevents .pyc file accumulation.
#   - PYTHONUNBUFFERED ensures logs flush immediately (no buffering).
#
# Signal handling:
#   - ENTRYPOINT uses exec form ["/entrypoint.sh"].
#   - entrypoint.sh uses 'exec uvicorn ...' to replace the shell with uvicorn.
#   - uvicorn is PID 1; SIGTERM is delivered directly to uvicorn for graceful
#     shutdown (drains in-flight requests before exiting).
# ──────────────────────────────────────────────────────────────────────────────

# ── Stage 1: Builder ───────────────────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

# System dependencies needed to compile asyncpg (C extension requires libpq-dev)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Create an isolated virtual environment for dependency installation.
# Using a venv makes copying to the runtime stage clean and prevents conflicts.
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy dependency manifests before application code to leverage Docker layer cache:
# if requirements.txt has not changed, this RUN layer is reused and pip is skipped.
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt


# ── Stage 2: Runtime ───────────────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

LABEL maintainer="VAYU-DRISHTI Engineering Team" \
      org.opencontainers.image.title="VAYU-DRISHTI Backend API" \
      org.opencontainers.image.description="Air quality monitoring and geospatial analytics platform" \
      org.opencontainers.image.version="0.1.0"

WORKDIR /app

# Runtime system dependencies only (no build tools)
# libpq5   — asyncpg PostgreSQL client library (runtime)
# curl     — Docker HEALTHCHECK probe
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user and group for running the application.
# UID/GID 1001 — non-privileged, explicitly assigned for reproducibility.
RUN groupadd --gid 1001 vayu \
    && useradd --uid 1001 --gid vayu --shell /bin/bash --create-home vayu

# Copy the virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Python runtime optimisations
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1

# Copy application source code owned by the non-root user
COPY --chown=vayu:vayu app/ ./app/
COPY --chown=vayu:vayu alembic/ ./alembic/
COPY --chown=vayu:vayu alembic.ini .

# Copy and configure entrypoint script.
# This must be done as root (before USER switch) so chmod is permitted.
# The script uses 'exec uvicorn ...' to make uvicorn PID 1, ensuring
# SIGTERM from Docker/Kubernetes reaches uvicorn for graceful shutdown.
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch to non-root user. All subsequent RUN, CMD, and ENTRYPOINT run as vayu.
USER vayu

# Expose the API port (matches the default PORT setting)
EXPOSE 8000

# Docker HEALTHCHECK: polls the health endpoint every 30 seconds.
# A container failing 3 consecutive checks is marked 'unhealthy' and
# replaced by Docker Swarm / Kubernetes.
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Exec-form ENTRYPOINT — JSON array syntax bypasses shell interpretation.
# The entrypoint script uses 'exec' to replace itself with uvicorn (PID 1).
# Set RUN_MIGRATIONS=true to run 'alembic upgrade head' before server start.
ENTRYPOINT ["/entrypoint.sh"]
