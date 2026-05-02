---
name: Rule-config admin UI — CRUD over transaction_monitoring_rules
status: done
created: 2026-05-02
completed: 2026-05-02
type: architecture-decision-record + sprint-plan
parent_story: 2.10 — Production Readiness — Compliance rule-config UI
relates_to:
  - docs/stories/2-8-transaction-rule-engine-architecture.md (Wave 23 — rule engine)
follows: Wave 24 (SAR submission)
phases_after_this:
  - Story 2.11 — release-from-hold UX polish
---

# Story 2.10 — Rule-config admin UI

## 1. Goal

Wave 23 даёт rule engine (`transaction_monitoring_rules` table + `evaluate_transaction_rules`). Admin сейчас редактирует rules **через SQL INSERT/UPDATE руками** — pilot-friendly но не institutional. Story 2.10 — простой CRUD UI на странице `/compliance/rules`: список правил, форма создания, форма редактирования, toggle is_active, удалить.

## 2. ADRs (this is a small CRUD story)

### ADR-1 — RBAC

- `super_admin` / `platform_admin` — read+write для всех orgs + могут редактировать global rules (`organization_id IS NULL`).
- `company_admin` — read+write для своего org. **Не** видит/трогает global rules (показывается, но read-only).
- `company_auditor` — read-only (видит правила в контексте triage). Для view, не mutate.
- `signer` / `end_user` / `company_operator` — 403.

### ADR-2 — Rule config validation per type

Pydantic model на route-level:
- `threshold` → `rule_config = {"threshold_usd": <decimal>}`
- `velocity` → `rule_config = {"count": <int>, "window_hours": <int>}`
- `blacklist_address` → `rule_config = {"addresses": [<str>, ...]}`

Unknown types отклоняются на 422.

### ADR-3 — Hard delete + audit_log

DELETE — реальный DROP row. Каждое create/update/delete пишет в `audit_log` (`resource_type='monitoring_rule'`, action `rule.create/update/delete`).

**Rationale:** soft-delete (`is_active=false`) уже закрыт через PATCH — operator может toggle вместо delete. Полный delete для cleanup конфигов.

### ADR-4 — Endpoints под `/api/v1/compliance/rules/*`

```
GET    /rules                — list (RBAC-scoped)
POST   /rules                — create
GET    /rules/{id}           — read one
PATCH  /rules/{id}           — partial update
DELETE /rules/{id}           — hard delete
```

### ADR-5 — Frontend — отдельная route `/compliance/rules`, не tab

Триаж и конфиг — разные mental modes. Триаж — frequent (compliance-офицер), конфиг — rare (admin раз в месяц). Отдельная страница чище в навигации.

### ADR-6 — UI design — table + Dialog для create/edit

- Table: `name | type | severity | action | active toggle | actions`
- «Добавить правило» button → Dialog с conditional form (поля меняются по `rule_type`)
- Click на row → edit Dialog (preserves all data)
- Toggle active inline (PATCH `is_active`)
- Delete — confirm dialog

### ADR-7 — Тесты — FakeConn (Wave 21+24)

Continuation. Pure-function validation tests + endpoint integration tests.

## 3. Sprint breakdown

### 2.10.1 — Backend CRUD endpoints

- 5 endpoints в `routes_compliance.py`
- New `RuleConfig*` Pydantic models per type
- Validation: rule_type ∈ supported, rule_config matches type-specific schema
- Audit-log writes (atomic via conn.transaction)
- +10-12 tests

### 2.10.2 — Frontend rule-config page

- New route `/compliance/rules/page.tsx`
- New components: `RuleListTable`, `RuleFormDialog`
- Fetcher in `lib/amlRules.ts`
- Sidebar link под admin role-gate

### 2.10.3 — Tests + RBAC matrix + docs

- RBAC parametrized tests (5 roles × 5 endpoints)
- CHANGELOG Wave 25

## 4. Defaults — going by

- 5 endpoints
- Hard delete + audit-log
- Separate route (not tab)
- FakeConn tests
- No bulk/import features

## 5. Definition of done

- [x] 3 sprints
- [x] CI subset: 214 → **232 pass** (+18 monitoring rules CRUD/RBAC)
- [x] `compileall` + `tsc --noEmit` exit 0
- [x] CHANGELOG Wave 25 entry
- [x] Backwards-compat: existing rules data unaffected (no schema change)
