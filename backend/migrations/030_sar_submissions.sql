-- Migration 030 — SAR submissions tracking (Wave 24, Story 2.9)
-- Idempotent.

CREATE TABLE IF NOT EXISTS public.sar_submissions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id uuid NOT NULL REFERENCES public.aml_alerts(id) ON DELETE RESTRICT,
    organization_id uuid NOT NULL,
    submitted_by integer NOT NULL,
    submission_backend varchar(50) NOT NULL,
    payload_json jsonb NOT NULL,
    rendered_markdown text NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'prepared'
        CHECK (status IN ('prepared', 'sent', 'acknowledged', 'failed')),
    external_reference varchar(100),
    response_body text,
    submitted_at timestamptz NOT NULL DEFAULT now(),
    acknowledged_at timestamptz,
    CONSTRAINT sar_submissions_one_per_alert UNIQUE (alert_id)
);

COMMENT ON TABLE public.sar_submissions IS
    'SAR (Suspicious Activity Report) submissions to the financial regulator. '
    'One row per alert (UNIQUE constraint), tracks the submission backend, '
    'rendered payload, and the regulator-side reference once acknowledged.';

CREATE INDEX IF NOT EXISTS idx_sar_submissions_org_submitted
    ON public.sar_submissions (organization_id, submitted_at DESC);

CREATE INDEX IF NOT EXISTS idx_sar_submissions_status
    ON public.sar_submissions (status, submitted_at DESC)
    WHERE status IN ('prepared', 'failed');
