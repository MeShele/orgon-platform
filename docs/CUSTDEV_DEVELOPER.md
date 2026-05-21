# Custdev — Role 3: Developer at asystem-core (Эрмек)

> **Подход.** Тянем, не толкаем. Идём от реальной траектории разработчика
> через наши интеграционные точки, фиксируем discoverability-issues и
> недостающие артефакты, делаем backlog.
>
> **Companion docs.** Operator + end-user role walks — в
> `docs/CUSTDEV_OPERATOR_END_USER.md`.
>
> Сверено с кодом 2026-05-21.

---

## Контекст

Эрмек — разработчик asystem-core. Получил задачу «подключить ORGON
Custody в новый operator deployment, потом реализовать Phase 4
outgoing payouts». Никогда раньше с ORGON не работал.

Что у него под рукой:
- доступ к `asystem-core/` репозиторию (Deno edge functions, React + TS frontend)
- credential к Supabase их инстанса
- браузер
- ссылка на наш репо `https://github.com/MeShele/orgon-platform`

Чего у него **нет**:
- доступа к нашему `https://orgon.asystem.ai/` админ UI
- знания внутренних имен Wave/Phase/Story
- готового sandbox merchant'а (по умолчанию — он должен запросить)

---

## Сценарий

| # | Шаг | Где это в коде / docs | Боль |
|---|---|---|---|
| 1 | Открывает наш репозиторий. Смотрит README.md. | `README.md` | Нет «Integrating with us?» секции в README. Подсказки на `docs/ASYSTEM_CORE_INTEGRATION.md` нет в README верхнего уровня. См. **DEV-1**. |
| 2 | Гуглит «asystem ORGON integration», находит `docs/ASYSTEM_INTEGRATION_PLAYBOOK.md` (606 строк, отлично написан, шаги 1-7) | `docs/ASYSTEM_INTEGRATION_PLAYBOOK.md` | OK. Это core artifact. |
| 3 | Видит в playbook'е TL;DR (line 15), self-service provisioning (line 29), key formats (line 66). | playbook §1 | OK. |
| 4 | Doc говорит «get a sandbox merchant via `POST /platform/merchants`». Эрмек думает: «откуда master-key?». | playbook §1 + (теперь) `docs/PLATFORM_API_GUIDE.md` | OK после моего вчерашнего гайда (PLATFORM_API_GUIDE.md дополняет playbook деталями). |
| 5 | Эрмек хочет тестово дёрнуть `/v1/ping` со своих ключей **локально** (не из edge function — просто проверить HMAC формат). Нужен sample script. | `sdks/typescript/examples/asystem-smoke/smoke.ts` существует, Deno-native, no install | **Эрмек об этом не знает**: ни `ASYSTEM_CORE_INTEGRATION.md`, ни `PLATFORM_API_GUIDE.md` не упоминают smoke. Playbook упоминает на line 583, но это глубоко в конце. См. **DEV-2**. |
| 6 | Альтернативно — он мог бы использовать SDK `@orgon/sdk`. Видит в `https://orgon.asystem.ai/developers` (наш landing). | `sdks/typescript/` + `frontend/src/app/(public)/developers/page.tsx` | **SDK не публикован в npm** (`git tag -l "sdk-*"` пустой). `npm install @orgon/sdk` не работает. На Deno из git repo подтянуть можно (`import { OrgonClient } from "https://esm.sh/@orgon/sdk"` после публикации, или vendored copy сейчас) — **никакой инструкции по Deno-консьюменю SDK нет в README**. См. **DEV-3**. |
| 7 | Эрмек пишет свой `_shared/orgon-client.ts` с нуля, читая playbook'овый HMAC раздел (§2 Phase 1). Получается bit-for-bit совпадение со smoke.ts (мы проверили — `verification matrix` memo). | `asystem-core/supabase/functions/_shared/orgon-client.ts` | Дублирование труда, но работает. См. **DEV-2** rec — указать на smoke.ts как drop-in. |
| 8 | Реализует Phase 1-3 (ping, users, wallets, webhook receiver). У него возникают вопросы по wallet pending. | playbook §3 «When `status='pending'`» (line 211) | OK — playbook это покрывает. |
| 9 | Что-то ломается в webhook'е (HMAC mismatch). Эрмек смотрит logs в Supabase Edge dashboard, но **не видит наших logs** (наш bot шлёт; для нас это outgoing). Хочет понять что мы посчитали как canonical body. | `webhook_delivery.py:113` + `WEBHOOKS.md` §Signing | Доступа к нашим логам нет. Эрмек должен сделать ту же HMAC локально и сравнить. **Нет debug-endpoint'а у нас типа `POST /v1/webhooks/replay/{delivery_id}`** который заново отправил бы webhook с raw payload Эрмеку для отладки. См. **DEV-4**. |
| 10 | Хочет видеть список всех `/v1/*` endpoint'ов сразу — что umeet каждый | `ARCHITECTURE.md` + `API.md` (репо root) + код `routes_public_v1.py` | **Нет единого catalog'а endpoint'ов** в read-friendly виде. `routes_public_v1.py` имеет 24 endpoints, разбросанных по 1000+ строкам. На `/developers` странице нашего лендинга есть partial — но не полный. SDK source — implicit catalog но requires reading `sdks/typescript/src/resources/`. См. **DEV-5**. |
| 11 | Переходит к Phase 4. Открывает `docs/ASYSTEM_CORE_PHASE4_SPEC.md` (мой вчерашний документ). | `docs/ASYSTEM_CORE_PHASE4_SPEC.md` | OK — детальная спека + drop-in Deno snippet. |
| 12 | Перед прод-rollout'ом хочет посмотреть «что я могу проверить чтобы убедиться что всё хорошо». | — | **Нет integration-test smoke checklist** для финальной валидации Phase 1-3 в проде. Smoke harness `asystem-smoke/smoke.ts` есть, но не упомянут в playbook'е как «обязательный pre-prod checklist». См. **DEV-6**. |
| 13 | Прошло 2 недели. Мы выпустили новое событие (например `transaction.uncertain` Wave 37). Как Эрмек узнает? | `CHANGELOG.md` + `WEBHOOKS.md` обновление | **Нет «what's new for integrators» канала**. CHANGELOG огромный, смешанный. У нас нет email-листа integration partners. См. **DEV-7**. |

