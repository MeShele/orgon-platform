-- Fix RLS policies: Remove super_admin checks (users.role doesn't exist yet)
-- We'll add super_admin later when role system is implemented

-- Drop existing policies
DROP POLICY IF EXISTS subscription_plans_select ON subscription_plans;
DROP POLICY IF EXISTS subscription_plans_insert ON subscription_plans;
DROP POLICY IF EXISTS subscription_plans_update ON subscription_plans;
DROP POLICY IF EXISTS subscriptions_select ON subscriptions;
DROP POLICY IF EXISTS subscriptions_insert ON subscriptions;
DROP POLICY IF EXISTS subscriptions_update ON subscriptions;
DROP POLICY IF EXISTS invoices_select ON invoices;
DROP POLICY IF EXISTS invoice_line_items_select ON invoice_line_items;
DROP POLICY IF EXISTS payments_select ON payments;
DROP POLICY IF EXISTS transaction_fees_select ON transaction_fees;

-- Subscription Plans: Everyone can read (for plan selection)
CREATE POLICY subscription_plans_select ON subscription_plans
    FOR SELECT
    USING (true);

-- Subscriptions: Org members can read their subscription
CREATE POLICY subscriptions_select ON subscriptions
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM user_organizations
            WHERE user_organizations.organization_id = subscriptions.organization_id
            AND user_organizations.user_id = current_setting('app.current_user_id')::UUID
        )
    );

CREATE POLICY subscriptions_insert ON subscriptions
    FOR INSERT
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM user_organizations
            WHERE user_organizations.organization_id = subscriptions.organization_id
            AND user_organizations.user_id = current_setting('app.current_user_id')::UUID
            AND user_organizations.role = 'admin'
        )
    );

CREATE POLICY subscriptions_update ON subscriptions
    FOR UPDATE
    USING (
        EXISTS (
            SELECT 1 FROM user_organizations
            WHERE user_organizations.organization_id = subscriptions.organization_id
            AND user_organizations.user_id = current_setting('app.current_user_id')::UUID
            AND user_organizations.role = 'admin'
        )
    );

-- Invoices: Org members can read their invoices
CREATE POLICY invoices_select ON invoices
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM user_organizations
            WHERE user_organizations.organization_id = invoices.organization_id
            AND user_organizations.user_id = current_setting('app.current_user_id')::UUID
        )
    );

-- Invoice Line Items: Accessible through invoice
CREATE POLICY invoice_line_items_select ON invoice_line_items
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM invoices
            JOIN user_organizations ON user_organizations.organization_id = invoices.organization_id
            WHERE invoices.id = invoice_line_items.invoice_id
            AND user_organizations.user_id = current_setting('app.current_user_id')::UUID
        )
    );

-- Payments: Org members can read their payments
CREATE POLICY payments_select ON payments
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM user_organizations
            WHERE user_organizations.organization_id = payments.organization_id
            AND user_organizations.user_id = current_setting('app.current_user_id')::UUID
        )
    );

-- Transaction Fees: Org members can read their fees
CREATE POLICY transaction_fees_select ON transaction_fees
    FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM user_organizations
            WHERE user_organizations.organization_id = transaction_fees.organization_id
            AND user_organizations.user_id = current_setting('app.current_user_id')::UUID
        )
    );
