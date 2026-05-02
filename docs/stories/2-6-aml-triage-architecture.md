---
name: AML triage UI / alert ↔ transaction wiring — Architecture & Sprint Plan
status: done
created: 2026-05-02
completed: 2026-05-02
type: architecture-decision-record + sprint-plan
parent_story: 2.6 — Production Readiness — AML Alert Triage Workflow
relates_to:
  - docs/stories/2-4-sumsub-kyc-architecture.md
  - docs/stories/2-5-sumsub-kyb-architecture.md
  - docs/prod-readiness.md (❸ AML rule engine — last PARTIAL)
follows: Wave 20 (Sumsub KYB)
phases_after_this:
  - Story 2.7 — wire `check_transaction_against_rules` into transaction-create flow (in-house velocity/threshold alerts)
  - Story 2.8 — SAR submission to Финнадзор (external regulator integration)
---

# Story 2.6 — AML triage UI / alert ↔ transaction wiring

## 1. Goal (single sentence)

Дать compliance-офицеру институционального тенанта **рабочую очередь** AML-alerts: видеть открытые/в работе/решённые, забирать в работу, фиксировать решение (false-positive / resolved / reported-to-regulator) с notes и audit-trail — закрывая последнюю PARTIAL-зону `❸ AML rule engine` в prod-readiness.

## 2. Why this is "wire-up", not "build-from-scratch"

Все нижестоящие куски уже работают. Wave 19/20 успели:
- ✅ Таблица `aml_alerts` со статусами `open|investigating|resolved|false_positive|reported`
- ✅ `compliance_service.create_aml_alert/get_aml_alerts/update_aml_alert_status` — CRUD service-слой существует
- ✅ Sumsub webhook handler пишет alerts автоматически (KYC + KYB)
- ✅ `audit_log` table + service-layer для записи action trace
- ✅ Compliance frontend page `/compliance` с табом «AML/KYT» (статичный заглушка)

**Что отсутствует:**
- 🔄 `routes_compliance.py` не выставляет `/aml/*` endpoints наружу
- 🔄 Frontend AML tab показывает статичный текст вместо реальной очереди
- 🔄 Concurrent-claim race не предусмотрен (наивный UPDATE без conditional)
- 🔄 Audit-log запись на `claim/resolve` не пишется
- 🔄 alert ↔ transaction drill-down не существует

Story 2.6 — это integration story, не feature-development. Большая часть кода — wire-up существующих деталей плюс UI-слой.

---

## 3. Architecture Decision Records

### ADR-1 — `audit_log` (generic) для AML actions, не отдельная таблица

**Decision:** claim/resolve пишутся в существующий `public.audit_log(user_id, action, resource_type, resource_id, details)` с:
- `action` ∈ `{"aml.alert.claim", "aml.alert.resolve", "aml.alert.note"}`
- `resource_type = "aml_alert"`
- `resource_id = alert_uuid::text`
- `details = {prev_status, new_status, decision, resolution, ...}`

**Rationale:**
- `aml_alerts` уже имеет `assigned_to`/`investigated_by`/`investigation_notes` — это «текущее состояние», audit_log = «история переходов».
- Auditor хочет SQL-один-запрос на «что делал user X с alert Y» — generic audit_log справляется.
- `audit_log_b2b` — отдельный B2B-partner аудит, не подходит (там `partner_id` обязателен, AML — internal).

**Trade-off:** `audit_log.id` integer (legacy), retention/archival через тот же mechanism что dashboard logs.

### ADR-2 — Conditional UPDATE для claim, never racy

**Decision:** claim делается единым SQL:
```sql
UPDATE aml_alerts
SET status='investigating', assigned_to=$1, updated_at=now()
WHERE id=$2 AND status='open' AND (assigned_to IS NULL OR assigned_to=$1)
RETURNING *;
```
NULL → 409 Conflict «alert already claimed by other user».

