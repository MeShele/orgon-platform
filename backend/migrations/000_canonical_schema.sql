--
-- ORGON canonical schema — single source of truth
--
-- This file replaces the historical 47-file migration chain (legacy
-- `backend/database/migrations/` + overlay `backend/migrations/[001..024]*`).
-- Those are preserved under `_historical/` for reference but are no
-- longer applied to fresh installs.
--
-- Generated: 2026-04-29 from local-dev DB (orgon_user/orgon_db) which
-- had every Wave 1-10 migration applied and is verified working with
-- the current backend code (86 unit tests passed, full UI smoke).
--
-- Properties:
--   * **NOT idempotent.** pg_dump emits bare `CREATE TABLE foo (...)`
--     with no `IF NOT EXISTS`, plus `CREATE TRIGGER`, `CREATE POLICY`,
--     and `ALTER TABLE ... ADD CONSTRAINT` which all fail on rerun.
--     This file applies ONCE to a fresh database. Re-runs are gated by
--     the `schema_migrations` tracking table inserted at the end of
--     this file — `entrypoint.sh` and CI both check for the canonical
--     marker row before deciding to apply.
--   * No role / ACL / tablespace dependencies (`--no-owner --no-acl
--     --no-tablespaces`) — applies cleanly to any Postgres 16 cluster
--     where the connecting user owns the public schema.
--   * Self-contained: extensions (pgcrypto, uuid-ossp), 15 functions,
--     triggers, RLS policies, 224 indexes — all here.
--
-- Apply order on a fresh install:
--   psql -v ON_ERROR_STOP=1 -f backend/migrations/000_canonical_schema.sql
--   # then any 025+ migrations in numeric order, each idempotent
--
-- After this file, all future schema changes go in NEW numbered
-- migrations (`025_*.sql` and onwards) — those MUST be idempotent
-- (`CREATE TABLE IF NOT EXISTS`, `ON CONFLICT DO NOTHING`, etc.).
-- Never edit this file in place — that breaks the "one canonical
-- truth" invariant. If you need to regenerate from a live DB, do so
-- atomically via the documented procedure in DEPLOYMENT.md.
--

--
-- PostgreSQL database dump
--


-- Dumped from database version 16.13
-- Dumped by pg_dump version 16.13

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Name: pgcrypto; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS pgcrypto WITH SCHEMA public;


--
-- Name: EXTENSION pgcrypto; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION pgcrypto IS 'cryptographic functions';


--
-- Name: uuid-ossp; Type: EXTENSION; Schema: -; Owner: -
--

CREATE EXTENSION IF NOT EXISTS "uuid-ossp" WITH SCHEMA public;


--
-- Name: EXTENSION "uuid-ossp"; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON EXTENSION "uuid-ossp" IS 'generate universally unique identifiers (UUIDs)';


--
-- Name: calculate_next_billing_date(timestamp without time zone, character varying); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.calculate_next_billing_date(start_date timestamp without time zone, billing_cycle character varying) RETURNS timestamp without time zone
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF billing_cycle = 'monthly' THEN
        RETURN start_date + INTERVAL '1 month';
    ELSIF billing_cycle = 'yearly' THEN
        RETURN start_date + INTERVAL '1 year';
    ELSE
        RETURN start_date + INTERVAL '1 month'; -- Default to monthly
    END IF;
END;
$$;


--
-- Name: clear_tenant_context(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.clear_tenant_context() RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    PERFORM set_config('app.current_organization_id', '', false);
    PERFORM set_config('app.is_super_admin', 'false', false);
END;
$$;


--
-- Name: FUNCTION clear_tenant_context(); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.clear_tenant_context() IS 'Clear session vars at request end so a recycled connection does not leak tenancy.';


--
-- Name: generate_invoice_number(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.generate_invoice_number() RETURNS character varying
    LANGUAGE plpgsql
    AS $$
DECLARE
    current_year INTEGER;
    next_number INTEGER;
    invoice_num VARCHAR(20);
BEGIN
    current_year := EXTRACT(YEAR FROM CURRENT_DATE);
    
    -- Get next number for this year
    SELECT COALESCE(MAX(
        CAST(SUBSTRING(invoice_number FROM 10) AS INTEGER)
    ), 0) + 1 INTO next_number
    FROM invoices
    WHERE SUBSTRING(invoice_number FROM 5 FOR 4) = current_year::TEXT;
    
    -- Format: INV-2026-001234
    invoice_num := 'INV-' || current_year || '-' || LPAD(next_number::TEXT, 6, '0');
    
    RETURN invoice_num;
END;
$$;


--
-- Name: generate_payment_number(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.generate_payment_number() RETURNS character varying
    LANGUAGE plpgsql
    AS $$
DECLARE
    current_year INTEGER;
    next_number INTEGER;
    payment_num VARCHAR(20);
BEGIN
    current_year := EXTRACT(YEAR FROM CURRENT_DATE);
    
    -- Get next number for this year
    SELECT COALESCE(MAX(
        CAST(SUBSTRING(payment_number FROM 10) AS INTEGER)
    ), 0) + 1 INTO next_number
    FROM payments
    WHERE SUBSTRING(payment_number FROM 5 FOR 4) = current_year::TEXT;
    
    -- Format: PAY-2026-001234
    payment_num := 'PAY-' || current_year || '-' || LPAD(next_number::TEXT, 6, '0');
    
    RETURN payment_num;
END;
$$;


--
-- Name: orgon_block_update_delete(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.orgon_block_update_delete() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'Table %.% is append-only — UPDATE is not allowed.',
            TG_TABLE_SCHEMA, TG_TABLE_NAME;
    ELSIF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION 'Table %.% is append-only — DELETE is not allowed.',
            TG_TABLE_SCHEMA, TG_TABLE_NAME;
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: orgon_current_org_or_super(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.orgon_current_org_or_super() RETURNS TABLE(org_id uuid, is_super boolean)
    LANGUAGE sql STABLE
    AS $$
    SELECT
        NULLIF(current_setting('app.current_organization_id', true), '')::uuid,
        COALESCE(current_setting('app.is_super_admin', true)::boolean, false)
$$;


--
-- Name: FUNCTION orgon_current_org_or_super(); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.orgon_current_org_or_super() IS 'Returns (current_org_id, is_super_admin) from session settings — used by RLS policies.';


--
-- Name: set_tenant_context(uuid, boolean); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.set_tenant_context(org_id uuid, is_admin boolean DEFAULT false) RETURNS void
    LANGUAGE plpgsql
    AS $$
BEGIN
    PERFORM set_config('app.current_organization_id', org_id::text, false);
    PERFORM set_config('app.is_super_admin', is_admin::text, false);
END;
$$;


--
-- Name: FUNCTION set_tenant_context(org_id uuid, is_admin boolean); Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON FUNCTION public.set_tenant_context(org_id uuid, is_admin boolean) IS 'Set Postgres session vars consumed by RLS policies. Called by RLSMiddleware on each request.';


--
-- Name: trigger_generate_invoice_number(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger_generate_invoice_number() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.invoice_number IS NULL THEN
        NEW.invoice_number := generate_invoice_number();
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: trigger_generate_payment_number(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger_generate_payment_number() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    IF NEW.payment_number IS NULL THEN
        NEW.payment_number := generate_payment_number();
    END IF;
    RETURN NEW;
END;
$$;


--
-- Name: trigger_update_timestamp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.trigger_update_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at := CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$;


--
-- Name: update_address_book_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_address_book_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


--
-- Name: update_partner_webhooks_timestamp(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_partner_webhooks_timestamp() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


--
-- Name: update_partners_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_partners_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


--
-- Name: update_updated_at_column(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_updated_at_column() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


--
-- Name: update_users_updated_at(); Type: FUNCTION; Schema: public; Owner: -
--

CREATE FUNCTION public.update_users_updated_at() RETURNS trigger
    LANGUAGE plpgsql
    AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$;


SET default_table_access_method = heap;

--
-- Name: address_book; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.address_book (
    id integer NOT NULL,
    name text NOT NULL,
    address text NOT NULL,
    network text,
    category text,
    notes text,
    favorite boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT address_book_category_check CHECK ((category = ANY (ARRAY['personal'::text, 'business'::text, 'exchange'::text, 'other'::text])))
);


--
-- Name: address_book_b2b; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.address_book_b2b (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    partner_id uuid NOT NULL,
    name character varying(255) NOT NULL,
    address character varying(255) NOT NULL,
    network_id integer NOT NULL,
    label character varying(100),
    notes text,
    is_favorite boolean DEFAULT false,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE address_book_b2b; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.address_book_b2b IS 'Per-partner saved addresses with labels';


--
-- Name: address_book_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.address_book_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: address_book_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.address_book_id_seq OWNED BY public.address_book.id;


--
-- Name: aml_alerts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.aml_alerts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    alert_type character varying(50) NOT NULL,
    severity character varying(20) DEFAULT 'medium'::character varying,
    transaction_id uuid,
    wallet_id uuid,
    kyc_record_id uuid,
    description text NOT NULL,
    details jsonb DEFAULT '{}'::jsonb,
    status character varying(20) DEFAULT 'open'::character varying,
    assigned_to integer,
    investigated_by integer,
    investigated_at timestamp with time zone,
    investigation_notes text,
    resolution text,
    reported_to_regulator boolean DEFAULT false,
    reported_at timestamp with time zone,
    report_reference character varying(100),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT aml_alerts_valid_severity CHECK (((severity)::text = ANY ((ARRAY['low'::character varying, 'medium'::character varying, 'high'::character varying, 'critical'::character varying])::text[]))),
    CONSTRAINT aml_alerts_valid_status CHECK (((status)::text = ANY ((ARRAY['open'::character varying, 'investigating'::character varying, 'resolved'::character varying, 'false_positive'::character varying, 'reported'::character varying])::text[])))
);


--
-- Name: TABLE aml_alerts; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.aml_alerts IS 'AML (Anti-Money Laundering) alerts and investigations';


--
-- Name: audit_log; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_log (
    id integer NOT NULL,
    user_id integer,
    action text NOT NULL,
    resource_type text,
    resource_id text,
    details jsonb,
    ip_address text,
    user_agent text,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE audit_log; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.audit_log IS 'Activity log for all user actions';


--
-- Name: COLUMN audit_log.action; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.audit_log.action IS 'Action type: create/update/delete/view/sign/reject';


--
-- Name: COLUMN audit_log.resource_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.audit_log.resource_type IS 'Resource type: wallet/transaction/contact/scheduled/signature';


--
-- Name: COLUMN audit_log.details; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.audit_log.details IS 'JSON details of the action';


--
-- Name: audit_log_b2b; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_log_b2b (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    partner_id uuid,
    user_id character varying(255),
    action character varying(100) NOT NULL,
    resource_type character varying(50),
    resource_id character varying(255),
    ip_address character varying(45),
    user_agent text,
    request_id character varying(64),
    changes jsonb,
    result character varying(20) DEFAULT 'success'::character varying,
    error_message text,
    metadata jsonb DEFAULT '{}'::jsonb,
    "timestamp" timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE audit_log_b2b; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.audit_log_b2b IS 'Comprehensive audit trail for compliance and security';


--
-- Name: audit_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.audit_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: audit_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.audit_log_id_seq OWNED BY public.audit_log.id;


--
-- Name: audit_logs; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_logs (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id integer,
    action character varying(100) NOT NULL,
    resource_type character varying(100),
    resource_id uuid,
    ip_address character varying(50),
    user_agent text,
    details jsonb,
    created_at timestamp without time zone DEFAULT now(),
    organization_id uuid
);

ALTER TABLE ONLY public.audit_logs FORCE ROW LEVEL SECURITY;


--
-- Name: TABLE audit_logs; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.audit_logs IS 'Security audit trail';


--
-- Name: COLUMN audit_logs.organization_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.audit_logs.organization_id IS 'Optional tenant reference for audit logs (NULL = system-wide)';


--
-- Name: balance_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.balance_history (
    id integer NOT NULL,
    token character varying(64) NOT NULL,
    total_value numeric(36,18) DEFAULT 0 NOT NULL,
    recorded_at timestamp with time zone DEFAULT now() NOT NULL,
    organization_id uuid
);


--
-- Name: balance_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.balance_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: balance_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.balance_history_id_seq OWNED BY public.balance_history.id;


--
-- Name: bank_accounts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.bank_accounts (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    user_id integer NOT NULL,
    account_holder_name character varying(255) NOT NULL,
    bank_name character varying(255),
    account_number_last4 character varying(4),
    account_number_encrypted text,
    routing_number character varying(50),
    iban character varying(34),
    swift_code character varying(11),
    bank_country character varying(2),
    currency character varying(3) DEFAULT 'USD'::character varying,
    verification_status character varying(20) DEFAULT 'pending'::character varying,
    verification_method character varying(50),
    verified_at timestamp with time zone,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT bank_account_valid_verification CHECK (((verification_status)::text = ANY ((ARRAY['pending'::character varying, 'verified'::character varying, 'rejected'::character varying])::text[])))
);


--
-- Name: TABLE bank_accounts; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.bank_accounts IS 'User bank accounts for fiat withdrawals';


--
-- Name: compliance_reports; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.compliance_reports (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    report_type character varying(50) NOT NULL,
    period_start date NOT NULL,
    period_end date NOT NULL,
    title character varying(255) NOT NULL,
    description text,
    generated_at timestamp with time zone DEFAULT now(),
    generated_by integer,
    report_data jsonb DEFAULT '{}'::jsonb NOT NULL,
    pdf_url text,
    excel_url text,
    xml_url text,
    status character varying(20) DEFAULT 'draft'::character varying,
    submitted_to_regulator boolean DEFAULT false,
    submitted_at timestamp with time zone,
    submission_reference character varying(100),
    submission_response jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT compliance_reports_valid_status CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'final'::character varying, 'submitted'::character varying])::text[])))
);


--
-- Name: TABLE compliance_reports; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.compliance_reports IS 'Regulatory compliance reports (monthly, KYC, AML)';


--
-- Name: contacts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.contacts (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    user_id integer,
    name character varying(255) NOT NULL,
    address character varying(255) NOT NULL,
    network integer,
    category character varying(100),
    notes text,
    is_favorite boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    organization_id uuid
);

ALTER TABLE ONLY public.contacts FORCE ROW LEVEL SECURITY;


--
-- Name: TABLE contacts; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.contacts IS 'Address book for frequent recipients';


--
-- Name: COLUMN contacts.organization_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.contacts.organization_id IS 'Tenant isolation: contact belongs to this organization';


--
-- Name: crypto_exchange_rates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.crypto_exchange_rates (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    crypto_currency character varying(10) NOT NULL,
    fiat_currency character varying(3) NOT NULL,
    rate numeric(12,6) NOT NULL,
    source character varying(50) DEFAULT 'coingecko'::character varying,
    fetched_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE crypto_exchange_rates; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.crypto_exchange_rates IS 'Cached crypto-to-fiat exchange rates';


--
-- Name: custom_domains; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.custom_domains (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    domain character varying(255) NOT NULL,
    subdomain character varying(100),
    verification_method character varying(50) DEFAULT 'dns_txt'::character varying,
    verification_token character varying(100),
    verification_record text,
    verified boolean DEFAULT false,
    verified_at timestamp with time zone,
    ssl_enabled boolean DEFAULT false,
    ssl_provider character varying(50),
    ssl_issued_at timestamp with time zone,
    ssl_expires_at timestamp with time zone,
    is_active boolean DEFAULT true,
    is_primary boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT domains_valid_verification CHECK (((verification_method)::text = ANY ((ARRAY['dns_txt'::character varying, 'dns_cname'::character varying, 'file_upload'::character varying])::text[])))
);


--
-- Name: TABLE custom_domains; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.custom_domains IS 'Custom domain verification and SSL management';


--
-- Name: email_templates; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.email_templates (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    template_type character varying(50) NOT NULL,
    template_name character varying(255) NOT NULL,
    subject character varying(255) NOT NULL,
    body_text text,
    body_html text,
    variables jsonb DEFAULT '[]'::jsonb,
    is_active boolean DEFAULT true,
    is_default boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    created_by integer
);


--
-- Name: TABLE email_templates; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.email_templates IS 'Customizable transactional email templates';


--
-- Name: fiat_transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.fiat_transactions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    user_id integer,
    transaction_type character varying(20) NOT NULL,
    fiat_amount numeric(12,2) NOT NULL,
    fiat_currency character varying(3) NOT NULL,
    crypto_amount numeric(20,8),
    crypto_currency character varying(10),
    exchange_rate numeric(12,6),
    payment_method character varying(50),
    payment_gateway character varying(50),
    gateway_transaction_id character varying(255),
    bank_account_id uuid,
    status character varying(20) DEFAULT 'pending'::character varying,
    created_at timestamp with time zone DEFAULT now(),
    processed_at timestamp with time zone,
    completed_at timestamp with time zone,
    metadata jsonb DEFAULT '{}'::jsonb,
    CONSTRAINT fiat_txn_valid_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'processing'::character varying, 'completed'::character varying, 'failed'::character varying, 'cancelled'::character varying, 'refunded'::character varying])::text[]))),
    CONSTRAINT fiat_txn_valid_type CHECK (((transaction_type)::text = ANY ((ARRAY['onramp'::character varying, 'offramp'::character varying])::text[])))
);


--
-- Name: TABLE fiat_transactions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.fiat_transactions IS 'Fiat on-ramp/off-ramp transactions';


--
-- Name: invoice_line_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invoice_line_items (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    invoice_id uuid NOT NULL,
    description character varying(255) NOT NULL,
    item_type character varying(50) NOT NULL,
    quantity numeric(10,2) DEFAULT 1,
    unit_price numeric(10,2) NOT NULL,
    amount numeric(10,2) NOT NULL,
    tax_rate numeric(5,2) DEFAULT 0,
    tax_amount numeric(10,2) DEFAULT 0,
    period_start date,
    period_end date,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: TABLE invoice_line_items; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.invoice_line_items IS 'Line items for invoices (subscription, fees, charges)';


--
-- Name: COLUMN invoice_line_items.item_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.invoice_line_items.item_type IS 'subscription, transaction_fee, one_time_charge, adjustment';


--
-- Name: invoices; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.invoices (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    subscription_id uuid,
    invoice_number character varying(50) NOT NULL,
    issue_date timestamp with time zone DEFAULT now(),
    due_date timestamp with time zone,
    subtotal numeric(12,2) DEFAULT 0 NOT NULL,
    tax_rate numeric(5,2) DEFAULT 0,
    tax_amount numeric(12,2) DEFAULT 0,
    total numeric(12,2) DEFAULT 0 NOT NULL,
    currency character varying(10) DEFAULT 'KGS'::character varying,
    status character varying(20) DEFAULT 'draft'::character varying,
    line_items jsonb DEFAULT '[]'::jsonb,
    notes text,
    payment_method character varying(50),
    payment_reference character varying(255),
    paid_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT invoices_number_format CHECK (((invoice_number)::text ~ '^INV-[0-9]{4}-[0-9]{4,6}$'::text)),
    CONSTRAINT invoices_positive_amounts CHECK (((subtotal >= (0)::numeric) AND (total >= (0)::numeric))),
    CONSTRAINT invoices_valid_status CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'sent'::character varying, 'paid'::character varying, 'overdue'::character varying, 'cancelled'::character varying])::text[])))
);


