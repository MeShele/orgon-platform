-- Add missing columns to tx_signatures
ALTER TABLE tx_signatures ADD COLUMN IF NOT EXISTS signed_at TIMESTAMPTZ;
ALTER TABLE tx_signatures ADD COLUMN IF NOT EXISTS action VARCHAR(50);
ALTER TABLE tx_signatures ADD COLUMN IF NOT EXISTS reason TEXT;
