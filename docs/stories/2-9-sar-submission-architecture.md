---
name: SAR submission to Финнадзор — Architecture & Sprint Plan
status: done
created: 2026-05-02
completed: 2026-05-02
type: architecture-decision-record + sprint-plan
parent_story: 2.9 — Production Readiness — Regulator Reporting (SAR)
relates_to:
  - docs/stories/2-6-aml-triage-architecture.md (Wave 21 — alert source)
  - docs/stories/2-7-safina-canonical-payload-architecture.md (Wave 22 — same "design-around-uncertainty" pattern)
follows: Wave 23 (in-house rule engine)
phases_after_this:
  - Story 2.10 — rule-config admin UI
  - Story 2.11 — release-from-hold button + AML drawer polish
---

# Story 2.9 — SAR submission to regulator

## 1. Goal (single sentence)

Закрыть последнюю compliance-полировку: автоматически собирать SAR-отчёт (Suspicious Activity Report) из alert + tx + org-context, и дать оператору **выбор канала подачи** (manual export PDF/JSON, email на адрес compliance, либо API когда Финнадзор его опубликует) — без ожидания публичной спецификации регулятора.

## 2. Why this is "design-around-uncertainty" again

Тот же блокер что и в Wave 22 (Safina canonical-payload):
- **Нет публичного API** Финнадзор для SAR submissions
- Каждый регулятор (Финнадзор Кыргызстана, FinCEN US, FCA UK) — свой формат
- Получить специфику от регулятора — недели coordination

Не ждём. Реализуем:
1. **Generator** — собирает все relevant fields (alert + linked tx + org info + reasoning) в **structured JSON + rendered Markdown**.
2. **Pluggable submission backend** registry: `manual_export | email | api_v1`. Default — `manual_export`.
3. **Idempotency через DB**: каждая попытка submission — row в `sar_submissions`. Повторный POST на тот же alert → returns existing.
4. **No PDF в MVP** — JSON + Markdown достаточно для официантского подачи через email/portal. Ask before adding `reportlab` или `weasyprint` (per global UI animation rule — но и здесь backend dep требует confirm).

## 3. ADRs

### ADR-1 — `sar_submissions` таблица (migration 030)

```sql
CREATE TABLE sar_submissions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id uuid NOT NULL REFERENCES aml_alerts(id),
    organization_id uuid NOT NULL,
    submitted_by integer NOT NULL,
    submission_backend varchar(50) NOT NULL,    -- manual_export | email | api_v1
    payload_json jsonb NOT NULL,                -- the structured SAR
    rendered_markdown text NOT NULL,            -- human-readable preview
    status varchar(20) NOT NULL DEFAULT 'prepared',  -- prepared | sent | acknowledged | failed
    external_reference varchar(100),            -- SAR-номер регулятора
    response_body text,                         -- error / receipt
    submitted_at timestamptz NOT NULL DEFAULT now(),
    acknowledged_at timestamptz,
    UNIQUE (alert_id)                           -- one SAR per alert
);
```

**Rationale:** альтернатива — записывать в `aml_alerts.report_reference` (existing field), но тогда теряется payload preview, retry-history, backend-discriminator. Отдельная таблица — clean.

### ADR-2 — Submission backend registry (mirror Wave 22 pattern)

```python
@dataclass(frozen=True)
class SubmissionBackend:
    name: str
    description: str
    submit: Callable[[dict], dict]   # (payload) → {status, external_reference?, response_body?}

_BACKENDS: dict[str, SubmissionBackend] = {
    "manual_export": ...,    # default — saves to DB, returns prepared, operator downloads
    "email":         ...,    # SMTP send to FINSUPERVISORY_SAR_EMAIL
    "api_v1":        ...,    # stub — POST к Finsupervisory API когда выйдет
    "dryrun":        ...,    # logs only, never persists — for tests
}
```

`FINSUPERVISORY_SAR_BACKEND` env var выбирает дефолт. Per-org override в админке (Story 2.10).

### ADR-3 — Generator — pure function `(alert + tx + org) → (json, markdown)`

`build_sar_payload(alert: dict, tx: dict|None, org: dict, officer: dict) -> dict`. Возвращает dict с полями:
```
{
  "filing_org": {name, registration_no, address, contact_email},
  "officer":    {name, email, phone},
  "alert":      {id, alert_type, severity, description, details_redacted},
  "transaction": {unid, value, to_address, network, ...} | null,
  "reasoning":  "<from alert.resolution>",
  "supporting_documents": [],   # placeholder for Story 2.10 file uploads
  "filed_at":   ISO 8601,
}
```

Markdown генерируется из того же JSON через template — для preview drawer и для email-body.

### ADR-4 — PII redaction reuses Wave 21 helper

Frontend уже маскирует `passport_number`, `national_id`, `inn`, `dob`, `taxId` в drawer details. Backend SAR generator reuses ту же логику — PII НЕ попадает в payload, только в supporting_documents (uploaded copies, attached separately).

**Rationale:** регулятор требует факт обнаружения нарушения, не сами personal-data в repository SAR-system. PII attached как secondary file submission per request.

### ADR-5 — Endpoint `POST /api/v1/compliance/aml/alerts/{alert_id}/sar`

```
Request body:
  {
    "backend": "manual_export" | "email" | "api_v1",  # optional — uses env default
    "officer_name": "...",
    "officer_phone": "...",
  }

Response 201 (created or 200 if idempotent re-fetch):
  {
    "id": "<sar_submission uuid>",
    "status": "prepared|sent|acknowledged|failed",
    "external_reference": "SAR-2026-001" | null,
    "rendered_markdown": "<full SAR text>",
    "payload_json": {...},
    "download_url": "/api/v1/compliance/aml/alerts/{aid}/sar.json"
  }
```

