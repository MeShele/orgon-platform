# Architecture

> Truthful description of the current implementation. If a feature is
> aspirational, it is marked `(planned)`. If a documented term doesn't match
> reality, fix the doc rather than the code.

---

## High-level

```
                  ┌──────────────────────────────────────────────┐
   browser  ──→   │  Cloudflare DNS                              │
                  │       ↓                                       │
                  │  Coolify v4 host (single-node, Docker)        │
                  │    orgon-frontend (Next.js)                   │
                  │    orgon-backend  (FastAPI)                   │
                  │    postgres-orgon  (per-env DB)               │
                  │       ↓                                       │
                  │  Safina Pay API (custody / signing)           │
                  └──────────────────────────────────────────────┘
```

ORGON is the operational layer above Safina. Safina holds private keys and
performs blockchain signatures; ORGON enforces M-of-N policy, KYC/KYB/AML,
audit log, and the operator UI.

The current canonical deployment target is a fresh Coolify-managed server.
Coolify-specific UUIDs / domains are tracked in [`DEPLOYMENT.md`](DEPLOYMENT.md)
once the new server is provisioned.

---

## Backend

**FastAPI ASGI app** (`backend/main.py`). Lifespan hook initializes a
shared `asyncpg.Pool`, then constructs services on top of it: `WalletService`,
`TransactionService`, `SignatureService`, `OrganizationService`, `AuthService`,
`AuditService`, `WebhookService`, `PartnerService`, `BillingService`,
`EmailService`, etc.

### Middleware stack (outer → inner)

```
LoginRateLimitMiddleware   5 req/min/IP for /api/auth/{login,verify-2fa,
                           reset-password,reset-password/confirm};
                           100 req/min/IP for everything else /api/*.
                           IP from X-Forwarded-For (we sit behind Coolify proxy).
PartnerRateLimitMiddleware tier-based limit for /api/v1/partner/*
B2BReplayMiddleware        HMAC + X-Nonce + X-Timestamp (±5 min drift) on
                           /api/v1/partner/*; nonces deduped via
                           partner_request_nonces PK; 15-min cleanup cron.
APIKeyAuthMiddleware       partner API-key for /api/v1/partner/*
CORSMiddleware             explicit whitelist (orgon.asystem.kg, preview, localhost)
AuthMiddleware             JWT bearer extraction → request.state.user
RLSMiddleware              SET app.current_organization_id + is_super_admin from
                           JWT-resolved org id, before each request
RequestLoggingMiddleware   structured request log; goes through observability
                           formatter when ORGON_JSON_LOGS=1
```

Global 500 handler returns `{detail: "Internal server error", error_id: "<uuid>"}`
to the client; full stacktrace stays in server logs (Sentry-shipped on
`SENTRY_DSN`), keyed by `error_id`.

### Routers

Auth & users:
- `/api/auth` — login, register, refresh, verify-2fa, reset-password
- `/api/users`, `/api/2fa`

Tenant data (JWT-scoped):
- `/api/organizations`, `/api/wallets`, `/api/transactions`,
  `/api/signatures`, `/api/scheduled`, `/api/contacts`,
  `/api/audit`, `/api/analytics`, `/api/networks`, `/api/tokens`,
  `/api/dashboard`

Compliance & ops:
- `/api/v1/billing` (plans, checkout, webhook, subscription, invoice, payment)
- `/api/v1/compliance`, `/api/v1/kyc-kyb`, `/api/v1/whitelabel`, `/api/v1/fiat`
- `/api/documents`, `/api/reports`, `/api/support`

Admin REST (super_admin / company_admin):
- `/api/v1/admin/partners` — provision / list / get / rotate / revoke
  partner API-key principals (`backend/api/routes_admin_partners.py`).

B2B partner API (HMAC + replay-guarded):
- `/api/v1/partner/*` — wallets, transactions, balances, webhooks,
  analytics scoped by `partners.organization_id`.

Health & ops:
- `/api/health` — public liveness
- `/api/health/run-migrations` — super_admin; canonical-then-overlay apply
- `/api/monitoring`, `/api/v1/billing/webhook` (Stripe events, public route
  with HMAC signature verification — no JWT)

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
- JWT carries the user's active `organization_id`.
- `RLSMiddleware` reads the JWT, sets two Postgres session variables
  (`app.current_organization_id`, `app.is_super_admin`) at the start of
  the request and clears them at the end.
