-- Migration 007: Compliance & Regulatory Tables
-- Phase: 2.2 Compliance
-- Date: 2026-02-11
-- Description: KYC/AML compliance, reports for regulator

-- ============================================================
-- COMPLIANCE TABLES
-- ============================================================

-- 1. KYC Records (Know Your Customer)
CREATE TABLE kyc_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    
    -- Customer info
    customer_name VARCHAR(255) NOT NULL,
    customer_email VARCHAR(255),
    customer_phone VARCHAR(50),
    customer_address TEXT,
    customer_country VARCHAR(2),  -- ISO 3166-1 alpha-2
    
    -- ID verification
    id_type VARCHAR(50),  -- passport/drivers_license/national_id
    id_number VARCHAR(100),
    id_expiry_date DATE,
    id_document_url TEXT,  -- Encrypted storage URL
    
    -- Verification status
    verification_status VARCHAR(20) DEFAULT 'pending',
    -- pending/in_review/approved/rejected/expired
    
    verification_method VARCHAR(50),  -- manual/automated/third_party
    verified_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    verified_at TIMESTAMPTZ,
    rejection_reason TEXT,
    
    -- Risk assessment
    risk_level VARCHAR(20) DEFAULT 'unknown',  -- low/medium/high/unknown
    risk_score INT,  -- 0-100
    risk_factors JSONB DEFAULT '[]',
    -- Example: ["high_transaction_volume", "sanctioned_country"]
    
    -- Provider data (if using third-party KYC)
    provider_name VARCHAR(100),  -- onfido/jumio/sumsub
    provider_verification_id VARCHAR(255),
    provider_response JSONB DEFAULT '{}',
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    expires_at TIMESTAMPTZ,  -- KYC re-verification date
    
    -- Constraints
    CONSTRAINT kyc_records_valid_status 
        CHECK (verification_status IN ('pending', 'in_review', 'approved', 'rejected', 'expired')),
    CONSTRAINT kyc_records_valid_risk 
        CHECK (risk_level IN ('low', 'medium', 'high', 'unknown'))
);

CREATE INDEX idx_kyc_records_org ON kyc_records(organization_id);
CREATE INDEX idx_kyc_records_user ON kyc_records(user_id);
CREATE INDEX idx_kyc_records_status ON kyc_records(verification_status);
CREATE INDEX idx_kyc_records_risk ON kyc_records(risk_level);
CREATE INDEX idx_kyc_records_expires ON kyc_records(expires_at);

CREATE TRIGGER update_kyc_records_updated_at 
    BEFORE UPDATE ON kyc_records
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 2. AML Alerts (Anti-Money Laundering)
CREATE TABLE aml_alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Alert details
    alert_type VARCHAR(50) NOT NULL,
    -- suspicious_transaction/high_value/rapid_movement/sanctioned_address/pattern_detected
    
    severity VARCHAR(20) DEFAULT 'medium',  -- low/medium/high/critical
    
    -- Related entities
    transaction_id UUID REFERENCES transactions(id) ON DELETE SET NULL,
    wallet_id UUID REFERENCES wallets(id) ON DELETE SET NULL,
    kyc_record_id UUID REFERENCES kyc_records(id) ON DELETE SET NULL,
    
    -- Alert data
    description TEXT NOT NULL,
    details JSONB DEFAULT '{}',
    -- Example: {"amount_usd": 100000, "threshold": 10000, "pattern": "structuring"}
    
    -- Status
    status VARCHAR(20) DEFAULT 'open',  -- open/investigating/resolved/false_positive/reported
    
    -- Investigation
    assigned_to INTEGER REFERENCES users(id) ON DELETE SET NULL,
    investigated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    investigated_at TIMESTAMPTZ,
    investigation_notes TEXT,
    resolution TEXT,
    
    -- Regulatory reporting
    reported_to_regulator BOOLEAN DEFAULT FALSE,
    reported_at TIMESTAMPTZ,
    report_reference VARCHAR(100),
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT aml_alerts_valid_severity 
        CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    CONSTRAINT aml_alerts_valid_status 
        CHECK (status IN ('open', 'investigating', 'resolved', 'false_positive', 'reported'))
);

CREATE INDEX idx_aml_alerts_org ON aml_alerts(organization_id);
CREATE INDEX idx_aml_alerts_type ON aml_alerts(alert_type);
CREATE INDEX idx_aml_alerts_severity ON aml_alerts(severity);
CREATE INDEX idx_aml_alerts_status ON aml_alerts(status);
CREATE INDEX idx_aml_alerts_transaction ON aml_alerts(transaction_id);
CREATE INDEX idx_aml_alerts_created ON aml_alerts(created_at DESC);