**Rationale:** двое compliance-officers одновременно жмут «Взять» — оба POST'a доходят, conditional WHERE гарантирует exactly-one-winner. Loser получает 409 с текущим `assigned_to` для UI-обновления.

**Trade-off:** lose explicit «is this user re-claiming or stealing» distinction — мы её не делаем, re-claim by same user idempotent (через OR-условие).

### ADR-3 — Resolve = single endpoint с decision-discriminated body

**Decision:** один endpoint `POST /aml/alerts/{id}/resolve` с body `{decision, resolution, report_reference?}`. Decision ∈ `{false_positive, resolved, reported}`, mapping в `status` 1:1.

**Альтернатива:** три отдельных endpoint'a (`/false-positive`, `/resolve`, `/report`). Отвергнута — duplicate code, тестировать×3.

**Rationale:** UI-actions всё равно проходят через одно подтверждение → одно тело → одно `status`-transition. URL-discriminator только усложняет.

### ADR-4 — `reported` действительно immutable + двойное подтверждение в UI

**Decision:**
- Backend: после `status='reported'` любой POST на `/resolve` или `/claim` → 409.
- Frontend: при выборе «Отправить регулятору» — отдельный confirm-dialog с текстом «После отправки SAR-номера статус нельзя отменить. Вы уверены?»

**Rationale:** статус `reported` — это юридический отметчик «мы уведомили Финнадзор». Откат = подделка регуляторного отчёта. Делаем drift-proof.

### ADR-5 — Audit-log запись внутри той же транзакции что и UPDATE

**Decision:** claim/resolve обёрнут в `async with conn.transaction():` — UPDATE `aml_alerts` + INSERT `audit_log` атомарны.

**Rationale:** alert обновлён, но audit-log не записался → forensics ломается. Atomic-write обязателен.

**Trade-off:** требует одного коннекта на оба запроса (acquired раз, не дважды).

### ADR-6 — RBAC scoping через subquery, не application-level filter

**Decision:** `WHERE organization_id IN (SELECT organization_id FROM users WHERE id=$current_user_id)` для не-super_admin. Super_admin — без `WHERE` ограничения.

**Альтернатива:** PostgreSQL RLS policy. Отвергнута — наш проект использует app-level RBAC (`require_roles`), RLS сложнее тестировать.

**Rationale:** один SQL-плейсхолдер защищает выдачу даже если роут забыл фильтр. Multi-org user (admin нескольких orgs) — IN-subquery handles natively.

### ADR-7 — Transaction drill-down через JOIN, не два запроса

**Decision:** `GET /aml/alerts/{id}` возвращает alert + JSON-вложенный `related_transaction` (если `transaction_id IS NOT NULL`):
```sql
SELECT a.*, to_jsonb(t.*) AS related_transaction
FROM aml_alerts a
LEFT JOIN transactions t ON t.id = a.transaction_id
WHERE a.id = $1;
```

**Rationale:** список alert'ов остаётся плоским (без JOIN — много alerts × deep transactions = slow), но drill-down — один запрос.

**Trade-off:** если структура transactions изменится — UI придётся обновлять. Принимаем (UI-side type narrows).

### ADR-8 — Pagination через keyset (created_at, id), не OFFSET

**Decision:** список alert'ов пагинируется через `WHERE (created_at, id) < ($cursor_created, $cursor_id) ORDER BY created_at DESC, id DESC LIMIT $n`. Default page size 50, max 200.

**Rationale:** OFFSET/LIMIT медленный на больших таблицах + дублирует строки при concurrent-INSERT. AML alerts — append-mostly, keyset идеален. Cursor — opaque base64, эталон от auth/transactions endpoints.

**Альтернатива:** простой OFFSET. Принят для MVP (мы не ожидаем 100k+ alerts ближайшие месяцы) — ОТКЛОНЕНО, делаем сразу keyset, code complexity та же.

