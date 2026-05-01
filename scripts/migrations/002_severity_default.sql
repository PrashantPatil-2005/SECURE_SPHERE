-- 002_severity_default.sql
-- Make severity non-nullable on incident-bearing tables. Idempotent and
-- safe to re-run on any existing SecuriSphere database.
--
-- Rationale: every kill chain incident must carry a severity label so the
-- frontend never falls back to "undefined". A multi-stage correlated
-- incident is "high" by definition; we floor at that.
--
-- Apply with:
--     psql "$DATABASE_URL" -f scripts/migrations/002_severity_default.sql

-- ── correlated_incidents ─────────────────────────────────────────────────
ALTER TABLE correlated_incidents
    ADD COLUMN IF NOT EXISTS severity VARCHAR(20);
UPDATE correlated_incidents
   SET severity = 'high'
 WHERE severity IS NULL OR severity = '';
ALTER TABLE correlated_incidents
    ALTER COLUMN severity SET DEFAULT 'high';
ALTER TABLE correlated_incidents
    ALTER COLUMN severity SET NOT NULL;

-- ── kill_chains ──────────────────────────────────────────────────────────
ALTER TABLE kill_chains
    ADD COLUMN IF NOT EXISTS severity VARCHAR(20);
UPDATE kill_chains
   SET severity = 'high'
 WHERE severity IS NULL OR severity = '';
ALTER TABLE kill_chains
    ALTER COLUMN severity SET DEFAULT 'high';
ALTER TABLE kill_chains
    ALTER COLUMN severity SET NOT NULL;

CREATE INDEX IF NOT EXISTS idx_correlated_incidents_severity ON correlated_incidents(severity);
CREATE INDEX IF NOT EXISTS idx_kill_chains_severity          ON kill_chains(severity);
