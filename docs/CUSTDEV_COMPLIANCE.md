# Custdev — Role 4: Compliance officer (Aigul)

> **Companion docs.**
> Operator + end-user — [`CUSTDEV_OPERATOR_END_USER.md`](CUSTDEV_OPERATOR_END_USER.md).
> Developer (asystem-core integrator) — [`CUSTDEV_DEVELOPER.md`](CUSTDEV_DEVELOPER.md).
>
> **Подход.** Тянем, не толкаем. Идём от ежедневного потока compliance-
> officer'а через продукт, фиксируем точки трения, превращаем в
> backlog.
>
> Сверено с кодом 2026-05-21 (после деплоя TD-12).

---

## Контекст

Айгуль — compliance officer на стороне лицензированного оператора
криптообменника (Kiril). Её мандат — пройти ежедневный AML-триаж
(claim → investigate → resolve), при подозрении сформировать SAR
для Финнадзора КР. На её стол попадают как клиентские KYC-заявки на
проверку, так и AML-алерты от transaction rule engine.

Доступ: `company_auditor` role (read + AML triage actions); часть
действий требует `company_admin` (rules CRUD).

---

## Сценарий «утренний триаж + SAR за день»

| # | Шаг | Где это в коде / docs | Боль до фикса · статус после |
|---|---|---|---|
| 1 | Логин на `kiril.asystem.ai`. Открывает sidebar, ищет AML-очередь. | `frontend/src/components/layout/sidebar-nav.ts` | **CO-1 [FIXED]**. До этой сессии sidebar показывал «AML алерты» → /compliance/reviews, но эта страница рендерила **KYC/KYB approvals** (`ReviewsPage` в `compliance/reviews/page.tsx`). Compliance officer кликал, видел не то что ожидал, плыл по поверхности страницы пытаясь найти AML. → См. **CO-1** ниже. |
| 2 | Видит в sidebar после фикса: «AML очередь» (новый вход) + «KYC/KYB заявки» (бывший reviews) | `sidebar-nav.ts` + 3 локали (ru/en/ky) | ✓ |
| 3 | Кликает «AML очередь» → `/compliance/aml-alerts` → видит таблицу алертов с фильтрами status/severity, статистика сверху | новая страница + `AmlAlertList` | ✓ Wave 21 component live |
| 4 | Кликает на алерт → открывается drawer (URL state `?alert=<id>`). Видит details, transaction info, severity, suspected reason. | `AmlAlertDrawer.tsx` | ✓ |
| 5 | Жмёт «Взять в работу» — claim. Status flips `open` → `investigating`, фиксируется `assigned_to`. | `compliance_service.claim_aml_alert` + audit_log | ✓ Wave 21 + TD-1 Phase A теперь пишет в `audit_log.organization_id` |
| 6 | Добавляет note: «Связалась с клиентом, ждём подтверждения источника средств» | `compliance_service.append_aml_note` | ✓ |
| 7 | Принимает решение `resolved` / `false_positive` / `reported`. Для `reported` обязателен SAR-номер. | `handleResolveConfirmed` в drawer'е | ✓ |
| 8 | Для SAR жмёт «Сформировать SAR» → скачивает JSON + Markdown structured-report. | drawer footer + `/api/v1/compliance/aml/alerts/{id}/sar.json` + `.md` | ✓ Wave 24 |
| 9 | Подаёт SAR в Финнадзор (out-of-band: email или через ГИС-Фининформ portal). Возвращается, вводит `report_reference` (например `SAR-2026-001`), переводит alert в `reported`. | drawer confirm dialog | ✓ |
| 10 | Хочет посмотреть audit-trail своих действий за день. | `/audit` sidebar entry | Audit log есть, но **нет direct-link** из drawer/list к фильтрованному audit-view. См. **CO-5** ниже. |
| 11 | В конце дня заходит в `/compliance/rules` посмотреть текущие правила engine'а, обновить threshold | `compliance/rules/page.tsx` (Wave 25) | ✓ Solid CRUD, RBAC, badges, alert-toast на ошибках (мы заменили `alert()` сегодня) |
| 12 | Хочет посмотреть SAR backend status (отправляем через `email` / `manual_export` / `api_v1`?). | `SarBackendIndicator` в /compliance index | **CO-2 [observation]**. Indicator живёт только на /compliance index, которая в sidebar помечена `roadmap: true`. Айгуль не пойдёт туда регулярно. См. ниже. |

---

## Найденные точки трения

### **CO-1 [BUG, FIXED 2026-05-21]** — Sidebar «AML алерты» → KYC/KYB

**Симптом.** Sidebar в `insights` группе показывал пункт «AML алерты»
во всех 3 локалях (`ru`/`en`/`ky`) с href `/compliance/reviews`. Но
страница `/compliance/reviews` рендерила компонент `ReviewsPage`,
которая показывает **KYC/KYB submission approval queue** — совершенно
другой workflow от AML triage.

Реальный AML triage (`AmlAlertList` компонент с Wave 21 функционалом
— claim/resolve/notes/SAR) был доступен **только** через вкладку
«AML» внутри страницы `/compliance` (которая в sidebar помечена
`roadmap: true` с бейджем «Скоро»).

**Last impact.** Compliance officer's daily-use entry-point был
сломан. Чтобы добраться до реального AML triage, нужно было:
1. Игнорировать «AML алерты» в sidebar (или попасть на ту страницу
   и понять что она про KYC/KYB)