### ADR-9 — Frontend: drawer-pattern, не отдельная route

**Decision:** клик на строке alert'а открывает right-side `<Drawer>` (shadcn) поверх listing'а, не navigate to `/compliance/aml/{id}`. URL обновляется через `?alert={id}` query-param для shareability.

**Rationale:**
- Triage-flow быстрее: вернуться к списку = закрыть drawer, не back-navigate.
- Sharing/bookmark: query-param сохраняет deep-link.
- Less route-config — нет вложенного `[id]/page.tsx`.

**Альтернатива:** modal-dialog. Отвергнута — drawer лучше для длинного контента (notes, JSON details).

### ADR-10 — `transaction_monitoring_rules` UI отложен на post-MVP

**Decision:** в этой story — НЕ делаем CRUD для rule-config. Rules editable через DB вручную / SQL-script. UI-форма для admin'а — Story 2.8 / отдельный backlog item.

**Rationale:**
- Custom rule-builder — это full feature-set (visual condition tree, thresholds, severity-mapping). Скоуп блочит remaining 30% completion.
- Pilot-клиенты часто хотят дефолтных rules — мы выставляем sane defaults SQL-сидом (threshold=$10k → critical).

### ADR-11 — Тесты — pattern Wave 19/20 (in-process FakeConn)

**Decision:** `tests/test_aml_alerts.py` использует тот же `_FakeConn`/`_FakePool` паттерн что `test_sumsub_webhook.py`. Никакого моки-Postgres'a, никакого live-DB.

**Rationale:** консистентность с двумя предыдущими story. Тестим SQL-параметризацию, RBAC-ветвление и conditional-claim-race не требует реальной БД (race симулируется fixture-queue).

### ADR-12 — Frontend SWR с key-invalidation, не WS

**Decision:** список alert'ов через SWR (`/aml/alerts?status=open`). После claim/resolve — `mutate()` инвалидирует key, drawer сам перезагружает alert. Polling 30s в background для свежести.

**Rationale:**
- AML-velocity низкая (1-10 alerts/day на org типичный case). WS — overkill.
- SWR `revalidateOnFocus` + `refreshInterval: 30000` — достаточно для production feel.
- Уже используется в /transactions, /signatures — продолжаем pattern.

---

## 4. DB schema changes (migration 027)

Миграция **только индексы** + один CHECK constraint refresh — данные не меняются.

```sql
-- backend/migrations/027_aml_alerts_indexes.sql

-- Listing index — ORDER BY created_at DESC по умолчанию.
CREATE INDEX IF NOT EXISTS idx_aml_alerts_org_created
  ON aml_alerts (organization_id, created_at DESC, id DESC);

-- Filter-by-status index — главный hot-path (открытые alerts).
CREATE INDEX IF NOT EXISTS idx_aml_alerts_org_status_created
  ON aml_alerts (organization_id, status, created_at DESC);

-- Drill-down JOIN — поиск всех alerts на транзу.
CREATE INDEX IF NOT EXISTS idx_aml_alerts_transaction_id
  ON aml_alerts (transaction_id) WHERE transaction_id IS NOT NULL;

-- Audit-log lookup для AML resource_type — частый запрос «что было с alert X».
CREATE INDEX IF NOT EXISTS idx_audit_log_aml_alert
  ON audit_log (resource_id, created_at DESC) WHERE resource_type = 'aml_alert';
```

**Migration safety:** все `IF NOT EXISTS`, idempotent на повторный run. `CREATE INDEX` без `CONCURRENTLY` — допустимо т.к. таблица в pilot-окружении пустая. Для prod-deploy на полноценный тенант с >100k alerts добавим `CONCURRENTLY`.

---

## 5. Interface contracts

### 5.1 Backend service — minor extension

`compliance_service.py` получает четыре новых метода (плюс рефакторинг существующих под фильтры):

