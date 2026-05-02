---
name: Transaction rule engine — wire-up & action enum (alert/hold/block)
status: done
created: 2026-05-02
completed: 2026-05-02
type: architecture-decision-record + sprint-plan
parent_story: 2.8 — Production Readiness — In-house AML rule engine
relates_to:
  - docs/stories/2-6-aml-triage-architecture.md (Wave 21 — alert sink)
  - docs/stories/2-7-safina-canonical-payload-architecture.md (Wave 22 — sibling pre-send check)
  - docs/prod-readiness.md (post-MVP polish — ❸ already DONE)
follows: Wave 22 (Safina canonical-payload)
phases_after_this:
  - Story 2.9 — SAR submission to Финнадзор
  - Story 2.10 — Rule-config admin UI (currently DB-edit-only)
---

# Story 2.8 — Transaction rule engine wire-up

## 1. Goal (single sentence)

Заставить **уже существующий** `compliance_service.check_transaction_against_rules` реально работать: вызвать его в `send_transaction` ДО отправки в Safina, расширить набор rule types (threshold + velocity + blacklist), и добавить action enum (`alert | hold | block`) — чтобы pilot-клиент мог настроить «$10k → block», «10 tx за час → hold», «адрес в чёрном списке → block» без изменения кода.

## 2. Why this is wire-up, not feature-development

- ✅ DB schema `transaction_monitoring_rules` уже существует с `rule_config jsonb`, `action`, `severity`, `is_active`
- ✅ `compliance_service.check_transaction_against_rules` уже читает rules + создаёт alerts (но только threshold)
- ✅ `aml_alerts` table — Wave 21 triage UI уже видит эти alerts
- ✅ Migration patterns + Wave 21/22 test infra
- 🔄 Что не сделано: вызов из `send_transaction`, action enum logic, velocity/blacklist types, `on_hold` status

## 3. ADRs (concise — это extension, не from-scratch)

### ADR-1 — Rule-check ДО Safina-call, не после

`send_transaction` после validate → rule-check → если block → 400 raise → ничего в Safina не уходит. Если hold → Safina-call идёт но `status='on_hold'` локально + tx_unid возвращается клиенту. Если alert-only → Safina-call как обычно.

**Rationale:** post-mortem rejection (Wave 22) применим к Safina-side mismatch, но in-house rules — это policy gate, должен быть pre-flight.

### ADR-2 — Action enum: `alert | hold | block`

- `alert` (default) — AML alert создан, tx идёт обычным путём
- `hold` — AML alert + tx уходит в Safina, но локально `status='on_hold'` (UI блокирует sign-action)
- `block` — AML alert + tx НЕ уходит в Safina, raise `TransactionBlockedError` → 400

**Rationale:** покрывает 3 регуляторных сценария — soft-flag (alert), manual-review (hold), hard-deny (block).

### ADR-3 — Migration 029 — `on_hold` в transactions.status

Расширяет existing CHECK-constraint из Wave 22 (migration 028) на новое значение. Идемпотентно через DROP IF EXISTS + ADD.

### ADR-4 — Rule types — initial 3, extensible

- `threshold` — `rule_config.threshold_usd` → `value > threshold` triggers
- `velocity` — `rule_config.count` + `rule_config.window_hours` → `COUNT(tx in window) >= count` triggers
- `blacklist_address` — `rule_config.addresses: list[str]` → `to_address in addresses` triggers

Каждый — function `(rule_config, tx_data, conn) -> bool`. Plug-in новых = dict-update.

### ADR-5 — Multiple triggered rules per tx → strictest wins

Если две rule fire'ят (одна alert, другая block) — берётся максимальная severity (`block > hold > alert`). Создаётся **N alerts**, но action — самый жёсткий.

**Rationale:** аудитор видит все nettriggered rules, но tx не идёт в раз-blocked-раз-passed состояние.

### ADR-6 — `org_id` для rule-check derivable из user

`send_transaction` принимает `user: dict` (из `require_roles`). `user.organization_id` → org-scope для rule-lookup. Если `None` (платформенный admin без org) — только global-rules (`organization_id IS NULL` в schema).

### ADR-7 — Rule-engine failure не блокирует tx

DB-error внутри rule-check — log + skip, tx идёт обычным путём. Compliance-friendly: «тестируйте rule-engine отдельно, prod-tx не должна падать из-за DB-glitch».

**Rationale:** trade-off: false-negative (миссед alert) лучше чем false-positive (заблокированная валидная tx). Аудитор знает о fallback по комментарию в коде + log-line.

### ADR-8 — Default rules — НЕ создаём автосидом

Operator руками INSERT'ит rules для своего org через SQL. Wave 22 same pattern (no auto-rules). Story 2.10 — UI form.

**Rationale:** пилот-клиенты часто хотят custom thresholds; sane default = $10k threshold может конфликтовать с jurisdiction.

