-- Migration 008: Two-Factor Authentication
-- Add TOTP support and backup codes

-- Add 2FA fields to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_secret VARCHAR(32);
ALTER TABLE users ADD COLUMN IF NOT EXISTS totp_enabled BOOLEAN DEFAULT FALSE;

-- Create backup codes table
CREATE TABLE IF NOT EXISTS twofa_backup_codes (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    code_hash VARCHAR(64) NOT NULL,
    created_at TIMESTAMP NOT NULL,
    used_at TIMESTAMP,
    UNIQUE(user_id, code_hash)
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_backup_codes_user ON twofa_backup_codes(user_id);
CREATE INDEX IF NOT EXISTS idx_backup_codes_unused ON twofa_backup_codes(user_id, used_at) WHERE used_at IS NULL;

-- Add comment
COMMENT ON TABLE twofa_backup_codes IS 'Backup codes for 2FA recovery';
COMMENT ON COLUMN users.totp_secret IS 'TOTP secret key (base32 encoded)';
COMMENT ON COLUMN users.totp_enabled IS 'Whether TOTP 2FA is enabled';