GET endpoint `/sar.json` и `/sar.md` отдают raw JSON / Markdown для скачивания.

### ADR-6 — Idempotency через UNIQUE alert_id

ON CONFLICT в INSERT возвращает existing row. Frontend trusts that re-clicking «Generate SAR» is safe. Audit-trail — отдельные attempts (с retries) пишутся в `audit_log` с `action='sar.submit_attempt'`.

### ADR-7 — `email` backend — SMTP, не SMTP-relay-aaS

Если pilot-tenant включает `FINSUPERVISORY_SAR_BACKEND=email`, мы шлём через стандартный SMTP (`SMTP_*` env vars — host/port/user/password/from). Existing pattern из notifications.

**Rationale:** email — universal fallback, и Финнадзор сейчас принимает по email. SaaS-relay (SendGrid/Postmark) — для отдельной story если потребуется.

### ADR-8 — `api_v1` backend — stub raising NotImplementedError

Заготовка с TODO — когда Финнадзор опубликует API, оператор просто меняет `FINSUPERVISORY_SAR_BACKEND=api_v1` + добавляет credentials. Код-shape готов.

### ADR-9 — Linked transaction enrichment

Если `aml_alerts.transaction_id` set, generator делает JOIN на `transactions` чтобы вытянуть `unid, value, to_addr, token, network, init_ts`. Если null (Sumsub-only KYC alert) — секция `transaction` остаётся null в payload.

### ADR-10 — Тесты — pattern Wave 21/22/23 (FakeAsyncDB)

Continuation. Pure-function tests на `build_sar_payload`, integration на endpoints через FakeConn.

## 4. DB migration 030

```sql
-- backend/migrations/030_sar_submissions.sql
CREATE TABLE IF NOT EXISTS public.sar_submissions (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_id uuid NOT NULL REFERENCES public.aml_alerts(id) ON DELETE RESTRICT,
    organization_id uuid NOT NULL,
    submitted_by integer NOT NULL,
    submission_backend varchar(50) NOT NULL,
    payload_json jsonb NOT NULL,
    rendered_markdown text NOT NULL,
    status varchar(20) NOT NULL DEFAULT 'prepared'
        CHECK (status IN ('prepared', 'sent', 'acknowledged', 'failed')),
    external_reference varchar(100),
    response_body text,
    submitted_at timestamptz NOT NULL DEFAULT now(),
    acknowledged_at timestamptz,
    CONSTRAINT sar_submissions_one_per_alert UNIQUE (alert_id)
);

CREATE INDEX IF NOT EXISTS idx_sar_submissions_org_submitted
    ON public.sar_submissions (organization_id, submitted_at DESC);
```

## 5. Sprint breakdown

### 2.9.1 — Backend module: generator + backends registry

- `backend/regulators/finsupervisory/__init__.py`
- `backend/regulators/finsupervisory/sar_generator.py` — `build_sar_payload`
- `backend/regulators/finsupervisory/submission_backends.py` — registry, `manual_export`, `email`, `api_v1` stub, `dryrun`
- Migration 030
- 8-10 pure-function tests on generator + backends

### 2.9.2 — API endpoint + service integration

- New service `SarSubmissionService` in `backend/services/`
- 3 endpoints: `POST /aml/alerts/{id}/sar`, `GET /aml/alerts/{id}/sar.json`, `GET /aml/alerts/{id}/sar.md`
- Idempotency via UNIQUE constraint
- 5-7 wire-up tests

### 2.9.3 — Frontend SAR generator

- В `AmlAlertDrawer` добавить «Сформировать SAR» button (показывается только если `decision==='reported'` уже зафиксирован)
- New small component `<SarPreviewModal>` — показывает rendered Markdown + JSON tabs + download
- Update `amlAlerts.ts` — `submitSar()`, `fetchSarJson/Md()` fetchers

### 2.9.4 — Docs

- Story `done`, prod-readiness заметка в ❸ section («SAR submission DONE»), CHANGELOG Wave 24, env vars в docker-compose

## 6. Defaults (going through)

Беру:
- 4 backends: `manual_export | email | api_v1 | dryrun` (api_v1 — stub)
- Migration 030 — UNIQUE (alert_id) for idempotency
- No PDF generation in MVP (avoid extra dep)
- PII redaction reuses Wave 21 helper
- Default backend = `manual_export`
- FakeConn pattern for tests

## 7. Risk register (short)

| ID | Risk | Mitigation |
|---|---|---|
| R1 | Финнадзор API выйдет с другим shape | api_v1 — заготовка, реализуется по docs |
| R2 | Email backend не доходит | SMTP error → status='failed', operator пробует manual_export |
| R3 | PII утечёт в payload (без attached docs) | ADR-4 — redaction обязательна, тест проверяет |
| R4 | Двойной submission | UNIQUE (alert_id) → ON CONFLICT returns existing |
| R5 | Operator забывает прислать SAR | После 7 дней — email-reminder (post-MVP, Story 2.10) |

## 8. Definition of done

- [x] 4 sprint
- [x] Migration 030 idempotent (CREATE IF NOT EXISTS + UNIQUE alert_id)
- [x] CI subset: 184 → **214 pass** (+19 generator, +11 endpoints)
- [x] `compileall` + `tsc --noEmit` exit 0
- [x] CHANGELOG Wave 24 entry
- [x] Default `manual_export` works without any external service
- [x] Backwards-compat: tenants без env-config работают (manual_export автоматически)
