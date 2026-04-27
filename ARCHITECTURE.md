# Architecture

> Truthful description of the current implementation. If a feature is
> aspirational, it is marked `(planned)`. If a documented term doesn't match
> reality, fix the doc rather than the code.

---

## High-level

```
                  ┌──────────────────────────────────────────────┐
   browser  ──→   │  Cloudflare DNS (proxied) → ax41 nginx       │
                  │       ↓                                       │
                  │  10.30.30.132 (asystem-proxmox)               │
                  │       ↓                                       │
                  │  Coolify-managed:                             │
                  │    orgon-frontend (Next.js, port 3100)        │
                  │    orgon-backend  (FastAPI,  port 8891)       │
                  │    orgon-preview-{frontend,backend}           │
                  │    coolify-postgres (shared DB)               │
                  │       ↓                                       │
                  │  Safina Pay API (custody / signing)           │
                  └──────────────────────────────────────────────┘
```

ORGON is the operational layer above Safina. Safina holds private keys and
performs blockchain signatures; ORGON enforces M-of-N policy, KYC/KYB/AML,
audit log, and the operator UI.

---

## Backend

**FastAPI ASGI app** (`backend/main.py`). Lifespan hook initializes a
shared `asyncpg.Pool`, then constructs services on top of it: `WalletService`,
`TransactionService`, `SignatureService`, `OrganizationService`, `AuthService`,
`AuditService`, `WebhookService`, `PartnerService`, etc.

### Middleware stack (outer → inner)

```
LoginRateLimitMiddleware   5 req/min/IP for /api/auth/{login,verify-2fa,
                           reset-password,reset-password/confirm};
                           100 req/min/IP for everything else /api/*.
                           IP from X-Forwarded-For (we sit behind nginx + traefik).
AuditLoggingMiddleware     captures request → audit_log
PartnerRateLimitMiddleware tier-based limit for /api/v1/partner/*
APIKeyAuthMiddleware       partner API-key for /api/v1/partner/*
CORSMiddleware             explicit whitelist (orgon.asystem.kg, preview, localhost)
AuthMiddleware             JWT bearer extraction → request.state.user
RLSMiddleware              SET app.current_tenant from header X-Organization-ID
RequestLoggingMiddleware   structured request log
```

Global 500 handler returns `{detail: "Internal server error", error_id: "<uuid>"}`
to the client; full stacktrace stays in server logs (Coolify), keyed by `error_id`.

### Routers

`/api/auth`, `/api/users`, `/api/2fa`, `/api/organizations`, `/api/wallets`,
`/api/transactions`, `/api/signatures`, `/api/scheduled`, `/api/contacts`,
`/api/audit`, `/api/analytics`, `/api/networks`, `/api/tokens`,
`/api/dashboard`, `/api/health`, `/api/monitoring`, `/api/documents`,
`/api/reports`, `/api/support`, `/api/v1/billing`, `/api/v1/compliance`,
`/api/v1/kyc-kyb`, `/api/v1/whitelabel`, `/api/v1/fiat`,
`/api/v1/partner/*` (B2B), `/api/webhooks/safina/callback`.

Compat routers `/api/billing`, `/api/compliance` returned mock data; **disabled
in this branch** (file kept for reference, removal scheduled).

### RBAC

`backend/rbac.py` defines a role hierarchy:

```
super_admin > platform_admin > company_admin > company_operator
> company_auditor > end_user
```

Plus legacy aliases `admin → company_admin`, `signer → company_operator`,
`viewer → company_auditor` so old `users.role` rows still resolve.

`require_roles("company_admin", ...)` is the canonical FastAPI dependency.
`super_admin` is auto-allowed for any check.

Used on every mutating endpoint and on sensitive read endpoints (audit logs,
detailed health, monitoring, billing admin actions).

### Multi-tenancy — actual implementation

- Each user has zero or more rows in `user_organizations` linking them to
  `organizations` with a per-org role.
- Frontend sends `X-Organization-ID` on every request.
- `RLSMiddleware` reads the header, validates the user belongs to that org,
  and sets two Postgres session variables: `app.current_organization_id`
  and `app.is_super_admin`.
- Service layer (`backend/services/*`) filters by `organization_id` in
  every query that reads tenant-scoped data — defense in depth.
- **Database-level RLS is now active**: migration `016_fix_rls_policies.sql`
  re-creates the policies that the buggy `005` failed to install (the
  original had mismatched quotes around `current_setting('app.is_super_admin', true)`
  on five of the six policies, so none of them were ever applied).
  The new migration uses a `STABLE` SQL helper `orgon_current_org_or_super()`
  and runs `ENABLE ROW LEVEL SECURITY` plus `FORCE ROW LEVEL SECURITY` on
  `wallets`, `transactions`, `signatures`, `contacts`, `scheduled_transactions`,
  `audit_logs`. A `DO $$ … $$` block at the end of the migration verifies
  every policy was created — the migration aborts loudly if any policy is
  missing.

For B2B partners the link is migration `017_partner_org_link.sql`:
`partners.organization_id` (nullable) ties an API-key principal to one
organization, and `routes_partner*.py` resolves it via
`_partner_org_ids(...)` before passing into the service layer's
`org_ids=[…]` filter. A partner whose row has no `organization_id` sees
nothing — that's the safe default.

