-- 006_audit_log.sql
-- Audit log for tracking all user actions

CREATE TABLE IF NOT EXISTS audit_log (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,  -- NULL for now (single-user system)
    action TEXT NOT NULL,  -- create/update/delete/view/sign/reject
    resource_type TEXT,  -- wallet/transaction/contact/scheduled/signature
    resource_id TEXT,
    details JSONB,
    ip_address TEXT,
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_audit_log_action ON audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_created_at ON audit_log(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_log_resource ON audit_log(resource_type, resource_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id);

-- Add some example entries (for testing)
INSERT INTO audit_log (action, resource_type, resource_id, details)
VALUES 
    ('create', 'wallet', '1', '{"name": "Test Wallet", "network": "ethereum"}'),
    ('sign', 'transaction', 'tx123', '{"status": "signed"}'),
    ('create', 'contact', '1', '{"name": "Alice", "address": "0x123..."}')
ON CONFLICT DO NOTHING;

COMMENT ON TABLE audit_log IS 'Activity log for all user actions';
COMMENT ON COLUMN audit_log.action IS 'Action type: create/update/delete/view/sign/reject';
COMMENT ON COLUMN audit_log.resource_type IS 'Resource type: wallet/transaction/contact/scheduled/signature';
COMMENT ON COLUMN audit_log.details IS 'JSON details of the action';
