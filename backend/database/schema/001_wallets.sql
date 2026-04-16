-- Wallets cache + local metadata
CREATE TABLE IF NOT EXISTS wallets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    wallet_id INTEGER,
    name TEXT UNIQUE NOT NULL,
    network INTEGER NOT NULL,
    wallet_type INTEGER,
    info TEXT,
    addr TEXT DEFAULT '',
    addr_info TEXT,
    my_unid TEXT,
    token_short_names TEXT,
    label TEXT,  -- local user label
    is_favorite INTEGER DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    synced_at DATETIME
);

CREATE INDEX IF NOT EXISTS idx_wallets_network ON wallets(network);
CREATE INDEX IF NOT EXISTS idx_wallets_name ON wallets(name);