---

## Найденные точки трения

### **DEV-1 — README верхнего уровня не указывает на integration docs.**

Эрмек открывает наш репо. `README.md` ничего не говорит «if you're
integrating us as a sub-system, read X». Doc indexing запутан:
`docs/INDEX.md` сама объявляет себя устаревшей, направляет к
root-level docs (README/ARCHITECTURE/API). Но в README нет блока
«**Integrating ORGON as a module?** Start at
`docs/ASYSTEM_INTEGRATION_PLAYBOOK.md`».

**Action.** В `README.md` после «Quick Start» добавить блок:

```md
## Integrating ORGON as a sub-system

If you're embedding ORGON as a custody backend in your platform
(like asystem-core does), start here:
1. `docs/ASYSTEM_INTEGRATION_PLAYBOOK.md` — step-by-step Phase 1-5
2. `docs/ASYSTEM_CORE_INTEGRATION.md` — current contract state
3. `docs/PLATFORM_API_GUIDE.md` — self-service merchant provisioning
4. `docs/ORGON_FOR_EXCHANGES.md` — what your operators will see
```

Effort: 5 минут.

### **DEV-2 — Smoke harness invisible to integrators.**

`sdks/typescript/examples/asystem-smoke/smoke.ts` — отличный артефакт:
Deno-native (no npm), стандартное Web Crypto API, валидирует все
Phase 1-3 endpoints. Эрмек **мог бы использовать его как drop-in
reference** вместо переписывания HMAC с нуля. Но playbook упоминает
его на line 583 (конце, секция «smoke harness»). `ASYSTEM_CORE_INTEGRATION.md`
не упоминает. `PLATFORM_API_GUIDE.md` (мой вчерашний) не упоминает.