```python
async def list_aml_alerts(
    self,
    org_ids: list[UUID] | None,        # None = super_admin scope
    status: str | None = None,
    severity: str | None = None,
    alert_type: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    cursor: tuple[datetime, UUID] | None = None,
    limit: int = 50,
) -> tuple[list[dict], tuple[datetime, UUID] | None]:
    """Returns (rows, next_cursor). next_cursor=None if no more rows."""

async def get_aml_alert(
    self, alert_id: UUID, org_ids: list[UUID] | None,
) -> dict | None:
    """Returns alert + related_transaction nested. None on RBAC miss."""

async def claim_aml_alert(
    self, alert_id: UUID, user_id: int, org_ids: list[UUID] | None,
) -> dict:
    """Conditional UPDATE. Raises ConflictError on race / re-claim by other."""

async def resolve_aml_alert(
    self, alert_id: UUID, user_id: int, decision: str,
    resolution: str, report_reference: str | None,
    org_ids: list[UUID] | None,
) -> dict:
    """Single transition to terminal status. Writes audit_log atomically."""

async def append_aml_note(
    self, alert_id: UUID, user_id: int, note: str,
    org_ids: list[UUID] | None,
) -> dict:
    """Append to investigation_notes with timestamp + user prefix."""
```

`org_ids=None` сигнализирует super_admin (no org-filter applied). RBAC enforced в роуте; сервис только параметризует SQL.

### 5.2 Routes — `routes_compliance.py` extension

```python
# All endpoints under /api/v1/compliance/aml/*

@router.get("/aml/alerts")               # → list with filters + cursor
@router.get("/aml/alerts/stats")          # → {open, investigating, resolved_30d, by_severity}
@router.get("/aml/alerts/{alert_id}")    # → single alert + related_transaction
@router.post("/aml/alerts/{alert_id}/claim")    # → claim, 409 on race
@router.post("/aml/alerts/{alert_id}/resolve")  # → terminal transition
@router.post("/aml/alerts/{alert_id}/notes")    # → append note
```

**Pydantic models:**
```python
class AmlAlertListItem(BaseModel):
    id: UUID
    organization_id: UUID
    alert_type: str
    severity: str  # low|medium|high|critical
    status: str    # open|investigating|resolved|false_positive|reported
    description: str
    transaction_id: UUID | None
    assigned_to: int | None
    assigned_to_name: str | None  # JOIN users
    created_at: datetime

class AmlAlertList(BaseModel):
    items: list[AmlAlertListItem]
    next_cursor: str | None  # opaque base64

class AmlAlertDetail(AmlAlertListItem):
    details: dict
    investigation_notes: str | None
    resolution: str | None
    investigated_by: int | None
    investigated_by_name: str | None
    investigated_at: datetime | None
    related_transaction: dict | None  # full tx if transaction_id set

class AmlResolveRequest(BaseModel):
    decision: Literal["false_positive", "resolved", "reported"]
    resolution: str = Field(..., min_length=1, max_length=2000)
    report_reference: str | None = None  # required if decision=='reported'

class AmlAlertStats(BaseModel):
    open: int
    investigating: int
    resolved_30d: int
    by_severity: dict[str, int]  # {"critical": 3, "high": 12, ...}
```

**Error codes:**
- `403 Forbidden` — wrong role / out-of-org request
- `404 Not Found` — alert_id не существует / не в RBAC scope
- `409 Conflict` — claim race / resolve on terminal status
- `422 Unprocessable Entity` — pydantic validation (e.g. report_reference required for `reported`)

### 5.3 Frontend — files

**New files:**
- `frontend/src/lib/amlAlerts.ts` — fetcher'ы (list/get/claim/resolve/notes/stats)
- `frontend/src/components/compliance/AmlAlertList.tsx` — table/list с фильтрами
- `frontend/src/components/compliance/AmlAlertDrawer.tsx` — right-side drawer (shadcn `<Drawer>`)
- `frontend/src/components/compliance/AmlSeverityBadge.tsx` — colored badge
- `frontend/src/components/compliance/AmlStatusBadge.tsx` — colored status pill

