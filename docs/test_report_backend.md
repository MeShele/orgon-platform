# Backend Audit Report — ORGON Platform

**Date:** 2026-02-14  
**Auditor:** Atlas (automated)  
**Backend:** FastAPI + PostgreSQL + Safina API  

---

## 1. API Endpoints Inventory & Status

### ✅ Working Endpoints

| Module | Endpoint | Method | Status | Notes |
|--------|----------|--------|--------|-------|
| **Health** | `/api/health` | GET | ✅ OK | Returns service status |
| | `/api/health/detailed` | GET | ✅ OK | Returns "healthy" with details |
| | `/api/health/safina` | GET | ✅ OK | Safina API connectivity check |
| **Auth** | `/api/auth/register` | POST | ✅ OK | Now supports 6 roles |
| | `/api/auth/login` | POST | ✅ OK | Returns JWT tokens |
| | `/api/auth/verify-2fa` | POST | ✅ OK | 2FA verification |
| | `/api/auth/refresh` | POST | ✅ OK | Token refresh |
| | `/api/auth/logout` | POST | ✅ OK | Session logout |
| | `/api/auth/me` | GET | ✅ OK | Current user info |
| | `/api/auth/change-password` | POST | ✅ OK | Password change |
| | `/api/auth/reset-password` | POST | ✅ OK | Password reset request |
| | `/api/auth/reset-password/confirm` | POST | ✅ OK | Reset confirmation |
| | `/api/auth/users` | GET | ✅ OK | List users (admin) |
| | `/api/auth/users/{id}` | GET/PATCH | ✅ OK | User management |
| | `/api/auth/roles` | GET | ✅ OK | Returns all 6+3 roles with permissions |
| **Wallets** | `/api/wallets` | GET | ✅ OK | Lists 10 wallets |
| | `/api/wallets/{name}` | GET | ✅ OK | Wallet details |
| | `/api/wallets/{name}/tokens` | GET | ✅ OK | Token balances |
| | `/api/wallets` | POST | ✅ OK | Create wallet |
| | `/api/wallets/{name}/label` | PATCH | ✅ OK | Update label |
| | `/api/wallets/{name}/favorite` | POST | ✅ OK | Toggle favorite |
| | `/api/wallets/sync` | POST | ✅ OK | Force sync from Safina |
| | `/api/wallets/by-unid/{unid}` | GET | ✅ NEW | Wallet lookup by UNID |
| **Transactions** | `/api/transactions` | GET | ✅ OK | List with filters |
| | `/api/transactions/pending` | GET | ✅ OK | Pending signatures |
| | `/api/transactions/{unid}` | GET | ✅ OK | Transaction details |
| | `/api/transactions/{unid}/signatures` | GET | ✅ OK | Signature details |
| | `/api/transactions/validate` | POST | ✅ OK | Validate before send |
| | `/api/transactions` | POST | ✅ OK | Create transaction |
| | `/api/transactions/{unid}/sign` | POST | ✅ OK | Sign transaction |
| | `/api/transactions/{unid}/reject` | POST | ✅ OK | Reject transaction |
| | `/api/transactions/sync` | POST | ✅ OK | Sync from Safina |
| **Signatures** | `/api/signatures/pending` | GET | ✅ OK | Pending signatures |
| | `/api/signatures/history` | GET | ✅ OK | Signature history |
| | `/api/signatures/{tx_unid}/status` | GET | ✅ OK | Signature status |
| | `/api/signatures/{tx_unid}/details` | GET | ✅ OK | Full details |
| | `/api/signatures/{tx_unid}/sign` | POST | ✅ OK | Sign |
| | `/api/signatures/{tx_unid}/reject` | POST | ✅ OK | Reject |
| | `/api/signatures/stats` | GET | ✅ OK | Statistics |
| **Dashboard** | `/api/dashboard/stats` | GET | ✅ OK | Key metrics |
| | `/api/dashboard/recent` | GET | ✅ OK | Recent activity |
| | `/api/dashboard/alerts` | GET | ✅ OK | Active alerts |
| | `/api/dashboard/overview` | GET | ✅ OK | Overview |
| | `/api/dashboard/balance-history` | GET | ✅ OK | Balance chart data |
| **Organizations** | `/api/organizations` | GET/POST | ✅ OK | CRUD |
| | `/api/organizations/{id}` | GET/PUT/DELETE | ✅ OK | |
| | `/api/organizations/{id}/members` | GET/POST | ✅ OK | Member management |
| | `/api/organizations/{id}/settings` | GET/PUT | ✅ OK | Settings |
| | `/api/organizations/tenant/switch` | POST | ✅ OK | Multi-tenancy |
| | `/api/organizations/tenant/current` | GET | ✅ OK | Current tenant |
| **Contacts** | `/api/contacts` | GET/POST | ✅ OK | 3 contacts found |
| | `/api/contacts/search` | GET | ✅ OK | Search |
| | `/api/contacts/favorites` | GET | ✅ OK | Favorites |
| | `/api/contacts/{id}` | GET/PUT/DELETE | ✅ OK | CRUD |
| **2FA** | `/api/2fa/status` | GET | ✅ OK | TOTP status |
| | `/api/2fa/totp/setup` | POST | ✅ OK | Setup TOTP |
| | `/api/2fa/totp/enable` | POST | ✅ OK | Enable |
| | `/api/2fa/totp/disable` | POST | ✅ OK | Disable |
| | `/api/2fa/verify` | POST | ✅ OK | Verify code |
| **Whitelabel** | `/api/whitelabel/branding` | GET/PUT | ✅ OK | Branding config |
| | `/api/whitelabel/email-templates` | GET | ✅ OK | Templates |
| | `/api/whitelabel/domains` | GET/POST | ✅ OK | Custom domains |
| **Compliance** | `/api/compliance/kyc` | GET/POST | ✅ OK | KYC management |
| | `/api/compliance/aml/alerts` | GET | ✅ OK | AML alerts |
| | `/api/compliance/reports` | GET | ✅ OK | Reports |
| **Audit** | `/api/audit` | GET | ✅ OK | Audit log |
| | `/api/audit/stats` | GET | ✅ OK | Statistics |
| | `/api/audit/search` | GET | ✅ OK | Search |
| **Fiat** | `/api/fiat/onramp` | POST | ✅ OK | Fiat on-ramp |
| | `/api/fiat/offramp` | POST | ✅ OK | Fiat off-ramp |
| | `/api/fiat/transactions` | GET | ✅ OK | Fiat TX list |
| | `/api/fiat/bank-accounts` | GET/POST | ✅ OK | Bank accounts |
| | `/api/fiat/rates/{crypto}/{fiat}` | GET | ✅ OK | Exchange rates |
| **Scheduled** | `/api/scheduled` | GET/POST | ✅ OK | Scheduled TX |
| | `/api/scheduled/upcoming` | GET | ✅ OK | Upcoming |
| | `/api/scheduled/{id}` | GET/DELETE | ✅ OK | Manage |
| **Partner** | `/api/partner/*` | Various | ✅ OK | B2B API |
| **Networks** | `/api/user/networks` | GET | ⚠️ Auth issue | "Invalid token" — may need different auth |
| **Billing** | `/api/billing/plans` | GET | ⚠️ 404 | Route may not be mounted |
| **Export** | `/api/export/transactions/csv` | GET | ⚠️ 404 | Route may not be mounted |

