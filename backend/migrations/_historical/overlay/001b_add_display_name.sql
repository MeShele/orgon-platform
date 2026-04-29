-- Migration 001b: Add display_name to organizations
-- Phase: 1.4 Fix - display_name column missing
-- Date: 2026-02-11

ALTER TABLE organizations ADD COLUMN IF NOT EXISTS display_name VARCHAR(255);

COMMENT ON COLUMN organizations.display_name IS 'Human-readable display name for the organization (e.g., Safina Exchange)';
