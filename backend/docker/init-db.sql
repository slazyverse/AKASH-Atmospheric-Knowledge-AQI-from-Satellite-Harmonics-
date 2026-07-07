-- VAYU-DRISHTI Database Initialisation Script
-- Runs once on fresh PostgreSQL container creation.
-- Enables the PostGIS extension required for geospatial sensor data.

-- Enable PostGIS (geometry/geography types, spatial indexes, spatial functions)
CREATE EXTENSION IF NOT EXISTS postgis;

-- Enable PostGIS topology (optional — for administrative boundary data)
CREATE EXTENSION IF NOT EXISTS postgis_topology;

-- Enable uuid-ossp for UUID primary key generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Verify installation
SELECT PostGIS_Version();
