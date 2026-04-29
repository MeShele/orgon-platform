-- 005_address_book.sql
-- Contact management for frequent recipients

CREATE TABLE IF NOT EXISTS address_book (
    id SERIAL PRIMARY KEY,
    name TEXT NOT NULL,
    address TEXT NOT NULL,
    network TEXT,
    category TEXT CHECK (category IN ('personal', 'business', 'exchange', 'other')),
    notes TEXT,
    favorite BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_address_book_name ON address_book(name);
CREATE INDEX IF NOT EXISTS idx_address_book_address ON address_book(address);
CREATE INDEX IF NOT EXISTS idx_address_book_favorite ON address_book(favorite);
CREATE INDEX IF NOT EXISTS idx_address_book_category ON address_book(category);

-- Updated_at trigger
CREATE OR REPLACE FUNCTION update_address_book_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER address_book_updated_at
    BEFORE UPDATE ON address_book
    FOR EACH ROW
    EXECUTE FUNCTION update_address_book_updated_at();

-- Add some example data (optional, for testing)
INSERT INTO address_book (name, address, network, category, notes, favorite)
VALUES 
    ('Alice Wallet', '0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb', 'ethereum', 'personal', 'Friend from university', true),
    ('Bob Exchange', '0x3f5CE5FBFe3E9af3971dD833D26bA9b5C936f0bE', 'polygon', 'exchange', 'Main exchange deposit', false),
    ('Company Payroll', '0x1234567890123456789012345678901234567890', 'ethereum', 'business', 'Monthly salary recipient', true)
ON CONFLICT DO NOTHING;
