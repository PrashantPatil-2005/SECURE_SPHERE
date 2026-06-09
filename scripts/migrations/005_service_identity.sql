-- 005_service_identity.sql — Service-centric correlation fields
-- Idempotent; safe to re-apply.

BEGIN;

-- security_events
ALTER TABLE security_events ADD COLUMN IF NOT EXISTS source_service_name VARCHAR(100);
ALTER TABLE security_events ADD COLUMN IF NOT EXISTS destination_service_name VARCHAR(100);
ALTER TABLE security_events ADD COLUMN IF NOT EXISTS workload_id VARCHAR(64);
ALTER TABLE security_events ADD COLUMN IF NOT EXISTS correlation_key VARCHAR(200);

CREATE INDEX IF NOT EXISTS idx_events_correlation_key ON security_events(correlation_key);
CREATE INDEX IF NOT EXISTS idx_events_source_service ON security_events(source_service_name);

-- correlated_incidents
ALTER TABLE correlated_incidents ADD COLUMN IF NOT EXISTS source_service_name VARCHAR(100);
ALTER TABLE correlated_incidents ADD COLUMN IF NOT EXISTS destination_service_name VARCHAR(100);
ALTER TABLE correlated_incidents ADD COLUMN IF NOT EXISTS service_path TEXT[] DEFAULT '{}';
ALTER TABLE correlated_incidents ADD COLUMN IF NOT EXISTS correlation_key VARCHAR(200);

CREATE INDEX IF NOT EXISTS idx_incidents_correlation_key ON correlated_incidents(correlation_key);

-- risk_scores: entity_type + entity_key (service-first)
ALTER TABLE risk_scores ADD COLUMN IF NOT EXISTS entity_type VARCHAR(20) DEFAULT 'ip';
ALTER TABLE risk_scores ADD COLUMN IF NOT EXISTS entity_key VARCHAR(200);

UPDATE risk_scores
SET entity_key = entity_ip, entity_type = 'ip'
WHERE entity_key IS NULL AND entity_ip IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_risk_entity_key ON risk_scores(entity_key)
    WHERE entity_key IS NOT NULL;

-- baseline_metrics
ALTER TABLE baseline_metrics ADD COLUMN IF NOT EXISTS entity_type VARCHAR(20) DEFAULT 'ip';
ALTER TABLE baseline_metrics ADD COLUMN IF NOT EXISTS entity_key VARCHAR(200);

UPDATE baseline_metrics
SET entity_key = entity_ip, entity_type = 'ip'
WHERE entity_key IS NULL AND entity_ip IS NOT NULL;

-- campaigns
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS source_service_name VARCHAR(100);
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS actor_type VARCHAR(20) DEFAULT 'ip';

CREATE INDEX IF NOT EXISTS idx_campaigns_actor_type_id ON campaigns(actor_type, actor_id);

COMMIT;
