-- Sync watermarks and cache tables
CREATE TABLE IF NOT EXISTS sync_state (
    key TEXT PRIMARY KEY,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS token_balances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token_id TEXT,
    wallet_id TEXT,
    wallet_name TEXT,
    network TEXT,
    token TEXT NOT NULL,
    value TEXT NOT NULL,
    decimals TEXT,
    value_hex TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS networks_cache (
    network_id INTEGER PRIMARY KEY,
    network_name TEXT NOT NULL,
    link TEXT,
    address_explorer TEXT,
    tx_explorer TEXT,
    block_explorer TEXT,
    info TEXT,
    status INTEGER,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS tokens_info_cache (
    token TEXT PRIMARY KEY,
    commission TEXT,
    commission_min TEXT,
    commission_max TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS balance_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT NOT NULL,
    network TEXT,
    total_value TEXT NOT NULL,
    recorded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_token_balances_wallet ON token_balances(wallet_name);
CREATE INDEX IF NOT EXISTS idx_balance_history_date ON balance_history(recorded_at);
