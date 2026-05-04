-- 004_campaigns.sql — Campaign Aggregation Layer
--
-- Adds the `campaigns` table and back-links it from `correlated_incidents`
-- and `kill_chains`. A campaign groups multiple incidents from the same
-- attacker into a single analyst-facing record so SecuriSphere emits one
-- evolving notification per attacker, not one per rule fire.
--
-- Idempotent: safe to re-apply on existing deployments. The
-- CampaignAggregator also runs the same DDL at boot via `_ensure_schema()`,
-- but this file is the canonical migration for fresh installs and CI.

BEGIN;

CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id        UUID PRIMARY KEY,
    actor_id           VARCHAR(100) NOT NULL,
    source_ip          VARCHAR(45),
    target_usernames   TEXT[]       NOT NULL DEFAULT '{}',
    incident_ids       UUID[]       NOT NULL DEFAULT '{}',
    incident_count     INTEGER      NOT NULL DEFAULT 0,
    service_path       TEXT[]       NOT NULL DEFAULT '{}',
    kill_chain_steps   JSONB        NOT NULL DEFAULT '[]',
    mitre_techniques   TEXT[]       NOT NULL DEFAULT '{}',
    layers_involved    TEXT[]       NOT NULL DEFAULT '{}',
    stages_seen        TEXT[]       NOT NULL DEFAULT '{}',
    severity           VARCHAR(20)  NOT NULL DEFAULT 'low',
    max_confidence     FLOAT        NOT NULL DEFAULT 0,
    first_event_at     TIMESTAMPTZ  NOT NULL,
    last_event_at      TIMESTAMPTZ  NOT NULL,
    status             VARCHAR(20)  NOT NULL DEFAULT 'active',
    closed_reason      VARCHAR(40),
    closed_at          TIMESTAMPTZ,
    discord_message_id VARCHAR(40),
    discord_channel_id VARCHAR(40),
    created_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

-- Invariant: at most one ACTIVE campaign per actor at any time.
-- Enforced via partial unique index so concurrent engine workers cannot
-- create duplicate campaigns for the same attacker (second worker hits
-- UniqueViolation, then re-reads + merges).
CREATE UNIQUE INDEX IF NOT EXISTS uq_campaign_active_actor
    ON campaigns (actor_id) WHERE status = 'active';

CREATE INDEX IF NOT EXISTS idx_campaigns_status_last
    ON campaigns (status, last_event_at DESC);
CREATE INDEX IF NOT EXISTS idx_campaigns_source_ip
    ON campaigns (source_ip);
CREATE INDEX IF NOT EXISTS idx_campaigns_severity
    ON campaigns (severity);
CREATE INDEX IF NOT EXISTS idx_campaigns_techniques_gin
    ON campaigns USING GIN (mitre_techniques);
CREATE INDEX IF NOT EXISTS idx_campaigns_steps_gin
    ON campaigns USING GIN (kill_chain_steps);

-- Back-links from existing tables. ON DELETE SET NULL so dropping a
-- campaign never cascades into incident loss.
ALTER TABLE correlated_incidents
    ADD COLUMN IF NOT EXISTS campaign_id UUID
        REFERENCES campaigns(campaign_id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_incidents_campaign
    ON correlated_incidents (campaign_id);

ALTER TABLE kill_chains
    ADD COLUMN IF NOT EXISTS campaign_id UUID
        REFERENCES campaigns(campaign_id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_kc_campaign
    ON kill_chains (campaign_id);

COMMIT;
