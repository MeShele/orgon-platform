-- 025_sumsub_kyc.sql
--
-- Migration: Sumsub KYC integration columns + applicant lookup table.
-- See docs/stories/2-4-sumsub-kyc-architecture.md ADR-6 for rationale.
--
-- This is the FIRST overlay migration on top of the canonical schema
-- (Wave 11 — backend/migrations/000_canonical_schema.sql).
-- Idempotent: every CREATE/ALTER guards on existence; can re-apply.

BEGIN;

-- ─── 1. Extend kyc_submissions with Sumsub-side identifiers ─────────

ALTER TABLE public.kyc_submissions
    ADD COLUMN IF NOT EXISTS sumsub_applicant_id     varchar(64),
    ADD COLUMN IF NOT EXISTS sumsub_inspection_id    varchar(64),
    ADD COLUMN IF NOT EXISTS sumsub_review_result    jsonb,
    ADD COLUMN IF NOT EXISTS sumsub_external_user_id varchar(64);

-- One row in kyc_submissions per Sumsub applicant. NULL allowed —
-- legacy submissions before this migration carry NULLs.
CREATE UNIQUE INDEX IF NOT EXISTS uniq_kyc_submissions_sumsub_applicant
    ON public.kyc_submissions(sumsub_applicant_id)
    WHERE sumsub_applicant_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_kyc_submissions_sumsub_external_user_id
    ON public.kyc_submissions(sumsub_external_user_id)
    WHERE sumsub_external_user_id IS NOT NULL;

-- Existing CHECK constraint on `status` accepts pending/approved/rejected.
-- Sumsub adds two more terminal-ish states. Drop and re-add the check
-- with the expanded set. The new states are documented in
-- docs/stories/2-4-sumsub-kyc-architecture.md ADR-5.

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'kyc_submissions'
          AND constraint_name = 'kyc_submissions_status_check'
    ) THEN
        ALTER TABLE public.kyc_submissions
            DROP CONSTRAINT kyc_submissions_status_check;
    END IF;
END$$;

ALTER TABLE public.kyc_submissions
    ADD CONSTRAINT kyc_submissions_status_check
    CHECK (status IN (
        'pending',
        'approved',
        'rejected',
        'manual_review',
        'needs_resubmit',
        'not_started'
    ));

-- ─── 2. Sumsub applicant lookup cache ───────────────────────────────

CREATE TABLE IF NOT EXISTS public.sumsub_applicants (
    user_id            integer       PRIMARY KEY REFERENCES public.users(id) ON DELETE CASCADE,
    applicant_id       varchar(64)   NOT NULL UNIQUE,
    external_user_id   varchar(64)   NOT NULL,
    level_name         varchar(64)   NOT NULL,
    review_status      varchar(32)   NOT NULL,
    review_result      jsonb,
    last_event_id      varchar(64),  -- for webhook idempotency (ADR-10)
    created_at         timestamptz   NOT NULL DEFAULT now(),
    updated_at         timestamptz   NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sumsub_applicants_review_status
    ON public.sumsub_applicants(review_status);

CREATE INDEX IF NOT EXISTS idx_sumsub_applicants_external_user_id
    ON public.sumsub_applicants(external_user_id);

COMMENT ON TABLE public.sumsub_applicants IS
    'Cache of Sumsub applicant records. Maps ORGON user → applicantId for fast webhook lookup. Wave 19.';

-- ─── 3. updated_at trigger (consistent with rest of canonical schema) ─

CREATE OR REPLACE FUNCTION public.set_sumsub_applicants_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END$$;

DROP TRIGGER IF EXISTS trg_sumsub_applicants_updated_at ON public.sumsub_applicants;
CREATE TRIGGER trg_sumsub_applicants_updated_at
    BEFORE UPDATE ON public.sumsub_applicants
    FOR EACH ROW
    EXECUTE FUNCTION public.set_sumsub_applicants_updated_at();

-- ─── 4. Mark migration applied ──────────────────────────────────────

INSERT INTO public.schema_migrations (version, description)
VALUES ('025_sumsub_kyc', 'Sumsub KYC integration: kyc_submissions extension + sumsub_applicants table')
ON CONFLICT (version) DO NOTHING;

COMMIT;