**Action.** Сверху в `ASYSTEM_INTEGRATION_PLAYBOOK.md` (после TL;DR)
вынести «### Reference implementation» с однострочным указанием
**«Before reading further: see
`sdks/typescript/examples/asystem-smoke/smoke.ts` — 200-строчный
Deno-native script который проверяет всю Phase 1-3 цепочку. Если он
проходит на ваших ключах, contract уже работает. Если нет — failure
point показывает где залипло».**

Effort: 10 минут.

### **DEV-3 — SDK существует но не usable из Deno without publish.**

`@orgon/sdk` версия 0.1.0 в `package.json`, но `git tag -l "sdk-*"`
показывает пусто — публикации на npm не было. `.github/workflows/sdk-publish.yml`
готов (Эрмек может это увидеть в репо), но trigger не сработал.

Соответственно `npm i @orgon/sdk` или `import from "npm:@orgon/sdk"`
в Deno не работает. Эрмек должен:
- либо vendored-копировать SDK в asystem-core (плохо — race с
  обновлениями)
- либо `import from "https://esm.sh/gh/MeShele/orgon-platform/sdks/typescript/src"`
  (esm.sh supports github → npm-like serving) — **рабочий paath но
  никем не задокументирован**

**Action 1 (немедленно).** Tagнуть `sdk-v0.1.0` и пушнуть → workflow
опубликует на npm. После этого `import from "npm:@orgon/sdk"` в Deno
работает out-of-the-box.

**Action 2 (если не публикуем).** Добавить в `sdks/typescript/README.md`
секцию `## Use from Deno (no npm install)` с примером:
```ts
import { OrgonClient } from "https://esm.sh/gh/MeShele/orgon-platform/sdks/typescript@main/src/index.ts";
```

Effort: 15-30 минут (зависит от npm publish setup).

### **DEV-4 — Нет webhook replay/debug endpoint'а.**

Когда Эрмек разбирается «почему HMAC не сошёлся», у него нет способа:
- посмотреть наш audit log по этой `delivery_id`
- попросить нас retry'ть webhook вручную с raw payload
- сравнить bytes-for-bytes что мы посчитали как canonical с тем, что
  его handler делает

`GET /v1/webhooks/deliveries` (Wave 30+) показывает delivery list
**но не raw body** — только метаданные.

**Action.** Расширить `GET /v1/webhooks/deliveries/{delivery_id}`
ответом включая `raw_body` (text) и `canonical_signed_msg` (для
debug). Это уже sandbox-only data (мы не храним прод
mainnet-payloads дольше N часов — Wave 49 webhook_retention).

Effort: 1-2ч (новый endpoint + retention guard).

**Альтернатива:** документировать debug-workflow в playbook'е
(«запустите smoke.ts с теми же ключами + теми же body bytes —
повторите HMAC из failing webhook вручную»). Эффективно без code-change.

### **DEV-5 — Нет единого `/v1/*` endpoints catalog'а в одном виде.**

24 endpoint'а в `routes_public_v1.py`. Playbook ходит по Phase 1-5
тематично — но если Эрмек думает «мне сейчас надо POST /v1/users —
куда смотреть» — он должен или знать что это Phase 2, или grep'ать.

Существующий каталог: `sdks/typescript/src/resources/*.ts` — там
структурированно. **Но не auto-generated** из FastAPI OpenAPI и
**не cross-linked** в playbook.

**Action 1 (минимальная).** В `ASYSTEM_INTEGRATION_PLAYBOOK.md`
добавить «### Endpoint quick-reference» таблицу с 24 endpoint'ами и
ссылкой на Phase секцию.

**Action 2 (тяжёлая).** Export `/api/docs` (Swagger UI) → JSON →
generate markdown table в CI. Auto-sync.

Effort: 30 минут (action 1), 2-3ч (action 2).

### **DEV-6 — Нет pre-prod smoke checklist для интегратора.**

