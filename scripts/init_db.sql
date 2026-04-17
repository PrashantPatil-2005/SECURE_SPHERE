-- SecuriSphere Database Schema v1.0

CREATE TABLE IF NOT EXISTS security_events (
    id SERIAL PRIMARY KEY,
    event_id UUID NOT NULL UNIQUE,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    source_layer VARCHAR(20) NOT NULL,
    source_monitor VARCHAR(50) NOT NULL,
    event_category VARCHAR(50) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    severity_level VARCHAR(20) NOT NULL,
    severity_score INTEGER NOT NULL,
    source_ip VARCHAR(45),
    source_container_id VARCHAR(64),
    source_container_name VARCHAR(100),
    target_ip VARCHAR(45),
    target_port INTEGER,
    target_service VARCHAR(100),
    detection_method VARCHAR(100),
    confidence FLOAT,
    description TEXT,
    evidence JSONB,
    correlation_tags TEXT[],
    mitre_technique VARCHAR(100),
    raw_data_reference TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS correlated_incidents (
    id SERIAL PRIMARY KEY,
    incident_id UUID NOT NULL UNIQUE,
    incident_type VARCHAR(50) NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    severity VARCHAR(20) NOT NULL,
    confidence FLOAT,
    source_ip VARCHAR(45),
    target_username VARCHAR(100),
    correlated_event_ids UUID[],
    layers_involved TEXT[],
    event_types TEXT[],
    mitre_techniques TEXT[],
    recommended_actions TEXT[],
    risk_score_at_time INTEGER,
    time_span_seconds FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS risk_scores (
    id SERIAL PRIMARY KEY,
    entity_ip VARCHAR(45) NOT NULL,
    current_score INTEGER DEFAULT 0,
    peak_score INTEGER DEFAULT 0,
    threat_level VARCHAR(20) DEFAULT 'normal',
    layers_involved TEXT[],
    event_count INTEGER DEFAULT 0,
    last_event_type VARCHAR(50),
    last_updated TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS baseline_metrics (
    id SERIAL PRIMARY KEY,
    entity_ip VARCHAR(45) NOT NULL,
    metric_name VARCHAR(50) NOT NULL,
    metric_value FLOAT NOT NULL,
    rolling_mean FLOAT,
    rolling_stddev FLOAT,
    sample_count INTEGER DEFAULT 0,
    window_start TIMESTAMP WITH TIME ZONE,
    window_end TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes
CREATE INDEX idx_events_timestamp ON security_events(timestamp);
CREATE INDEX idx_events_source_ip ON security_events(source_ip);
CREATE INDEX idx_events_event_type ON security_events(event_type);
CREATE INDEX idx_events_source_layer ON security_events(source_layer);
CREATE INDEX idx_events_severity ON security_events(severity_level);

CREATE INDEX idx_incidents_timestamp ON correlated_incidents(created_at);
CREATE INDEX idx_incidents_severity ON correlated_incidents(severity);
CREATE INDEX idx_incidents_source_ip ON correlated_incidents(source_ip);

CREATE INDEX idx_risk_entity ON risk_scores(entity_ip);

CREATE INDEX idx_baseline_entity ON baseline_metrics(entity_ip, metric_name);


-- Target Application Tables (for API Server)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) DEFAULT 'user',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ─── Kill Chain Reconstruction Table ────────────────────────────────────────
-- Stores ordered attack steps, service traversal paths, and MTTD measurements
-- as produced by engine/kill_chain/reconstructor.py
CREATE TABLE IF NOT EXISTS kill_chains (
    id               SERIAL PRIMARY KEY,
    incident_id      UUID   NOT NULL UNIQUE,
    incident_type    VARCHAR(80),
    source_ip        VARCHAR(45),
    -- JSONB array of {service_name, event_type, timestamp, severity, mitre, source_ip, layer}
    steps            JSONB  NOT NULL DEFAULT '[]',
    -- Ordered list of service names traversed by the attack
    service_path     TEXT[] NOT NULL DEFAULT '{}',
    first_service    VARCHAR(100),
    last_service     VARCHAR(100),
    mitre_techniques TEXT[] NOT NULL DEFAULT '{}',
    -- Timing fields
    first_event_at   TIMESTAMP WITH TIME ZONE,
    detected_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    duration_seconds FLOAT,
    -- mttd_seconds = detected_at − first_event_at (precise measurement)
    mttd_seconds     FLOAT,
    severity         VARCHAR(20),
    created_at       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kc_incident_id  ON kill_chains(incident_id);
CREATE INDEX IF NOT EXISTS idx_kc_source_ip    ON kill_chains(source_ip);
CREATE INDEX IF NOT EXISTS idx_kc_detected_at  ON kill_chains(detected_at);
CREATE INDEX IF NOT EXISTS idx_kc_incident_type ON kill_chains(incident_type);

-- ─── Topology Snapshot Table ──────────────────────────────────────────────
-- Optional: persist topology snapshots for historical analysis
CREATE TABLE IF NOT EXISTS topology_snapshots (
    id           SERIAL PRIMARY KEY,
    snapshot     JSONB  NOT NULL,
    service_count INTEGER,
    captured_at  TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_topo_captured_at ON topology_snapshots(captured_at);

-- ─── Registered Sites (Browser Monitor / Phase 1) ──────────────────────────
-- Sites that embed the ShopSphere browser agent (static/agent.js) must be
-- registered here before the browser-monitor (:5090) will accept events
-- from them. site_id = first 8 hex chars of sha256(url + name).
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS registered_sites (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        TEXT NOT NULL,
    url         TEXT NOT NULL,
    email       TEXT NOT NULL,
    site_id     TEXT UNIQUE NOT NULL,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_registered_sites_site_id ON registered_sites(site_id);

-- Seed Data
INSERT INTO users (username, email, password_hash, role) VALUES
('admin', 'admin@example.com', 'admin123', 'admin'),
('user1', 'user1@example.com', 'password123', 'user'),
('user2', 'user2@example.com', 'securepass', 'user')
ON CONFLICT DO NOTHING;