2. Найти `/compliance` под «Скоро»-бейджем (≠ продакшен сигнал)
3. Кликнуть AML-таб внутри

**Fix shipped (2026-05-21):**

* Новая страница `/compliance/aml-alerts` — thin wrapper над
  `<AmlAlertList />` с собственным Header'ом и подсказкой про
  источники сигналов (Sumsub-bridge + transaction rule engine).
* Новый sidebar entry `complianceAml` → «AML очередь» / «AML Queue»
  / «AML кезеги», icon `solar:shield-warning`.
* Существующий entry `complianceReviews` переименован в
  «KYC/KYB заявки» / «KYC/KYB Reviews» / «KYC/KYB өтүнмөлөрү» с
  иконкой `solar:clipboard-check` (правильно отражает что страница
  делает).
* Banner на `/compliance` index'е, который ошибочно указывал на
  «/compliance/reviews (AML-очередь, SAR)», обновлён — теперь
  правильно указывает на `/compliance/aml-alerts` для AML и
  `/compliance/reviews` для KYC/KYB.

### **CO-2 [observation]** — SAR backend indicator hidden inside roadmap page

`SarBackendIndicator` компонент показывает compliance officer'у
текущий backend SAR-submission'ов (`manual_export | email | api_v1 |
dryrun`), готовность (`ready: bool`), missing env vars, target-email
и SMTP-конфигурацию. Это важно для compliance officer'а — без него
непонятно куда фактически уходят SAR.

Сейчас живёт ТОЛЬКО на `/compliance` index в самом верху, и эта
страница в sidebar помечена `roadmap: true` — Айгуль естественно
будет туда заходить редко.

**Action (defer — minor).** Дублировать `SarBackendIndicator` в
шапку нового `/compliance/aml-alerts` (там, где compliance officer
проводит большую часть дня). Маленький компонент, не блокирует
основной flow, но снимает один вопрос «куда уходят мои SAR».

Effort: 5 минут (импорт + render).

### **CO-3 [observation]** — Нет explicit-link из drawer'а в audit

После того как Айгуль ресолвит alert, она может захотеть проверить
свой audit-trail — особенно если её работа подлежит compliance-аудиту
(внешний инспектор Финнадзора может прийти с проверкой её действий
за квартал).

Прямой link "View audit log" из drawer'а (или из row в списке)
отсутствует. `/audit` есть в sidebar, но фильтрация по
`resource_type=aml_alert AND resource_id=<id>` требует ручного
параметра в query string.

**Action (defer — UX polish).** Добавить link "Audit trail for this
alert" в footer drawer'а → переходит на `/audit?resource_type=
aml_alert&resource_id=<id>`. Backend `/api/audit/events` уже
поддерживает эти фильтры (см. `routes_audit.py`).

Effort: 15 минут.

### **CO-4 [observation]** — Нет standalone «sanction list lookup» UI

GSFR-screening (sanctions / PEP / high-risk-countries) работает
автоматически в `compliance_service.evaluate_transaction_rules`.
Compliance officer видит результаты только через AML алерты (когда
правило сработало).

Бывают сценарии когда compliance officer хочет ad-hoc проверить:
«вот мне дали имя — есть ли оно в санкционных листах перед тем как
открыть процесс ускоренной верификации?». Сейчас такой surface нет —
надо ждать пока клиент попробует транзакцию и rule engine сработает.

**Action (defer — out-of-scope для текущего sprint).** Standalone
форма `/compliance/screening` с пол-страничным reusable lookup'ом
поверх существующего GSFR-индекса. Backend уже имеет данные
(Wave 23-26). Полудневный кусок UI.

Не блокирует pilot — defer пока не попросит конкретный compliance
officer оператора.

---

## Что прошло проверку

* AmlAlertList компонент (Wave 21) — full triage UI с фильтрами,
  пагинацией, drawer'ом, URL-state. ✓
* AmlAlertDrawer (Wave 21+24) — claim/resolve/notes + SAR generation
  (JSON + Markdown) + report_reference confirmation dialog. ✓
* `/compliance/rules` (Wave 25) — solid CRUD с RBAC, badges,
  toast-уведомления на ошибках (вчера заменили `alert()` calls). ✓
* SAR backend channels (Wave 24) — `manual_export | email | api_v1 |
  dryrun`, GSFR-list-fetch cron через pg_cron + pg_net. ✓
* audit_log теперь tagged `organization_id` (TD-1 Phase A) — Айгуль
  не leak'ает в чужие tenant'ы данные. ✓
* signature_history полностью покрыт sign'ом — единый audit trail
  multi-sig действий (TD-2). ✓
* Inline-emit webhook gate тестово зафиксированы — будущие
  изменения в `sync_transactions`/`sync_wallets` не сломают tx-event
  доставку в asystem-core (TD-12). ✓

---

## Приоритезация

| ID | Боль | Status | Effort |
|---|---|---|---|
| **CO-1** | Sidebar mislabel | ✅ FIXED 2026-05-21 | — |
| **CO-2** | SAR indicator hidden | Defer (5 мин) | Low |
| **CO-3** | Audit linkage from drawer | Defer (15 мин) | Low |
| **CO-4** | Standalone sanction lookup | Defer (4ч UI) | Medium |

Эта роль закрыта прилично — Waves 21+24+25 покрыли почти все
ключевые потоки. CO-1 был единственный реальный блокер для
ежедневного пользователя; теперь исправлен.
