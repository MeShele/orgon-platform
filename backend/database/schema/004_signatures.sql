-- Signature tracking tables

-- Signature history (local tracking of sign/reject actions)
CREATE TABLE IF NOT EXISTS signature_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tx_unid TEXT NOT NULL,
    signer_address TEXT NOT NULL,
    action TEXT NOT NULL CHECK(action IN ('signed', 'rejected')),
    reason TEXT,
    signed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_signature_history_tx ON signature_history(tx_unid);
CREATE INDEX IF NOT EXISTS idx_signature_history_signer ON signature_history(signer_address);
CREATE INDEX IF NOT EXISTS idx_signature_history_date ON signature_history(signed_at);

-- Pending signatures check tracking (for detecting new pending signatures)
CREATE TABLE IF NOT EXISTS pending_signatures_checked (
    tx_unid TEXT PRIMARY KEY,
    checked_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_pending_checked_date ON pending_signatures_checked(checked_at);
