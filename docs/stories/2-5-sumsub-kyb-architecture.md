---
name: Sumsub KYB integration (businesses) — Architecture & Sprint Plan
status: done
created: 2026-05-02
completed: 2026-05-02
type: architecture-decision-record + sprint-plan
parent_story: 2.5 — Production Readiness — Sumsub KYB for Businesses
relates_to: docs/stories/2-4-sumsub-kyc-architecture.md (precedent), docs/prod-readiness.md
follows: Wave 19 (Sumsub KYC for individuals)
phases_after_this:
  - Story 2.6 — AML triage UI / alert ↔ transaction wiring
---

# Story 2.5 — Sumsub KYB integration (businesses)

## 1. Goal (single sentence)

Расширить Sumsub-интеграцию (Wave 19) на верификацию **юридических лиц** так, чтобы организация-клиент могла загрузить регистрационные документы + информацию о бенефициарах через тот же WebSDK iframe, переиспользуя 80% инфраструктуры от 2.4 — закрывая последний gap для онбординга банков, брокеров и финтех-клиентов.

## 2. Why this is just delta from 2.4

KYC и KYB у Sumsub — **один и тот же applicant API**, отличается только `levelName`. Поэтому:

- ✅ `SumsubService` уже принимает `level_name` параметр (Wave 19) — work as-is
- ✅ Webhook handler (`routes_webhooks_sumsub.py`) обрабатывает события для applicant'а любого типа — work as-is
- ✅ Frontend `SumsubWebSdkContainer` параметризуется access-token'ом, не привязан к KYC — work as-is
- 🔄 Нужно: **новые endpoints** (`/sumsub/kyb-*`), **новая DB-таблица** (`sumsub_kyb_applicants`), **новая frontend-страница** (`/compliance/kyb`)

KYB-applicant в Sumsub привязан к **организации**, не к user'у. Один пользователь может быть admin'ом нескольких организаций — для каждой из них отдельный KYB-applicant.

---

## 3. Architecture Decision Records (delta-only — общий контекст в 2.4)

### ADR-1 — Отдельная таблица `sumsub_kyb_applicants`, не расширение `sumsub_applicants`

**Decision:** Создаём `sumsub_kyb_applicants(organization_id PK, applicant_id UNIQUE, ...)` рядом с существующей `sumsub_applicants(user_id PK, ...)`.

**Rationale:**
- KYC = per-user (1:1 user → applicant); KYB = per-organization (1:1 organization → applicant)
- Разные PK, разные FK, разная семантика. Полиморфная single-table проще in code, но запутаннее in queries.
- Webhook handler легко определит таблицу по `externalUserId` префиксу: `orgon-user-{id}` → KYC, `orgon-org-{uuid}` → KYB.

### ADR-2 — `externalUserId` префиксная схема

**Decision:**
- KYC applicant `externalUserId` = `orgon-user-{user.id}` (уже работает с Wave 19)
- KYB applicant `externalUserId` = `orgon-org-{organization.id}`

**Rationale:** Стабильный, человекочитаемый, гарантированно уникальный (UUID организации != int user.id). Webhook handler парсит префикс чтобы понять в какую таблицу писать.

### ADR-3 — Sumsub level_name для KYB настраивается отдельным env

**Decision:** Добавить `SUMSUB_KYB_LEVEL_NAME` env var, default `basic-kyb-level`. Не переиспользуем `SUMSUB_LEVEL_NAME` (тот для KYC).

**Rationale:** В Sumsub Dashboard клиент создаёт **два разных** verification level — один для KYC (passport+selfie+liveness), другой для KYB (registration cert + UBO discovery + AML). Имена настраиваются независимо.

### ADR-4 — Только `company_admin` может стартовать KYB своей организации

**Decision:** Endpoint `/sumsub/kyb/access-token?organization_id={uuid}` требует:
- `user.role IN (super_admin, company_admin)`
- ПЛЮС RLS-проверка: user.organization_id == organization_id (super_admin bypass)

**Rationale:** KYB — корпоративная процедура, не должна стартоваться signer'ами или viewer'ами. Standard RBAC + multi-tenant RLS.

