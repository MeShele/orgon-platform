---
name: Sumsub KYC integration (MVP — individuals) — Architecture & Sprint Plan
status: done (2026-05-02 — implementation merged on feature/demo-simulator)
created: 2026-05-02
completed: 2026-05-02
type: architecture-decision-record + sprint-plan
parent_story: 2.4 — Production Readiness — Sumsub KYC for Individuals
relates_to: docs/prod-readiness.md (sections 5 ❸ AML, 5 ❹ KYC), docs/stories/2-3-kms-signer-architecture.md (precedent pattern), CHANGELOG.md (Wave 19)
follows: Wave 18 (KMS signer)
sprints_completed: [2.4.1, 2.4.2, 2.4.3, 2.4.4]
final_test_count: 207 passed, 0 skipped (was 167)
phases_after_this:
  - Story 2.5 — Sumsub KYB for businesses (next session)
  - Story 2.6 — Sumsub AML alerts integration (after KYB)
---

# Story 2.4 — Sumsub KYC integration (individuals only, MVP)

## 1. Goal (single sentence)

Подключить Sumsub в качестве KYC-провайдера для физических лиц так чтобы клиент проходил верификацию через embedded WebSDK-iframe, а ORGON получал статусы через webhook'и — закрывая блокер ❹ (KYC document upload) одной интеграцией без необходимости поднимать S3-bucket, virus-scan и UI drag-drop.

## 2. Why now / Why Sumsub

### Контекст

Из 4 institutional-блокеров `prod-readiness.md`:
- ❶ KMS — DONE (Wave 18)
- ❷ Safina canonical-payload — внешняя зависимость, ждём ответа Safina-команды
- ❸ AML rule engine — `aml_alerts` пустой CRUD shell, детектора нет
- ❹ KYC/KYB doc upload — endpoints возвращают `placeholder://`, реального upload нет

User сказал «настраиваем под Sumsub». Sumsub — managed KYC/AML provider, **покрывает ❸ и ❹ одной интеграцией**:
- KYC: WebSDK iframe → user снимается на selfie/делает liveness/загружает паспорт прямо в Sumsub. Нам не нужен S3, ClamAV, drag-drop.
- KYB (бизнесы): отдельный flow с тем же провайдером — сдвигаем в Story 2.5.
- AML: Sumsub автоматом screening'ит applicant'a через sanctions/PEP/adverse-media базы — webhook событиями зальём в наш `aml_alerts`. Story 2.6.

### Альтернативы и почему отбросили

| Опция | Pro | Con | Решение |
|---|---|---|---|
| **Sumsub** | Покрывает KYC+KYB+AML, $1-3/верификация, RU/EAEU friendly | Vendor lock, custom enterprise pricing для AML monitoring | ✓ выбрано |
| Chainalysis | Лучший AML для on-chain analytics | $$$ (от $50K/year), overkill для MVP | отложено до scale |
| Onfido | Сильный KYC | KYB слабее, цены сравнимы Sumsub | Sumsub предпочтительнее в нашем регионе |
| In-house | Полный контроль | 3-5 дней дев + lifetime поддержка sanction-lists | unfavourable cost/value |

### Phase scope

