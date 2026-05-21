# Custdev — Role 5: Super-admin / platform-admin (Каиссар)

> **Companion docs.**
> Operator + end-user — [`CUSTDEV_OPERATOR_END_USER.md`](CUSTDEV_OPERATOR_END_USER.md).
> Developer (asystem-core integrator) — [`CUSTDEV_DEVELOPER.md`](CUSTDEV_DEVELOPER.md).
> Compliance officer — [`CUSTDEV_COMPLIANCE.md`](CUSTDEV_COMPLIANCE.md).
>
> **Подход.** Тянем, не толкаем. Идём от ежедневного потока platform-
> admin'а, фиксируем friction points, превращаем в backlog.
>
> Сверено с кодом 2026-05-21 (после деплоев `b6e707b` + `23e0ab5` +
> `2655850`).

---

## Контекст

Каиссар — platform-owner ORGON'а. Управляет всеми merchant'ами
(в нашем случае это и asystem-core operator'ы, и прямые B2B clients).
Его роль в RBAC — `super_admin` (или `platform_admin`; они различимы
только на backend для эскалационных операций — здесь рассматриваются
как одна роль).

Его типичные задачи:
1. Подключить нового merchant'а (вручную или принять self-provision
   call от asystem-core)
2. Выдать API-keys + ротировать compromised
3. Просмотреть quota / usage / billing
4. Suspend / reactivate проблемного merchant'а
5. Смотреть deposit/transaction lookup'ы при support-тикетах
6. Контролировать platform-wide AML alerts (cross-tenant)

Доступ через JWT с `role = super_admin`, плюс знание
`ORGON_PLATFORM_MASTER_KEY` для machine-driven self-provisioning.

---

## Сценарий «утренний обход + onboarding нового клиента»

| # | Шаг | Где это в коде | Боль до фикса · статус после |
|---|---|---|---|
| 1 | Логин → /dashboard. Каиссар видит sidebar — ищет `/admin/merchants` или подобное. | `AceternitySidebar` + `sidebar-nav.ts` | **SA-1 [CRITICAL, FIXED 2026-05-21]**. До фикса: НИКАКОГО sidebar entry для admin/merchants. `/admin/merchants` существовала как страница (Wave 28), но в новом sidebar (после redesign) её не было. Каиссар должен был знать URL наизусть. Плюс escalation-баг: `super_admin` user.role не матчился ни с одной `roles:` array → super_admin видел МЕНЬШЕ items чем обычный admin. См. **SA-1**. |
| 2 | После фикса: в группе «platform» появился пункт «Мерчанты» (только для super_admin/platform_admin) → клик → `/admin/merchants`. | `sidebar-nav.ts` + 3 локали | ✓ |
| 3 | Видит таблицу: имя, тип, план, среда (sandbox/live), статус, источник (manual/api), кол-во ключей, юзеров. | `admin/merchants/page.tsx` (Wave 28) | ✓ Solid. |
| 4 | Замечает нового merchant'а с `provisioning_source: api` — значит asystem-core самопровизонилась через `/platform/merchants`. | `routes_platform_admin.py` (Wave 33) | ✓ |
| 5 | Кликает на merchant → `/admin/merchants/[id]` → видит вкладки Биллинг, Treasury, deposit lookup, invoices, api-keys management. | Wave 35, 36, 37 builds | ✓ |
| 6 | Ротирует одну compromised API-key пару кнопкой Revoke + Issue new. | `POST /api/admin/merchants/{id}/api-keys` + `POST .../api-keys/{key_id}/revoke` | ✓ |
| 7 | Открывает Treasury вкладку конкретного merchant'а — видит их balance breakdown по сетям + кошелькам. | `routes_merchant_admin.py:425` + frontend | ✓ Wave 32 |
| 8 | Support-тикет: «клиент жалуется что отправил USDT-TRC20, мы не видим». Каиссар открывает merchant'а → Deposit lookup → вводит tx_hash. | `routes_merchant_admin.py:393 /deposits/lookup` (Wave 35) | ✓ |
| 9 | Хочет подключить новый merchant — кликает «Onboard merchant». | `/admin/merchants/new` page | ✓ Готов |
| 10 | На «new» странице вводит данные, выпускает первую пару ключей; secret показывается ОДИН раз. | `routes_merchant_admin.py:121,303` | ✓ |
| 11 | Перед выпуском live-merchant'а хочет проверить состояние backend (DB ✓, Safina ✓, KMS ✓ если включён). | `/settings/system` для admin | ✓ (но виден только role:admin сейчас — см. **SA-2**) |
| 12 | Также хочет смотреть **platform-wide** AML alerts (cross-tenant) — все алерты по всем merchant'ам, а не одного оператора. | `/compliance/aml-alerts` (новая страница) | **SA-3 [observation]**. Сегодня AML list endpoint имеет фильтр `org_ids` для admin-роли. Super_admin может пройти `org_ids=null` чтобы увидеть все. Однако UI этот режим не сигнализирует (фильтр не показан, нет переключателя «все merchant'ы / мой merchant»). См. **SA-3**. |