### ADR-5 — Webhook идемпотентность раздельно для KYC и KYB

**Decision:** Поле `last_event_id` в `sumsub_kyb_applicants` копирует pattern из `sumsub_applicants`. Webhook handler пишет в правильную таблицу по `externalUserId` префиксу.

**Rationale:** Прямое продолжение ADR-10 из 2.4 — same idempotency model, разные таблицы.

### ADR-6 — Status mapping для KYB переиспользуем из KYC

**Decision:** `_map_sumsub_to_orgon_status` функция (уже есть в `routes_kyc_kyb.py` и `routes_webhooks_sumsub.py`) работает one-to-one для KYB событий.

**Rationale:** Sumsub возвращает те же `reviewStatus` (`pending`/`completed`/`onHold`/...) и `reviewAnswer` (`GREEN`/`RED`) для обоих flows. Нет смысла дублировать.

### ADR-7 — Существующий `kyb_submissions` table остаётся (legacy + Sumsub coexist)

**Decision:** `kyb_submissions` table (с email-submit-flow от Wave 1) остаётся как есть. Расширяем по pattern Wave 19 — добавляем `sumsub_kyb_applicant_id`, `sumsub_review_result`, `sumsub_external_user_id` колонки.

**Rationale:** Backward compat: legacy admin queue (`/compliance/reviews`) уже работает с `kyb_submissions`. Новый Sumsub flow пишет в ту же таблицу, плюс mirror в `sumsub_kyb_applicants` для быстрого webhook lookup.

---

## 4. DB schema changes (migration 026)

```sql
-- 026_sumsub_kyb.sql

-- 1. Extend kyb_submissions (mirror of 025 KYC pattern)
ALTER TABLE public.kyb_submissions
    ADD COLUMN IF NOT EXISTS sumsub_applicant_id     varchar(64),
    ADD COLUMN IF NOT EXISTS sumsub_inspection_id    varchar(64),
    ADD COLUMN IF NOT EXISTS sumsub_review_result    jsonb,
    ADD COLUMN IF NOT EXISTS sumsub_external_user_id varchar(64);

CREATE UNIQUE INDEX IF NOT EXISTS uniq_kyb_submissions_sumsub_applicant
    ON public.kyb_submissions(sumsub_applicant_id)
    WHERE sumsub_applicant_id IS NOT NULL;

-- 2. Drop+re-add kyb_submissions status check with the same enum extension as KYC
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.table_constraints
        WHERE table_name = 'kyb_submissions'
          AND constraint_name = 'kyb_submissions_status_check'
    ) THEN
        ALTER TABLE public.kyb_submissions
            DROP CONSTRAINT kyb_submissions_status_check;
    END IF;
END$$;

ALTER TABLE public.kyb_submissions
    ADD CONSTRAINT kyb_submissions_status_check
    CHECK (status IN (
        'pending', 'approved', 'rejected',
        'manual_review', 'needs_resubmit', 'not_started'
    ));

-- 3. Sumsub KYB applicant lookup cache (mirror of sumsub_applicants for KYC)
CREATE TABLE IF NOT EXISTS public.sumsub_kyb_applicants (
    organization_id    uuid          PRIMARY KEY REFERENCES public.organizations(id) ON DELETE CASCADE,
    applicant_id       varchar(64)   NOT NULL UNIQUE,
    external_user_id   varchar(64)   NOT NULL,
    level_name         varchar(64)   NOT NULL,
    review_status      varchar(32)   NOT NULL,
    review_result      jsonb,
    last_event_id      varchar(64),
    created_at         timestamptz   NOT NULL DEFAULT now(),
    updated_at         timestamptz   NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_sumsub_kyb_applicants_review_status
    ON public.sumsub_kyb_applicants(review_status);

CREATE INDEX IF NOT EXISTS idx_sumsub_kyb_applicants_external_user_id
    ON public.sumsub_kyb_applicants(external_user_id);

-- 4. updated_at trigger (reuse Wave 19's set_updated_at_now() if exists, else create)
DROP TRIGGER IF EXISTS trg_sumsub_kyb_applicants_updated_at ON public.sumsub_kyb_applicants;
CREATE TRIGGER trg_sumsub_kyb_applicants_updated_at
    BEFORE UPDATE ON public.sumsub_kyb_applicants
    FOR EACH ROW
    EXECUTE FUNCTION public.set_sumsub_applicants_updated_at();
-- ^ reuse the existing function from migration 025 — same logic.

-- 5. Mark migration applied
INSERT INTO public.schema_migrations (version, description)
VALUES ('026_sumsub_kyb', 'Sumsub KYB integration: kyb_submissions extension + sumsub_kyb_applicants table')
ON CONFLICT (version) DO NOTHING;
```

