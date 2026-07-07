#!/bin/sh
# ──────────────────────────────────────────────────────────────────────────────
# VAYU-DRISHTI — Container Entrypoint
#
# Why this script exists:
#   The original Dockerfile used CMD ["sh", "-c", "uvicorn ..."], which means
#   the shell (sh) becomes PID 1 inside the container. SIGTERM sent by
#   Docker/Kubernetes during shutdown is delivered to PID 1 (sh), which does
#   NOT forward it to child processes. Uvicorn never receives SIGTERM and
#   cannot perform a graceful shutdown (drain in-flight requests, close DB
#   connections, flush log buffers).
#
#   This script uses the POSIX 'exec' builtin. 'exec' replaces the current
#   shell process with the uvicorn process — uvicorn becomes PID 1 directly.
#   SIGTERM is now delivered to uvicorn, which handles it by finishing in-
#   flight requests (up to --timeout-graceful-shutdown seconds) before exiting.
#
# Optional migration:
#   Set RUN_MIGRATIONS=true to run 'alembic upgrade head' before starting the
#   server. Useful for single-container deployments or docker-compose environments
#   where a separate migration job is not run first.
#
# Usage:
#   # In Dockerfile: ENTRYPOINT ["/entrypoint.sh"]
#   # Override workers: docker run -e WORKERS=4 vayu-api
#   # With migrations: docker run -e RUN_MIGRATIONS=true vayu-api
# ──────────────────────────────────────────────────────────────────────────────

set -e

# ── Optional: Run Alembic migrations before starting the API server ────────────
if [ "${RUN_MIGRATIONS:-false}" = "true" ]; then
    echo "[entrypoint] Running Alembic database migrations..."
    alembic upgrade head
    echo "[entrypoint] Migrations complete."
fi

# ── Start uvicorn as PID 1 ─────────────────────────────────────────────────────
# 'exec' is critical: it replaces this shell with the uvicorn process.
# Without 'exec', sh is PID 1 and uvicorn is a child that never receives
# container lifecycle signals (SIGTERM, SIGINT).
exec uvicorn app.main:app \
    --host "${HOST:-0.0.0.0}" \
    --port "${PORT:-8000}" \
    --workers "${WORKERS:-1}" \
    --no-access-log