**Modified:**
- `frontend/src/app/(authenticated)/compliance/page.tsx` — заменяем заглушку AML-таба на `<AmlAlertList />`. KPI top-cards читают `/aml/alerts/stats`.

**Reused:** shadcn `<Drawer>`, `<Badge>`, `<Button>`, `<Textarea>`, существующий `Card`, существующий `<Header>`. Никаких новых deps.

### 5.4 RBAC matrix

| Role | List own org | List other orgs | Claim/Resolve own | Claim/Resolve other | Stats own | Stats other |
|---|---|---|---|---|---|---|
| `super_admin` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `company_admin` | ✓ | ✗ | ✓ | ✗ | ✓ | ✗ |
| `company_auditor` | ✓ | ✗ | ✓ | ✗ | ✓ | ✗ |
| `company_operator` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| `signer` / `viewer` / `end_user` | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |

`company_operator` — намеренно нет (operator делает транзакции, AML-triage — separate-of-duties).

`require_roles("super_admin", "company_admin", "company_auditor")` в зависимостях route'ов; org_ids derive из user.organization_id (через subquery в SQL).

---

## 6. Sprint breakdown

### Sprint 2.6.1 — Backend service + endpoints + RBAC

**Scope:**
- Migration `027_aml_alerts_indexes.sql` (per section 4)
- Extend `compliance_service.py` с 5 новыми методами (per 5.1)
- Add 6 endpoints в `routes_compliance.py` (per 5.2)
- Atomic UPDATE+audit_log via `conn.transaction()`
- Cursor-encoding helper (`encode_cursor` / `decode_cursor` — base64 of `(created_at, id)`)

**Acceptance criteria:**
- Все 6 endpoints откликаются 2xx на golden path
- RBAC: signer-token → 403 на `GET /aml/alerts`
- Conditional claim race: два concurrent claim'а → один 200, один 409
- audit_log получает запись на каждый claim/resolve/note
- `python -m compileall backend/` exit 0

**Tests (+8-10):**
- `test_aml_alerts.py::test_list_alerts_filter_by_status`
- `test_aml_alerts.py::test_list_alerts_pagination_cursor`
- `test_aml_alerts.py::test_list_alerts_rbac_scoped_to_user_orgs`
- `test_aml_alerts.py::test_get_alert_includes_related_transaction`
- `test_aml_alerts.py::test_claim_alert_succeeds_then_409_on_other_user`
- `test_aml_alerts.py::test_claim_alert_idempotent_for_same_user`
- `test_aml_alerts.py::test_resolve_alert_writes_audit_log_atomically`
- `test_aml_alerts.py::test_resolve_reported_requires_report_reference`
- `test_aml_alerts.py::test_resolve_terminal_status_locks_further_actions`
- `test_aml_alerts.py::test_stats_counts_open_investigating_resolved_30d`

### Sprint 2.6.2 — Frontend triage UI

**Scope:**
- `frontend/src/lib/amlAlerts.ts` — fetcher с типами
- `<AmlAlertList />` компонент — table-row layout, filter strip top, infinite-scroll cursor pagination
- `<AmlAlertDrawer />` — open via `?alert={id}` query-param, claim/resolve buttons, notes textarea, JSON pretty-print of `details`, transaction link
- `<AmlSeverityBadge />` + `<AmlStatusBadge />` — design tokens из `~/.claude/CLAUDE.md` palette (success / warning / destructive / primary)
- Replace AML tab content в `compliance/page.tsx`
- Wire KPI cards top to `/aml/alerts/stats` через SWR