---

## 5. Interface contracts

### 5.1 SumsubService — без изменений

`SumsubService.create_or_get_applicant(external_user_id, level_name=...)` уже принимает `level_name`. Просто вызываем с KYB-уровнем.

### 5.2 Новые endpoints (extend `routes_kyc_kyb.py`)

```
POST /api/v1/kyc-kyb/sumsub/kyb/access-token?organization_id={uuid}
  Auth: company_admin or super_admin (own org for company_admin)
  Returns: { access_token, expires_in, applicant_id, organization_id, external_user_id, level_name }
  Errors: 400 (no organization_id), 403 (not admin of this org), 503 (Sumsub unconfigured)

GET /api/v1/kyc-kyb/sumsub/kyb/applicant-status?organization_id={uuid}
  Auth: any user with organization membership
  Returns: { applicant_id, organization_id, review_status, review_result, level_name, mapped_status }
  Errors: 404 (no KYB applicant for this org yet), 503
```

### 5.3 Webhook handler updates

`routes_webhooks_sumsub.py` — пара дополнений:

```python
# При получении webhook парсим externalUserId:
# - "orgon-user-{int}" → KYC, table sumsub_applicants
# - "orgon-org-{uuid}" → KYB, table sumsub_kyb_applicants

if external_user_id.startswith("orgon-org-"):
    # KYB path
    org_id = external_user_id.removeprefix("orgon-org-")
    UPDATE sumsub_kyb_applicants ...
    UPDATE kyb_submissions ...
else:
    # KYC path (existing Wave 19 code)
    ...
```

### 5.4 Frontend — новая страница `/compliance/kyb`

Mirror of `/compliance/kyc`:
- При mount читает `organization_id` из user-context (если у user одна org — auto-pick; если несколько — selector)
- Полностью переиспользует `SumsubWebSdkContainer` — он не знает про KYC vs KYB, ему нужен только access-token
- Pre-launch banner идентичен KYC (тот же graceful 503)
- Status panel такой же

---

## 6. Sprint breakdown

### Sprint 2.5.1 — backend service + DB

**Acceptance criteria:**
- DB migration `026_sumsub_kyb.sql` (per section 4)
- Two new endpoints in `routes_kyc_kyb.py` (per section 5.2)
- New helper `get_kyb_external_user_id(org_uuid)` returning `f"orgon-org-{org_uuid}"`
- Tests: extend `test_sumsub_service.py` with KYB-level test, new test_kyb endpoints test file
- Existing 207 tests remain green; +5-7 new

**Estimated effort:** меньше 2.4.1 (Wave 19), потому что SumsubService и migration pattern reused.

### Sprint 2.5.2 — webhook handler update + tests

**Acceptance criteria:**
- `routes_webhooks_sumsub.py` парсит `externalUserId` префикс, ветвится на KYC vs KYB tables
- Тест: KYB-applicant webhook с GREEN review → UPDATE в `sumsub_kyb_applicants` и `kyb_submissions`, не KYC tables
- Тест: AML alert на KYB applicant пишется в `aml_alerts` с `organization_id` из webhook (не из users.organization_id как в KYC)
- +6-8 new tests

### Sprint 2.5.3 — frontend KYB page

**Acceptance criteria:**
- New `frontend/src/app/(authenticated)/compliance/kyb/page.tsx` — mirror of kyc/page.tsx с KYB-specific endpoints
- Если у user'a >1 организации — селектор организаций перед iframe (если 1 — auto-pick)
- `tsc --noEmit` clean
- ESLint baseline ≤ existing

### Sprint 2.5.4 — docs + integration

