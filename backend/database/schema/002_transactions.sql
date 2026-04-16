-- Transaction history and signature status
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    safina_id INTEGER,
    tx_hash TEXT,
    token TEXT NOT NULL,
    token_name TEXT,
    to_addr TEXT NOT NULL,
    value TEXT NOT NULL,
    value_hex TEXT,
    unid TEXT UNIQUE NOT NULL,
    init_ts INTEGER,
    min_sign INTEGER,
    status TEXT DEFAULT 'pending',  -- pending, signed, rejected, confirmed, failed
    info TEXT,
    wallet_name TEXT,
    network INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    synced_at DATETIME
);

CREATE TABLE IF NOT EXISTS tx_signatures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tx_unid TEXT NOT NULL REFERENCES transactions(unid),
    ec_address TEXT NOT NULL,
    sig_type TEXT NOT NULL,  -- 'wait' or 'signed'
    ec_sign TEXT,
    signed_at DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_transactions_unid ON transactions(unid);
CREATE INDEX IF NOT EXISTS idx_transactions_status ON transactions(status);
CREATE INDEX IF NOT EXISTS idx_transactions_wallet ON transactions(wallet_name);
CREATE INDEX IF NOT EXISTS idx_tx_signatures_tx ON tx_signatures(tx_unid);
