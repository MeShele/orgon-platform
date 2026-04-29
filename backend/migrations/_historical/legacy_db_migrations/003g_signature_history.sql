-- Create signature_history table
CREATE TABLE IF NOT EXISTS signature_history (
    id SERIAL PRIMARY KEY,
    tx_unid VARCHAR(255) NOT NULL,
    signer_address VARCHAR(255),
    action VARCHAR(50) NOT NULL,
    reason TEXT,
    signed_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_sig_history_tx ON signature_history(tx_unid);
CREATE INDEX IF NOT EXISTS idx_sig_history_action ON signature_history(action);
CREATE INDEX IF NOT EXISTS idx_sig_history_signed ON signature_history(signed_at);
