-- Create compliance tables

CREATE TABLE IF NOT EXISTS kyc_records (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'pending',
    risk_level VARCHAR(50) DEFAULT 'low',
    full_name VARCHAR(255),
    date_of_birth DATE,
    nationality VARCHAR(100),
    document_type VARCHAR(100),
    document_number VARCHAR(100),
    documents JSONB DEFAULT '[]',
    notes TEXT,
    reviewed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kyc_records_user ON kyc_records(user_id);
CREATE INDEX IF NOT EXISTS idx_kyc_records_org ON kyc_records(organization_id);
CREATE INDEX IF NOT EXISTS idx_kyc_records_status ON kyc_records(status);

CREATE TABLE IF NOT EXISTS kyb_records (
    id SERIAL PRIMARY KEY,
    organization_id UUID REFERENCES organizations(id) ON DELETE SET NULL,
    status VARCHAR(50) DEFAULT 'pending',
    risk_level VARCHAR(50) DEFAULT 'low',
    company_name VARCHAR(255),
    registration_number VARCHAR(100),
    tax_id VARCHAR(100),
    country VARCHAR(100),
    documents JSONB DEFAULT '[]',
    notes TEXT,
    reviewed_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_kyb_records_org ON kyb_records(organization_id);
CREATE INDEX IF NOT EXISTS idx_kyb_records_status ON kyb_records(status);