--
-- Name: TABLE invoices; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.invoices IS 'Monthly invoices for subscriptions and fees';


--
-- Name: COLUMN invoices.invoice_number; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.invoices.invoice_number IS 'Human-readable invoice number (INV-YYYY-NNNNNN)';


--
-- Name: COLUMN invoices.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.invoices.status IS 'draft: not finalized, open: awaiting payment, paid: fully paid, void: cancelled, uncollectible: write-off';


--
-- Name: kyb_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.kyb_records (
    id integer NOT NULL,
    organization_id uuid,
    company_name character varying(255),
    registration_number character varying(100),
    tax_id character varying(100),
    country character varying(100),
    verification_status character varying(50) DEFAULT 'pending'::character varying,
    risk_level character varying(50) DEFAULT 'low'::character varying,
    documents jsonb DEFAULT '[]'::jsonb,
    notes text,
    verified_by integer,
    verified_at timestamp with time zone,
    reviewed_by integer,
    reviewed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: kyb_records_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.kyb_records_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: kyb_records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.kyb_records_id_seq OWNED BY public.kyb_records.id;


--
-- Name: kyb_submissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.kyb_submissions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    submitted_by integer NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying,
    company_name character varying(255) NOT NULL,
    registration_number character varying(100),
    tax_id character varying(100),
    legal_address text,
    country character varying(2),
    documents jsonb DEFAULT '[]'::jsonb NOT NULL,
    beneficiaries jsonb DEFAULT '[]'::jsonb,
    reviewer_id integer,
    reviewed_at timestamp with time zone,
    review_comment text,
    risk_level character varying(20) DEFAULT 'unknown'::character varying,
    submitted_at timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT kyb_submissions_valid_risk CHECK (((risk_level)::text = ANY ((ARRAY['low'::character varying, 'medium'::character varying, 'high'::character varying, 'unknown'::character varying])::text[]))),
    CONSTRAINT kyb_submissions_valid_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'in_review'::character varying, 'approved'::character varying, 'rejected'::character varying, 'expired'::character varying])::text[])))
);


--
-- Name: kyc_records; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.kyc_records (
    id integer NOT NULL,
    user_id integer,
    organization_id uuid,
    customer_name character varying(255),
    customer_email character varying(255),
    id_type character varying(100),
    id_number character varying(100),
    verification_status character varying(50) DEFAULT 'pending'::character varying,
    risk_level character varying(50) DEFAULT 'low'::character varying,
    full_name character varying(255),
    date_of_birth date,
    nationality character varying(100),
    document_type character varying(100),
    document_number character varying(100),
    documents jsonb DEFAULT '[]'::jsonb,
    notes text,
    verified_by integer,
    verified_at timestamp with time zone,
    reviewed_by integer,
    reviewed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE kyc_records; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.kyc_records IS 'KYC (Know Your Customer) verification records';


--
-- Name: kyc_records_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.kyc_records_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: kyc_records_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.kyc_records_id_seq OWNED BY public.kyc_records.id;


--
-- Name: kyc_submissions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.kyc_submissions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    user_id integer NOT NULL,
    organization_id uuid,
    status character varying(20) DEFAULT 'pending'::character varying,
    documents jsonb DEFAULT '[]'::jsonb NOT NULL,
    full_name character varying(255) NOT NULL,
    date_of_birth date,
    nationality character varying(2),
    address text,
    phone character varying(50),
    reviewer_id integer,
    reviewed_at timestamp with time zone,
    review_comment text,
    risk_level character varying(20) DEFAULT 'unknown'::character varying,
    submitted_at timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    expires_at timestamp with time zone,
    CONSTRAINT kyc_submissions_valid_risk CHECK (((risk_level)::text = ANY ((ARRAY['low'::character varying, 'medium'::character varying, 'high'::character varying, 'unknown'::character varying])::text[]))),
    CONSTRAINT kyc_submissions_valid_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'in_review'::character varying, 'approved'::character varying, 'rejected'::character varying, 'expired'::character varying])::text[])))
);


--
-- Name: networks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.networks (
    network_id integer NOT NULL,
    name character varying(255),
    short_name character varying(50),
    tokens jsonb DEFAULT '[]'::jsonb,
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: networks_cache; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.networks_cache (
    network_id integer NOT NULL,
    network_name character varying(255),
    short_name character varying(100),
    link text,
    address_explorer text,
    tx_explorer text,
    block_explorer text,
    info text,
    status integer DEFAULT 1,
    tokens jsonb DEFAULT '[]'::jsonb,
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: organization_branding; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organization_branding (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    logo_url text,
    logo_dark_url text,
    favicon_url text,
    color_primary character varying(7) DEFAULT '#3B82F6'::character varying,
    color_secondary character varying(7) DEFAULT '#10B981'::character varying,
    color_accent character varying(7) DEFAULT '#F59E0B'::character varying,
    color_background character varying(7) DEFAULT '#FFFFFF'::character varying,
    color_text character varying(7) DEFAULT '#1F2937'::character varying,
    font_family character varying(100) DEFAULT 'Inter'::character varying,
    font_url text,
    custom_domain character varying(255),
    domain_verified boolean DEFAULT false,
    domain_verified_at timestamp with time zone,
    platform_name character varying(100),
    tagline character varying(255),
    footer_text text,
    support_email character varying(255),
    support_phone character varying(50),
    social_links jsonb DEFAULT '{}'::jsonb,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT branding_valid_color_primary CHECK (((color_primary)::text ~ '^#[0-9A-F]{6}$'::text)),
    CONSTRAINT branding_valid_color_secondary CHECK (((color_secondary)::text ~ '^#[0-9A-F]{6}$'::text))
);


--
-- Name: TABLE organization_branding; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.organization_branding IS 'White label branding configuration (logo, colors, domain)';


--
-- Name: organization_payment_methods; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organization_payment_methods (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    type character varying(20) NOT NULL,
    is_default boolean DEFAULT false,
    card_last4 character varying(4),
    card_brand character varying(20),
    card_exp_month integer,
    card_exp_year integer,
    card_holder_name character varying(100),
    bank_name character varying(100),
    account_last4 character varying(4),
    account_holder_name character varying(100),
    payment_gateway character varying(50),
    gateway_payment_method_id character varying(100),
    is_active boolean DEFAULT true,
    verified boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE organization_payment_methods; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.organization_payment_methods IS 'Saved payment methods for organizations';


--
-- Name: organization_settings; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organization_settings (
    organization_id uuid NOT NULL,
    billing_enabled boolean DEFAULT true NOT NULL,
    kyc_enabled boolean DEFAULT false NOT NULL,
    fiat_enabled boolean DEFAULT false NOT NULL,
    features jsonb DEFAULT '{}'::jsonb NOT NULL,
    limits jsonb DEFAULT '{}'::jsonb NOT NULL,
    branding jsonb DEFAULT '{}'::jsonb NOT NULL,
    integrations jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE organization_settings; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.organization_settings IS 'Organization-specific configuration (features, limits, branding, integrations)';


--
-- Name: COLUMN organization_settings.features; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organization_settings.features IS 'Feature flags and settings (flexible JSON)';


--
-- Name: COLUMN organization_settings.limits; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organization_settings.limits IS 'Transaction and usage limits (flexible JSON)';


--
-- Name: COLUMN organization_settings.branding; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organization_settings.branding IS 'White Label branding (logo, colors, domain)';


--
-- Name: COLUMN organization_settings.integrations; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organization_settings.integrations IS 'External integrations (Safina API, webhooks, etc.)';


--
-- Name: organization_subscriptions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organization_subscriptions (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    plan_id uuid NOT NULL,
    billing_cycle character varying(20) DEFAULT 'monthly'::character varying,
    start_date timestamp with time zone DEFAULT now(),
    end_date timestamp with time zone,
    status character varying(20) DEFAULT 'pending'::character varying,
    price numeric(12,2) NOT NULL,
    currency character varying(10) DEFAULT 'KGS'::character varying,
    is_trial boolean DEFAULT false,
    trial_end_date timestamp with time zone,
    auto_renew boolean DEFAULT true,
    payment_method character varying(50),
    cancelled_at timestamp with time zone,
    cancellation_reason text,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    stripe_customer_id text,
    stripe_subscription_id text,
    stripe_session_id text,
    CONSTRAINT org_subscriptions_valid_status CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'trialing'::character varying, 'past_due'::character varying, 'suspended'::character varying, 'cancelled'::character varying, 'expired'::character varying, 'pending'::character varying])::text[])))
);


--
-- Name: TABLE organization_subscriptions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.organization_subscriptions IS 'Active subscriptions for organizations';


--
-- Name: organizations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.organizations (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(255) NOT NULL,
    slug character varying(100) NOT NULL,
    license_type character varying(20) DEFAULT 'free'::character varying NOT NULL,
    status character varying(20) DEFAULT 'active'::character varying NOT NULL,
    subscription_expires_at timestamp without time zone,
    email character varying(255),
    phone character varying(50),
    address text,
    city character varying(100),
    country character varying(100),
    settings jsonb DEFAULT '{}'::jsonb NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    updated_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by integer,
    display_name character varying(255),
    kyb_verified boolean DEFAULT false,
    kyb_verified_at timestamp with time zone,
    CONSTRAINT organizations_license_type_check CHECK (((license_type)::text = ANY ((ARRAY['free'::character varying, 'basic'::character varying, 'pro'::character varying, 'enterprise'::character varying])::text[]))),
    CONSTRAINT organizations_status_check CHECK (((status)::text = ANY ((ARRAY['active'::character varying, 'suspended'::character varying, 'cancelled'::character varying])::text[])))
);


--
-- Name: TABLE organizations; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.organizations IS 'Multi-tenant organizations for ORGON-Safina integration (170+ crypto exchanges)';


--
-- Name: COLUMN organizations.slug; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.slug IS 'URL-friendly unique identifier for organization (e.g., exchange-1, safina-kyrgyzstan)';


