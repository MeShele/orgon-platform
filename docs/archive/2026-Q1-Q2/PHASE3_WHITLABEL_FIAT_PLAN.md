# Phase 3: White Label & Fiat Integration

**ETA:** 2-3 days  
**Status:** 🔵 STARTING

---

## Overview

Phase 3 adds white-label capabilities and fiat on/off-ramp для ORGON platform:
- **White Label UI** — organizations can brand their own exchange
- **Fiat Integration** — credit card → crypto, crypto → bank transfers

---

## 3.1: White Label UI (ETA: 1 day)

### Database (Migration 008)
**Tables:**
- `organization_branding` — logo, colors, domain, favicon
- `email_templates` — custom transactional emails (welcome, invoice, KYC)
- `custom_domains` — domain verification, SSL certs

### Backend API
**Service:** `WhiteLabelService`
- `get_branding()` — fetch org branding
- `update_branding()` — update logo/colors/domain
- `get_email_template()` — fetch custom template
- `update_email_template()` — customize email
- `verify_custom_domain()` — DNS verification

**Routes:** `/api/v1/whitelabel/*`
- GET/PUT `/branding`
- GET/PUT `/email-templates/{type}`
- POST `/domains/verify`

### Frontend UI
**Pages:**
- `/settings/branding` — upload logo, choose colors, set domain
- `/settings/email-templates` — customize email text/design
- Dynamic theming system (CSS variables from branding table)

### Features
- Logo upload (S3/CloudFlare R2)
- Color picker (primary, secondary, accent)
- Custom domain (DNS verification flow)
- Email template editor (WYSIWYG or Markdown)
- Preview mode (see changes before publish)

---

## 3.2: Fiat Integration (ETA: 1 day)

### Database (Migration 009)
**Tables:**
- `fiat_transactions` — on-ramp/off-ramp transactions
- `bank_accounts` — user bank accounts для withdrawals
- `payment_gateways` — Stripe/PayPal/bank transfer configs

### Backend API
**Service:** `FiatService`
- `create_onramp_transaction()` — buy crypto with fiat
- `create_offramp_transaction()` — sell crypto for fiat
- `get_payment_methods()` — list available methods
- `add_bank_account()` — add withdrawal bank account
- `process_fiat_payment()` — webhook handler (Stripe/PayPal)

**Routes:** `/api/v1/fiat/*`
- POST `/onramp` — create buy order
- POST `/offramp` — create sell order
- GET `/payment-methods`
- POST `/bank-accounts`
- POST `/webhook/stripe` — Stripe webhook

### Third-Party Integrations
**On-Ramp Providers:**
- Stripe (credit card)
- PayPal
- Bank transfer (manual reconciliation)

**Off-Ramp:**
- Bank transfer (ACH/SEPA/SWIFT)
- PayPal payout

### Frontend UI
**Pages:**
- `/buy-crypto` — credit card → crypto flow
- `/sell-crypto` — crypto → bank transfer flow
- `/payment-methods` — manage cards/bank accounts

### Features
- Stripe Checkout integration
- KYC verification before fiat (link to compliance)
- AML monitoring (large fiat transactions)
- Transaction history (fiat + crypto)

---

## 3.3: Testing & Polish (ETA: 1 day)

### Tests
**White Label:**
- test_white_label_branding.py
- test_email_templates.py
- test_custom_domain_verification.py

**Fiat:**
- test_fiat_onramp.py
- test_fiat_offramp.py
- test_stripe_webhook.py
- test_kyc_fiat_integration.py (must have approved KYC)

### Integration Tests
- E2E: User buys crypto with credit card
- E2E: User sells crypto, gets bank transfer
- White label theme applies across all pages

### Performance
- Logo loading <50ms (CDN)
- Stripe Checkout loads <200ms
- Email sending <1s

### Security
- Custom domain SSL verification
- Bank account ownership verification
- Fiat transaction AML checks

---

## Technical Decisions

### 1. Logo Storage: CloudFlare R2
**Why:** Cheap, fast CDN, S3-compatible API.
**Alternative:** AWS S3 (more expensive).

### 2. Payment Gateway: Stripe
**Why:** Best developer experience, global support.
**Future:** Add more providers (PayPal, Revolut, etc.).

### 3. Email Service: SendGrid or AWS SES
**Why:** Transactional emails need high deliverability.
**Alternative:** Self-hosted (not recommended).

### 4. Custom Domain Verification: DNS TXT record
**Why:** Industry standard (same as Google Workspace).
**Flow:** User adds TXT record → we verify → enable SSL.

### 5. Fiat-Crypto Rate: CoinGecko API
**Why:** Free tier, reliable pricing.
**Fallback:** Safina API rates.

---

## Milestones

| Milestone | ETA | Status |
|-----------|-----|--------|
| Migration 008 (White Label) | +2h | ⏳ |
| WhiteLabelService + API | +4h | ⏳ |
| Frontend branding UI | +6h | ⏳ |
| Migration 009 (Fiat) | +2h | ⏳ |
| FiatService + Stripe integration | +6h | ⏳ |
| Frontend buy/sell pages | +6h | ⏳ |
| Tests (white label + fiat) | +4h | ⏳ |
| **Total** | **30h** | **🔵** |

---

## Risks & Mitigations

### Risk 1: Stripe account approval
**Impact:** Can't test real payments.
**Mitigation:** Use Stripe test mode, mock webhooks.

### Risk 2: Custom domain SSL automation
**Impact:** Manual SSL setup slow.
**Mitigation:** Use Let's Encrypt API or CloudFlare SSL.

### Risk 3: KYC bottleneck for fiat
**Impact:** Users can't buy crypto if KYC pending.
**Mitigation:** Allow small amounts (<$100) без KYC, require для larger.

---

## Success Criteria

**White Label:**
- ✅ Organization can upload logo
- ✅ Custom colors apply globally
- ✅ Custom domain works (DNS verified)
- ✅ Email templates customizable

**Fiat:**
- ✅ User can buy crypto with credit card
- ✅ User can sell crypto for bank transfer
- ✅ Stripe webhook processes payments
- ✅ KYC enforced for fiat transactions

**Testing:**
- ✅ 20+ tests passing (white label + fiat)
- ✅ E2E flows work end-to-end
- ✅ Performance benchmarks met

---

_Starting Phase 3.1 now..._
