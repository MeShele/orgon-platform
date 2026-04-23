-- Add missing columns to transactions table
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS safina_id INTEGER;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS token TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS token_name TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS to_addr TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS value TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS value_hex TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS unid TEXT UNIQUE;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS init_ts BIGINT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS min_sign INTEGER DEFAULT 0;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS wallet_name TEXT;
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS network INTEGER;

-- Add missing columns to tx_signatures
ALTER TABLE tx_signatures ADD COLUMN IF NOT EXISTS ec_address TEXT;
ALTER TABLE tx_signatures ADD COLUMN IF NOT EXISTS sig_type TEXT;
ALTER TABLE tx_signatures ADD COLUMN IF NOT EXISTS ec_sign TEXT;

-- Fix unique constraint for tx_signatures (needs ec_address not signer_address)
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'tx_signatures_tx_ec_unique2') THEN
        ALTER TABLE tx_signatures ADD CONSTRAINT tx_signatures_tx_ec_unique2 UNIQUE (tx_unid, ec_address);
    END IF;
EXCEPTION WHEN duplicate_object THEN NULL;
END $$;