### ADR-9 — Тесты — pattern Wave 22 (FakeAsyncDB)

Continuation. `_FakeAsyncDB.calls` records every SQL — assertions на rule-fetch, alert-INSERT, status-flip.

### ADR-10 — `TransactionBlockedError` — отдельный exception

Не reuse `TransactionValidationError` — у них разные семантики (validation = bad input, block = policy gate). 400 в обеих случаях, но `error.code` отличается.

## 4. DB migration 029

```sql
-- backend/migrations/029_transactions_on_hold.sql
ALTER TABLE public.transactions
    DROP CONSTRAINT IF EXISTS transactions_status_check;
ALTER TABLE public.transactions
    ADD CONSTRAINT transactions_status_check
    CHECK (status IN (
        'pending', 'signed', 'submitted', 'confirmed', 'failed',
        'rejected_signer_mismatch', 'on_hold'
    ));

CREATE INDEX IF NOT EXISTS idx_transactions_status_on_hold
    ON public.transactions (created_at DESC)
    WHERE status = 'on_hold';
```

## 5. Interface contracts

```python
# Extends compliance_service.check_transaction_against_rules:
async def check_transaction_against_rules(
    self,
    org_id: UUID | None,
    tx: dict,                # {value, to_address, token, network}
    user_id: int,
) -> dict:
    """
    Returns:
      {
        "triggered": [{rule_id, rule_name, severity, action, alert_id}, ...],
        "verdict":   "allow" | "hold" | "block",
      }
    """

# New exception in transaction_service:
class TransactionBlockedError(Exception):
    """Rule engine blocked this transaction."""
    def __init__(self, message: str, triggered: list[dict]):
        super().__init__(message)
        self.triggered = triggered

# In send_transaction(), inserted between validation and Safina call:
verdict = await self._compliance.check_transaction_against_rules(
    org_id=user.get("organization_id"),
    tx={"value": value, "to_address": ..., ...},
    user_id=user["id"],
)
if verdict["verdict"] == "block":
    raise TransactionBlockedError("Blocked by AML rule", verdict["triggered"])
# hold-flow: Safina-call still happens, but local status forced to 'on_hold'.
```

## 6. Sprint breakdown

### Sprint 2.8.1 — Backend rule engine + types

- Migration 029 (on_hold status)
- Extend `check_transaction_against_rules` per 5
- 3 rule-checker funcs: `_check_threshold`, `_check_velocity`, `_check_blacklist`
- New `TransactionBlockedError`
- +6-8 tests on rule logic

### Sprint 2.8.2 — Wire-up in send_transaction

- Inject `ComplianceService` into `TransactionService.__init__`
- Call rule-check after validation, before Safina-call
- Block-flow → raise + 400 in route
- Hold-flow → tx goes to Safina, local status='on_hold'
- +5-7 wire-up tests

### Sprint 2.8.3 — Frontend status badge + UI hint

- Add `on_hold` → «На удержании» в STATUS_RU + StatusBadge
- На transaction-detail page: warning banner если status='on_hold' с link на /compliance AML

### Sprint 2.8.4 — Docs

- Story frontmatter done
- prod-readiness — добавить «In-house rule engine» в ❸ (post-DONE polish)
- CHANGELOG Wave 23 entry

## 7. Risk register (short — это small story)

| ID | Риск | Mitigation |
|---|---|---|
| R1 | Rule-engine падает на каждой tx | ADR-7 — try/except, log+skip, tx идёт. |
| R2 | Velocity-rule SQL медленный на больших таблицах | Indexed `(organization_id, created_at)` уже существует. Window-query — partial WHERE. |
| R3 | Hold-status confusing для clients | Frontend banner + link на compliance/AML. |
| R4 | Multiple rules fire — UI spam | ADR-5 — все alerts создаются, но action один. |
| R5 | Blacklist `addresses` list растёт большим | Для MVP — JSONB. Если >100 addresses — отдельная таблица (Story 2.10). |

## 8. Defaults (going through, no separate approval)

Беру по умолчанию:
- 3 rule types: `threshold | velocity | blacklist_address`
- Action enum: `alert | hold | block`
- Migration 029 — `on_hold` status
- ComplianceService inject в TransactionService через __init__
- Strictest-wins (block > hold > alert)
- No auto-seed rules
- FakeAsyncDB pattern для тестов

## 9. Definition of done

- [x] 4 sprint
- [x] Migration 029 idempotent (DROP IF EXISTS + ADD)
- [x] CI subset: 161 → **184 pass**
- [x] `compileall` + `tsc --noEmit` exit 0
- [x] CHANGELOG Wave 23 entry
- [x] Backwards-compat: tenants без rules в DB работают (no-op verdict='allow' через `_FakeCompliance` wire-up tests)