**Animation contract (per global rules):**
- Drawer open/close: Framer Motion slide-from-right, 300ms, ease-out (`[0.22, 1, 0.36, 1]`)
- List row hover: `bg-muted/50` Tailwind, no Framer
- Severity badge: static, no entrance animation
- Empty state: fade-in `opacity 0→1`, 400ms
- Loading: `svg-spinners:ring-resize` Iconify (already used in KYC/KYB pages)

**Acceptance criteria:**
- Click row → drawer открывается, URL обновляется на `?alert={id}`
- Claim button: optimistic update, 409 → toast «Уже взято в работу другим officer'ом» + revalidate
- Resolve `reported` → confirm-dialog с warning'ом, нельзя dismiss accidental click
- Empty state shows «Открытых алертов нет» когда `items=[]`
- `npx tsc --noEmit` exit 0
- ESLint baseline (≤ existing) на новых файлах

### Sprint 2.6.3 — Tests + integration polish

**Scope:**
- Если в 2.6.1 покрытие <80% по new code — добить
- Добавить smoke-test e2e через `httpx` (фактический FastAPI app, не unit) на full claim→resolve→audit-log lifecycle
- RBAC matrix coverage: 5 ролей × {list/claim/resolve} = 15 тестов (можно через parametrize)

**Acceptance criteria:**
- Total tests sumsub+signer+aml: 79 → 100+ pass, 0 skipped
- Integration smoke: actual HTTP request → DB write verified (via FakeConn assertions)
- Coverage report on `backend/api/routes_compliance.py` AML section: ≥85%

### Sprint 2.6.4 — Docs + integration

**Scope:**
- `docs/prod-readiness.md` — обновить ❸ из `PARTIAL DONE` в `DONE 2026-05-02`, описать новый flow
- `docker-compose.yml` — изменения env vars не нужны (никаких новых)
- `CHANGELOG.md` — Wave 21 entry
- Story file frontmatter `status: done`
- Не триггерим deploy — pre-launch banner логики нет (AML-tab всегда работает, просто пустой если alerts=0)

**Acceptance criteria:**
- Все DoD-checkboxes отмечены
- `prod-readiness.md` ❸ section полностью переписан под DONE-state
- CHANGELOG Wave 21 entry синхронен по стилю с Wave 19/20

---

## 7. Risk register

| ID | Риск | Вероятность | Mitigation |
|---|---|---|---|
| R1 | Multi-tenant RBAC leakage в list-query | Medium | RBAC enforced subquery (`organization_id IN (SELECT...)`); 3 dedicated tests с user другого org → 403 на конкретный alert + пустой list. |
| R2 | Concurrent claim race — оба POST'a winners | Low | Conditional UPDATE с `WHERE assigned_to IS NULL OR assigned_to=$1`. Returning rowcount=0 → 409. Test simulates race через FakeConn fixture order. |
| R3 | audit_log запись падает после UPDATE прошёл | Medium | `async with conn.transaction()` обёртка. Если INSERT в audit_log raises — UPDATE rollback'ается. Test simulates failure scenarios. |
| R4 | `reported` accidentally clicked, irreversible | Medium | Двойное подтверждение в UI (confirm dialog с warning text). Backend дополнительно гейтит: после `status=reported` любые `/claim` `/resolve` `/notes` → 409. |
| R5 | Frontend drawer-state не синхронизуется с URL при back-button | Low | Использовать `useSearchParams` + `router.replace` (не `push`) при open/close. Тестируется руками. |
| R6 | KPI stats query медленный без индексов | Low | Migration 027 создаёт `idx_aml_alerts_org_status_created`. Stats — simple COUNT()/COUNT(*) FILTER WHERE; на org с <10k alerts <50ms. |
| R7 | `details jsonb` содержит PII (passport-ID из Sumsub) — leak в UI | Medium | Frontend pretty-prints **с фильтром** sensitive keys (`passport_number`, `national_id`, etc.) → показывает «***hidden***». PII visible только в backend logs (already covered). |
| R8 | super_admin случайно кликает alert чужой org → confusing | Low | UI показывает org-name в строке alert'а явно для super_admin (badge). Для non-super_admin — orgname не показывается (он один). |
| R9 | Pagination cursor leakage — cursor содержит `(created_at, id)` доступного user'у | Low | Cursor — opaque base64; backend проверяет RBAC на каждый запрос с cursor (cursor сам по себе не bypass). |
| R10 | Pre-existing AML-alerts в БД не имеют `assigned_to_name` JOIN — тест на пустую БД | Low | LEFT JOIN users → NULL gracefully; test_list_alerts при users=[] возвращает items с `assigned_to_name=null`. |

