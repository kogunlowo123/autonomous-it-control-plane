-- =============================================================================
-- Agent Session Audit Ledger Schema
-- Immutable audit trail for all agent actions and identity events
-- =============================================================================

CREATE SCHEMA IF NOT EXISTS identity;

-- Agent credential registry
CREATE TABLE IF NOT EXISTS identity.agent_credentials (
    agent_id        VARCHAR(255) PRIMARY KEY,
    agent_type      VARCHAR(100) NOT NULL,
    tier            VARCHAR(10) NOT NULL,
    public_key      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,
    revoked_at      TIMESTAMPTZ,
    metadata        JSONB DEFAULT '{}'
);

-- Session audit ledger (append-only, never update/delete)
CREATE TABLE IF NOT EXISTS identity.session_ledger (
    id              BIGSERIAL PRIMARY KEY,
    session_id      UUID NOT NULL,
    agent_id        VARCHAR(255) NOT NULL,
    agent_type      VARCHAR(100) NOT NULL,
    action          VARCHAR(255) NOT NULL,
    resource_type   VARCHAR(100),
    resource_id     VARCHAR(255),
    outcome         VARCHAR(50) NOT NULL,  -- success, failure, escalated, denied
    tier_claimed    VARCHAR(10),
    tenant_id       VARCHAR(255) NOT NULL DEFAULT 'default',
    ip_address      INET,
    request_id      UUID,
    event_data      JSONB DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for efficient querying
CREATE INDEX IF NOT EXISTS idx_session_ledger_session_id
    ON identity.session_ledger(session_id);
CREATE INDEX IF NOT EXISTS idx_session_ledger_agent_id
    ON identity.session_ledger(agent_id);
CREATE INDEX IF NOT EXISTS idx_session_ledger_created_at
    ON identity.session_ledger(created_at);
CREATE INDEX IF NOT EXISTS idx_session_ledger_resource
    ON identity.session_ledger(resource_type, resource_id);

-- Token TTL policies
CREATE TABLE IF NOT EXISTS identity.token_ttl_policies (
    tier            VARCHAR(10) PRIMARY KEY,
    ttl_seconds     INTEGER NOT NULL,
    max_renewals    INTEGER NOT NULL DEFAULT 0,
    description     TEXT
);

INSERT INTO identity.token_ttl_policies (tier, ttl_seconds, max_renewals, description)
VALUES
    ('T1', 3600,   3, 'T1 autonomous agent tokens — 1 hour, up to 3 renewals'),
    ('T2', 1800,   0, 'T2 human-approval agent tokens — 30 min, no renewal'),
    ('T3',  900,   0, 'T3 emergency tokens — 15 min, no renewal')
ON CONFLICT (tier) DO UPDATE SET
    ttl_seconds  = EXCLUDED.ttl_seconds,
    max_renewals = EXCLUDED.max_renewals,
    description  = EXCLUDED.description;

-- Grant minimal permissions (run as superuser during setup)
-- GRANT USAGE ON SCHEMA identity TO itsm_app;
-- GRANT SELECT, INSERT ON identity.session_ledger TO itsm_app;
-- GRANT SELECT, INSERT, UPDATE ON identity.agent_credentials TO itsm_app;
