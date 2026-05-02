---
name: Release-from-hold UX polish — lift on_hold from AML drawer
status: done
created: 2026-05-02
completed: 2026-05-02
type: architecture-decision-record + sprint-plan
parent_story: 2.11 — Production Readiness — release tx from on_hold via UI
relates_to:
  - docs/stories/2-8-transaction-rule-engine-architecture.md (Wave 23 — sets on_hold)
  - docs/stories/2-6-aml-triage-architecture.md (Wave 21 — alert drawer host)
follows: Wave 25 (rule-config admin UI)
---

# Story 2.11 — Release tx from on_hold via UI

## 1. Goal

Wave 23 переводит транзакцию в `status='on_hold'` когда срабатывает rule
с action=hold. Снять удержание — сейчас requires SQL UPDATE.
Story 2.11 — добавить **endpoint** + **button в AML drawer** который
делает это атомарно: проверяет RBAC, переводит tx → `pending`,
пишет audit-log, опционально resolve'ит alert.

## 2. ADRs (small story)

### ADR-1 — Endpoint живёт под `/aml/alerts/{id}/release-hold`

Семантически часть triage flow — officer работает в alert-drawer и
освобождает транзакцию по этому alert'у. Альтернатива:
`/transactions/{unid}/release-hold` — отвергнута, потому что без
alert-context officer не помнит почему он releaseит.

### ADR-2 — Atomic UPDATE: alert.transaction must match

Endpoint:
```
POST /api/v1/compliance/aml/alerts/{alert_id}/release-hold
Body: { reason: str (required, min 1) }
```
Логика:
1. RBAC через triage roles
2. Resolve alert + linked transaction
3. Если alert не имеет `transaction_id` → 422 «No tx linked»
4. Если tx.status != `on_hold` → 409 «Not held»
5. UPDATE transactions SET status='pending'
6. Audit-log INSERT (`action='aml.release_hold'`, details: alert_id + tx_unid + reason)
7. Не trogаем alert.status — operator может отдельно его resolve через resolve-flow

ADR-3: **Не** auto-resolve alert. Officer может release tx и оставить alert «investigating» если ещё нужно дополнить notes / решить final decision.

### ADR-4 — Reason required

Audit trail для регулятора: «почему compliance-officer снял hold»? Frontend требует non-empty textarea, backend гейтит pydantic min_length=1.

### ADR-5 — Audit-log запись через тот же `_write_audit` helper

Wave 21 имеет `_write_audit` для AML alert actions. Reuse — `action='aml.release_hold'`, `resource_type='aml_alert'`, `details={tx_unid, prev_status, reason}`.

### ADR-6 — RBAC matrix

Same as claim/resolve — super_admin / company_admin / company_auditor / platform_admin.

### ADR-7 — Тесты — FakeConn pattern (Wave 21+)

## 3. Sprint breakdown

### 2.11.1 — Backend endpoint + tests

- New `release_held_transaction` method в ComplianceService
- New endpoint в routes_compliance
- Atomic UPDATE+audit_log via conn.transaction()
- +6-8 tests

### 2.11.2 — Frontend button + docs

- В AmlAlertDrawer добавить «Снять удержание» button когда tx on_hold
- Reason-required confirm dialog
- CHANGELOG Wave 26
- Story done

## 4. Definition of done

- [x] 2 sprints
- [x] CI subset: 232 → **239 pass** (+7 release-hold tests)
- [x] `compileall` + `tsc --noEmit` exit 0
- [x] CHANGELOG Wave 26 entry