CREATE TRIGGER update_aml_alerts_updated_at 
    BEFORE UPDATE ON aml_alerts
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 3. Compliance Reports (for regulator)
CREATE TABLE compliance_reports (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Report details
    report_type VARCHAR(50) NOT NULL,
    -- monthly_transactions/kyc_summary/aml_alerts/suspicious_activity/tax_report
    
    period_start DATE NOT NULL,
    period_end DATE NOT NULL,
    
    -- Report metadata
    title VARCHAR(255) NOT NULL,
    description TEXT,
    
    -- Generated data
    generated_at TIMESTAMPTZ DEFAULT NOW(),
    generated_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    
    -- Report content (JSONB for flexibility)
    report_data JSONB NOT NULL DEFAULT '{}',
    -- Example: {"total_transactions": 1000, "total_volume_usd": 500000, "kyc_approved": 50}
    
    -- File exports
    pdf_url TEXT,  -- Cloud storage URL
    excel_url TEXT,
    xml_url TEXT,
    
    -- Status
    status VARCHAR(20) DEFAULT 'draft',  -- draft/final/submitted
    
    -- Submission to regulator
    submitted_to_regulator BOOLEAN DEFAULT FALSE,
    submitted_at TIMESTAMPTZ,
    submission_reference VARCHAR(100),
    submission_response JSONB DEFAULT '{}',
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    
    -- Constraints
    CONSTRAINT compliance_reports_valid_status 
        CHECK (status IN ('draft', 'final', 'submitted'))
);

CREATE INDEX idx_compliance_reports_org ON compliance_reports(organization_id);
CREATE INDEX idx_compliance_reports_type ON compliance_reports(report_type);
CREATE INDEX idx_compliance_reports_period ON compliance_reports(period_start, period_end);
CREATE INDEX idx_compliance_reports_status ON compliance_reports(status);
CREATE INDEX idx_compliance_reports_submitted ON compliance_reports(submitted_to_regulator);

CREATE TRIGGER update_compliance_reports_updated_at 
    BEFORE UPDATE ON compliance_reports
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 4. Sanctioned Addresses (blocklist)
CREATE TABLE sanctioned_addresses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Address details
    address VARCHAR(100) UNIQUE NOT NULL,
    network VARCHAR(20) NOT NULL,  -- tron/bsc/ethereum
    
    -- Sanction info
    sanction_type VARCHAR(50) NOT NULL,
    -- terrorism/crime/fraud/mixer/darknet_market
    
    source VARCHAR(100),  -- OFAC/Chainalysis/local_regulator
    description TEXT,
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Metadata
    added_at TIMESTAMPTZ DEFAULT NOW(),
    added_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    expires_at TIMESTAMPTZ,
    
    -- Additional data
    metadata JSONB DEFAULT '{}'
);

CREATE INDEX idx_sanctioned_addresses_address ON sanctioned_addresses(address);
CREATE INDEX idx_sanctioned_addresses_network ON sanctioned_addresses(network);
CREATE INDEX idx_sanctioned_addresses_active ON sanctioned_addresses(is_active);

-- 5. Transaction Monitoring Rules (AML rules)
CREATE TABLE transaction_monitoring_rules (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    organization_id UUID REFERENCES organizations(id) ON DELETE CASCADE,
    
    -- Rule details
    rule_name VARCHAR(255) NOT NULL,
    rule_type VARCHAR(50) NOT NULL,
    -- threshold/pattern/velocity/geo/sanctioned_address
    
    description TEXT,
    
    -- Rule configuration (JSONB for flexibility)
    rule_config JSONB NOT NULL DEFAULT '{}',
    -- Example: {"threshold_usd": 10000, "time_window_hours": 24}
    
    -- Actions
    action VARCHAR(50) DEFAULT 'alert',  -- alert/block/review
    severity VARCHAR(20) DEFAULT 'medium',
    
    -- Status
    is_active BOOLEAN DEFAULT TRUE,
    
    -- Metadata
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    created_by INTEGER REFERENCES users(id) ON DELETE SET NULL
);

CREATE INDEX idx_monitoring_rules_org ON transaction_monitoring_rules(organization_id);
CREATE INDEX idx_monitoring_rules_type ON transaction_monitoring_rules(rule_type);
CREATE INDEX idx_monitoring_rules_active ON transaction_monitoring_rules(is_active);

CREATE TRIGGER update_monitoring_rules_updated_at 
    BEFORE UPDATE ON transaction_monitoring_rules
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================================
-- COMMENTS
-- ============================================================

COMMENT ON TABLE kyc_records IS 'KYC (Know Your Customer) verification records';
COMMENT ON TABLE aml_alerts IS 'AML (Anti-Money Laundering) alerts and investigations';
COMMENT ON TABLE compliance_reports IS 'Regulatory compliance reports (monthly, KYC, AML)';
COMMENT ON TABLE sanctioned_addresses IS 'Blocklist of sanctioned/risky addresses';
COMMENT ON TABLE transaction_monitoring_rules IS 'AML transaction monitoring rules';

-- ============================================================
-- SEED DATA
-- ============================================================

-- Default monitoring rules (basic AML compliance)
INSERT INTO transaction_monitoring_rules (rule_name, rule_type, description, rule_config, action, severity) VALUES
('High Value Transaction', 'threshold', 'Alert on transactions > $10,000 USD', 
 '{"threshold_usd": 10000}', 'alert', 'medium'),

('Very High Value Transaction', 'threshold', 'Block transactions > $100,000 USD', 
 '{"threshold_usd": 100000}', 'block', 'high'),

('Rapid Succession', 'velocity', 'Alert on > 10 transactions within 1 hour', 
 '{"max_transactions": 10, "time_window_hours": 1}', 'alert', 'medium'),

('Daily Volume Exceeded', 'threshold', 'Alert on daily volume > $50,000 USD', 
 '{"threshold_usd": 50000, "time_window_hours": 24}', 'alert', 'high'),

('Sanctioned Address', 'sanctioned_address', 'Block transactions to/from sanctioned addresses', 
 '{}', 'block', 'critical');
