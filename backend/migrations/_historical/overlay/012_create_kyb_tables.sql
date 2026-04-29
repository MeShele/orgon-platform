-- Migration 012: KYB/KYC submissions (user.id = INTEGER, org.id = UUID)

-- 1. KYC Submissions
CREATE TABLE IF NOT EXISTS kyc_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    status VARCHAR(20) DEFAULT 'pending',
    documents JSONB NOT NULL DEFAULT '[]',
    full_name VARCHAR(255) NOT NULL,
    date_of_birth DATE,
    nationality VARCHAR(2),
    address TEXT,
    phone VARCHAR(50),
    reviewer_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    review_comment TEXT,
    risk_level VARCHAR(20) DEFAULT 'unknown',
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,
    CONSTRAINT kyc_submissions_valid_status CHECK (status IN ('pending', 'in_review', 'approved', 'rejected', 'expired')),
    CONSTRAINT kyc_submissions_valid_risk CHECK (risk_level IN ('low', 'medium', 'high', 'unknown'))
);
CREATE INDEX IF NOT EXISTS idx_kyc_submissions_user ON kyc_submissions(user_id);
CREATE INDEX IF NOT EXISTS idx_kyc_submissions_status ON kyc_submissions(status);
CREATE INDEX IF NOT EXISTS idx_kyc_submissions_org ON kyc_submissions(organization_id);

-- 2. KYB Submissions
CREATE TABLE IF NOT EXISTS kyb_submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    submitted_by INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    status VARCHAR(20) DEFAULT 'pending',
    company_name VARCHAR(255) NOT NULL,
    registration_number VARCHAR(100),
    tax_id VARCHAR(100),
    legal_address TEXT,
    country VARCHAR(2),
    documents JSONB NOT NULL DEFAULT '[]',
    beneficiaries JSONB DEFAULT '[]',
    reviewer_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    review_comment TEXT,
    risk_level VARCHAR(20) DEFAULT 'unknown',
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    CONSTRAINT kyb_submissions_valid_status CHECK (status IN ('pending', 'in_review', 'approved', 'rejected', 'expired')),
    CONSTRAINT kyb_submissions_valid_risk CHECK (risk_level IN ('low', 'medium', 'high', 'unknown'))
);
CREATE INDEX IF NOT EXISTS idx_kyb_submissions_org ON kyb_submissions(organization_id);
CREATE INDEX IF NOT EXISTS idx_kyb_submissions_status ON kyb_submissions(status);

-- 3. Add verification flags
ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS kyc_verified_at TIMESTAMPTZ;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS kyb_verified BOOLEAN DEFAULT FALSE;
ALTER TABLE organizations ADD COLUMN IF NOT EXISTS kyb_verified_at TIMESTAMPTZ;
