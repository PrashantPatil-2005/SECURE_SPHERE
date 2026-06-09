-- 007_rbac_auth.sql — RBAC roles, permissions, refresh tokens, user soft-delete
-- Idempotent. Safe to re-run.

CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- ── Roles ───────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS roles (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(32) NOT NULL UNIQUE,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS permissions (
    id          SERIAL PRIMARY KEY,
    name        VARCHAR(64) NOT NULL UNIQUE,
    description TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id       INT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INT NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INT NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY (user_id, role_id)
);

-- ── Users enhancements ────────────────────────────────────────────────────────
ALTER TABLE users ADD COLUMN IF NOT EXISTS deleted_at  TIMESTAMPTZ;
ALTER TABLE users ADD COLUMN IF NOT EXISTS updated_at  TIMESTAMPTZ DEFAULT NOW();
ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active   BOOLEAN NOT NULL DEFAULT TRUE;

CREATE INDEX IF NOT EXISTS users_active_idx ON users(is_active) WHERE deleted_at IS NULL;
CREATE INDEX IF NOT EXISTS users_role_idx   ON users(role);

-- Migrate legacy role names
UPDATE users SET role = 'viewer' WHERE role IN ('user', 'readonly', 'guest');

-- ── Refresh tokens (rotation) ─────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS refresh_tokens (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      INT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token_hash   VARCHAR(64) NOT NULL,
    expires_at   TIMESTAMPTZ NOT NULL,
    revoked_at   TIMESTAMPTZ,
    replaced_by  UUID,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    ip           VARCHAR(45),
    user_agent   VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS refresh_tokens_user_idx  ON refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS refresh_tokens_hash_idx  ON refresh_tokens(token_hash);
CREATE INDEX IF NOT EXISTS refresh_tokens_exp_idx   ON refresh_tokens(expires_at);

-- ── audit_logs alias view (audit_log table from 001) ─────────────────────────
-- Application uses audit_log; this documents the canonical name for RBAC docs.
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.tables
        WHERE table_name = 'audit_logs'
    ) THEN
        CREATE VIEW audit_logs AS SELECT * FROM audit_log;
    END IF;
END $$;

-- ── Seed roles ──────────────────────────────────────────────────────────────
INSERT INTO roles (name, description) VALUES
    ('admin',   'Full platform control — users, settings, audit'),
    ('analyst', 'Investigate incidents, campaigns, MITRE, reports'),
    ('viewer',  'Read-only dashboards, topology, incidents')
ON CONFLICT (name) DO NOTHING;

-- ── Seed permissions ──────────────────────────────────────────────────────────
INSERT INTO permissions (name, description) VALUES
    ('users.manage',       'Create, update, deactivate users'),
    ('incidents.read',     'View incidents and kill chains'),
    ('incidents.write',    'Triage and update incidents'),
    ('campaigns.read',     'View attack campaigns'),
    ('dashboard.read',     'View SOC dashboards'),
    ('topology.read',      'View service dependency graphs'),
    ('mitre.read',         'View MITRE mappings'),
    ('reports.generate',   'Generate AI / analyst reports'),
    ('audit.read',         'View system audit logs'),
    ('system.manage',      'Change system configuration'),
    ('alerts.manage',      'Configure alert channels'),
    ('evaluation.read',    'View MTTD evaluation results'),
    ('replay.read',        'Access attack replay')
ON CONFLICT (name) DO NOTHING;

-- ── Role → permission mapping ─────────────────────────────────────────────────
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r, permissions p
WHERE r.name = 'admin'
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r
JOIN permissions p ON p.name IN (
    'incidents.read','incidents.write','campaigns.read','dashboard.read',
    'topology.read','mitre.read','reports.generate','evaluation.read','replay.read'
)
WHERE r.name = 'analyst'
ON CONFLICT DO NOTHING;

INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r
JOIN permissions p ON p.name IN (
    'dashboard.read','topology.read','incidents.read'
)
WHERE r.name = 'viewer'
ON CONFLICT DO NOTHING;

-- Sync user_roles from users.role column
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id FROM users u
JOIN roles r ON r.name = u.role
WHERE u.deleted_at IS NULL
ON CONFLICT DO NOTHING;