Эрмек написал свой `_shared/orgon-client.ts`. Перед прод-roll-out'ом
для нового оператора — что он должен проверить? Сейчас он guess'ит.

`smoke.ts` это и есть тот чеклист по сути, но не назван так и не
объявлен как «обязательная gate». Идеально:

```bash
# До production-deploy для нового operator'а:
ORGON_KEY=<their key> ORGON_SECRET=<their secret> deno run --allow-net --allow-env smoke.ts
# All green = safe to flip module activation in their /admin/modules
```

**Action.** Переименовать секцию в playbook'е и в `smoke.ts` README
с «smoke harness» → «**Pre-production gate**». Сделать exit-code 0
contract'ом для CI Эрмека.

Effort: 15 минут (rewording + checklist).

### **DEV-7 — Нет integration-partners changelog/notification канала.**

Когда мы выкатили Wave 37 (`transaction.uncertain` событие) или Wave
32 (`wallet.requested` событие + Treasury pull endpoints) —
Эрмек узнает только если периодически проверяет `WEBHOOKS.md` или
`CHANGELOG.md`. Нет push-сигнала.

**Action 1 (легко).** Завести `docs/INTEGRATION_CHANGELOG.md` —
**только** breaking-or-additive changes for integrators. Не WhatsNew
для маркетинга. ~5-10 entries в год. Линковать в email Эрмеку при
изменении.

**Action 2 (среднее).** Webhook `system.contract_changed` с payload
`{event_added: [...], event_changed: [...], event_removed: [...]}`.
Эмитим при PR'е что меняет webhook catalog. Эрмек подписан, видит
в `orgon_webhook_deliveries`.

**Action 3 (тяжёлое).** Email-listу integration partners. Требует
CRM, ручная работа.

Effort: 30 минут (action 1), 2-3ч (action 2), бесконечность (action 3).

---

## Приоритезация

| ID | Боль | Effort | ROI |
|---|---|---|---|
| **DEV-1** | README не указывает на integration docs | 5 мин | Высокий — first-touch fix |
| **DEV-2** | Smoke harness invisible | 10 мин | Высокий — экономит каждому новому integrator'у пол-дня |
| **DEV-6** | Pre-prod smoke checklist | 15 мин | Высокий — снижает риск regressions у Эрмека |
| **DEV-3** | SDK не publish'ed | 15-30 мин | Средний — Эрмек уже без SDK справился, но следующий integrator выиграет |
| **DEV-7** | Integration changelog | 30 мин (action 1) | Средний — превентивно, ROI растёт со временем |
| **DEV-5** | Endpoints catalog | 30 мин (action 1) | Средний — playbook покрывает большую часть |
| **DEV-4** | Webhook debug endpoint | 1-2ч | Низкий — пока никто не жаловался |

---

## Что чисто наше (Orgon)

1. **README.md update** (DEV-1) — 5 мин, добавить block «Integrating
   ORGON as a sub-system».
2. **ASYSTEM_INTEGRATION_PLAYBOOK.md update** (DEV-2 + DEV-6) — 25
   мин, вынести smoke.ts наверх как «reference impl» и «pre-prod
   gate».
3. **docs/INTEGRATION_CHANGELOG.md** (DEV-7 action 1) — 30 мин,
   завести файл с шаблоном записи.
4. **docs/INDEX.md update** — добавить новые docs (PHASE4_SPEC,
   PLATFORM_API_GUIDE, ORGON_FOR_EXCHANGES, CUSTDEV_*) в asystem-core
   секцию. 5 мин.
5. **`sdk-v0.1.0` tag + push** (DEV-3 action 1) — публикация SDK. 5
   мин (если CI workflow реально работает) или **проверить и закрыть
   гэп** если workflow упадёт.

Total «легкоразрешимое» в этой сессии: **~75 минут работы**, закрывает
DEV-1, DEV-2, DEV-6, DEV-7 полностью + DEV-3 наполовину.

DEV-4 и DEV-5 — отложить пока никто не пожалуется (premature
infrastructure).