### ⚠️ Issues Found

| # | Issue | Severity | Status |
|---|-------|----------|--------|
| 1 | Networks endpoint returns "Invalid token" | Medium | TODO — likely uses different auth mechanism (Safina token vs JWT) |
| 2 | Billing at /api/v1/billing/plans (not /api/billing) | Low | TODO — route may not be included in main app router |
| 3 | Export at /export/transactions/csv (not /api/export) | Low | TODO — route may not be included in main app router |

---

## 2. Changes Made

### 2.1 RBAC: Expanded from 3 to 6 roles ✅

**File:** `backend/services/auth_service.py`
- Added 6 business roles: `super_admin`, `platform_admin`, `company_admin`, `company_operator`, `company_auditor`, `end_user`
- Added `ROLE_HIERARCHY` dict for level-based access control
- Kept legacy `admin`, `signer`, `viewer` for backward compatibility

**File:** `backend/api/routes_auth.py`
- Updated `require_role()` hierarchy to support all 9 roles (6 new + 3 legacy)
- Updated `require_admin()` to accept super_admin, platform_admin, company_admin
- Updated registration validation to accept new roles
- Updated user patch validation to accept new roles

### 2.2 New Endpoint: GET /api/wallets/by-unid/{unid} ✅

**File:** `backend/api/routes_wallets.py`
- Added endpoint to look up wallet by Safina UNID
- Returns 404 if not found, 500 on error

---

## 3. TODO (Remaining)

| Priority | Task | Notes |
|----------|------|-------|
| High | Fix billing routes mounting | Check if `routes_billing` is included in `main.py` |
| High | Fix export routes mounting | Check if `routes_export` is included in `main.py` |
| Medium | Fix networks auth | May need Safina token passthrough |
| Medium | Add batch transactions endpoint | Safina API gap |
| Medium | Add RBAC middleware per-endpoint | Currently only `require_admin` and `require_role` used |
| Low | Add transaction templates | Nice-to-have |
| Low | Add cold storage API | Enterprise feature |

---

## 4. Architecture Notes

- **Total endpoints:** ~100+ across 18 route modules
- **Auth:** JWT-based with access/refresh tokens, optional TOTP 2FA
- **Database:** PostgreSQL (asyncpg)
- **External:** Safina API (KAZ.ONE) for blockchain operations
- **Multi-tenancy:** Organization-based with tenant switching
- **Event system:** Internal event manager for real-time updates