Эта story = **MVP только для физлиц (individuals)**. Что НЕ входит:
- KYB / business verification → **Story 2.5**
- AML alerts feed → **Story 2.6** (минимально — webhook'и для AML mark-ов мы поймаем уже здесь, но не будем строить полноценный alert-pipeline в `/compliance/aml` page)
- Custom verification levels (per-org)
- Travel Rule transaction monitoring

---

## 3. Architecture Decision Records

### ADR-1 — Sumsub WebSDK (iframe), не Mobile SDK / pure-API

**Decision:** Используем Sumsub **WebSDK** — iframe который встраивается в `/compliance/kyc` страницу.

**Rationale:**
- ORGON фронт = Next.js, мобильного приложения нет
- WebSDK сам обрабатывает webcam, document scan, liveness — мы НЕ пилим UI с нуля
- Поддержка `@sumsub/websdk-react` как npm-пакет либо чистый `<script>` тег
- iframe полностью изолирован — fewer security concerns про user-uploaded files

**Trade-off:** Меньше кастомизации UI (есть Sumsub branding), но это норма для KYC-provider iframe'ов.

### ADR-2 — Backend генерит WebSDK access-token, frontend никогда не видит app-secret

**Decision:**
- Backend хранит `SUMSUB_APP_TOKEN` + `SUMSUB_SECRET_KEY` в Coolify env, **никогда** не отправляет на фронт
- Endpoint `POST /api/v1/kyc-kyb/sumsub/access-token` создаёт **short-lived** (15-30 min) access token для конкретного `applicantId`
- Frontend получает токен, открывает iframe с ним, токен сгорает после успешного сабмита

**Rationale:** Стандартная Sumsub-рекомендация. Утечка short-lived token = ущерб ограничен временем токена и одним applicant'ом, не всем нашим аккаунтом.

### ADR-3 — Один applicant per (user_id, level) пара, retry-friendly

**Decision:**
- Если у user'а уже есть applicant в Sumsub для уровня `basic-kyc-level` — переиспользуем (re-authenticate в WebSDK с тем же applicantId)
- Не создаём новых applicant'ов на каждый клик «start verification» — Sumsub билит за создание

**Rationale:** Cost optimization + лучше UX (юзер не теряет прогресс если отвалится сеть).

**Implementation:** В нашей БД таблица `sumsub_applicants` хранит mapping `(user_id) → applicant_id, level, status, last_review_result`. На повторный submit лезем в Sumsub-API за свежим access-token для того же applicant'a.

### ADR-4 — Webhook signature verification — обязательно, fail closed

**Decision:**
- Webhook endpoint `/api/v1/webhooks/sumsub` валидирует HMAC-SHA-256 подпись через `X-Payload-Digest` header + `SUMSUB_WEBHOOK_SECRET`
- Без подписи или с невалидной подписью — **403 immediately**, событие игнорируется и не пишется в БД
- Logs пишем `WARN` с request-ID но не payload (чтобы не записать PII)

**Rationale:** Webhook endpoint публичный (Sumsub'у нужно достучаться). Без подписи любой может POST'ить fake `applicantReviewed{status: GREEN}` и продвинуть юзера через KYC. Это критично.

### ADR-5 — Statuses mapping: Sumsub → ORGON

**Decision:**
| Sumsub `reviewStatus` + `reviewResult.reviewAnswer` | ORGON `kyc_submissions.status` |
|---|---|
| `init` (applicant created, no docs yet) | `not_started` |
| `pending` (docs uploaded, in queue) | `pending` |
| `prechecked` / `queued` | `pending` |
| `onHold` (manual reviewer needed) | `manual_review` |
| `completed` + `GREEN` | `approved` |
| `completed` + `RED` (final reject) | `rejected` |
| `completed` + `RED` + `clientComment` (retry possible) | `needs_resubmit` |

**Rationale:** Existing schema `status varchar(20)` accommodates these. We add `manual_review` and `needs_resubmit` to the existing `pending/approved/rejected` set — minor migration.

### ADR-6 — DB: extend kyc_submissions, separate sumsub_applicants

**Decision:**

Add columns to `kyc_submissions`:
```sql
ALTER TABLE kyc_submissions
  ADD COLUMN sumsub_applicant_id varchar(64),
  ADD COLUMN sumsub_inspection_id varchar(64),
  ADD COLUMN sumsub_review_result jsonb,
  ADD COLUMN sumsub_external_user_id varchar(64);
CREATE UNIQUE INDEX uniq_kyc_sumsub_applicant ON kyc_submissions(sumsub_applicant_id) WHERE sumsub_applicant_id IS NOT NULL;
```

New table `sumsub_applicants` (cache + last-known-state, can be regenerated from kyc_submissions):
```sql
CREATE TABLE sumsub_applicants (
  user_id integer PRIMARY KEY REFERENCES users(id),
  applicant_id varchar(64) NOT NULL UNIQUE,
  external_user_id varchar(64) NOT NULL,
  level_name varchar(64) NOT NULL,
  review_status varchar(32) NOT NULL,
  review_result jsonb,
  created_at timestamptz DEFAULT now(),
  updated_at timestamptz DEFAULT now()
);
CREATE INDEX idx_sumsub_applicants_review_status ON sumsub_applicants(review_status);
```

**Rationale:** `kyc_submissions` остаётся primary KYC-record (мы можем мержить документы из Sumsub для аудита). `sumsub_applicants` — быстрый lookup в одном месте: если webhook прилетел с `applicantId=X`, мы быстро находим `user_id`.

### ADR-7 — Verification level — single global для MVP

**Decision:** Всё через single Sumsub level — `basic-kyc-level` (имя настраивается в Sumsub Dashboard).

**Rationale:** MVP. Per-org levels (institutional vs retail) — features Story 2.5+. Hardcode level name в env var `SUMSUB_LEVEL_NAME`.

### ADR-8 — Frontend: чистый `<script>` тег, не npm package

**Decision:** Загружаем `https://static.sumsub.com/idensic/static/sns-websdk-builder.js` через native `<script>` тег в page-component'е, инициализируем через `window.snsWebSdk`.

**Rationale:**
- npm-пакет `@sumsub/websdk-react` существует но v3.x last update 18 месяцев назад, ставит избыточные deps
- Скрипт от Sumsub автообновляется — bug fixes / security patches приходят сразу без bumb'а нашей зависимости
- Меньше bundle-size

**Trade-off:** TypeScript-declarations нужно описать вручную (одна `declare global`). 30 строк.

### ADR-9 — Mocking strategy в тестах

**Decision:** Sumsub-API мокаем через `unittest.mock.patch` напрямую (NOT через httpx mock-transport). Webhook signature verification тестируем с реальным HMAC.

**Rationale:** Sumsub-сервис — pure HTTP-wrapper, тесты на вызовы и сериализацию. Тяжёлой логики нет — мокаем `httpx.AsyncClient.post/get` через monkeypatch на одной строке. Не оверинженерим как с KMS-fake.

### ADR-11 — Graceful degradation when SUMSUB_APP_TOKEN unset

**Decision:** Если `SUMSUB_APP_TOKEN` env пуст — `SumsubService` запускается в **disabled mode**:
- Все backend endpoint'ы (`/access-token`, `/applicant-status`, `/webhooks/sumsub`) возвращают **503 Service Unavailable** с чистым JSON `{"detail": "Sumsub is not configured"}`
- Frontend `/compliance/kyc` ловит 503, показывает баннер: «KYC verification will be enabled once the platform configures it. Contact support@... if you need to onboard.»
- Backend stage-up НЕ ломается — startup проходит, остальные endpoints работают
- Webhook endpoint **отказывает** даже если URL настроен в Sumsub (defense in depth — пока секрет не выставлен)

**Rationale:** Идентичный паттерн как `STRIPE_API_KEY` (если пуст → billing endpoints 503 cleanly). Pilot setup procedure: paste 3 env-vars в Coolify → redeploy backend → KYC сразу работает. Между «нет аккаунта» и «есть аккаунт» — только конфигурация, не код.

**Implementation:** В `build_sumsub_service()` (factory function в main.py) проверяем env. Если ключ пуст — кладём в `app.state.sumsub` маркер `None`. Endpoints зависят от `Depends(get_sumsub_service)` который raise'ит `HTTPException(503, "Sumsub is not configured")` если service is None.

### ADR-10 — Idempotency на webhook'ах через `applicantId + reviewStatus`

**Decision:**
- Webhook handler хранит `last_event_id` в `sumsub_applicants.review_result` jsonb
- Если приходит дубль (Sumsub retries при таймауте) — проверяем по `(applicantId, applicantStatus, ts)` — `INSERT ... ON CONFLICT DO NOTHING` для аудит-лога
- Update самого статуса всегда применяем — последний-выигрывает

**Rationale:** Sumsub doc'и говорят что они могут retry'ить webhook 5 раз с exp-backoff если мы не вернули 200. Дублирование — норма, нужна idempotency на нашей стороне.

---

## 4. Component diagram

```
┌──────────────────────────────────────────────────────────────────┐
│  Browser (user)                                                   │
│                                                                    │
│  /compliance/kyc page                                              │
│     │                                                              │
│     │  1. fetch /api/v1/kyc-kyb/sumsub/access-token                │
│     ▼                                                              │
│  ORGON backend                                                     │
│     │  2. POST /resources/applicants  (idempotent — re-use)        │
│     │  3. POST /resources/accessTokens (15min TTL)                 │
│     ▼                                                              │
│  Sumsub API (api.sumsub.com)                                       │
│     │                                                              │
│     │ ← {applicantId, accessToken}                                 │
│     ▼                                                              │
│  ORGON backend stores applicantId in sumsub_applicants table       │
│     │                                                              │
│     │ ← {accessToken}                                              │
│     ▼                                                              │
│  Browser embeds Sumsub WebSDK iframe with accessToken              │
│     │                                                              │
│     │ User uploads docs / does liveness — all in Sumsub iframe     │
│     ▼                                                              │
│  Sumsub processes (auto-checks + manual review queue)              │
│     │                                                              │
│     │  webhook POST /api/v1/webhooks/sumsub                        │
│     │  with X-Payload-Digest HMAC                                  │
│     ▼                                                              │
│  ORGON backend                                                     │
│     │  1. Verify HMAC                                              │
│     │  2. Map Sumsub status → ORGON status                         │
│     │  3. UPDATE kyc_submissions + sumsub_applicants               │
│     │  4. If AML alert event → INSERT aml_alerts                   │
│     │  5. (future Story 2.6) push WebSocket event to UI            │
│     ▼                                                              │
│  Frontend polls /api/v1/kyc-kyb/sumsub/applicant-status             │
│  (or listens via WebSocket — out of scope for MVP)                 │
└──────────────────────────────────────────────────────────────────┘
```

---

## 5. Interface contracts

### 5.1 Backend service `SumsubService`

```python
class SumsubService:
    def __init__(self, app_token: str, secret_key: str, webhook_secret: str,
                 level_name: str, base_url: str = "https://api.sumsub.com"): ...

    async def create_or_get_applicant(self, user_id: int, external_user_id: str) -> dict:
        """Returns {applicantId, externalUserId, level, status}.
        Idempotent: if user already has applicant in our DB, returns existing.
        """

    async def generate_access_token(self, applicant_id: str, ttl_seconds: int = 1800) -> str:
        """Returns short-lived WebSDK token. Caller embeds in iframe."""

    async def get_applicant_status(self, applicant_id: str) -> dict:
        """Returns {reviewStatus, reviewResult, levelName, createdAt}."""

    def verify_webhook_signature(self, payload_bytes: bytes, signature: str) -> bool:
        """HMAC-SHA-256 of payload with webhook_secret == signature?"""
```

### 5.2 New API endpoints

```
POST /api/v1/kyc-kyb/sumsub/access-token
  Auth: any logged-in user
  Returns: { "accessToken": "_act-...", "expiresIn": 1800, "applicantId": "..." }
  Errors: 503 if SUMSUB_APP_TOKEN unset (clean degradation), 502 on Sumsub API error

GET /api/v1/kyc-kyb/sumsub/applicant-status
  Auth: any logged-in user
  Returns: { "applicantId": "...", "reviewStatus": "...", "reviewResult": {...}, "ourMappedStatus": "pending|approved|..." }
  Errors: 404 if user has no applicant yet (frontend triggers /access-token)

POST /api/v1/webhooks/sumsub
  Auth: HMAC signature in X-Payload-Digest header (verified against SUMSUB_WEBHOOK_SECRET)
  Body: Sumsub webhook payload (JSON)
  Returns: 200 always (idempotent), 403 if signature invalid
  Side effects: UPDATE sumsub_applicants + kyc_submissions; INSERT aml_alerts (if AML event)
```

### 5.3 Frontend

```typescript
// New hook in frontend/src/lib/sumsubKyc.ts
export function useSumsubKyc() {
  // Returns: { accessToken, applicantId, status, refresh }
  // Manages: fetch token → poll status while iframe open
}

// In compliance/kyc/page.tsx — replace placeholder UI with:
<SumsubWebSdkContainer
  accessToken={accessToken}
  onComplete={() => router.refresh()}
  onError={(err) => toast.error(err.message)}
/>
```

---

## 6. Sumsub-specific gotchas

### 6.1 HMAC signing of API requests

Every Sumsub API request needs:
```
X-App-Token: <SUMSUB_APP_TOKEN>
X-App-Access-Sig: <HMAC-SHA-256 hex>
X-App-Access-Ts: <unix-timestamp>
```
where signature = `HMAC-SHA-256(secret, ts + method + path + body)`.

Implementation in `sumsub_service.py` will be a small `_sign_request(method, path, body)` helper.

### 6.2 Webhook signature

```
X-Payload-Digest: <HMAC-SHA-256(SUMSUB_WEBHOOK_SECRET, raw_body) hex>
```

We verify in route handler **before** parsing JSON. If bytes are even 1 char off, mismatch → 403.

### 6.3 Idempotent applicant creation

Sumsub allows `externalUserId` field — our `user_id`-as-string. If we POST `/resources/applicants` with same `externalUserId` twice, Sumsub returns `409 Conflict {applicantId: existing}`. We handle this case as expected — don't error, just look up existing.

### 6.4 WebSDK init JS pattern

```html
<script src="https://static.sumsub.com/idensic/static/sns-websdk-builder.js"></script>
<script>
  window.snsWebSdk
    .init(accessToken, () => fetch('/api/v1/kyc-kyb/sumsub/access-token').then(r => r.json()).then(j => j.accessToken))
    .withConf({lang: 'ru'})
    .withOptions({addViewportTag: false, adaptIframeHeight: true})
    .on('idCheck.onApplicantSubmitted', () => location.reload())
    .build()
    .launch('#sumsub-websdk-container');
</script>
```

Wrap in React component with proper script-tag injection and lifecycle management.

### 6.5 Test sandbox

Sumsub has a **sandbox** environment (`api.sumsub.com` with separate test app credentials). Tests don't need to hit real Sumsub — we mock all calls. But Sprint 2.4.4 should include one-shot smoke test against sandbox if user provides creds.

---

## 7. Test strategy

### 7.1 Sprint 2.4.1 backend service tests

```python
# backend/tests/test_sumsub_service.py
class TestSumsubService:
    def test_sign_request_produces_correct_hmac(): ...
    def test_create_applicant_returns_existing_on_409(): ...
    def test_create_applicant_propagates_other_errors(): ...
    def test_generate_access_token_signature_matches_doc(): ...
    def test_verify_webhook_signature_accepts_valid(): ...
    def test_verify_webhook_signature_rejects_tampered_body(): ...
    def test_verify_webhook_signature_rejects_wrong_secret(): ...
```

Mock httpx.AsyncClient via monkeypatch.

### 7.2 Sprint 2.4.2 webhook endpoint tests

```python
# backend/tests/test_sumsub_webhook.py
async def test_webhook_unsigned_returns_403(): ...
async def test_webhook_with_tampered_signature_returns_403(): ...
async def test_webhook_applicantReviewed_GREEN_marks_kyc_approved(): ...
async def test_webhook_applicantReviewed_RED_marks_rejected(): ...
async def test_webhook_applicantOnHold_marks_manual_review(): ...
async def test_webhook_aml_alert_inserts_into_aml_alerts_table(): ...
async def test_webhook_idempotent_duplicate_event_is_ok(): ...
```

Use `httpx.AsyncClient` test transport; pre-compute valid HMAC for each payload fixture.

### 7.3 Sprint 2.4.3 frontend tests

`tsc --noEmit` clean. Manual click-through after deploy: `/compliance/kyc` opens iframe (Sumsub sandbox creds), drag-drop test PDF, see status update.

### 7.4 Coverage targets

- `sumsub_service.py`: 100% on signing helpers, 80%+ overall (skipping happy-path retry loops)
- Webhook handler: 100% (signature paths + each event type)
- DB migration: applied cleanly, indices in place

### 7.5 CI integration

Add `backend/tests/test_sumsub_service.py` and `backend/tests/test_sumsub_webhook.py` to `.github/workflows/ci.yml` test list. Goal: **167 → 180+** total, 0 skipped.

---

## 8. Sprint breakdown

### Sprint 2.4.1 — Backend service + DB

**Acceptance criteria:**
- New file `backend/services/sumsub_service.py` (~200 lines)
- New migration `backend/migrations/025_sumsub_kyc.sql`:
  - `ALTER TABLE kyc_submissions ADD COLUMN sumsub_*` (4 columns)
  - `CREATE TABLE sumsub_applicants` (per ADR-6)
  - `INSERT INTO schema_migrations VALUES ('025_sumsub_kyc', 'Sumsub KYC integration columns')`
- New endpoints in `routes_kyc_kyb.py`:
  - `POST /sumsub/access-token`
  - `GET /sumsub/applicant-status`
- Tests: `test_sumsub_service.py` — 7+ tests, all passing
- compileall clean
- existing 167 tests still pass + 7 new = 174

**Files:**
- `backend/requirements.txt` — possibly +1 line if we add new dep (but `httpx` already there ✓)
- `backend/services/sumsub_service.py` (new)
- `backend/migrations/025_sumsub_kyc.sql` (new)
- `backend/api/routes_kyc_kyb.py` (~60 lines added)
- `backend/tests/test_sumsub_service.py` (new, ~150 lines)
- `.github/workflows/ci.yml` (+1 line)

### Sprint 2.4.2 — Webhook receiver

**Acceptance criteria:**
- New file `backend/api/routes_webhooks_sumsub.py` (~100 lines)
- Wired in `backend/main.py` `app.include_router(...)`
- HMAC verification before parsing
- Status mapping per ADR-5
- Idempotency per ADR-10
- AML event handler stores into `aml_alerts` (basic — full Story 2.6 expands)
- Tests: `test_sumsub_webhook.py` — 7+ tests, all passing
- existing 174 tests still pass + 7 new = 181

**Files:**
- `backend/api/routes_webhooks_sumsub.py` (new)
- `backend/main.py` (+1 line for router include)
- `backend/tests/test_sumsub_webhook.py` (new, ~200 lines)
- `.github/workflows/ci.yml` (+1 line)

### Sprint 2.4.3 — Frontend integration

**Acceptance criteria:**
- New file `frontend/src/lib/sumsubKyc.ts` — TS-declaration of `window.snsWebSdk` + helper hook
- New component `frontend/src/components/compliance/SumsubWebSdkContainer.tsx`
- Replace placeholder UI in `frontend/src/app/(authenticated)/compliance/kyc/page.tsx`
- Загрузка SDK через `<Script src="https://static.sumsub.com/...">`
- Status display panel
- `tsc --noEmit` clean
- ESLint baseline ≤ existing (no new warnings)

**Files:**
- `frontend/src/lib/sumsubKyc.ts` (new)
- `frontend/src/components/compliance/SumsubWebSdkContainer.tsx` (new)
- `frontend/src/app/(authenticated)/compliance/kyc/page.tsx` (rewrite)
- `frontend/src/i18n/locales/{ru,en,ky}.json` — minor strings

### Sprint 2.4.4 — Integration + docs

**Acceptance criteria:**
- `docs/prod-readiness.md` — section 5 ❹ (KYC) переведена в DONE с конкретными Coolify env vars; section 5 ❸ (AML) — partially DONE (basic webhook bridge), full Story 2.6 deferred
- `docker-compose.yml` — env-hint block для Sumsub vars
- `CHANGELOG.md` — Wave 19 entry
- Story file (этот) — frontmatter `status: done`, sprints completed list
- (Опционально) Smoke test против Sumsub sandbox если у пользователя есть creds
- Backend deploy НЕ триггерим автоматом — Sumsub vars нужно сначала выставить в Coolify env

**Files:**
- `docs/prod-readiness.md` — обновление секции 5
- `docker-compose.yml` — +5 строк env-hint
- `CHANGELOG.md` — +entry
- `docs/stories/2-4-sumsub-kyc-architecture.md` — frontmatter

---

## 9. Risk register

| ID | Риск | Вероятность | Mitigation |
|---|---|---|---|
| R1 | Sumsub API rate limits в проде | Low | Default 10 req/sec — наш use case далеко ниже. Add retry-on-429 в service. |
| R2 | Webhook идёт не через CF (Sumsub-side IP whitelist миссы) | Medium | Sumsub допускает custom-domain webhook URL. Используем `https://orgon.asystem.ai/api/v1/webhooks/sumsub` — CF принимает. Whitelist Sumsub-IP не нужен (HMAC + path obscurity). |
| R3 | WebSDK iframe ломается на mobile / incognito | Medium | Sumsub WebSDK сам тестирован на mobile. Manual smoke на 375px viewport в Sprint 2.4.3. |
| R4 | applicantId утечёт через client-side logging | Low | applicantId не secret сам по себе (требуется access-token чтобы что-то с ним сделать). Не PII. |
| R5 | SUMSUB_WEBHOOK_SECRET утечёт через Coolify-API | Medium | Mitigation в архитектуре: webhook делает только UPDATE статусов. Утечка = поддельные статусы для applicant'ов. Не кражa middle-game value. |
| R6 | Test environment vs prod Sumsub-app credentials confusion | High | Two **separate** Sumsub apps (`sandbox` vs `prod`) с разными `SUMSUB_APP_TOKEN`/`SUMSUB_SECRET_KEY`. Документировано в prod-readiness.md. |
| R7 | DB migration 025 ломает существующие kyc_submissions данные | Low | `ALTER TABLE ADD COLUMN` с DEFAULT NULL — non-destructive. Existing rows получают NULL для новых колонок. Миграция idempotent (per pattern Wave 11). |
| R8 | KYB flow требует совершенно другого Sumsub level — может конфликтовать | Low | KYB explicitly out of scope. `SUMSUB_LEVEL_NAME` = single value пока. Story 2.5 добавит per-org level mapping. |
| R9 | Sumsub WebSDK script tag — XSS в нашем app | Very low | Loading from `static.sumsub.com` — Sumsub-managed. CSP headers (если добавим) должны разрешить этот origin. |
| R10 | i18n: Sumsub iframe internal language vs ORGON UI lang mismatch | Low | WebSDK has `lang` config — pass user's locale ('ru'/'en'/'ky'). Auto-fallback to 'en'. |

---

## 10. Open questions for user

1. **Sumsub account**: уже есть у группы ASYSTEM или нужно зарегистрировать? Sumsub onboarding — sales-flow с MSA, ~3-5 рабочих дней. Если ещё нет — нужно начать SALES-процесс параллельно с разработкой; код можно писать против sandbox.

2. **Sumsub level name**: предлагаю default `basic-kyc-level` (стандартный Sumsub-level с document + selfie + liveness). Если у вас уже есть custom level в Sumsub Dashboard — какое имя использовать?

3. **AML coverage в этой story**: я предлагаю **минимум** — webhook handler ловит `aml_alert_*` события и пишет в `aml_alerts` таблицу. Полный UI / детектор / dashboard — отдельная Story 2.6. ОК?

4. **KYB scope confirm**: KYB **не** в этой story (Sumsub KYB — отдельный flow с beneficial-owner-discovery, отдельные docs, нужен product-decision про level mapping). Story 2.5. Подтверждаем?

5. **Webhook URL strategy**: у нас prod = `orgon.asystem.ai` (shared test). Для pilot-клиента будет `<client>.asystem.ai`. Sumsub поддерживает per-environment webhook URL через app-config — клиент конфигурирует свой webhook URL в их Sumsub-app. Запишу в pilot-runbook. OK?

6. **Frontend dependency**: я предлагаю чистый `<script>` тег (ADR-8), не npm package. ОК?

7. **Integration test против Sandbox в Sprint 2.4.4**: optional. Есть ли у тебя Sumsub sandbox creds сейчас? Если да — добавлю manual smoke step. Если нет — пропустим, mocked tests достаточно для merge.

---

## 11. Definition of done — для всей story 2.4

- [ ] Все 4 sprint'а выполнены
- [ ] `python -m pytest <test list>` — 181+ tests pass, 0 skipped, 0 failed
- [ ] `python -m compileall backend/` — exit 0
- [ ] `cd frontend && npx tsc --noEmit` — exit 0
- [ ] Migration 025 применилась чисто на свежей БД
- [ ] `docs/prod-readiness.md` секции 5 ❹ DONE, 5 ❸ partial DONE
- [ ] `CHANGELOG.md` Wave 19 entry
- [ ] Story file (этот) frontmatter `status: done`
- [ ] Коммит на `feature/demo-simulator`, push
- [ ] **Не триггерим Coolify deploy автоматом** — нужно сначала выставить SUMSUB_* env vars иначе backend упадёт на первом обращении к KYC endpoint'у. Документирую как «manual deploy after Coolify env config».

---

## 12. Estimated execution time

Похоже на 2.3 (KMS) — реалистично **одна полная сессия** при условии:
- Sumsub API работает как документировано (риски R1, R6)
- WebSDK iframe не имеет surprise edge case на нашей build-pipeline (риск R3)
- Migration 025 проходит чисто (риск R7)

Если будут сюрпризы — добавляем итерации debug, но скоп story остаётся MVP-KYC-individuals.

---

## 13. Что мне нужно от тебя ДО старта

**Минимум:**
- ✓/✗ approval плана как написан
- Ответы на open questions 1-7 (либо «по дефолту, решай сам»)

**Идеально:**
- `SUMSUB_APP_TOKEN` + `SUMSUB_SECRET_KEY` для **sandbox** (sandbox.sumsub.com) — добавлю Sprint 2.4.4 smoke test
- `SUMSUB_LEVEL_NAME` если custom; иначе default `basic-kyc-level`

После approval — запускаю Sprint 2.4.1, дальше по плану. Между sprints буду фиксировать `tsc/lint/test` чек-поинты. Deploy на orgon.asystem.ai НЕ делаем без явного OK + предварительной выставки env vars в Coolify.
