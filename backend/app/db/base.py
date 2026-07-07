"""
SQLAlchemy declarative base and shared metadata configuration.

Design decisions:
  - Single Base class: all ORM models in the project must inherit from this
    Base. This ensures Alembic sees every table through one metadata object
    and can produce a correct, complete diff-based migration.
  - NAMING_CONVENTION: naming all constraints explicitly is required by
    Alembic to generate deterministic, repeatable constraint names across
    environments. Without this, Alembic generates migration files with
    database-generated names (e.g., "fk_1234abcd") that differ between
    development and production, causing false-positive drift detections.
  - GeoAlchemy2 integration: importing GeoAlchemy2 geometry types in model
    files (e.g., from geoalchemy2 import Geometry) automatically registers
    the PostGIS-aware type with SQLAlchemy's type system. No explicit
    dialect configuration is needed here.
  - Future models (Sensor, AirQualityReading, Station, Alert) will subclass
    Base and their tables will be auto-detected by Alembic via the import
    in alembic/env.py.
"""

from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# ── Constraint Naming Convention ───────────────────────────────────────────────
# Ensures all generated SQL objects have deterministic, readable names.
# Required for Alembic batch migrations on databases that don't support
# transactional DDL (e.g., MySQL) and good practice on all databases.
NAMING_CONVENTION: dict[str, str] = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """
    Project-wide SQLAlchemy declarative base.

    All ORM model classes must inherit from Base. The shared MetaData instance
    (with naming conventions applied) is automatically inherited.

    Example usage:

        from app.db.base import Base
        from sqlalchemy import Column, Integer, String
        from geoalchemy2 import Geography

        class Sensor(Base):
            __tablename__ = "sensors"

            id = Column(Integer, primary_key=True)
            name = Column(String(255), nullable=False)
            location = Column(Geography(geometry_type="POINT", srid=4326))
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)