---

## Найденные точки трения

### **SA-1 [CRITICAL BUG, FIXED 2026-05-21]** — Super-admin был слепым через sidebar

**Симптом.** Два связанных бага:

(a) **Нет sidebar entry для `/admin/merchants`.** Wave 28 добавила
    страницу `/admin/merchants` + связанные routes (`new`, `[id]`).
    Legacy `Sidebar.tsx` имел entry. Но redesign (commit `735951a`
    и далее) перешёл на `AceternitySidebar` + `sidebar-nav.ts`,
    куда entry не перенесли. Каиссар должен знать URL наизусть.

(b) **Escalation gap в `filterByRole`.** Тип
    `SidebarRole = "all" | "admin" | "signer" | "viewer"` НЕ включал
    `super_admin` или `platform_admin`. `AceternitySidebar` кастует
    `user.role` к этому типу через `as` (assertion, не transform).
    Когда `user.role === "super_admin"`, `filterByRole("super_admin")`
    дёргает `items.filter(i => i.roles.includes("super_admin"))` —
    но ни у одного item роли `super_admin` нет. Super_admin user
    видел **только** items с `roles: ["all"]` — меньше чем обычный
    `admin`. Это backwards-incompatible с тем как admin escalation
    обычно работает (super_admin = все права + дополнительные).

**Last impact.** Платформ-овнер заходил в свой собственный продукт и
видел меньше функций чем обычный operator-admin. Бизнес-критическая
страница `/admin/merchants` была inaccessible через UI.

**Fix shipped (2026-05-21):**

* `SidebarRole` расширен: добавлены `super_admin` и `platform_admin`.
* Новая константа `_ADMIN_ESCALATION` описывает наследование:
  `super_admin → [super_admin, platform_admin, admin]`,
  `platform_admin → [platform_admin, admin]`. Это даёт super_admin'у
  всё что видит admin + дополнительные super_admin-only items.
* `filterByRole` теперь резолвит effective role set через
  `_ADMIN_ESCALATION` и проверяет `effective.some(r =>
  i.roles.includes(r))`. Defensive fallback на `[role]` если
  backend выкатит новый role-value не описанный в map.
* Новый sidebar entry в группе `platform`: `/admin/merchants` →
  «Мерчанты» / «Merchants» / «Merchants», icon `solar:shop`. Видим
  только `super_admin` + `platform_admin`.
* i18n keys `merchants` добавлены в `en.json` + `ky.json`, заменена
  «Merchants» на «Мерчанты» в `ru.json` (была англ копия).

**Тесты:** ручной runtime check через `tsx -e` — 5 cases (5 ролей)
все pass. `super_admin` и `platform_admin` видят merchants, остальные
не видят. Все 5 видят dashboard (`roles: ["all"]`). Это не unit-тест
с pytest — pure function, инлайн-verify достаточно.

### **SA-2 [observation]** — System / monitoring доступы только role:admin