--
-- Name: COLUMN organizations.license_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.license_type IS 'Subscription tier: free (trial), basic, pro, enterprise';


--
-- Name: COLUMN organizations.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.status IS 'Organization status: active, suspended (payment issue), cancelled';


--
-- Name: COLUMN organizations.settings; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.settings IS 'Flexible JSON for future features (API keys, webhooks, etc.)';


--
-- Name: COLUMN organizations.display_name; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.organizations.display_name IS 'Human-readable display name for the organization (e.g., Safina Exchange)';


--
-- Name: partner_api_keys; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partner_api_keys (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    partner_id uuid NOT NULL,
    api_key character varying(64) NOT NULL,
    api_secret_hash character varying(255) NOT NULL,
    name character varying(255),
    scopes text[],
    expires_at timestamp with time zone,
    last_used_at timestamp with time zone,
    ip_whitelist text[],
    created_at timestamp with time zone DEFAULT now(),
    revoked_at timestamp with time zone
);


--
-- Name: TABLE partner_api_keys; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.partner_api_keys IS 'Multiple API keys per partner for rotation and environments';


--
-- Name: partner_request_nonces; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partner_request_nonces (
    partner_id uuid NOT NULL,
    nonce character varying(128) NOT NULL,
    seen_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: TABLE partner_request_nonces; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.partner_request_nonces IS 'B2B replay-protection — one row per (partner_id, nonce). Pruned hourly.';


--
-- Name: partner_webhooks; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partner_webhooks (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    partner_id uuid NOT NULL,
    url character varying(500) NOT NULL,
    event_types text[] DEFAULT '{}'::text[] NOT NULL,
    description text,
    is_active boolean DEFAULT true,
    secret character varying(255),
    success_count integer DEFAULT 0,
    failure_count integer DEFAULT 0,
    last_triggered_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: partners; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.partners (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(255) NOT NULL,
    api_key character varying(64) NOT NULL,
    api_secret_hash character varying(255) NOT NULL,
    tier character varying(50) DEFAULT 'free'::character varying,
    rate_limit_per_minute integer DEFAULT 60,
    webhook_url character varying(500),
    webhook_secret character varying(255),
    ec_address character varying(42) NOT NULL,
    status character varying(20) DEFAULT 'active'::character varying,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    organization_id uuid
);


--
-- Name: TABLE partners; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.partners IS 'B2B partners/tenants with API access';


--
-- Name: COLUMN partners.organization_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.partners.organization_id IS 'Organization this B2B partner is scoped to. NULL = unscoped (legacy or platform-admin).';


--
-- Name: password_reset_tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.password_reset_tokens (
    id integer NOT NULL,
    user_id integer NOT NULL,
    token text NOT NULL,
    expires_at timestamp with time zone NOT NULL,
    used boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE password_reset_tokens; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.password_reset_tokens IS 'Password reset tokens (one-time use)';


--
-- Name: password_reset_tokens_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.password_reset_tokens_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: password_reset_tokens_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.password_reset_tokens_id_seq OWNED BY public.password_reset_tokens.id;


--
-- Name: payment_gateways; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payment_gateways (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    gateway_name character varying(50) NOT NULL,
    gateway_type character varying(20) NOT NULL,
    config jsonb DEFAULT '{}'::jsonb NOT NULL,
    fee_percentage numeric(5,2) DEFAULT 0,
    fee_fixed numeric(12,2) DEFAULT 0,
    fiat_currency character varying(3) DEFAULT 'USD'::character varying,
    min_amount numeric(12,2),
    max_amount numeric(12,2),
    daily_limit numeric(12,2),
    is_active boolean DEFAULT true,
    is_test_mode boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE payment_gateways; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.payment_gateways IS 'Payment gateway configurations (Stripe, PayPal, etc.)';


--
-- Name: payments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.payments (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    invoice_id uuid,
    payment_reference character varying(255) NOT NULL,
    amount numeric(12,2) NOT NULL,
    currency character varying(10) DEFAULT 'KGS'::character varying,
    payment_method character varying(50) NOT NULL,
    payment_gateway character varying(50),
    card_last4 character varying(4),
    card_brand character varying(20),
    status character varying(20) DEFAULT 'pending'::character varying,
    completed_at timestamp with time zone,
    failed_reason text,
    gateway_response jsonb,
    admin_confirmed_by uuid,
    admin_confirmed_at timestamp with time zone,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    CONSTRAINT payments_positive_amount CHECK ((amount >= (0)::numeric)),
    CONSTRAINT payments_valid_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'completed'::character varying, 'failed'::character varying, 'refunded'::character varying])::text[])))
);


--
-- Name: TABLE payments; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.payments IS 'Payment records (card, bank transfer, crypto)';


--
-- Name: COLUMN payments.payment_method; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.payments.payment_method IS 'card, bank_transfer, crypto, manual';


--
-- Name: COLUMN payments.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.payments.status IS 'pending: processing, succeeded: completed, failed: payment failed, refunded: money returned';