- Service layer (`backend/services/*`) **also** filters by
  `organization_id` in every query that reads tenant-scoped data —
  defense in depth.
- Database-level RLS is active on `wallets`, `transactions`,
  `signatures`, `contacts`, `scheduled_transactions`, `audit_log`. The
  `STABLE` SQL helper `orgon_current_org_or_super()` resolves the
  effective scope from session vars, with `super_admin` short-circuit.
  `ENABLE ROW LEVEL SECURITY` + `FORCE ROW LEVEL SECURITY` so even
  table-owner roles cannot bypass.

For B2B partners: `partners.organization_id` (nullable) ties an API-key
principal to one organization, and `routes_partner*.py` resolves it via
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

**Replay / double-sign protection is enforced.** A `UNIQUE INDEX
(tx_unid, signer_address, action)` on `signature_history` (partial —
`WHERE signer_address IS NOT NULL`, so older system rows are exempt).
`SignatureService.sign_transaction` and `reject_transaction` check for
an existing row from the same signer **before** the Safina round-trip
and raise `DuplicateSignatureError`, surfaced as `409 Conflict`. The
UNIQUE index is the second line of defence against race-condition
replays.

**Signer key abstraction (Wave 12).** `backend/safina/signer_backends.py`
defines a `SignerBackend` protocol with three implementations:

| Backend | Status | Use case |
|---|---|---|
| `EnvSignerBackend` | live | dev / preview / single-org pilots — key in env, in-process |
| `KMSSignerBackend` | stub | AWS KMS asymmetric SECP256K1 key. Wiring checklist (6 steps) in docstring |
| `VaultSignerBackend` | stub | HashiCorp Vault Transit engine. Wiring checklist (5 steps) in docstring |

`SafinaSigner` accepts either a hex private key (legacy convenience) or
a `backend=…` kwarg. Internal `_eth_sign` delegates to
`backend.sign_msg_hash` so a KMS or Vault swap is one line. Selection
via `ORGON_SIGNER_BACKEND` env (default `env`).

**Local signature-verification primitive (Wave 13).** `signature_verifier.py`
exposes `recover_signer_address(msg_hash, sig_hex)` and
`verify_signer(msg_hash, sig_hex, expected_address)` — pure ECDSA
recovery, no canonical-payload assumptions. The high-level
`verify_safina_tx_signer(...)` is wired but `canonical_payload()` raises
`NotImplementedError` until Safina's exact byte format is confirmed
against their docs. `is_verification_enabled()` probes this gate so
accidentally setting `ORGON_VERIFY_SAFINA_SIGS=1` without wiring the
payload doesn't silently turn on broken verification.

### B2B HMAC replay protection

Every request to `/api/v1/partner/*` must carry:

- `Authorization: Bearer <api_key>` — the partner principal
- `X-Nonce: <random>` — unique per request
- `X-Timestamp: <unix_seconds>` — within ±5 minutes of server time
- `X-Signature: <hmac_sha256_hex>` of `<method>|<path>|<body>|<nonce>|<timestamp>`,
  keyed by the partner's `api_secret_hash`

The middleware records `(partner_id, nonce)` in `partner_request_nonces`
with a PK-conflict on replay. A 15-minute APScheduler cron prunes
nonces whose `seen_at < NOW() - interval '1 hour'` so the table stays
small. `ORGON_PARTNER_REPLAY_OFF=1` is a dev-only escape hatch.

### Append-only audit

DB triggers `BEFORE UPDATE OR DELETE` on `audit_log` and
`signature_history` `RAISE EXCEPTION 'Table %.% is append-only'`. Once
a row is inserted, it cannot be altered or removed — even by the
application. Verified live (try `UPDATE audit_log SET …` → fails).

### Schema management — Wave 11 onward

The pre-Wave-11 47-file migration chain (legacy
`backend/database/migrations/` + overlay `backend/migrations/[001..024]*`)
is preserved under `backend/migrations/_historical/` for git history but
is no longer applied to fresh installs. The single canonical file
`backend/migrations/000_canonical_schema.sql` (60 tables, 15 functions,
36 triggers, 7 RLS policies, 311 indexes — generated via `pg_dump
--schema-only` from a verified-working DB) is now the source of truth.

