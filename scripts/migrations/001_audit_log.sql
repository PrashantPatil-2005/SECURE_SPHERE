-- 001_audit_log.sql
-- Append-only system audit log. Idempotent — safe to re-run on any
-- existing SecuriSphere database. Does not touch existing tables.
--
-- Apply with:
--     psql "$DATABASE_URL" -f scripts/migrations/001_audit_log.sql
-- or via docker:
--     docker compose exec database psql -U $POSTGRES_USER -d $POSTGRES_DB \
--         -f /docker-entrypoint-initdb.d/001_audit_log.sql

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

CREATE TABLE IF NOT EXISTS audit_log (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    actor       VARCHAR(120) NOT NULL,
    actor_type  VARCHAR(20)  NOT NULL,
    action      VARCHAR(80)  NOT NULL,
    target_type VARCHAR(40),
    target_id   VARCHAR(120),
    detail      JSONB        NOT NULL DEFAULT '{}'::jsonb,
    severity    VARCHAR(20)  NOT NULL DEFAULT 'info',
    source_ip   VARCHAR(45)
);

CREATE INDEX IF NOT EXISTS audit_log_timestamp_idx ON audit_log(timestamp DESC);
CREATE INDEX IF NOT EXISTS audit_log_action_idx    ON audit_log(action);
CREATE INDEX IF NOT EXISTS audit_log_actor_idx     ON audit_log(actor);
CREATE INDEX IF NOT EXISTS audit_log_severity_idx  ON audit_log(severity);