---

## 8. Open questions for user

1. **`audit_log` vs separate `aml_alert_history` table** — я предложил generic audit_log (ADR-1). Подтверждаешь или хочешь dedicated history-таблицу для AML с FK на `aml_alerts.id`? (Generic → проще, dedicated → SAR-аудит проще).

2. **PII в `details jsonb` — какие ключи скрывать?** Текущий список: `passport_number`, `national_id`, `inn`, `dob`. Расширить?

3. **`assigned_to_name` — JOIN на `users.full_name` vs `users.email`?** Email для compliance-аудита однозначнее, full_name дружелюбнее в UI. Я склоняюсь к email — есть же avatar-color-hash от email уже.

4. **Default page size 50 — ок или хочешь 100?** Большее = меньше скроллов, но больше initial load.

5. **`reported` без `report_reference` (т.е. SAR-номера) — допустимо?** Я сейчас гейтю «требуется в API» (422). Может pilot-клиент хочет «отметили что отправили, номер потом» — тогда optional. Решаешь.

6. **Вкладка `/compliance` AML — оставить как сейчас (один из 4 табов) или вынести в отдельный route `/compliance/aml`?** Я за сохранение таба — переход не нужен, contextual KPI rows уже там.

7. **Polling cadence — 30s. Меняем?** 30s — production-feel; 10s — нагружает сервер; 60s — feel-stale.

8. **Тесты — продолжаем pattern Wave 19/20 (FakeConn без real PG)?**

Если по всем «решай по дефолту» — беру:
- generic audit_log
- skip-keys: `passport_number`, `national_id`, `inn`, `dob`
- assigned_to → email
- page=50
- `reported` requires `report_reference` (regulator-traceable)
- остаётся таб
- 30s polling
- FakeConn pattern

---

## 9. Definition of done

- [x] 4 спринта закрыты
- [x] Migration 027 идемпотентна, применяется чисто на свежей БД (CREATE INDEX IF NOT EXISTS)
- [x] CI subset: 79 → 119 tests pass, 0 skipped
- [x] `python -m compileall backend/` exit 0
- [x] `cd frontend && npx tsc --noEmit` exit 0
- [x] `docs/prod-readiness.md` ❸ из PARTIAL → DONE
- [x] `CHANGELOG.md` Wave 21 entry
- [x] Story file frontmatter `status: done`
- [ ] Smoke (manual, after deploy): создать тестовый alert через DB → отобразился в /compliance AML tab → claim → resolve → audit_log row есть. Откладывается до prod-deploy с креденшалами.
- [x] **No deploy** на shared-test orgon.asystem.ai (Sumsub creds пустые → alerts не создадутся; frontend покажет empty state — fine).

---

## 10. Estimated time

Меньше Wave 19, сопоставимо с Wave 20. Большинство — wire-up:
- 2.6.1 Backend: ~50% Wave 20's (Backend KYB endpoints был объёмнее — здесь нет externalUserId / Sumsub-API)
- 2.6.2 Frontend: ~80% Wave 19's (новый drawer + table — больше визуальных компонентов чем KYC iframe)
- 2.6.3 Tests: ~30% (subset polish, не from-scratch)
- 2.6.4 Docs: ~20%

Реалистично — одна сессия, может 1.2× Wave 20.