A `schema_migrations` tracking table inserted at the bottom of the
canonical (`version='000_canonical_schema'`) gates re-runs:
`entrypoint.sh` (with `ORGON_AUTO_MIGRATE=1`) and
`POST /api/health/run-migrations` both check for the marker before
applying. Future schema changes go in `025_*.sql`, `026_*.sql` … each
**must** be idempotent (`CREATE TABLE IF NOT EXISTS`, `ON CONFLICT DO
NOTHING`, …) and append its own `schema_migrations` row.

### Demo data

`backend/migrations/seed_test_organizations.sql` seeds 2 demo
organizations + 3 user accounts for local dev / e2e tests. Apply once
after the canonical lands; idempotent. Note: this is a fixture, not a
migration — kept in `backend/migrations/` only because the e2e test
suite references that path.

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
  /billing/{success,cancel}    Stripe Checkout return URLs
(authenticated)/      logged-in app — guarded by middleware redirect
  /dashboard, /wallets, /transactions, /signatures, /partners,
  /settings, /settings/keys, /profile, …
```

`middleware.ts` runs on every request, redirects unauthenticated users
hitting protected routes back to `/login?next=<path>`. Public routes
whitelist explicit. AuthContext detects cookie/localStorage drift on
mount and forces re-login if they disagree.

Data fetching: SWR keyed on path, refresh interval 30–60s on dashboard
endpoints. WebSocket `/ws/updates` (auto-refresh on `transaction.created`,
`balance.updated`, `signature.approved`, etc.) — token in path,
verified server-side.

i18n: `next-intl` with locale cookie `NEXT_LOCALE`; full reload on locale
switch (acceptable trade-off for now). RU / EN have parity; KY covers
navigation and dashboard, full landing/compliance parity is `(planned)`.

### Animation stack (per `~/.claude/CLAUDE.md`)

- **Framer Motion** — primary engine.
- **Tailwind + tailwindcss-animate** — micro transitions.
- **Magic UI** — copy-pasted Marquee, NumberTicker, AnimatedBeam.
- **Motion Primitives** — copy-pasted TextEffect (split-by-word reveal).
- Custom: `MagneticButton` (cursor pull) and `TiltCard` (3D rotate from cursor),
  both Framer-Motion-only, transform/opacity only, `prefers-reduced-motion` safe.

---

## Infrastructure

**Coolify v4 self-hosted** runs on the deployment target host. Coolify
orchestrates Docker containers for ORGON (frontend, backend) and the
per-env Postgres instance.

Routing: Coolify's bundled proxy (Traefik) terminates HTTPS and routes
by host header. Cloudflare DNS resolves `orgon.<domain>` and
`orgon-api.<domain>` proxied to the host IP.

Coolify env vars are the source of truth for production config (see
`DEPLOYMENT.md` — Required environment variables table). `.env` files
in repo are for local dev only.

Backups: nightly `pg_dump | gzip` via [`scripts/backup_pg.sh`](scripts/backup_pg.sh)
to `/var/backups/orgon/orgon-<utc-timestamp>.sql.gz`, retained 14 days.
Off-site mirror via S3-compatible upload (AWS S3 / Cloudflare R2 / Wasabi
/ MinIO) when `ORGON_BACKUP_S3_BUCKET` is set; size-verified
post-upload via `aws s3api head-object`. systemd timer template in
`DEPLOYMENT.md`.

Observability: `backend/observability.py` flips on JSON log formatting
(`ORGON_JSON_LOGS=1`) and Sentry SDK init (`SENTRY_DSN=…`). Both off by
default; production env enables them.

---

## Compliance posture (honest)

- **FATF Travel Rule**: implemented at the data-model level (we record
  originator/beneficiary on cross-VASP transfers); integration with
  Sumsub/Notabene is `(planned)`.
- **ISO 27001:2022**: `(planned)`.
- **SOC 2 Type II**: `(planned)`.
- **Лицензия НБ КР**: in progress.
- **AML rule engine**: `aml_alerts` table is a CRUD shell only — no
  detector wired yet (Sumsub / Chainalysis or in-house rules `(planned)`).
- **KYC/KYB document upload**: backend is `placeholder://`; UI shows a
  banner directing users to email. Full S3/R2 + vendor integration
  `(planned)`.

These statuses are reflected in the public footer. Update them as soon as
they change — never display certification we don't actually hold.
