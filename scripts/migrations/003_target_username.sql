-- 003_target_username.sql
-- User-activity monitoring: ensure every incident-bearing table can carry
-- the targeted account name. correlated_incidents already declares the
-- column in init_db.sql but older deployments may predate it; kill_chains
-- never had it. Idempotent and safe to re-run.
--
-- Apply with:
--     psql "$DATABASE_URL" -f scripts/migrations/003_target_username.sql

ALTER TABLE correlated_incidents
    ADD COLUMN IF NOT EXISTS target_username VARCHAR(100);

ALTER TABLE kill_chains
    ADD COLUMN IF NOT EXISTS target_username VARCHAR(100);

CREATE INDEX IF NOT EXISTS idx_correlated_incidents_target_username
    ON correlated_incidents(target_username);
CREATE INDEX IF NOT EXISTS idx_kill_chains_target_username
    ON kill_chains(target_username);