--
-- Name: pending_signatures_checked; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.pending_signatures_checked (
    tx_unid character varying(255) NOT NULL,
    checked_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: rate_limit_tracking; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.rate_limit_tracking (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    partner_id uuid NOT NULL,
    endpoint character varying(255) NOT NULL,
    window_start timestamp with time zone NOT NULL,
    request_count integer DEFAULT 1,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE rate_limit_tracking; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.rate_limit_tracking IS 'Track API usage per partner for rate limiting';


--
-- Name: sanctioned_addresses; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sanctioned_addresses (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    address character varying(100) NOT NULL,
    network character varying(20) NOT NULL,
    sanction_type character varying(50) NOT NULL,
    source character varying(100),
    description text,
    is_active boolean DEFAULT true,
    added_at timestamp with time zone DEFAULT now(),
    added_by integer,
    expires_at timestamp with time zone,
    metadata jsonb DEFAULT '{}'::jsonb
);


--
-- Name: TABLE sanctioned_addresses; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.sanctioned_addresses IS 'Blocklist of sanctioned/risky addresses';


--
-- Name: scheduled_transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scheduled_transactions (
    id integer NOT NULL,
    token text NOT NULL,
    to_address text NOT NULL,
    value text NOT NULL,
    info text,
    json_info jsonb,
    scheduled_at timestamp with time zone NOT NULL,
    recurrence_rule text,
    status text DEFAULT 'pending'::text NOT NULL,
    sent_at timestamp with time zone,
    tx_unid text,
    error_message text,
    created_by text,
    created_at timestamp with time zone DEFAULT now() NOT NULL,
    updated_at timestamp with time zone DEFAULT now() NOT NULL,
    next_run_at timestamp with time zone,
    organization_id uuid
);

ALTER TABLE ONLY public.scheduled_transactions FORCE ROW LEVEL SECURITY;


--
-- Name: TABLE scheduled_transactions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.scheduled_transactions IS 'Recurring/scheduled payments';


--
-- Name: COLUMN scheduled_transactions.organization_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.scheduled_transactions.organization_id IS 'Tenant isolation: scheduled transaction belongs to this organization';


--
-- Name: scheduled_transactions_b2b; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.scheduled_transactions_b2b (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    partner_id uuid NOT NULL,
    wallet_name character varying(255) NOT NULL,
    token character varying(100) NOT NULL,
    to_address character varying(255) NOT NULL,
    amount character varying(50) NOT NULL,
    schedule_type character varying(20) NOT NULL,
    schedule_time timestamp with time zone NOT NULL,
    cron_expression character varying(100),
    status character varying(20) DEFAULT 'pending'::character varying,
    last_executed_at timestamp with time zone,
    next_execution_at timestamp with time zone,
    execution_count integer DEFAULT 0,
    max_executions integer,
    tx_unid character varying(255),
    error_message text,
    metadata jsonb DEFAULT '{}'::jsonb,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE scheduled_transactions_b2b; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.scheduled_transactions_b2b IS 'Scheduled and recurring transaction management';


--
-- Name: scheduled_transactions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.scheduled_transactions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: scheduled_transactions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.scheduled_transactions_id_seq OWNED BY public.scheduled_transactions.id;


--
-- Name: signature_history; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.signature_history (
    id integer NOT NULL,
    tx_unid character varying(255) NOT NULL,
    signer_address character varying(255),
    action character varying(50) NOT NULL,
    reason text,
    signed_at timestamp with time zone DEFAULT now(),
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: signature_history_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.signature_history_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: signature_history_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.signature_history_id_seq OWNED BY public.signature_history.id;


--
-- Name: signatures; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.signatures (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    transaction_id uuid,
    user_id integer,
    signature text,
    status character varying(50) DEFAULT 'pending'::character varying,
    created_at timestamp with time zone DEFAULT now(),
    organization_id uuid
);

ALTER TABLE ONLY public.signatures FORCE ROW LEVEL SECURITY;


--
-- Name: TABLE signatures; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.signatures IS 'Multi-signature approvals';


--
-- Name: COLUMN signatures.organization_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.signatures.organization_id IS 'Tenant isolation: signature belongs to this organization';


--
-- Name: subscription_plans; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subscription_plans (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    name character varying(100) NOT NULL,
    slug character varying(50) NOT NULL,
    description text,
    monthly_price numeric(12,2) DEFAULT 0 NOT NULL,
    yearly_price numeric(12,2),
    currency character varying(10) DEFAULT 'KGS'::character varying,
    features jsonb DEFAULT '{}'::jsonb,
    max_organizations integer,
    max_wallets integer,
    max_monthly_transactions integer,
    max_monthly_volume_usd numeric(18,2),
    margin_min numeric(5,2),
    is_active boolean DEFAULT true,
    sort_order integer DEFAULT 0,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE subscription_plans; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.subscription_plans IS 'Pricing tiers (Free, Pro, Enterprise)';


--
-- Name: COLUMN subscription_plans.features; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.subscription_plans.features IS 'JSON object with plan features and limits';


--
-- Name: subscriptions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.subscriptions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    organization_id uuid NOT NULL,
    plan_id uuid NOT NULL,
    status character varying(20) DEFAULT 'trial'::character varying NOT NULL,
    trial_start_date timestamp without time zone,
    trial_end_date timestamp without time zone,
    start_date timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    current_period_start timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    current_period_end timestamp without time zone NOT NULL,
    cancelled_at timestamp without time zone,
    ended_at timestamp without time zone,
    billing_cycle character varying(10) DEFAULT 'monthly'::character varying,
    next_billing_date timestamp without time zone,
    current_usage jsonb DEFAULT '{}'::jsonb,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT subscriptions_status_check CHECK (((status)::text = ANY ((ARRAY['trial'::character varying, 'active'::character varying, 'past_due'::character varying, 'cancelled'::character varying, 'expired'::character varying])::text[])))
);


--
-- Name: TABLE subscriptions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.subscriptions IS 'Active subscriptions for organizations';


--
-- Name: COLUMN subscriptions.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.subscriptions.status IS 'trial: free trial, active: paid, past_due: payment failed, cancelled: user cancelled, expired: ended';


--
-- Name: COLUMN subscriptions.current_usage; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.subscriptions.current_usage IS 'JSON object with current usage metrics for metered billing';


--
-- Name: sync_state; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.sync_state (
    key text NOT NULL,
    value text,
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE sync_state; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.sync_state IS 'Blockchain sync tracking';


--
-- Name: token_balances; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.token_balances (
    id integer NOT NULL,
    token_id character varying(64),
    wallet_id character varying(255),
    network character varying(64),
    token character varying(64) NOT NULL,
    value character varying(64),
    decimals character varying(8),
    value_hex character varying(128),
    updated_at timestamp with time zone DEFAULT now() NOT NULL
);


--
-- Name: token_balances_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.token_balances_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: token_balances_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.token_balances_id_seq OWNED BY public.token_balances.id;


--
-- Name: tokens; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tokens (
    token character varying(255) NOT NULL,
    network_id integer,
    name character varying(255),
    short_name character varying(50),
    decimals integer DEFAULT 18,
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: tokens_info_cache; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tokens_info_cache (
    token character varying(255) NOT NULL,
    commission text,
    commission_min text,
    commission_max text,
    updated_at timestamp with time zone DEFAULT now()
);


--
-- Name: transaction_analytics; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.transaction_analytics (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    partner_id uuid,
    wallet_name character varying(255),
    network_id integer,
    token character varying(50),
    tx_type character varying(20),
    amount_decimal numeric(36,18),
    amount_usd numeric(18,2),
    fee_decimal numeric(36,18),
    fee_usd numeric(18,2),
    status character varying(50),
    tx_hash character varying(255),
    tx_unid character varying(255),
    "timestamp" timestamp with time zone DEFAULT now(),
    metadata jsonb DEFAULT '{}'::jsonb
);


--
-- Name: TABLE transaction_analytics; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.transaction_analytics IS 'Aggregated transaction data for reporting and analytics';


--
-- Name: transaction_fees; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.transaction_fees (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    transaction_id uuid,
    network character varying(50),
    transaction_hash character varying(255),
    amount numeric(36,18),
    token character varying(50),
    amount_usd numeric(18,2),
    exchange_rate numeric(18,8),
    fee_type character varying(50) DEFAULT 'blockchain'::character varying,
    billable boolean DEFAULT true,
    billed_in_invoice_id uuid,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE transaction_fees; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.transaction_fees IS 'Blockchain transaction fees to bill';


--
-- Name: COLUMN transaction_fees.fee_type; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.transaction_fees.fee_type IS 'percentage, fixed, tiered';


--
-- Name: transaction_monitoring_rules; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.transaction_monitoring_rules (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid,
    rule_name character varying(255) NOT NULL,
    rule_type character varying(50) NOT NULL,
    description text,
    rule_config jsonb DEFAULT '{}'::jsonb NOT NULL,
    action character varying(50) DEFAULT 'alert'::character varying,
    severity character varying(20) DEFAULT 'medium'::character varying,
    is_active boolean DEFAULT true,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    created_by integer
);


--
-- Name: TABLE transaction_monitoring_rules; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.transaction_monitoring_rules IS 'AML transaction monitoring rules';


--
-- Name: transactions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.transactions (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    wallet_id uuid,
    tx_hash character varying(255),
    from_address character varying(255),
    to_address character varying(255),
    amount numeric(36,18),
    network integer,
    status character varying(50) DEFAULT 'pending'::character varying,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    organization_id uuid,
    safina_id integer,
    token text,
    token_name text,
    to_addr text,
    value text,
    value_hex text,
    unid text,
    init_ts bigint,
    min_sign integer DEFAULT 0,
    wallet_name text,
    synced_at timestamp with time zone
);

ALTER TABLE ONLY public.transactions FORCE ROW LEVEL SECURITY;


--
-- Name: TABLE transactions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.transactions IS 'Transaction history (send/receive)';


--
-- Name: COLUMN transactions.organization_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.transactions.organization_id IS 'Tenant isolation: transaction belongs to this organization';


--
-- Name: twofa_backup_codes; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.twofa_backup_codes (
    id integer NOT NULL,
    user_id integer NOT NULL,
    code_hash character varying(64) NOT NULL,
    created_at timestamp without time zone NOT NULL,
    used_at timestamp without time zone
);


--
-- Name: TABLE twofa_backup_codes; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.twofa_backup_codes IS 'Backup codes for 2FA recovery';


--
-- Name: twofa_backup_codes_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.twofa_backup_codes_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: twofa_backup_codes_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.twofa_backup_codes_id_seq OWNED BY public.twofa_backup_codes.id;


--
-- Name: tx_signatures; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.tx_signatures (
    id integer NOT NULL,
    tx_unid character varying(255) NOT NULL,
    signer_address character varying(255),
    signature text,
    status character varying(50) DEFAULT 'pending'::character varying,
    signer_id integer,
    organization_id uuid,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    ec_address text,
    sig_type text,
    ec_sign text,
    signed_at timestamp with time zone,
    action character varying(50),
    reason text
);


--
-- Name: tx_signatures_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.tx_signatures_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: tx_signatures_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.tx_signatures_id_seq OWNED BY public.tx_signatures.id;


--
-- Name: upload_assets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.upload_assets (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    organization_id uuid NOT NULL,
    file_name character varying(255) NOT NULL,
    file_type character varying(100),
    file_size_bytes integer,
    storage_provider character varying(50) DEFAULT 'r2'::character varying,
    storage_url text NOT NULL,
    storage_key character varying(255),
    uploaded_by integer,
    uploaded_at timestamp with time zone DEFAULT now(),
    asset_type character varying(50),
    is_public boolean DEFAULT true
);


--
-- Name: TABLE upload_assets; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.upload_assets IS 'Uploaded files (logos, favicons, etc.)';


--
-- Name: user_organizations; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_organizations (
    user_id integer NOT NULL,
    organization_id uuid NOT NULL,
    role character varying(20) DEFAULT 'viewer'::character varying NOT NULL,
    created_at timestamp without time zone DEFAULT now() NOT NULL,
    created_by integer,
    CONSTRAINT user_organizations_role_check CHECK (((role)::text = ANY ((ARRAY['admin'::character varying, 'operator'::character varying, 'viewer'::character varying])::text[])))
);


--
-- Name: TABLE user_organizations; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.user_organizations IS 'Many-to-many: users can belong to multiple organizations with different roles';


--
-- Name: COLUMN user_organizations.role; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.user_organizations.role IS 'Access level: admin (full access), operator (create transactions), viewer (read-only)';


--
-- Name: user_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_sessions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    refresh_token text NOT NULL,
    ip_address text,
    user_agent text,
    expires_at timestamp with time zone NOT NULL,
    created_at timestamp with time zone DEFAULT now()
);


--
-- Name: TABLE user_sessions; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.user_sessions IS 'Active user sessions with refresh tokens';


--
-- Name: user_sessions_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_sessions_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_sessions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_sessions_id_seq OWNED BY public.user_sessions.id;


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id integer NOT NULL,
    email text NOT NULL,
    password_hash text NOT NULL,
    full_name text,
    role text DEFAULT 'viewer'::text NOT NULL,
    is_active boolean DEFAULT true,
    email_verified boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    last_login_at timestamp with time zone,
    totp_secret character varying(32),
    totp_enabled boolean DEFAULT false,
    kyc_verified boolean DEFAULT false,
    kyc_verified_at timestamp with time zone
);


--
-- Name: TABLE users; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.users IS 'System users with authentication and RBAC';


--
-- Name: COLUMN users.role; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.role IS 'User role: admin (full access), signer (can sign TX), viewer (read-only)';


--
-- Name: COLUMN users.totp_secret; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.totp_secret IS 'TOTP secret key (base32 encoded)';


--
-- Name: COLUMN users.totp_enabled; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.users.totp_enabled IS 'Whether TOTP 2FA is enabled';


--
-- Name: users_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.users_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.users_id_seq OWNED BY public.users.id;


--
-- Name: wallets; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.wallets (
    id uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    wallet_id integer,
    name character varying(255) NOT NULL,
    network integer NOT NULL,
    wallet_type integer,
    info text,
    addr character varying(255) DEFAULT ''::character varying,
    addr_info text,
    my_unid character varying(255),
    token_short_names text,
    label text,
    is_favorite boolean DEFAULT false,
    created_at timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now(),
    synced_at timestamp with time zone,
    created_by integer,
    organization_id uuid
);

ALTER TABLE ONLY public.wallets FORCE ROW LEVEL SECURITY;


--
-- Name: TABLE wallets; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.wallets IS 'Cryptocurrency wallets (Tron/BNB/ETH)';


--
-- Name: COLUMN wallets.organization_id; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.wallets.organization_id IS 'Tenant isolation: wallet belongs to this organization';


--
-- Name: webhook_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.webhook_events (
    id uuid DEFAULT gen_random_uuid() NOT NULL,
    partner_id uuid NOT NULL,
    event_type character varying(100) NOT NULL,
    payload jsonb NOT NULL,
    status character varying(20) DEFAULT 'pending'::character varying,
    attempts integer DEFAULT 0,
    max_attempts integer DEFAULT 10,
    last_attempt_at timestamp with time zone,
    next_retry_at timestamp with time zone,
    response_code integer,
    response_body text,
    error_message text,
    created_at timestamp with time zone DEFAULT now(),
    sent_at timestamp with time zone,
    event_id uuid,
    webhook_url text
);


--
-- Name: TABLE webhook_events; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON TABLE public.webhook_events IS 'Event queue for webhook delivery to partners';


--
-- Name: COLUMN webhook_events.payload; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.webhook_events.payload IS 'Event data (JSON)';


--
-- Name: COLUMN webhook_events.status; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.webhook_events.status IS 'pending | delivered | failed | cancelled';


--
-- Name: COLUMN webhook_events.attempts; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.webhook_events.attempts IS 'Number of delivery attempts';


--
-- Name: COLUMN webhook_events.next_retry_at; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON COLUMN public.webhook_events.next_retry_at IS 'Next retry timestamp (exponential backoff)';


--
-- Name: address_book id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.address_book ALTER COLUMN id SET DEFAULT nextval('public.address_book_id_seq'::regclass);


--
-- Name: audit_log id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log ALTER COLUMN id SET DEFAULT nextval('public.audit_log_id_seq'::regclass);


--
-- Name: balance_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.balance_history ALTER COLUMN id SET DEFAULT nextval('public.balance_history_id_seq'::regclass);


--
-- Name: kyb_records id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kyb_records ALTER COLUMN id SET DEFAULT nextval('public.kyb_records_id_seq'::regclass);


--
-- Name: kyc_records id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kyc_records ALTER COLUMN id SET DEFAULT nextval('public.kyc_records_id_seq'::regclass);


--
-- Name: password_reset_tokens id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens ALTER COLUMN id SET DEFAULT nextval('public.password_reset_tokens_id_seq'::regclass);


--
-- Name: scheduled_transactions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scheduled_transactions ALTER COLUMN id SET DEFAULT nextval('public.scheduled_transactions_id_seq'::regclass);


--
-- Name: signature_history id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.signature_history ALTER COLUMN id SET DEFAULT nextval('public.signature_history_id_seq'::regclass);


--
-- Name: token_balances id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.token_balances ALTER COLUMN id SET DEFAULT nextval('public.token_balances_id_seq'::regclass);


--
-- Name: twofa_backup_codes id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.twofa_backup_codes ALTER COLUMN id SET DEFAULT nextval('public.twofa_backup_codes_id_seq'::regclass);


--
-- Name: tx_signatures id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tx_signatures ALTER COLUMN id SET DEFAULT nextval('public.tx_signatures_id_seq'::regclass);


--
-- Name: user_sessions id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sessions ALTER COLUMN id SET DEFAULT nextval('public.user_sessions_id_seq'::regclass);


--
-- Name: users id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users ALTER COLUMN id SET DEFAULT nextval('public.users_id_seq'::regclass);


--
-- Name: address_book_b2b address_book_b2b_partner_id_address_network_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.address_book_b2b
    ADD CONSTRAINT address_book_b2b_partner_id_address_network_id_key UNIQUE (partner_id, address, network_id);


--
-- Name: address_book_b2b address_book_b2b_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.address_book_b2b
    ADD CONSTRAINT address_book_b2b_pkey PRIMARY KEY (id);


--
-- Name: address_book address_book_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.address_book
    ADD CONSTRAINT address_book_pkey PRIMARY KEY (id);


--
-- Name: aml_alerts aml_alerts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aml_alerts
    ADD CONSTRAINT aml_alerts_pkey PRIMARY KEY (id);


--
-- Name: audit_log_b2b audit_log_b2b_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log_b2b
    ADD CONSTRAINT audit_log_b2b_pkey PRIMARY KEY (id);


--
-- Name: audit_log audit_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log
    ADD CONSTRAINT audit_log_pkey PRIMARY KEY (id);


--
-- Name: audit_logs audit_logs_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_pkey PRIMARY KEY (id);


--
-- Name: balance_history balance_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.balance_history
    ADD CONSTRAINT balance_history_pkey PRIMARY KEY (id);


--
-- Name: bank_accounts bank_accounts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bank_accounts
    ADD CONSTRAINT bank_accounts_pkey PRIMARY KEY (id);


--
-- Name: compliance_reports compliance_reports_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.compliance_reports
    ADD CONSTRAINT compliance_reports_pkey PRIMARY KEY (id);


--
-- Name: contacts contacts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contacts
    ADD CONSTRAINT contacts_pkey PRIMARY KEY (id);


--
-- Name: crypto_exchange_rates crypto_exchange_rates_crypto_currency_fiat_currency_source_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crypto_exchange_rates
    ADD CONSTRAINT crypto_exchange_rates_crypto_currency_fiat_currency_source_key UNIQUE (crypto_currency, fiat_currency, source);


--
-- Name: crypto_exchange_rates crypto_exchange_rates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.crypto_exchange_rates
    ADD CONSTRAINT crypto_exchange_rates_pkey PRIMARY KEY (id);


--
-- Name: custom_domains custom_domains_domain_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.custom_domains
    ADD CONSTRAINT custom_domains_domain_key UNIQUE (domain);


--
-- Name: custom_domains custom_domains_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.custom_domains
    ADD CONSTRAINT custom_domains_pkey PRIMARY KEY (id);


--
-- Name: custom_domains custom_domains_verification_token_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.custom_domains
    ADD CONSTRAINT custom_domains_verification_token_key UNIQUE (verification_token);


--
-- Name: email_templates email_templates_organization_id_template_type_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_templates
    ADD CONSTRAINT email_templates_organization_id_template_type_key UNIQUE (organization_id, template_type);


--
-- Name: email_templates email_templates_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_templates
    ADD CONSTRAINT email_templates_pkey PRIMARY KEY (id);


--
-- Name: fiat_transactions fiat_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fiat_transactions
    ADD CONSTRAINT fiat_transactions_pkey PRIMARY KEY (id);


--
-- Name: invoice_line_items invoice_line_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_line_items
    ADD CONSTRAINT invoice_line_items_pkey PRIMARY KEY (id);


--
-- Name: invoices invoices_invoice_number_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_invoice_number_key UNIQUE (invoice_number);


--
-- Name: invoices invoices_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_pkey PRIMARY KEY (id);


--
-- Name: kyb_records kyb_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kyb_records
    ADD CONSTRAINT kyb_records_pkey PRIMARY KEY (id);


--
-- Name: kyb_submissions kyb_submissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kyb_submissions
    ADD CONSTRAINT kyb_submissions_pkey PRIMARY KEY (id);


--
-- Name: kyc_records kyc_records_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kyc_records
    ADD CONSTRAINT kyc_records_pkey PRIMARY KEY (id);


--
-- Name: kyc_submissions kyc_submissions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kyc_submissions
    ADD CONSTRAINT kyc_submissions_pkey PRIMARY KEY (id);


--
-- Name: networks_cache networks_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.networks_cache
    ADD CONSTRAINT networks_cache_pkey PRIMARY KEY (network_id);


--
-- Name: networks networks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.networks
    ADD CONSTRAINT networks_pkey PRIMARY KEY (network_id);


--
-- Name: organization_branding organization_branding_organization_id_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_branding
    ADD CONSTRAINT organization_branding_organization_id_key UNIQUE (organization_id);


--
-- Name: organization_branding organization_branding_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_branding
    ADD CONSTRAINT organization_branding_pkey PRIMARY KEY (id);


--
-- Name: organization_payment_methods organization_payment_methods_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_payment_methods
    ADD CONSTRAINT organization_payment_methods_pkey PRIMARY KEY (id);


--
-- Name: organization_settings organization_settings_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_settings
    ADD CONSTRAINT organization_settings_pkey PRIMARY KEY (organization_id);


--
-- Name: organization_subscriptions organization_subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_subscriptions
    ADD CONSTRAINT organization_subscriptions_pkey PRIMARY KEY (id);


--
-- Name: organizations organizations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_pkey PRIMARY KEY (id);


--
-- Name: organizations organizations_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_slug_key UNIQUE (slug);


--
-- Name: partner_api_keys partner_api_keys_api_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partner_api_keys
    ADD CONSTRAINT partner_api_keys_api_key_key UNIQUE (api_key);


--
-- Name: partner_api_keys partner_api_keys_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partner_api_keys
    ADD CONSTRAINT partner_api_keys_pkey PRIMARY KEY (id);


--
-- Name: partner_request_nonces partner_request_nonces_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partner_request_nonces
    ADD CONSTRAINT partner_request_nonces_pkey PRIMARY KEY (partner_id, nonce);


--
-- Name: partner_webhooks partner_webhooks_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partner_webhooks
    ADD CONSTRAINT partner_webhooks_pkey PRIMARY KEY (id);


--
-- Name: partners partners_api_key_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partners
    ADD CONSTRAINT partners_api_key_key UNIQUE (api_key);


--
-- Name: partners partners_ec_address_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partners
    ADD CONSTRAINT partners_ec_address_key UNIQUE (ec_address);


--
-- Name: partners partners_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partners
    ADD CONSTRAINT partners_pkey PRIMARY KEY (id);


--
-- Name: password_reset_tokens password_reset_tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_pkey PRIMARY KEY (id);


--
-- Name: password_reset_tokens password_reset_tokens_token_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_token_key UNIQUE (token);


--
-- Name: payment_gateways payment_gateways_organization_id_gateway_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_gateways
    ADD CONSTRAINT payment_gateways_organization_id_gateway_name_key UNIQUE (organization_id, gateway_name);


--
-- Name: payment_gateways payment_gateways_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_gateways
    ADD CONSTRAINT payment_gateways_pkey PRIMARY KEY (id);


--
-- Name: payments payments_payment_reference_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_payment_reference_key UNIQUE (payment_reference);


--
-- Name: payments payments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_pkey PRIMARY KEY (id);


--
-- Name: pending_signatures_checked pending_signatures_checked_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.pending_signatures_checked
    ADD CONSTRAINT pending_signatures_checked_pkey PRIMARY KEY (tx_unid);


--
-- Name: rate_limit_tracking rate_limit_tracking_partner_id_endpoint_window_start_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rate_limit_tracking
    ADD CONSTRAINT rate_limit_tracking_partner_id_endpoint_window_start_key UNIQUE (partner_id, endpoint, window_start);


--
-- Name: rate_limit_tracking rate_limit_tracking_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rate_limit_tracking
    ADD CONSTRAINT rate_limit_tracking_pkey PRIMARY KEY (id);


--
-- Name: sanctioned_addresses sanctioned_addresses_address_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sanctioned_addresses
    ADD CONSTRAINT sanctioned_addresses_address_key UNIQUE (address);


--
-- Name: sanctioned_addresses sanctioned_addresses_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sanctioned_addresses
    ADD CONSTRAINT sanctioned_addresses_pkey PRIMARY KEY (id);


--
-- Name: scheduled_transactions_b2b scheduled_transactions_b2b_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scheduled_transactions_b2b
    ADD CONSTRAINT scheduled_transactions_b2b_pkey PRIMARY KEY (id);


--
-- Name: scheduled_transactions scheduled_transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scheduled_transactions
    ADD CONSTRAINT scheduled_transactions_pkey PRIMARY KEY (id);


--
-- Name: scheduled_transactions scheduled_transactions_tx_unid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scheduled_transactions
    ADD CONSTRAINT scheduled_transactions_tx_unid_key UNIQUE (tx_unid);


--
-- Name: signature_history signature_history_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.signature_history
    ADD CONSTRAINT signature_history_pkey PRIMARY KEY (id);


--
-- Name: signatures signatures_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.signatures
    ADD CONSTRAINT signatures_pkey PRIMARY KEY (id);


--
-- Name: subscription_plans subscription_plans_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_plans
    ADD CONSTRAINT subscription_plans_pkey PRIMARY KEY (id);


--
-- Name: subscription_plans subscription_plans_slug_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscription_plans
    ADD CONSTRAINT subscription_plans_slug_key UNIQUE (slug);


--
-- Name: subscriptions subscriptions_organization_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_organization_unique UNIQUE (organization_id);


--
-- Name: subscriptions subscriptions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_pkey PRIMARY KEY (id);


--
-- Name: sync_state sync_state_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sync_state
    ADD CONSTRAINT sync_state_pkey PRIMARY KEY (key);


--
-- Name: token_balances token_balances_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.token_balances
    ADD CONSTRAINT token_balances_pkey PRIMARY KEY (id);


--
-- Name: tokens_info_cache tokens_info_cache_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tokens_info_cache
    ADD CONSTRAINT tokens_info_cache_pkey PRIMARY KEY (token);


--
-- Name: tokens tokens_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tokens
    ADD CONSTRAINT tokens_pkey PRIMARY KEY (token);


--
-- Name: transaction_analytics transaction_analytics_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transaction_analytics
    ADD CONSTRAINT transaction_analytics_pkey PRIMARY KEY (id);


--
-- Name: transaction_fees transaction_fees_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transaction_fees
    ADD CONSTRAINT transaction_fees_pkey PRIMARY KEY (id);


--
-- Name: transaction_monitoring_rules transaction_monitoring_rules_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transaction_monitoring_rules
    ADD CONSTRAINT transaction_monitoring_rules_pkey PRIMARY KEY (id);


--
-- Name: transactions transactions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_pkey PRIMARY KEY (id);


--
-- Name: transactions transactions_tx_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_tx_hash_key UNIQUE (tx_hash);


--
-- Name: transactions transactions_unid_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_unid_key UNIQUE (unid);


--
-- Name: twofa_backup_codes twofa_backup_codes_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.twofa_backup_codes
    ADD CONSTRAINT twofa_backup_codes_pkey PRIMARY KEY (id);


--
-- Name: twofa_backup_codes twofa_backup_codes_user_id_code_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.twofa_backup_codes
    ADD CONSTRAINT twofa_backup_codes_user_id_code_hash_key UNIQUE (user_id, code_hash);


--
-- Name: tx_signatures tx_signatures_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tx_signatures
    ADD CONSTRAINT tx_signatures_pkey PRIMARY KEY (id);


--
-- Name: tx_signatures tx_signatures_tx_ec_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tx_signatures
    ADD CONSTRAINT tx_signatures_tx_ec_unique UNIQUE (tx_unid, signer_address);


--
-- Name: tx_signatures tx_signatures_tx_ec_unique2; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tx_signatures
    ADD CONSTRAINT tx_signatures_tx_ec_unique2 UNIQUE (tx_unid, ec_address);


--
-- Name: upload_assets upload_assets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.upload_assets
    ADD CONSTRAINT upload_assets_pkey PRIMARY KEY (id);


--
-- Name: user_organizations user_organizations_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_organizations
    ADD CONSTRAINT user_organizations_pkey PRIMARY KEY (user_id, organization_id);


--
-- Name: user_sessions user_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_pkey PRIMARY KEY (id);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: wallets wallets_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_name_key UNIQUE (name);


--
-- Name: wallets wallets_name_unique; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_name_unique UNIQUE (name);


--
-- Name: wallets wallets_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_pkey PRIMARY KEY (id);


--
-- Name: webhook_events webhook_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_events
    ADD CONSTRAINT webhook_events_pkey PRIMARY KEY (id);


--
-- Name: idx_address_book_address; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_address_book_address ON public.address_book USING btree (address);


--
-- Name: idx_address_book_b2b_favorite; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_address_book_b2b_favorite ON public.address_book_b2b USING btree (is_favorite) WHERE (is_favorite = true);


--
-- Name: idx_address_book_b2b_network; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_address_book_b2b_network ON public.address_book_b2b USING btree (network_id);


--
-- Name: idx_address_book_b2b_partner; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_address_book_b2b_partner ON public.address_book_b2b USING btree (partner_id);


--
-- Name: idx_address_book_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_address_book_category ON public.address_book USING btree (category);


--
-- Name: idx_address_book_favorite; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_address_book_favorite ON public.address_book USING btree (favorite);


--
-- Name: idx_address_book_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_address_book_name ON public.address_book USING btree (name);


--
-- Name: idx_addresses_favorite; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_addresses_favorite ON public.address_book_b2b USING btree (partner_id, is_favorite, created_at DESC) WHERE (is_favorite = true);


--
-- Name: idx_addresses_network; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_addresses_network ON public.address_book_b2b USING btree (partner_id, network_id, created_at DESC);


--
-- Name: idx_addresses_partner_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_addresses_partner_created ON public.address_book_b2b USING btree (partner_id, created_at DESC);


--
-- Name: idx_addresses_unique; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_addresses_unique ON public.address_book_b2b USING btree (partner_id, address, network_id);


--
-- Name: idx_aml_alerts_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_aml_alerts_created ON public.aml_alerts USING btree (created_at DESC);


--
-- Name: idx_aml_alerts_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_aml_alerts_org ON public.aml_alerts USING btree (organization_id);


--
-- Name: idx_aml_alerts_severity; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_aml_alerts_severity ON public.aml_alerts USING btree (severity);


--
-- Name: idx_aml_alerts_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_aml_alerts_status ON public.aml_alerts USING btree (status);


--
-- Name: idx_aml_alerts_transaction; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_aml_alerts_transaction ON public.aml_alerts USING btree (transaction_id);


--
-- Name: idx_aml_alerts_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_aml_alerts_type ON public.aml_alerts USING btree (alert_type);


--
-- Name: idx_analytics_network; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_analytics_network ON public.transaction_analytics USING btree (partner_id, network_id, "timestamp" DESC) WHERE (partner_id IS NOT NULL);


--
-- Name: idx_analytics_partner_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_analytics_partner_timestamp ON public.transaction_analytics USING btree (partner_id, "timestamp" DESC) WHERE (partner_id IS NOT NULL);


--
-- Name: idx_analytics_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_analytics_status ON public.transaction_analytics USING btree (partner_id, status, "timestamp" DESC) WHERE (partner_id IS NOT NULL);


--
-- Name: idx_analytics_token; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_analytics_token ON public.transaction_analytics USING btree (partner_id, token, "timestamp" DESC) WHERE ((partner_id IS NOT NULL) AND (token IS NOT NULL));


--
-- Name: idx_analytics_wallet_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_analytics_wallet_timestamp ON public.transaction_analytics USING btree (wallet_name, "timestamp" DESC);


--
-- Name: idx_audit_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_action ON public.audit_log_b2b USING btree (action, partner_id, "timestamp" DESC);


--
-- Name: idx_audit_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_created ON public.audit_logs USING btree (created_at DESC);


--
-- Name: idx_audit_log_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_action ON public.audit_log USING btree (action);


--
-- Name: idx_audit_log_b2b_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_b2b_action ON public.audit_log_b2b USING btree (action);


--
-- Name: idx_audit_log_b2b_partner_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_b2b_partner_id ON public.audit_log_b2b USING btree (partner_id);


--
-- Name: idx_audit_log_b2b_resource; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_b2b_resource ON public.audit_log_b2b USING btree (resource_type, resource_id);


--
-- Name: idx_audit_log_b2b_result; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_b2b_result ON public.audit_log_b2b USING btree (result);


--
-- Name: idx_audit_log_b2b_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_b2b_timestamp ON public.audit_log_b2b USING btree ("timestamp" DESC);


--
-- Name: idx_audit_log_b2b_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_b2b_user_id ON public.audit_log_b2b USING btree (user_id);


--
-- Name: idx_audit_log_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_created_at ON public.audit_log USING btree (created_at DESC);


--
-- Name: idx_audit_log_resource; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_resource ON public.audit_log USING btree (resource_type, resource_id);


--
-- Name: idx_audit_log_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_log_user ON public.audit_log USING btree (user_id);


--
-- Name: idx_audit_logs_organization; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_logs_organization ON public.audit_logs USING btree (organization_id);


--
-- Name: idx_audit_partner_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_partner_timestamp ON public.audit_log_b2b USING btree (partner_id, "timestamp" DESC);


--
-- Name: idx_audit_resource; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_resource ON public.audit_log_b2b USING btree (resource_type, resource_id, "timestamp" DESC);


--
-- Name: idx_audit_result; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_result ON public.audit_log_b2b USING btree (result, partner_id, "timestamp" DESC) WHERE ((result)::text = 'failure'::text);


--
-- Name: idx_audit_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_audit_user ON public.audit_log_b2b USING btree (user_id, "timestamp" DESC) WHERE (user_id IS NOT NULL);


--
-- Name: idx_backup_codes_unused; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_backup_codes_unused ON public.twofa_backup_codes USING btree (user_id, used_at) WHERE (used_at IS NULL);


--
-- Name: idx_backup_codes_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_backup_codes_user ON public.twofa_backup_codes USING btree (user_id);


--
-- Name: idx_balance_history_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_balance_history_org ON public.balance_history USING btree (organization_id, recorded_at DESC);


--
-- Name: idx_balance_history_recorded_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_balance_history_recorded_at ON public.balance_history USING btree (recorded_at DESC);


--
-- Name: idx_bank_accounts_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bank_accounts_org ON public.bank_accounts USING btree (organization_id);


--
-- Name: idx_bank_accounts_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bank_accounts_status ON public.bank_accounts USING btree (verification_status);


--
-- Name: idx_bank_accounts_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_bank_accounts_user ON public.bank_accounts USING btree (user_id);


--
-- Name: idx_branding_domain; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_branding_domain ON public.organization_branding USING btree (custom_domain);


--
-- Name: idx_branding_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_branding_org ON public.organization_branding USING btree (organization_id);


--
-- Name: idx_compliance_reports_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_compliance_reports_org ON public.compliance_reports USING btree (organization_id);


--
-- Name: idx_compliance_reports_period; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_compliance_reports_period ON public.compliance_reports USING btree (period_start, period_end);


--
-- Name: idx_compliance_reports_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_compliance_reports_status ON public.compliance_reports USING btree (status);


--
-- Name: idx_compliance_reports_submitted; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_compliance_reports_submitted ON public.compliance_reports USING btree (submitted_to_regulator);


--
-- Name: idx_compliance_reports_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_compliance_reports_type ON public.compliance_reports USING btree (report_type);


--
-- Name: idx_contacts_address; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contacts_address ON public.contacts USING btree (address);


--
-- Name: idx_contacts_category; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contacts_category ON public.contacts USING btree (category);


--
-- Name: idx_contacts_favorite; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contacts_favorite ON public.contacts USING btree (is_favorite);


--
-- Name: idx_contacts_network; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contacts_network ON public.contacts USING btree (network);


--
-- Name: idx_contacts_organization; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contacts_organization ON public.contacts USING btree (organization_id);


--
-- Name: idx_contacts_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_contacts_user ON public.contacts USING btree (user_id);


--
-- Name: idx_custom_domains_domain; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_custom_domains_domain ON public.custom_domains USING btree (domain);


--
-- Name: idx_custom_domains_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_custom_domains_org ON public.custom_domains USING btree (organization_id);


--
-- Name: idx_custom_domains_verified; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_custom_domains_verified ON public.custom_domains USING btree (verified);


--
-- Name: idx_email_templates_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_email_templates_org ON public.email_templates USING btree (organization_id);


--
-- Name: idx_email_templates_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_email_templates_type ON public.email_templates USING btree (template_type);


--
-- Name: idx_exchange_rates_fetched; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_exchange_rates_fetched ON public.crypto_exchange_rates USING btree (fetched_at DESC);


--
-- Name: idx_exchange_rates_pair; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_exchange_rates_pair ON public.crypto_exchange_rates USING btree (crypto_currency, fiat_currency);


--
-- Name: idx_fiat_txn_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fiat_txn_created ON public.fiat_transactions USING btree (created_at DESC);


--
-- Name: idx_fiat_txn_gateway_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fiat_txn_gateway_id ON public.fiat_transactions USING btree (gateway_transaction_id);


--
-- Name: idx_fiat_txn_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fiat_txn_org ON public.fiat_transactions USING btree (organization_id);


--
-- Name: idx_fiat_txn_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fiat_txn_status ON public.fiat_transactions USING btree (status);


--
-- Name: idx_fiat_txn_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fiat_txn_type ON public.fiat_transactions USING btree (transaction_type);


--
-- Name: idx_fiat_txn_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_fiat_txn_user ON public.fiat_transactions USING btree (user_id);


--
-- Name: idx_invoice_line_items_invoice; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoice_line_items_invoice ON public.invoice_line_items USING btree (invoice_id);


--
-- Name: idx_invoice_line_items_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoice_line_items_type ON public.invoice_line_items USING btree (item_type);


--
-- Name: idx_invoices_due_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoices_due_date ON public.invoices USING btree (due_date);


--
-- Name: idx_invoices_number; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoices_number ON public.invoices USING btree (invoice_number);


--
-- Name: idx_invoices_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoices_org ON public.invoices USING btree (organization_id);


--
-- Name: idx_invoices_organization; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoices_organization ON public.invoices USING btree (organization_id);


--
-- Name: idx_invoices_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoices_status ON public.invoices USING btree (status);


--
-- Name: idx_invoices_subscription; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_invoices_subscription ON public.invoices USING btree (subscription_id);


--
-- Name: idx_kyb_records_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_kyb_records_org ON public.kyb_records USING btree (organization_id);


--
-- Name: idx_kyb_records_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_kyb_records_status ON public.kyb_records USING btree (verification_status);


--
-- Name: idx_kyb_submissions_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_kyb_submissions_org ON public.kyb_submissions USING btree (organization_id);


--
-- Name: idx_kyb_submissions_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_kyb_submissions_status ON public.kyb_submissions USING btree (status);


--
-- Name: idx_kyc_records_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_kyc_records_org ON public.kyc_records USING btree (organization_id);


--
-- Name: idx_kyc_records_risk; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_kyc_records_risk ON public.kyc_records USING btree (risk_level);


--
-- Name: idx_kyc_records_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_kyc_records_status ON public.kyc_records USING btree (verification_status);


--
-- Name: idx_kyc_records_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_kyc_records_user ON public.kyc_records USING btree (user_id);


--
-- Name: idx_kyc_submissions_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_kyc_submissions_org ON public.kyc_submissions USING btree (organization_id);


--
-- Name: idx_kyc_submissions_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_kyc_submissions_status ON public.kyc_submissions USING btree (status);


--
-- Name: idx_kyc_submissions_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_kyc_submissions_user ON public.kyc_submissions USING btree (user_id);


--
-- Name: idx_monitoring_rules_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_monitoring_rules_active ON public.transaction_monitoring_rules USING btree (is_active);


--
-- Name: idx_monitoring_rules_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_monitoring_rules_org ON public.transaction_monitoring_rules USING btree (organization_id);


--
-- Name: idx_monitoring_rules_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_monitoring_rules_type ON public.transaction_monitoring_rules USING btree (rule_type);


--
-- Name: idx_networks_cache_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_networks_cache_status ON public.networks_cache USING btree (status);


--
-- Name: idx_org_payment_methods_default; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_org_payment_methods_default ON public.organization_payment_methods USING btree (is_default);


--
-- Name: idx_org_payment_methods_one_default; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX idx_org_payment_methods_one_default ON public.organization_payment_methods USING btree (organization_id) WHERE (is_default = true);


--
-- Name: idx_org_payment_methods_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_org_payment_methods_org ON public.organization_payment_methods USING btree (organization_id);


--
-- Name: idx_org_subs_stripe_customer; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_org_subs_stripe_customer ON public.organization_subscriptions USING btree (stripe_customer_id) WHERE (stripe_customer_id IS NOT NULL);


--
-- Name: idx_org_subscriptions_end_date; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_org_subscriptions_end_date ON public.organization_subscriptions USING btree (end_date);


--
-- Name: idx_org_subscriptions_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_org_subscriptions_org ON public.organization_subscriptions USING btree (organization_id);


--
-- Name: idx_org_subscriptions_plan; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_org_subscriptions_plan ON public.organization_subscriptions USING btree (plan_id);


--
-- Name: idx_org_subscriptions_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_org_subscriptions_status ON public.organization_subscriptions USING btree (status);


--
-- Name: idx_organization_settings_billing; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_organization_settings_billing ON public.organization_settings USING btree (billing_enabled);


--
-- Name: idx_organization_settings_kyc; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_organization_settings_kyc ON public.organization_settings USING btree (kyc_enabled);


--
-- Name: idx_organization_settings_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_organization_settings_org ON public.organization_settings USING btree (organization_id);


--
-- Name: idx_organizations_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_organizations_created_at ON public.organizations USING btree (created_at);


--
-- Name: idx_organizations_license; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_organizations_license ON public.organizations USING btree (license_type);


--
-- Name: idx_organizations_slug; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_organizations_slug ON public.organizations USING btree (slug);


--
-- Name: idx_organizations_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_organizations_status ON public.organizations USING btree (status);


--
-- Name: idx_partner_api_keys_api_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_partner_api_keys_api_key ON public.partner_api_keys USING btree (api_key);


--
-- Name: idx_partner_api_keys_expires; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_partner_api_keys_expires ON public.partner_api_keys USING btree (expires_at) WHERE (expires_at IS NOT NULL);


--
-- Name: idx_partner_api_keys_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_partner_api_keys_key ON public.partner_api_keys USING btree (api_key) WHERE (revoked_at IS NULL);


--
-- Name: idx_partner_api_keys_partner; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_partner_api_keys_partner ON public.partner_api_keys USING btree (partner_id, created_at DESC);


--
-- Name: idx_partner_api_keys_partner_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_partner_api_keys_partner_id ON public.partner_api_keys USING btree (partner_id);


--
-- Name: idx_partner_api_keys_revoked; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_partner_api_keys_revoked ON public.partner_api_keys USING btree (revoked_at) WHERE (revoked_at IS NULL);


--
-- Name: idx_partner_request_nonces_seen_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_partner_request_nonces_seen_at ON public.partner_request_nonces USING btree (seen_at);


--
-- Name: idx_partner_webhooks_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_partner_webhooks_active ON public.partner_webhooks USING btree (is_active);


--
-- Name: idx_partner_webhooks_partner_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_partner_webhooks_partner_id ON public.partner_webhooks USING btree (partner_id);


--
-- Name: idx_partners_api_key; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_partners_api_key ON public.partners USING btree (api_key) WHERE ((status)::text = 'active'::text);


--
-- Name: idx_partners_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_partners_created_at ON public.partners USING btree (created_at);


--
-- Name: idx_partners_ec_address; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_partners_ec_address ON public.partners USING btree (ec_address);


--
-- Name: idx_partners_organization_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_partners_organization_id ON public.partners USING btree (organization_id) WHERE (organization_id IS NOT NULL);


--
-- Name: idx_partners_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_partners_status ON public.partners USING btree (status);


--
-- Name: idx_partners_tier; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_partners_tier ON public.partners USING btree (tier);


--
-- Name: idx_password_reset_tokens_token; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_password_reset_tokens_token ON public.password_reset_tokens USING btree (token);


--
-- Name: idx_password_reset_tokens_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_password_reset_tokens_user ON public.password_reset_tokens USING btree (user_id);


--
-- Name: idx_payment_gateways_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payment_gateways_active ON public.payment_gateways USING btree (is_active);


--
-- Name: idx_payment_gateways_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payment_gateways_org ON public.payment_gateways USING btree (organization_id);


--
-- Name: idx_payments_invoice; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payments_invoice ON public.payments USING btree (invoice_id);


--
-- Name: idx_payments_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payments_org ON public.payments USING btree (organization_id);


--
-- Name: idx_payments_organization; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payments_organization ON public.payments USING btree (organization_id);


--
-- Name: idx_payments_reference; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payments_reference ON public.payments USING btree (payment_reference);


--
-- Name: idx_payments_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_payments_status ON public.payments USING btree (status);


--
-- Name: idx_pending_sig_checked_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_pending_sig_checked_at ON public.pending_signatures_checked USING btree (checked_at DESC);


--
-- Name: idx_rate_limit_tracking_partner; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rate_limit_tracking_partner ON public.rate_limit_tracking USING btree (partner_id);


--
-- Name: idx_rate_limit_tracking_window; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rate_limit_tracking_window ON public.rate_limit_tracking USING btree (window_start);


--
-- Name: idx_rate_limits_check; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rate_limits_check ON public.rate_limit_tracking USING btree (partner_id, endpoint, window_start DESC);


--
-- Name: idx_rate_limits_window; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_rate_limits_window ON public.rate_limit_tracking USING btree (window_start);


--
-- Name: idx_sanctioned_addresses_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sanctioned_addresses_active ON public.sanctioned_addresses USING btree (is_active);


--
-- Name: idx_sanctioned_addresses_address; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sanctioned_addresses_address ON public.sanctioned_addresses USING btree (address);


--
-- Name: idx_sanctioned_addresses_network; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sanctioned_addresses_network ON public.sanctioned_addresses USING btree (network);


--
-- Name: idx_scheduled_next_run; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scheduled_next_run ON public.scheduled_transactions USING btree (next_run_at);


--
-- Name: idx_scheduled_partner_list; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scheduled_partner_list ON public.scheduled_transactions_b2b USING btree (partner_id, created_at DESC);


--
-- Name: idx_scheduled_partner_next_exec; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scheduled_partner_next_exec ON public.scheduled_transactions_b2b USING btree (partner_id, next_execution_at) WHERE ((status)::text = 'pending'::text);


--
-- Name: idx_scheduled_pending; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scheduled_pending ON public.scheduled_transactions_b2b USING btree (status, next_execution_at) WHERE ((status)::text = 'pending'::text);


--
-- Name: idx_scheduled_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scheduled_status ON public.scheduled_transactions USING btree (status);


--
-- Name: idx_scheduled_transactions_organization; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scheduled_transactions_organization ON public.scheduled_transactions USING btree (organization_id);


--
-- Name: idx_scheduled_tx_b2b_next_exec; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scheduled_tx_b2b_next_exec ON public.scheduled_transactions_b2b USING btree (next_execution_at) WHERE ((status)::text = 'pending'::text);


--
-- Name: idx_scheduled_tx_b2b_partner; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scheduled_tx_b2b_partner ON public.scheduled_transactions_b2b USING btree (partner_id);


--
-- Name: idx_scheduled_tx_b2b_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scheduled_tx_b2b_status ON public.scheduled_transactions_b2b USING btree (status);


--
-- Name: idx_scheduled_tx_b2b_wallet; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scheduled_tx_b2b_wallet ON public.scheduled_transactions_b2b USING btree (wallet_name);


--
-- Name: idx_scheduled_tx_next_run; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scheduled_tx_next_run ON public.scheduled_transactions USING btree (status, next_run_at);


--
-- Name: idx_scheduled_tx_status_time; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scheduled_tx_status_time ON public.scheduled_transactions USING btree (status, scheduled_at);


--
-- Name: idx_scheduled_wallet; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_scheduled_wallet ON public.scheduled_transactions_b2b USING btree (wallet_name, status, next_execution_at);


--
-- Name: idx_sig_history_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sig_history_action ON public.signature_history USING btree (action);


--
-- Name: idx_sig_history_signed; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sig_history_signed ON public.signature_history USING btree (signed_at);


--
-- Name: idx_sig_history_tx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_sig_history_tx ON public.signature_history USING btree (tx_unid);


--
-- Name: idx_signatures_organization; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_signatures_organization ON public.signatures USING btree (organization_id);


--
-- Name: idx_signatures_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_signatures_status ON public.signatures USING btree (status);


--
-- Name: idx_signatures_transaction; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_signatures_transaction ON public.signatures USING btree (transaction_id);


--
-- Name: idx_signatures_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_signatures_user ON public.signatures USING btree (user_id);


--
-- Name: idx_subscription_plans_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_subscription_plans_active ON public.subscription_plans USING btree (is_active);


--
-- Name: idx_subscription_plans_slug; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_subscription_plans_slug ON public.subscription_plans USING btree (slug);


--
-- Name: idx_subscriptions_next_billing; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_subscriptions_next_billing ON public.subscriptions USING btree (next_billing_date);


--
-- Name: idx_subscriptions_organization; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_subscriptions_organization ON public.subscriptions USING btree (organization_id);


--
-- Name: idx_subscriptions_plan; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_subscriptions_plan ON public.subscriptions USING btree (plan_id);


--
-- Name: idx_subscriptions_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_subscriptions_status ON public.subscriptions USING btree (status);


--
-- Name: idx_token_balances_token; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_token_balances_token ON public.token_balances USING btree (token);


--
-- Name: idx_token_balances_wallet; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_token_balances_wallet ON public.token_balances USING btree (wallet_id);


--
-- Name: idx_transaction_analytics_network; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transaction_analytics_network ON public.transaction_analytics USING btree (network_id);


--
-- Name: idx_transaction_analytics_partner; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transaction_analytics_partner ON public.transaction_analytics USING btree (partner_id);


--
-- Name: idx_transaction_analytics_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transaction_analytics_status ON public.transaction_analytics USING btree (status);


--
-- Name: idx_transaction_analytics_timestamp; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transaction_analytics_timestamp ON public.transaction_analytics USING btree ("timestamp" DESC);


--
-- Name: idx_transaction_analytics_token; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transaction_analytics_token ON public.transaction_analytics USING btree (token);


--
-- Name: idx_transaction_analytics_wallet; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transaction_analytics_wallet ON public.transaction_analytics USING btree (wallet_name);


--
-- Name: idx_transaction_fees_billable; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transaction_fees_billable ON public.transaction_fees USING btree (billable);


--
-- Name: idx_transaction_fees_invoice; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transaction_fees_invoice ON public.transaction_fees USING btree (billed_in_invoice_id);


--
-- Name: idx_transaction_fees_network; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transaction_fees_network ON public.transaction_fees USING btree (network);


--
-- Name: idx_transaction_fees_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transaction_fees_org ON public.transaction_fees USING btree (organization_id);


--
-- Name: idx_transaction_fees_organization; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transaction_fees_organization ON public.transaction_fees USING btree (organization_id);


--
-- Name: idx_transaction_fees_transaction; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transaction_fees_transaction ON public.transaction_fees USING btree (transaction_id);


--
-- Name: idx_transaction_fees_unbilled; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transaction_fees_unbilled ON public.transaction_fees USING btree (organization_id, billable) WHERE (billed_in_invoice_id IS NULL);


--
-- Name: idx_transactions_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transactions_created ON public.transactions USING btree (created_at DESC);


--
-- Name: idx_transactions_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transactions_hash ON public.transactions USING btree (tx_hash);


--
-- Name: idx_transactions_network; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transactions_network ON public.transactions USING btree (network, created_at DESC);


--
-- Name: idx_transactions_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transactions_org ON public.transactions USING btree (organization_id);


--
-- Name: idx_transactions_organization; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transactions_organization ON public.transactions USING btree (organization_id);


--
-- Name: idx_transactions_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transactions_status ON public.transactions USING btree (status);


--
-- Name: idx_transactions_tx_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transactions_tx_hash ON public.transactions USING btree (tx_hash);


--
-- Name: idx_transactions_unid; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transactions_unid ON public.transactions USING btree (unid) WHERE (unid IS NOT NULL);


--
-- Name: idx_transactions_wallet; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_transactions_wallet ON public.transactions USING btree (wallet_id);


--
-- Name: idx_tx_signatures_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tx_signatures_status ON public.tx_signatures USING btree (status);


--
-- Name: idx_tx_signatures_tx; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_tx_signatures_tx ON public.tx_signatures USING btree (tx_unid);


--
-- Name: idx_upload_assets_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_upload_assets_org ON public.upload_assets USING btree (organization_id);


--
-- Name: idx_upload_assets_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_upload_assets_type ON public.upload_assets USING btree (asset_type);


--
-- Name: idx_user_organizations_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_organizations_org ON public.user_organizations USING btree (organization_id);


--
-- Name: idx_user_organizations_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_organizations_role ON public.user_organizations USING btree (role);


--
-- Name: idx_user_organizations_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_organizations_user ON public.user_organizations USING btree (user_id);


--
-- Name: idx_user_sessions_expires; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_sessions_expires ON public.user_sessions USING btree (expires_at);


--
-- Name: idx_user_sessions_token; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_sessions_token ON public.user_sessions USING btree (refresh_token);


--
-- Name: idx_user_sessions_user; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_user_sessions_user ON public.user_sessions USING btree (user_id);


--
-- Name: idx_users_active; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_active ON public.users USING btree (is_active);


--
-- Name: idx_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_email ON public.users USING btree (email);


--
-- Name: idx_users_role; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_users_role ON public.users USING btree (role);


--
-- Name: idx_wallets_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_wallets_created ON public.wallets USING btree (created_at DESC);


--
-- Name: idx_wallets_name; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_wallets_name ON public.wallets USING btree (name);


--
-- Name: idx_wallets_network; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_wallets_network ON public.wallets USING btree (network);


--
-- Name: idx_wallets_org; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_wallets_org ON public.wallets USING btree (organization_id);


--
-- Name: idx_wallets_organization; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_wallets_organization ON public.wallets USING btree (organization_id);


--
-- Name: idx_webhook_events_created_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_webhook_events_created_at ON public.webhook_events USING btree (created_at DESC);


--
-- Name: idx_webhook_events_event_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_webhook_events_event_id ON public.webhook_events USING btree (event_id);


--
-- Name: idx_webhook_events_event_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_webhook_events_event_type ON public.webhook_events USING btree (event_type);


--
-- Name: idx_webhook_events_next_retry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_webhook_events_next_retry ON public.webhook_events USING btree (next_retry_at) WHERE ((status)::text = 'pending'::text);


--
-- Name: idx_webhook_events_partner_created; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_webhook_events_partner_created ON public.webhook_events USING btree (partner_id, created_at DESC);


--
-- Name: idx_webhook_events_partner_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_webhook_events_partner_id ON public.webhook_events USING btree (partner_id);


--
-- Name: idx_webhook_events_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_webhook_events_status ON public.webhook_events USING btree (status);


--
-- Name: idx_webhook_events_status_retry; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_webhook_events_status_retry ON public.webhook_events USING btree (status, next_retry_at) WHERE ((status)::text = 'pending'::text);


--
-- Name: idx_webhooks_event_type; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_webhooks_event_type ON public.webhook_events USING btree (event_type, partner_id, created_at DESC);


--
-- Name: idx_webhooks_failed; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_webhooks_failed ON public.webhook_events USING btree (partner_id, status, created_at DESC) WHERE ((status)::text = 'failed'::text);


--
-- Name: idx_webhooks_partner_history; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_webhooks_partner_history ON public.webhook_events USING btree (partner_id, created_at DESC);


--
-- Name: idx_webhooks_retry_queue; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_webhooks_retry_queue ON public.webhook_events USING btree (status, next_retry_at) WHERE ((status)::text = ANY ((ARRAY['pending'::character varying, 'retrying'::character varying])::text[]));


--
-- Name: uniq_org_subs_stripe_sub; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uniq_org_subs_stripe_sub ON public.organization_subscriptions USING btree (stripe_subscription_id) WHERE (stripe_subscription_id IS NOT NULL);


--
-- Name: uniq_sig_history_tx_signer_action; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX uniq_sig_history_tx_signer_action ON public.signature_history USING btree (tx_unid, signer_address, action) WHERE (signer_address IS NOT NULL);


--
-- Name: INDEX uniq_sig_history_tx_signer_action; Type: COMMENT; Schema: public; Owner: -
--

COMMENT ON INDEX public.uniq_sig_history_tx_signer_action IS 'Replay/double-sign guard: one row per (tx_unid, signer, action). NULL signer rows are exempt.';


--
-- Name: address_book_b2b address_book_b2b_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER address_book_b2b_updated_at BEFORE UPDATE ON public.address_book_b2b FOR EACH ROW EXECUTE FUNCTION public.update_partners_updated_at();


--
-- Name: address_book address_book_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER address_book_updated_at BEFORE UPDATE ON public.address_book FOR EACH ROW EXECUTE FUNCTION public.update_address_book_updated_at();


--
-- Name: invoices before_insert_invoice_number; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER before_insert_invoice_number BEFORE INSERT ON public.invoices FOR EACH ROW EXECUTE FUNCTION public.trigger_generate_invoice_number();


--
-- Name: payments before_insert_payment_number; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER before_insert_payment_number BEFORE INSERT ON public.payments FOR EACH ROW EXECUTE FUNCTION public.trigger_generate_payment_number();


--
-- Name: invoices before_update_invoices_timestamp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER before_update_invoices_timestamp BEFORE UPDATE ON public.invoices FOR EACH ROW EXECUTE FUNCTION public.trigger_update_timestamp();


--
-- Name: payments before_update_payments_timestamp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER before_update_payments_timestamp BEFORE UPDATE ON public.payments FOR EACH ROW EXECUTE FUNCTION public.trigger_update_timestamp();


--
-- Name: subscription_plans before_update_subscription_plans_timestamp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER before_update_subscription_plans_timestamp BEFORE UPDATE ON public.subscription_plans FOR EACH ROW EXECUTE FUNCTION public.trigger_update_timestamp();


--
-- Name: subscriptions before_update_subscriptions_timestamp; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER before_update_subscriptions_timestamp BEFORE UPDATE ON public.subscriptions FOR EACH ROW EXECUTE FUNCTION public.trigger_update_timestamp();


--
-- Name: audit_log orgon_immutable_audit_log; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER orgon_immutable_audit_log BEFORE DELETE OR UPDATE ON public.audit_log FOR EACH ROW EXECUTE FUNCTION public.orgon_block_update_delete();


--
-- Name: signature_history orgon_immutable_signature_history; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER orgon_immutable_signature_history BEFORE DELETE OR UPDATE ON public.signature_history FOR EACH ROW EXECUTE FUNCTION public.orgon_block_update_delete();


--
-- Name: partners partners_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER partners_updated_at BEFORE UPDATE ON public.partners FOR EACH ROW EXECUTE FUNCTION public.update_partners_updated_at();


--
-- Name: scheduled_transactions_b2b scheduled_tx_b2b_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER scheduled_tx_b2b_updated_at BEFORE UPDATE ON public.scheduled_transactions_b2b FOR EACH ROW EXECUTE FUNCTION public.update_partners_updated_at();


--
-- Name: aml_alerts update_aml_alerts_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_aml_alerts_updated_at BEFORE UPDATE ON public.aml_alerts FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: bank_accounts update_bank_accounts_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_bank_accounts_updated_at BEFORE UPDATE ON public.bank_accounts FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: organization_branding update_branding_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_branding_updated_at BEFORE UPDATE ON public.organization_branding FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: compliance_reports update_compliance_reports_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_compliance_reports_updated_at BEFORE UPDATE ON public.compliance_reports FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: contacts update_contacts_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_contacts_updated_at BEFORE UPDATE ON public.contacts FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: custom_domains update_custom_domains_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_custom_domains_updated_at BEFORE UPDATE ON public.custom_domains FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: email_templates update_email_templates_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_email_templates_updated_at BEFORE UPDATE ON public.email_templates FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: invoices update_invoices_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_invoices_updated_at BEFORE UPDATE ON public.invoices FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: kyc_records update_kyc_records_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_kyc_records_updated_at BEFORE UPDATE ON public.kyc_records FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: transaction_monitoring_rules update_monitoring_rules_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_monitoring_rules_updated_at BEFORE UPDATE ON public.transaction_monitoring_rules FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: organization_payment_methods update_org_payment_methods_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_org_payment_methods_updated_at BEFORE UPDATE ON public.organization_payment_methods FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: organization_subscriptions update_org_subscriptions_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_org_subscriptions_updated_at BEFORE UPDATE ON public.organization_subscriptions FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: organization_settings update_organization_settings_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_organization_settings_updated_at BEFORE UPDATE ON public.organization_settings FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: organizations update_organizations_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_organizations_updated_at BEFORE UPDATE ON public.organizations FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: payment_gateways update_payment_gateways_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_payment_gateways_updated_at BEFORE UPDATE ON public.payment_gateways FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: payments update_payments_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_payments_updated_at BEFORE UPDATE ON public.payments FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: scheduled_transactions update_scheduled_transactions_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_scheduled_transactions_updated_at BEFORE UPDATE ON public.scheduled_transactions FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: subscription_plans update_subscription_plans_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_subscription_plans_updated_at BEFORE UPDATE ON public.subscription_plans FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: transactions update_transactions_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_transactions_updated_at BEFORE UPDATE ON public.transactions FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: users update_users_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: wallets update_wallets_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER update_wallets_updated_at BEFORE UPDATE ON public.wallets FOR EACH ROW EXECUTE FUNCTION public.update_updated_at_column();


--
-- Name: users users_updated_at; Type: TRIGGER; Schema: public; Owner: -
--

CREATE TRIGGER users_updated_at BEFORE UPDATE ON public.users FOR EACH ROW EXECUTE FUNCTION public.update_users_updated_at();


--
-- Name: address_book_b2b address_book_b2b_partner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.address_book_b2b
    ADD CONSTRAINT address_book_b2b_partner_id_fkey FOREIGN KEY (partner_id) REFERENCES public.partners(id) ON DELETE CASCADE;


--
-- Name: aml_alerts aml_alerts_assigned_to_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aml_alerts
    ADD CONSTRAINT aml_alerts_assigned_to_fkey FOREIGN KEY (assigned_to) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: aml_alerts aml_alerts_investigated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aml_alerts
    ADD CONSTRAINT aml_alerts_investigated_by_fkey FOREIGN KEY (investigated_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: aml_alerts aml_alerts_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aml_alerts
    ADD CONSTRAINT aml_alerts_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: aml_alerts aml_alerts_transaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aml_alerts
    ADD CONSTRAINT aml_alerts_transaction_id_fkey FOREIGN KEY (transaction_id) REFERENCES public.transactions(id) ON DELETE SET NULL;


--
-- Name: aml_alerts aml_alerts_wallet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.aml_alerts
    ADD CONSTRAINT aml_alerts_wallet_id_fkey FOREIGN KEY (wallet_id) REFERENCES public.wallets(id) ON DELETE SET NULL;


--
-- Name: audit_log_b2b audit_log_b2b_partner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_log_b2b
    ADD CONSTRAINT audit_log_b2b_partner_id_fkey FOREIGN KEY (partner_id) REFERENCES public.partners(id) ON DELETE SET NULL;


--
-- Name: audit_logs audit_logs_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE SET NULL;


--
-- Name: audit_logs audit_logs_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_logs
    ADD CONSTRAINT audit_logs_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: balance_history balance_history_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.balance_history
    ADD CONSTRAINT balance_history_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: bank_accounts bank_accounts_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bank_accounts
    ADD CONSTRAINT bank_accounts_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: bank_accounts bank_accounts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.bank_accounts
    ADD CONSTRAINT bank_accounts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: compliance_reports compliance_reports_generated_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.compliance_reports
    ADD CONSTRAINT compliance_reports_generated_by_fkey FOREIGN KEY (generated_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: compliance_reports compliance_reports_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.compliance_reports
    ADD CONSTRAINT compliance_reports_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: contacts contacts_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contacts
    ADD CONSTRAINT contacts_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: contacts contacts_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.contacts
    ADD CONSTRAINT contacts_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: custom_domains custom_domains_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.custom_domains
    ADD CONSTRAINT custom_domains_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: email_templates email_templates_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_templates
    ADD CONSTRAINT email_templates_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: email_templates email_templates_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.email_templates
    ADD CONSTRAINT email_templates_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: fiat_transactions fiat_transactions_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fiat_transactions
    ADD CONSTRAINT fiat_transactions_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: fiat_transactions fiat_transactions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fiat_transactions
    ADD CONSTRAINT fiat_transactions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: fiat_transactions fk_fiat_txn_bank_account; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.fiat_transactions
    ADD CONSTRAINT fk_fiat_txn_bank_account FOREIGN KEY (bank_account_id) REFERENCES public.bank_accounts(id) ON DELETE SET NULL;


--
-- Name: invoice_line_items invoice_line_items_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoice_line_items
    ADD CONSTRAINT invoice_line_items_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id) ON DELETE CASCADE;


--
-- Name: invoices invoices_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.partners(id) ON DELETE CASCADE;


--
-- Name: invoices invoices_subscription_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.invoices
    ADD CONSTRAINT invoices_subscription_id_fkey FOREIGN KEY (subscription_id) REFERENCES public.organization_subscriptions(id);


--
-- Name: kyb_records kyb_records_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kyb_records
    ADD CONSTRAINT kyb_records_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE SET NULL;


--
-- Name: kyb_records kyb_records_reviewed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kyb_records
    ADD CONSTRAINT kyb_records_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: kyb_records kyb_records_verified_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kyb_records
    ADD CONSTRAINT kyb_records_verified_by_fkey FOREIGN KEY (verified_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: kyb_submissions kyb_submissions_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kyb_submissions
    ADD CONSTRAINT kyb_submissions_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: kyb_submissions kyb_submissions_reviewer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kyb_submissions
    ADD CONSTRAINT kyb_submissions_reviewer_id_fkey FOREIGN KEY (reviewer_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: kyb_submissions kyb_submissions_submitted_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kyb_submissions
    ADD CONSTRAINT kyb_submissions_submitted_by_fkey FOREIGN KEY (submitted_by) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: kyc_records kyc_records_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kyc_records
    ADD CONSTRAINT kyc_records_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE SET NULL;


--
-- Name: kyc_records kyc_records_reviewed_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kyc_records
    ADD CONSTRAINT kyc_records_reviewed_by_fkey FOREIGN KEY (reviewed_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: kyc_records kyc_records_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kyc_records
    ADD CONSTRAINT kyc_records_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: kyc_records kyc_records_verified_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kyc_records
    ADD CONSTRAINT kyc_records_verified_by_fkey FOREIGN KEY (verified_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: kyc_submissions kyc_submissions_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kyc_submissions
    ADD CONSTRAINT kyc_submissions_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE SET NULL;


--
-- Name: kyc_submissions kyc_submissions_reviewer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kyc_submissions
    ADD CONSTRAINT kyc_submissions_reviewer_id_fkey FOREIGN KEY (reviewer_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: kyc_submissions kyc_submissions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.kyc_submissions
    ADD CONSTRAINT kyc_submissions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: organization_branding organization_branding_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_branding
    ADD CONSTRAINT organization_branding_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: organization_payment_methods organization_payment_methods_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_payment_methods
    ADD CONSTRAINT organization_payment_methods_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: organization_settings organization_settings_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_settings
    ADD CONSTRAINT organization_settings_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: organization_subscriptions organization_subscriptions_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_subscriptions
    ADD CONSTRAINT organization_subscriptions_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.partners(id) ON DELETE CASCADE;


--
-- Name: organization_subscriptions organization_subscriptions_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organization_subscriptions
    ADD CONSTRAINT organization_subscriptions_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.subscription_plans(id);


--
-- Name: organizations organizations_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.organizations
    ADD CONSTRAINT organizations_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: partner_api_keys partner_api_keys_partner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partner_api_keys
    ADD CONSTRAINT partner_api_keys_partner_id_fkey FOREIGN KEY (partner_id) REFERENCES public.partners(id) ON DELETE CASCADE;


--
-- Name: partner_request_nonces partner_request_nonces_partner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partner_request_nonces
    ADD CONSTRAINT partner_request_nonces_partner_id_fkey FOREIGN KEY (partner_id) REFERENCES public.partners(id) ON DELETE CASCADE;


--
-- Name: partner_webhooks partner_webhooks_partner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partner_webhooks
    ADD CONSTRAINT partner_webhooks_partner_id_fkey FOREIGN KEY (partner_id) REFERENCES public.partners(id) ON DELETE CASCADE;


--
-- Name: partners partners_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.partners
    ADD CONSTRAINT partners_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE SET NULL;


--
-- Name: password_reset_tokens password_reset_tokens_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.password_reset_tokens
    ADD CONSTRAINT password_reset_tokens_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: payment_gateways payment_gateways_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payment_gateways
    ADD CONSTRAINT payment_gateways_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: payments payments_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_invoice_id_fkey FOREIGN KEY (invoice_id) REFERENCES public.invoices(id);


--
-- Name: payments payments_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.payments
    ADD CONSTRAINT payments_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.partners(id) ON DELETE CASCADE;


--
-- Name: rate_limit_tracking rate_limit_tracking_partner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.rate_limit_tracking
    ADD CONSTRAINT rate_limit_tracking_partner_id_fkey FOREIGN KEY (partner_id) REFERENCES public.partners(id) ON DELETE CASCADE;


--
-- Name: sanctioned_addresses sanctioned_addresses_added_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.sanctioned_addresses
    ADD CONSTRAINT sanctioned_addresses_added_by_fkey FOREIGN KEY (added_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: scheduled_transactions_b2b scheduled_transactions_b2b_partner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scheduled_transactions_b2b
    ADD CONSTRAINT scheduled_transactions_b2b_partner_id_fkey FOREIGN KEY (partner_id) REFERENCES public.partners(id) ON DELETE CASCADE;


--
-- Name: scheduled_transactions scheduled_transactions_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.scheduled_transactions
    ADD CONSTRAINT scheduled_transactions_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: signatures signatures_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.signatures
    ADD CONSTRAINT signatures_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: signatures signatures_transaction_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.signatures
    ADD CONSTRAINT signatures_transaction_id_fkey FOREIGN KEY (transaction_id) REFERENCES public.transactions(id) ON DELETE CASCADE;


--
-- Name: signatures signatures_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.signatures
    ADD CONSTRAINT signatures_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id);


--
-- Name: subscriptions subscriptions_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: subscriptions subscriptions_plan_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.subscriptions
    ADD CONSTRAINT subscriptions_plan_id_fkey FOREIGN KEY (plan_id) REFERENCES public.subscription_plans(id);


--
-- Name: transaction_analytics transaction_analytics_partner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transaction_analytics
    ADD CONSTRAINT transaction_analytics_partner_id_fkey FOREIGN KEY (partner_id) REFERENCES public.partners(id) ON DELETE SET NULL;


--
-- Name: transaction_fees transaction_fees_billed_in_invoice_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transaction_fees
    ADD CONSTRAINT transaction_fees_billed_in_invoice_id_fkey FOREIGN KEY (billed_in_invoice_id) REFERENCES public.invoices(id);


--
-- Name: transaction_fees transaction_fees_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transaction_fees
    ADD CONSTRAINT transaction_fees_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.partners(id) ON DELETE CASCADE;


--
-- Name: transaction_monitoring_rules transaction_monitoring_rules_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transaction_monitoring_rules
    ADD CONSTRAINT transaction_monitoring_rules_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: transaction_monitoring_rules transaction_monitoring_rules_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transaction_monitoring_rules
    ADD CONSTRAINT transaction_monitoring_rules_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: transactions transactions_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: transactions transactions_wallet_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.transactions
    ADD CONSTRAINT transactions_wallet_id_fkey FOREIGN KEY (wallet_id) REFERENCES public.wallets(id) ON DELETE CASCADE;


--
-- Name: twofa_backup_codes twofa_backup_codes_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.twofa_backup_codes
    ADD CONSTRAINT twofa_backup_codes_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: tx_signatures tx_signatures_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tx_signatures
    ADD CONSTRAINT tx_signatures_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE SET NULL;


--
-- Name: tx_signatures tx_signatures_signer_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.tx_signatures
    ADD CONSTRAINT tx_signatures_signer_id_fkey FOREIGN KEY (signer_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: upload_assets upload_assets_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.upload_assets
    ADD CONSTRAINT upload_assets_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: upload_assets upload_assets_uploaded_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.upload_assets
    ADD CONSTRAINT upload_assets_uploaded_by_fkey FOREIGN KEY (uploaded_by) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: user_organizations user_organizations_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_organizations
    ADD CONSTRAINT user_organizations_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: user_organizations user_organizations_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_organizations
    ADD CONSTRAINT user_organizations_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: user_organizations user_organizations_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_organizations
    ADD CONSTRAINT user_organizations_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: user_sessions user_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: wallets wallets_created_by_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_created_by_fkey FOREIGN KEY (created_by) REFERENCES public.users(id);


--
-- Name: wallets wallets_organization_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.wallets
    ADD CONSTRAINT wallets_organization_id_fkey FOREIGN KEY (organization_id) REFERENCES public.organizations(id) ON DELETE CASCADE;


--
-- Name: webhook_events webhook_events_partner_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.webhook_events
    ADD CONSTRAINT webhook_events_partner_id_fkey FOREIGN KEY (partner_id) REFERENCES public.partners(id) ON DELETE CASCADE;


--
-- Name: audit_logs; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.audit_logs ENABLE ROW LEVEL SECURITY;

--
-- Name: audit_logs audit_logs_isolation_policy; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY audit_logs_isolation_policy ON public.audit_logs FOR SELECT USING ((( SELECT orgon_current_org_or_super.is_super
   FROM public.orgon_current_org_or_super() orgon_current_org_or_super(org_id, is_super)) OR (organization_id = ( SELECT orgon_current_org_or_super.org_id
   FROM public.orgon_current_org_or_super() orgon_current_org_or_super(org_id, is_super)))));


--
-- Name: contacts; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.contacts ENABLE ROW LEVEL SECURITY;

--
-- Name: contacts contacts_isolation_policy; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY contacts_isolation_policy ON public.contacts USING (((organization_id = ( SELECT orgon_current_org_or_super.org_id
   FROM public.orgon_current_org_or_super() orgon_current_org_or_super(org_id, is_super))) OR ( SELECT orgon_current_org_or_super.is_super
   FROM public.orgon_current_org_or_super() orgon_current_org_or_super(org_id, is_super)))) WITH CHECK (((organization_id = ( SELECT orgon_current_org_or_super.org_id
   FROM public.orgon_current_org_or_super() orgon_current_org_or_super(org_id, is_super))) OR ( SELECT orgon_current_org_or_super.is_super
   FROM public.orgon_current_org_or_super() orgon_current_org_or_super(org_id, is_super))));


--
-- Name: invoice_line_items; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.invoice_line_items ENABLE ROW LEVEL SECURITY;

--
-- Name: invoices; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.invoices ENABLE ROW LEVEL SECURITY;

--
-- Name: payments; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;

--
-- Name: scheduled_transactions; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.scheduled_transactions ENABLE ROW LEVEL SECURITY;

--
-- Name: scheduled_transactions scheduled_transactions_isolation_policy; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY scheduled_transactions_isolation_policy ON public.scheduled_transactions USING (((organization_id = ( SELECT orgon_current_org_or_super.org_id
   FROM public.orgon_current_org_or_super() orgon_current_org_or_super(org_id, is_super))) OR ( SELECT orgon_current_org_or_super.is_super
   FROM public.orgon_current_org_or_super() orgon_current_org_or_super(org_id, is_super)))) WITH CHECK (((organization_id = ( SELECT orgon_current_org_or_super.org_id
   FROM public.orgon_current_org_or_super() orgon_current_org_or_super(org_id, is_super))) OR ( SELECT orgon_current_org_or_super.is_super
   FROM public.orgon_current_org_or_super() orgon_current_org_or_super(org_id, is_super))));


--
-- Name: signatures; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.signatures ENABLE ROW LEVEL SECURITY;

--
-- Name: signatures signatures_isolation_policy; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY signatures_isolation_policy ON public.signatures USING (((organization_id = ( SELECT orgon_current_org_or_super.org_id
   FROM public.orgon_current_org_or_super() orgon_current_org_or_super(org_id, is_super))) OR ( SELECT orgon_current_org_or_super.is_super
   FROM public.orgon_current_org_or_super() orgon_current_org_or_super(org_id, is_super)))) WITH CHECK (((organization_id = ( SELECT orgon_current_org_or_super.org_id
   FROM public.orgon_current_org_or_super() orgon_current_org_or_super(org_id, is_super))) OR ( SELECT orgon_current_org_or_super.is_super
   FROM public.orgon_current_org_or_super() orgon_current_org_or_super(org_id, is_super))));


--
-- Name: subscription_plans; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.subscription_plans ENABLE ROW LEVEL SECURITY;

--
-- Name: subscription_plans subscription_plans_select; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY subscription_plans_select ON public.subscription_plans FOR SELECT USING (true);


--
-- Name: subscriptions; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.subscriptions ENABLE ROW LEVEL SECURITY;

--
-- Name: transaction_fees; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.transaction_fees ENABLE ROW LEVEL SECURITY;

--
-- Name: transactions; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.transactions ENABLE ROW LEVEL SECURITY;

--
-- Name: transactions transactions_isolation_policy; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY transactions_isolation_policy ON public.transactions USING (((organization_id = ( SELECT orgon_current_org_or_super.org_id
   FROM public.orgon_current_org_or_super() orgon_current_org_or_super(org_id, is_super))) OR ( SELECT orgon_current_org_or_super.is_super
   FROM public.orgon_current_org_or_super() orgon_current_org_or_super(org_id, is_super)))) WITH CHECK (((organization_id = ( SELECT orgon_current_org_or_super.org_id
   FROM public.orgon_current_org_or_super() orgon_current_org_or_super(org_id, is_super))) OR ( SELECT orgon_current_org_or_super.is_super
   FROM public.orgon_current_org_or_super() orgon_current_org_or_super(org_id, is_super))));


--
-- Name: wallets; Type: ROW SECURITY; Schema: public; Owner: -
--

ALTER TABLE public.wallets ENABLE ROW LEVEL SECURITY;

--
-- Name: wallets wallets_isolation_policy; Type: POLICY; Schema: public; Owner: -
--

CREATE POLICY wallets_isolation_policy ON public.wallets USING (((organization_id = ( SELECT orgon_current_org_or_super.org_id
   FROM public.orgon_current_org_or_super() orgon_current_org_or_super(org_id, is_super))) OR ( SELECT orgon_current_org_or_super.is_super
   FROM public.orgon_current_org_or_super() orgon_current_org_or_super(org_id, is_super)))) WITH CHECK (((organization_id = ( SELECT orgon_current_org_or_super.org_id
   FROM public.orgon_current_org_or_super() orgon_current_org_or_super(org_id, is_super))) OR ( SELECT orgon_current_org_or_super.is_super
   FROM public.orgon_current_org_or_super() orgon_current_org_or_super(org_id, is_super))));


--
-- PostgreSQL database dump complete
--


--
-- ORGON canonical-marker addendum (NOT from pg_dump)
--
-- The `schema_migrations` tracking table records which versioned
-- migrations have been applied to this database. It exists so that
-- entrypoint.sh and CI can decide whether to apply 000_canonical
-- (only on a virgin DB) or skip straight to 025+ overlay migrations.
--

CREATE TABLE IF NOT EXISTS public.schema_migrations (
    version     VARCHAR(255) PRIMARY KEY,
    applied_at  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    description TEXT
);

INSERT INTO public.schema_migrations (version, description)
VALUES (
    '000_canonical_schema',
    'Initial canonical schema generated 2026-04-29 from local-dev DB; '
    'consolidates Wave 1-10 historical migrations preserved under _historical/.'
)
ON CONFLICT (version) DO NOTHING;