**Acceptance criteria:**
- `docs/prod-readiness.md` — новая секция «KYB» рядом с ❹, описывает env var `SUMSUB_KYB_LEVEL_NAME`
- `docker-compose.yml` — добавить `SUMSUB_KYB_LEVEL_NAME: "${SUMSUB_KYB_LEVEL_NAME:-basic-kyb-level}"` в env block
- `CHANGELOG.md` — Wave 20 entry
- Story file frontmatter `status: done`
- Не триггерим deploy

---

## 7. Risk register

| ID | Риск | Вероятность | Mitigation |
|---|---|---|---|
| R1 | Sumsub KYB level требует beneficial-owner-discovery (UBO), которого нет в WebSDK iframe — отдельный server-side flow | Medium | Документация Sumsub описывает оба варианта. Если требуется UBO — добавим Sprint 2.5.5 (post-MVP); MVP принимает что Sumsub iframe закрывает 80% случаев. |
| R2 | Один user — много организаций. UI selector может быть сложным | Low | Если 1 org — auto. Если 0 (странно — admin без org) — ошибка 400. Если >1 — простой dropdown. |
| R3 | KYB applicant с тем же `externalUserId` как KYC applicant — collision? | Very low | Префиксы разные (`orgon-user-` vs `orgon-org-`), плюс UUID не пересекается с int. |
| R4 | Migration 026 ломает existing `kyb_submissions` rows | Low | `ALTER ADD COLUMN ... DEFAULT NULL` non-destructive. CHECK constraint расширяем (`pending` → `pending|...new...`), existing rows не нарушают. |
| R5 | Webhook handler ветвление на KYC vs KYB — complexity creep | Low | Минимум: одно `if external_user_id.startswith("orgon-org-")` ветвление. Все mapping функции переиспользуются. |
| R6 | Sumsub KYB level имени default `basic-kyb-level` может не существовать в реальном Sumsub-аккаунте | Low | Same проблема как с KYC `basic-kyc-level` — клиент в Dashboard создаёт нужный level. Документировано. |

---

## 8. Open questions for user

1. **Sumsub KYB level name** — default `basic-kyb-level`. Подтверждаем?
2. **UBO (Ultimate Beneficial Owner) collection** — Sumsub WebSDK iframe сам собирает UBO для KYB level. Не нужно отдельный API для нас. **Подтверждаем что MVP полагается на iframe.**
3. **One-org-per-user vs multi-org** — поддерживаем сценарий когда user является admin'ом нескольких организаций? (auto-detect, dropdown selector если >1) Или строго 1:1?
4. **Frontend route** — `/compliance/kyb` (новая страница) **или** добавить tab на существующий `/compliance` page? Я за отдельную страницу — clean separation.
5. **Тесты** — same pattern как 2.4 (in-process FakeConn + httpx mocks). Подтверждаем без moto/real Sumsub?

Если по всем «решай по дефолту» — беру:
- `basic-kyb-level`
- UBO через iframe (на MVP)
- Multi-org с auto-pick / dropdown
- Отдельная страница `/compliance/kyb`
- Тесты как в 2.4

---

## 9. Definition of done

- [x] 4 спринта закрыты
- [x] Migration 026 идемпотентна, применяется чисто на свежей БД
- [x] CI subset: sumsub+signer 79/79 pass; webhook tests 16 → 21 (+5 KYB)
- [x] `python -m compileall backend/` exit 0
- [x] `cd frontend && npx tsc --noEmit` exit 0
- [x] `docs/prod-readiness.md` обновлён, KYB секция добавлена
- [x] `CHANGELOG.md` Wave 20 entry
- [x] Story file frontmatter `status: done`
- [x] **No deploy** на shared-test orgon.asystem.ai (Sumsub creds всё равно пусты)

---

## 10. Estimated time

Меньше Wave 19 — большинство кода reuse-ится:
- 2.5.1 Backend: ~30% Wave 19's
- 2.5.2 Webhook: ~10% (просто ветвление в одной строке + тесты)
- 2.5.3 Frontend: ~50% Wave 19's
- 2.5.4 Docs: ~20%

Реалистично — одна сессия, может быть короче чем Wave 19.
