-- 006_kill_chain_graph.sql — Graph structure for D3 kill-chain visualization

BEGIN;

ALTER TABLE kill_chains ADD COLUMN IF NOT EXISTS graph JSONB NOT NULL DEFAULT '{"nodes":[],"edges":[]}';
ALTER TABLE kill_chains ADD COLUMN IF NOT EXISTS correlation_key VARCHAR(200);
ALTER TABLE kill_chains ADD COLUMN IF NOT EXISTS source_service_name VARCHAR(100);
ALTER TABLE kill_chains ADD COLUMN IF NOT EXISTS narrative TEXT;

CREATE INDEX IF NOT EXISTS idx_kc_correlation_key ON kill_chains(correlation_key);

COMMIT;