Pages `/settings/system` и `/settings/system/monitoring` в sidebar
имеют `roles: ["admin"]`. Через новую escalation logic super_admin
теперь их видит (через admin наследование). Но семантически эти
страницы — platform-wide observability (DB health, Safina reachability,
KMS status). Стоит ли их явно maркировать как `super_admin`-only?

Сейчас на kiril.asystem.ai (shared-test) demo-admin имеет role
`admin` и видит эти страницы. Это нормально для shared-test (где
один tenant = весь mock-environment), но на multi-tenant prod
operator-admin от одного merchant'а не должен видеть системные
healthchecks другого.

**Action (defer).** Когда multi-tenant prod заведётся реально (не
shared-test), переключить `/settings/system*` на `roles:
["super_admin", "platform_admin"]`. Сейчас не блокирует.

### **SA-3 [observation]** — Cross-tenant AML view нет в UI

`/compliance/aml-alerts` (созданная вчера) использует `AmlAlertList`
который дёргает `/api/v1/compliance/aml/alerts`. Endpoint accept'ит
optional `org_id` фильтр; для super_admin без фильтра возвращает
все alerts по всем tenant'ам.

Однако UI:
- Не показывает selector «мой operator / все operators»
- Не показывает org_id колонку в таблице (super_admin не знает
  какой alert от какого operator'а)
- Не показывает per-operator stats breakdown в шапке

**Action (defer, 1-2ч).** Добавить org-filter в UI с auto-detect:
- Если `user.role` ∈ {super_admin, platform_admin}: показать
  selector + org_id колонку
- Иначе: hidden, всегда фильтрует по моему оператору

Эта features blueprint похожа на admin/merchants — он уже умеет
показывать cross-tenant view. Можно подсмотреть.

Effort: 1-2ч (UI + data fetch).

### **SA-4 [observation]** — Self-provisioning (`/platform/merchants`) не имеет UI

`/platform/merchants` self-provision endpoint live (Wave 33). Master-
key используется asystem-core'ом для machine-driven provisioning.
Сам Каиссар не использует master-key — для ручного onboarding
существует `/admin/merchants/new` (JWT-route).

Но иногда Каиссар хочет дёрнуть `/platform/merchants` сам — например
протестить с curl как поведёт себя при двойном slug. Документации
для этого нет на UI-уровне; нужно открыть `docs/PLATFORM_API_GUIDE.md`.

**Action (low priority).** Маленькая команда `Open API docs` в
`/admin/merchants` (link на `/api/docs#tag/platform-admin` Swagger)
плюс просто упоминание в /admin/merchants header'е что есть второй
вход для машинной автоматизации. Может быть полезно для документации
self vs автоматизация.

Effort: 5-10 минут.

---

## Что прошло проверку

* `/admin/merchants` Wave 28 — list + filter + drill-down ✓
* `/admin/merchants/new` — Onboard merchant form, выдаёт secret-once ✓
* `/admin/merchants/[id]` — tabs: Биллинг, Treasury, deposit lookup,
  invoices, api-keys management ✓
* `routes_merchant_admin` Wave 28+32+35+36+37 — full lifecycle CRUD ✓
* `routes_platform_admin` Wave 33 — self-provision endpoint, audit
  trail, idempotency by slug ✓
* `PlatformMasterAuthMiddleware` — Bearer-token validation, 503 on
  unconfigured, vague 401 on wrong-token (no probe-leak) ✓

---

## Приоритезация

| ID | Боль | Status | Effort |
|---|---|---|---|
| **SA-1** | Sidebar entry + escalation broken | ✅ FIXED 2026-05-21 | — |
| **SA-2** | `/settings/system*` гранулярность | Defer (multi-tenant gate) | Low |
| **SA-3** | Cross-tenant AML view | Defer (1-2ч UI) | Medium |
| **SA-4** | Self-provision UI hint | Defer (5-10 мин) | Low |

Super-admin роль закрыта с одним критическим фиксом (SA-1) и тремя
отложенными observations.