### Multi-signature — actual implementation

- Wallet has a network, a Safina-side `min_sign` threshold, and a list of
  signer addresses.
- Operator initiates a transaction → ORGON forwards to Safina.
- Each signer's approval is forwarded to Safina; Safina records it.
- ORGON also writes a row to `signature_history` (`tx_unid`,
  `signer_address`, `action`, `signed_at`).
- When threshold reached, Safina broadcasts to chain.

**Replay / double-sign protection is enforced.** Migration `018` adds a
`UNIQUE INDEX (tx_unid, signer_address, action)` on `signature_history`
(partial — `WHERE signer_address IS NOT NULL`, so older system rows are
exempt). `SignatureService.sign_transaction` and `reject_transaction`
check for an existing row from the same signer **before** the Safina
round-trip and raise `DuplicateSignatureError`, which the API surfaces as
`409 Conflict`. The UNIQUE index is the second line of defence against
race-condition replays.

**ORGON does not currently verify signature payloads locally.** It still
trusts Safina's response on the cryptographic side; full canonical-payload
verification (hash of `tx_unid + network + value + to_address` checked
against the EC-recovered signer) is on the next-sprint list. The
HMAC-layer replay window in `middleware_b2b` (nonce + timestamp
±5 min) is also not yet wired.

### Append-only audit

Migration `015_immutability_triggers.sql` adds `BEFORE UPDATE OR DELETE`
triggers on `audit_log` and `signature_history` that `RAISE EXCEPTION`.
Once a row is inserted, it cannot be altered or removed — even by the
application. Verified live in preview DB.

### Demo data

Migrations `013_demo_data.sql` (orgs, members, transactions, signatures)
and `014_wallet_labels.sql` (human-readable wallet labels) seed the
preview/prod database. Both are idempotent (`ON CONFLICT DO NOTHING`,
`UPDATE WHERE label IS NULL`).

---

## Frontend

**Next.js 16** with App Router. Default theme is light (Crimson Ledger
palette: paper `#fafaf7`, ink `#14110f`, brand crimson `#9c1825`); dark theme
is composed (not inverted) — navy `#070d1a` background, brighter crimson.

Routing:

```
(public)/             marketing + auth
  /, /features, /pricing, /about
  /login, /register, /forgot-password, /reset-password
(authenticated)/      logged-in app — guarded by middleware redirect
  /dashboard, /wallets, /transactions, /signatures, …
```

`middleware.ts` runs on every request, redirects unauthenticated users
hitting protected routes back to `/`. Public routes whitelist explicit.

Data fetching: SWR keyed on path, refresh interval 30–60s on dashboard
endpoints. WebSocket `/ws/updates` (auto-refresh on `transaction.created`,
`balance.updated`, `signature.approved`, etc.) — token in path,
verified server-side.

i18n: `next-intl` with locale cookie `NEXT_LOCALE`; full reload on locale
switch (acceptable trade-off for now).

### Animation stack (per `~/.claude/CLAUDE.md`)

- **Framer Motion** — primary engine.
- **Tailwind + tailwindcss-animate** — micro transitions.
- **Magic UI** — copy-pasted Marquee, NumberTicker, AnimatedBeam.
- **Motion Primitives** — copy-pasted TextEffect (split-by-word reveal).
- Custom: `MagneticButton` (cursor pull) and `TiltCard` (3D rotate from cursor),
  both Framer-Motion-only, transform/opacity only, `prefers-reduced-motion` safe.

---

## Infrastructure

**Hetzner-ax41** is the physical Hetzner node. It hosts proxmox VMs, one of
which is `asystem-proxmox` (10.30.30.132). Coolify v4 runs there; it
orchestrates Docker containers for ORGON, the Postgres DB, and other
asystem.kg projects.

Routing: ax41 nginx terminates HTTPS for `*.asystem.kg` and forwards by
host header to the right port on 10.30.30.132. Cloudflare DNS resolves
`orgon.asystem.kg` and `orgon-api.asystem.kg` proxied to the ax41 IP.

Coolify env vars (Coolify UI / API): `DATABASE_URL`, `JWT_SECRET_KEY`,
`SAFINA_EC_PRIVATE_KEY`, `NEXT_PUBLIC_API_URL`. `.env` files in repo are
**not** the source of truth for production — Coolify is.

Backups: nightly `pg_dump` via [`scripts/backup_pg.sh`](scripts/backup_pg.sh)
to `/var/backups/orgon/orgon-<utc-timestamp>.sql.gz`, retained 14 days.
Wiring instructions live in [`CI-CD.md`](CI-CD.md#backups). The script is
in repo; the cron entry on `asystem-proxmox` is the host-side step.

---

## Compliance posture (honest)

- **FATF Travel Rule**: implemented at the data-model level (we record
  originator/beneficiary on cross-VASP transfers); integration with
  Sumsub/Notabene is `(planned)`.
- **ISO 27001:2022**: in progress (gap analysis in 2026Q2).
- **SOC 2 Type I**: in progress.
- **Лицензия НБ КР**: in progress.

These statuses are reflected in the public footer. Update them as soon as
they change — never display certification we don't actually hold.
