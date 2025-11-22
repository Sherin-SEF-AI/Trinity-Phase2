-- Trinity Phase 2 - PostgreSQL Initialization Script
-- Creates database schema and initial configuration

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- For faster text search

-- Create schema
CREATE SCHEMA IF NOT EXISTS trinity;

-- Set search path
SET search_path TO trinity, public;

-- Create enum types
CREATE TYPE severity_level AS ENUM ('INFO', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL');
CREATE TYPE session_status AS ENUM ('PENDING', 'RECORDING', 'PAUSED', 'COMPLETED', 'FAILED');
CREATE TYPE event_type AS ENUM (
    'NEAR_MISS',
    'HIGH_SPEED_APPROACH',
    'HARD_BRAKING',
    'LANE_CHANGE',
    'SHARP_TURN',
    'SPEED_VIOLATION',
    'PEDESTRIAN_INTERACTION',
    'CUSTOM'
);

-- Performance indexes will be created by SQLAlchemy models
-- This script just ensures the database and extensions are ready

-- Grant permissions
GRANT ALL PRIVILEGES ON SCHEMA trinity TO trinity_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA trinity TO trinity_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA trinity TO trinity_user;

-- Create application user if doesn't exist (for compatibility)
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'trinity_app') THEN
        CREATE ROLE trinity_app WITH LOGIN PASSWORD 'trinity_app_password';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE trinity_av_testing TO trinity_app;
GRANT USAGE ON SCHEMA trinity TO trinity_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA trinity TO trinity_app;

-- Logging
\echo 'Trinity Phase 2 database initialized successfully'
