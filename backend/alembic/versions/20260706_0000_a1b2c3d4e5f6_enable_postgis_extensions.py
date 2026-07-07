"""
Enable PostGIS and supporting PostgreSQL extensions.

Revision ID: a1b2c3d4e5f6
Revises:     (root — no prior migration)
Created:     2026-07-06 00:00

Why this migration exists:
  PostGIS extensions were previously enabled via a Docker Compose volume
  mount (docker/init-db.sql → /docker-entrypoint-initdb.d/). That approach
  was not version-controlled in the migration history and ran only on
  fresh container creation, making it invisible to Alembic's state tracking.

  Moving extension setup into Alembic ensures:
    1. The enabled extensions are recorded in Alembic's revision chain.
    2. The setup is idempotent (IF NOT EXISTS) and runs safely on any
       existing database that may already have the extensions.
    3. CI, staging, and production environments all follow the same
       migration path — no manual SQL needed after 'alembic upgrade head'.

Extensions enabled:
  - postgis:          Core PostGIS extension. Provides geometry/geography
                      column types, spatial indexes, and ST_* functions.
                      Required for sensor location storage and spatial queries.
  - postgis_topology: Administrative boundary and topology data support.
                      Not required for Day 1-2 but enabled now to avoid
                      a future destructive migration.
  - uuid-ossp:        UUID generation functions (uuid_generate_v4()).
                      Required by ORM models that use UUID primary keys.

Downgrade:
  Extensions are intentionally NOT dropped on downgrade. Dropping postgis
  would cascade-drop ALL geometry columns and spatial indexes in the database,
  which is a destructive, irreversible operation in a production system.
  If extension removal is truly required, it must be done manually with a
  reviewed, explicit DBA procedure.
"""

from alembic import op

# ── Migration metadata ─────────────────────────────────────────────────────────
revision: str = "a1b2c3d4e5f6"
down_revision: str | None = None   # Root migration — no prior revision
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Enable PostGIS and supporting extensions. Idempotent (IF NOT EXISTS)."""

    # PostGIS core — geometry/geography types, spatial indexes, ST_* functions
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis")

    # PostGIS topology — boundary and topology data support
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology")

    # uuid-ossp — UUID generation (uuid_generate_v4() for primary keys)
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')


def downgrade() -> None:
    """
    Intentionally a no-op.

    Dropping PostGIS cascades to all geometry columns and spatial indexes.
    This is a destructive action that must never be performed automatically.
    If extension removal is required, execute manually after a full data review.
    """
