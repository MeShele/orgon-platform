-- 026_sumsub_kyb.sql
--
-- Migration: Sumsub KYB integration columns + organization-scoped
-- applicant lookup table.
--
-- Mirror of 025_sumsub_kyc.sql but per-organization rather than
-- per-user. KYB applicants live in their own table; webhook handler
-- routes events by `externalUserId` prefix:
--    "orgon-user-<int>"  → KYC, sumsub_applicants
--    "orgon-org-<uuid>"  → KYB, sumsub_kyb_applicants
--
-- See docs/stories/2-5-sumsub-kyb-architecture.md ADR-1, ADR-2.
-- Idempotent: every CREATE/ALTER guards on existence; safe re-run.

BEGIN;

-- ─── 1. Extend kyb_submissions with Sumsub-side identifiers ─────────

ALTER TABLE public.kyb_submissions
    ADD COLUMN IF NOT EXISTS sumsub_applicant_id     varchar(64),
    ADD COLUMN IF NOT EXISTS sumsub_inspection_id    varchar(64),
    ADD COLUMN IF NOT EXISTS sumsub_review_result    jsonb,
    ADD COLUMN IF NOT EXISTS sumsub_external_user_id varchar(64);

CREATE UNIQUE INDEX IF NOT EXISTS uniq_kyb_submissions_sumsub_applicant
    ON public.kyb_submissions(sumsub_applicant_id)
    WHERE sumsub_applicant_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_kyb_submissions_sumsub_external_user_id
    ON public.kyb_submissions(sumsub_external_user_id)
    WHERE sumsub_external_user_id IS NOT NULL;

-- ─── 2. Drop+re-add status check with same expanded enum as KYC ─────

DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'kyb_submissions'
          AND constraint_name = 'kyb_submissions_status_check'
    ) THEN
        ALTER TABLE public.kyb_submissions
            DROP CONSTRAINT kyb_submissions_status_check;
    END IF;
END$$;

ALTER TABLE public.kyb_submissions
    ADD CONSTRAINT kyb_submissions_status_check
    CHECK (status IN (
        'pending',
        'approved',
        'rejected',
        'manual_review',
        'needs_resubmit',
        'not_started'
    ));

-- ─── 3. Sumsub KYB applicant lookup table ───────────────────────────

CREATE TABLE IF NOT EXISTS public.sumsub_kyb_applicants (
    organization_id    uuid          PRIMARY KEY REFERENCES public.organizations(id) ON DELETE CASCADE,
    applicant_id       varchar(64)   NOT NULL UNIQUE,
    external_user_id   varchar(64)   NOT NULL,
    level_name         varchar(64)   NOT NULL,
    review_status      varchar(32)   NOT NULL,
    review_result      jsonb,
    last_event_id      varchar(64),  -- webhook idempotency (mirror of KYC ADR-10)
    created_at         timestamptz   NOT NULL DEFAULT now(),
    updated_at         timestamptz   NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sumsub_kyb_applicants_review_status
    ON public.sumsub_kyb_applicants(review_status);

CREATE INDEX IF NOT EXISTS idx_sumsub_kyb_applicants_external_user_id
    ON public.sumsub_kyb_applicants(external_user_id);

COMMENT ON TABLE public.sumsub_kyb_applicants IS
    'Cache of Sumsub KYB applicant records. Maps ORGON organization → applicantId for fast webhook lookup. Wave 20.';

-- ─── 4. updated_at trigger — reuse function from migration 025 ──────

DROP TRIGGER IF EXISTS trg_sumsub_kyb_applicants_updated_at ON public.sumsub_kyb_applicants;
CREATE TRIGGER trg_sumsub_kyb_applicants_updated_at
    BEFORE UPDATE ON public.sumsub_kyb_applicants
    FOR EACH ROW
    EXECUTE FUNCTION public.set_sumsub_applicants_updated_at();

-- ─── 5. Mark migration applied ──────────────────────────────────────

INSERT INTO public.schema_migrations (version, description)
VALUES ('026_sumsub_kyb', 'Sumsub KYB integration: kyb_submissions extension + sumsub_kyb_applicants table')
ON CONFLICT (version) DO NOTHING;

COMMIT;
