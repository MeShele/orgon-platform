# Custdev — operator + end-user role walkthroughs

> **Companion.** Developer role (asystem-core integrator) — отдельный
> файл [`CUSTDEV_DEVELOPER.md`](CUSTDEV_DEVELOPER.md). Этот файл
> покрывает только **роли 1 и 2** — оператор обменника и конечный
> пользователь обменника.
>
> **Подход.** Тянем, а не толкаем. Не придумываем фичи сверху —
> идём от реального пути человека через продукт, фиксируем точки
> трения, превращаем их в задачи бэклога. Каждый блокер ниже —
> кандидат на отдельный sprint-кусок.
>
> **Скоп.** Только сценарий **dual-custody через asystem-core**:
> оператор уже на их платформе, ORGON Custody — модуль в их каталоге
> рядом с DFNS. ORGON's собственный `orgon.asystem.ai` UI (sales-demo,
> см. `demo-walkthrough.md`) — отдельный flow, не здесь.
>
> Сверено с кодом 2026-05-21.

---

## 🏢 Роль 1: Оператор обменника (Kiril)

### Контекст

Kiril — владелец лицензированного обменника в КР. У него уже развёрнут
asystem-core под доменом `kiril.asystem.ai`. Он `operator_admin` своей
организации, ходит в `/admin/*` секцию.

Хочет принимать клиентский крипто-депозит через ORGON вместо ручных
кошельков в company_settings (чтобы каждый клиент получал свой
адрес, чтобы депозиты ловились автоматически, чтобы не путать).

### Сценарий «впервые подключаю ORGON»

| # | Шаг | Где это в коде | Боль |
|---|---|---|---|
| 1 | Заходит в `/admin/modules`. Видит каталог из 26 модулей. | `asystem-core/src/pages/admin/AdminModules.tsx` | Категория `wallets` показывает 2 модуля в `exclusive_group='custody'`: ORGON и DFNS. **Нет подсказки какой выбрать.** Описание ORGON — одно предложение в карточке (`migration 20260516_001`), сравнительной таблицы нет. См. **OP-1**. |
| 2 | Кликает «Активировать» на ORGON Custody. Получает confirm-dialog «отключит DFNS если активен». | AdminModules `exclusive_group` logic | ОК — это работает корректно. |
| 3 | Открывает форму с 4 полями: `ORGON_KEY`, `ORGON_SECRET`, `ORGON_BASE_URL`, `ORGON_ENV`. | `requires_api_keys` в миграции `20260516_001_orgon_custody_module.sql` | **Откуда взять ключи?** Карточка модуля их не подсказывает. Нет ссылки «Получить ключи →». См. **OP-2**. |
| 4 | (Сейчас нет.) Kiril должен написать sales@asystem.ai или связаться через Telegram. Получает по out-of-band каналу ORGON_KEY и ORGON_SECRET. | `routes_platform_admin.py:provision_merchant` существует, но только для master-key holders | Нет UX чтобы оператор сам зарегистрировался. См. **OP-3**. |
| 5 | Вставляет ключи. `ORGON_BASE_URL = https://orgon.asystem.ai`, `ORGON_ENV = sandbox`. Сохраняет. | `operator_api_keys` vault (per asystem-core) | OK. |
| 6 | Жмёт «Проверить подключение». Frontend дёргает `orgon-ping` edge → `GET /v1/ping`. Зелёный success. | `backend/api/routes_public_v1.py:public_ping` | OK — ping echoes `merchant_id` + scopes. |
| 7 | Жмёт «Зарегистрировать webhook». Edge генерит 32-байт hex secret, пишет в vault как `ORGON_WEBHOOK_SECRET`, дёргает `PUT /v1/webhooks/config` у ORGON. | `asystem-core/orgon-webhook-register/index.ts` + Orgon `put_webhook_config` | OK. |
| 8 | Хочет проверить end-to-end до пуска клиентов: создать тестовый sell-order, отправить USDT-TRC20 на nile-testnet, увидеть как заявка флипнется в `paid`. | — | **Нет sandbox-flow на стороне asystem-core**: оператор должен сам создать тестового клиента, прогнать KYC (или открыть KYC-stub), создать ордер. И **где взять faucet-крипту на TRX-Nile?** См. **OP-4**. |
| 9 | После активации хочет видеть состояние: сколько ORGON-кошельков выдано, какие в `pending`, какие активны. | `/admin/custody-wallets` (asystem-core) — Эрмек выкатил 2026-05-21 | OK — есть единый view orgon_wallets + dfns_wallets. |
| 10 | Хочет посмотреть **debug-журнал webhook'ов** ORGON → asystem-core. | `orgon_webhook_deliveries` таблица существует, но **UI на asystem-core нет**. | Если deposit не пришёл — оператор беспомощен. См. **OP-5**. |

### Найденные точки трения

**OP-1 — Нет сравнения ORGON vs DFNS в каталоге модулей.**
Описание ORGON в карточке ровно одно предложение. Описание DFNS то же.
Оператору неоткуда понять различия (сети, цена, m-of-n vs MPC).
DFNS уже описан гайдом `docs/DFNS_FOR_EXCHANGES.md` на их стороне,
аналогичного гайда «ORGON для обменников» в их репо нет.
**Action.** Написать `Orgon/docs/ORGON_FOR_EXCHANGES.md` mirroring
структуру DFNS-гайда. Передать Эрмеку чтобы добавил ссылку в
карточку модуля как `setup_url`.

**OP-2 — Нет deep-link «Получить ORGON-ключи» в карточке модуля.**
Поле `requires_api_keys` есть, кнопка «настроить ключи» есть, но
оператор не знает откуда они приходят. DFNS-гайд явно говорит «зайти
на app.dfns.io, создать service account» — у нас нет аналога.
**Action.** Написать раздел «Как получить ключи» в новом
`ORGON_FOR_EXCHANGES.md`. URL и контакт sales/самопровижн.

**OP-3 — Нет self-service ORGON merchant provisioning UX.**
`POST /platform/merchants` существует, проверено живым smoke
2026-05-20. Но это **gated** ORGON_PLATFORM_MASTER_KEY — токен лежит
в Coolify env asystem-core и используется их edge-функцией. На
сегодня **на asystem-core стороне такой edge-функции нет.** Оператор
ждёт пока человек из ORGON sales отдаст ему окл/окст ключи
вручную. Из HANDOVER asystem-core:
> ORGON_PLATFORM_MASTER_KEY in Coolify env. Needs to be shared with
> asystem-core's operator out-of-band so their edge layer can
> self-provision Orgon merchants.
TODO на их стороне. **Action на нас.** Сделать гайд по
self-provisioning + sample curl/Deno snippet для Эрмека —
`docs/PLATFORM_API_GUIDE.md` (новый).

**OP-4 — Нет sandbox-runbook'а для оператора.**
После активации модуля оператор хочет «попробовать на тесте».
Сейчас он должен:
- найти TRX-Nile faucet (не подсказано)
- создать тестового user'а с фиктивным KYC (зависит от их провайдера —
  SumSub vs BiometricVision — у каждого свой sandbox-flow)
- создать ордер через свой UI (что для UI-flow требует выполненного KYC)
- отправить крипту со своего тестового кошелька на полученный
  deposit-адрес
- наблюдать webhook → status flip в `/admin/orders`
- кликнуть `PayoutConfirmDialog` чтобы завершить (manual fiat)

Этого runbook'а нет ни в asystem-core docs, ни у нас. **Action.**
Раздел «End-to-end sandbox-проверка» в `ORGON_FOR_EXCHANGES.md`.
Faucet URLs для всех 3 testnet (tron-nile, eth-sepolia, orgon-testnet —
последний наш собственный, у нас же есть).

**OP-5 — Нет webhook-deliveries debug UI для оператора.**
Когда deposit не приходит — оператор не может сам диагностировать.
ORGON эмитит webhook → asystem-core пишет в `orgon_webhook_deliveries`
(audit + replay-guard). Но UI нет: `/admin/custody-wallets` показывает
только кошельки. И **на ORGON-стороне** у мерчанта есть
`GET /v1/webhooks/deliveries` (Wave 30+) — но к нему может ходить
только asystem-core (HMAC-key) а не оператор через UI.

**Action 1 (Orgon).** Нет дополнительных action'ов — endpoint уже есть.
**Action 2 (asystem-core, Эрмек).** UI на `/admin/custody-wallets`
секция «Webhook deliveries» — `SELECT * FROM orgon_webhook_deliveries
ORDER BY created_at DESC LIMIT 100`. RLS по operator_id.

---

## 🧑‍💻 Роль 2: Конечный пользователь (Айбек)

### Контекст

Айбек — физлицо, живёт в Бишкеке. Хочет продать 100 USDT-TRC20 с
бинанс-кошелька за сомы (KGS) на карту мобильного банка. Заходит
на `kiril.asystem.ai` с мобильного.

### Happy-path сценарий

| # | Шаг | Где это в коде | Боль |
|---|---|---|---|
| 1 | Заходит на лендинг. Видит ExchangeWidget с "Продать крипту → получить KGS". | `asystem-core/src/components/ExchangeWidget.tsx` | OK. |
| 2 | Выбирает: «продаю USDT, network TRX (Tron)», вводит сумму 100. Видит сумму к получению в KGS. | `useSellOrder` hook | OK. |
| 3 | Регистрация → KYC. Загружает паспорт через активный KYC-провайдер (SumSub / BV / Didit / встроенный). | `src/components/kyc/KYCProvider.tsx` | OK — провайдеры работают. |
| 4 | После approve KYC возвращается к ордеру, нажимает «Создать заказ». | `useSellOrder.executeSellOrder` | OK. |
| 5 | Backend (asystem-core edge `orgon-provision-wallet`) дёргает ORGON `POST /v1/users` → `POST /v1/wallets`. Получает deposit_address. Показывает Айбеку: «отправь USDT на адрес `TXabcd…`, ожидаем 5-15 минут». | `useSellOrder.executeManualSell:82-102` + Orgon `routes_public_v1.create_wallet` | См. **EU-1**, **EU-2** ниже. |
| 6 | Айбек копирует адрес, шлёт 100 USDT-TRC20 с бинанса. Ждёт. | — | См. **EU-3**, **EU-4**. |
| 7 | ORGON's `deposit_watcher` детектит транзакцию через Safina sync. Эмитит `wallet.deposit.detected` webhook. asystem-core принимает, находит ордер по `wallet_address`, флипает `status='paid'`, запускает AML chain. | `Orgon/backend/services/deposit_watcher.py:153` → `asystem-core/orgon-webhook/index.ts:220` | OK для happy-path. |
| 8 | Оператор Kiril видит в `/admin/orders` ордер в статусе `paid`. Подтверждает выплату через `PayoutConfirmDialog`. Шлёт деньги вручную (Finik / mobile bank). | `asystem-core/src/components/admin/PayoutConfirmDialog.tsx` | OK для ORGON-flow (потому что Phase 4 outgoing — задача asystem-core/Эрмека). |
| 9 | Айбек получает KGS на карту. | — | Конец. |

### Найденные точки трения

**EU-1 — ORGON wallet может вернуться в `status='pending'` без адреса.**
Из `merchant_wallet_service.py:_row_to_public`:
```python
"address": addr or None,
"status": "active" if addr else "pending",
```
Если на момент `POST /v1/wallets` Safina не успела активировать
кошелёк (SLA 60-90с по Suimonkul), возвращается `{address: null,
status: 'pending'}`.

На asystem-core стороне `orgon-provision-wallet:301` возвращает
`{pending: true, deposit_address: null}`. И `useSellOrder.ts:92`:
```ts
if (res?.address) {
  walletAddress = res.address;
}
// если address null — fallthrough
```
Если адреса нет — fallthrough в manual wallet branch. Если оператор
не настроил `manual_wallet_address` → **`throw new Error('Кошелёк для
приёма платежей не настроен. Обратитесь к оператору.')`**.

Айбек видит ошибку на 90% полностью валидного flow. Просто потому
что фоновая активация в Safina ещё не закончилась.

**Action 1 (asystem-core, Эрмек).** В `useSellOrder` при
`res.pending === true` — показывать UI «активируем кошелёк, 30-90с»,
поллить через timer повторными вызовами `orgon-provision-wallet`
(он сам делает GET /v1/wallets/{id} polling по cached row).

**Action 2 (Orgon).** Документировать SLA активации в
`ORGON_FOR_EXCHANGES.md` и `WEBHOOKS.md` (по событию `wallet.activated`).

**EU-2 — UX нет «асинхронной активации».**
Frontend ждёт синхронного ответа `provision-wallet`. Нет состояния
«ваш адрес генерируется». В DFNS-flow аналогичная проблема — оба
custody-провайдера могут вернуть pending. Решение единое.

**EU-3 — Wrong-network depo катастрофически тих.**
Если Айбек по невнимательности шлёт USDT-**ERC20** на адрес
USDT-**TRC20** (или наоборот) — `deposit_watcher` слушает только
правильную сеть. Транзакция «потерянная»: на ORGON-стороне ничего не
появилось, у оператора ордер так и висит в `awaiting_payment` →
timeout 30 минут (или какой настроен).

Оператор может найти через `GET /v1/deposits/lookup?tx_hash=...`
(Wave 35) — но это **support-tool оператора, не клиентский путь**.
Айбек жалуется в чат поддержки, оператор ищет.

**Action 1 (asystem-core).** Перед показом адреса — клиент-side
warning «убедитесь что отправляете на сеть **Tron (TRC20)**, не
Ethereum». Большой visual, network-icon, цветовое выделение.

**Action 2 (Orgon).** `GET /v1/deposits/lookup` уже есть. Эрмек
может проксировать его в админ-UI обменника как «найти потерянный
депозит». Документирую в `ORGON_FOR_EXCHANGES.md`.

**EU-4 — Нет timeout-сигнала для Айбека «ваш депозит не пришёл за N мин».**
Сейчас ордер просто висит в `awaiting_payment` до общего timeout.
Айбеку никто не пишет «не видим вашего перевода, проверьте сеть».

**Action (asystem-core).** Если `awaiting_payment` > 15 минут и
`orgon_wallets.deposit_address` есть но `deposits` пуст — отправить
in-app/email уведомление «не видим перевод по адресу X, network Y».
Wave 37 на ORGON-стороне (`transaction.uncertain` за 10 минут) — это
для исходящих; для входящих эквивалентного сигнала нет.

**Action 2 (Orgon).** Добавить `wallet.deposit.pending` событие —
fire когда watcher видит mempool-tx но без подтверждений. Полезно
сократить ложный «не пришёл». Сейчас нет (deposit_watcher эмитит
только при `status='confirmed'`).

**EU-5 — Айбек не знает что происходит после `paid`.**
После того как ORGON детектил депозит, ордер флипается в `paid`.
Оператор должен **вручную** подтвердить выплату. Айбек видит у себя
«статус: оплачено» — но фактически он ещё ждёт перевод KGS на свою
карту. Может быть 5 минут, может быть 2 часа.

**Action (asystem-core).** Уточнить лейбл статусов в клиентском UI:
`paid` ≠ финальное состояние. Лучше `received` или
`awaiting_payout`. Финальное — `completed`.

---

## Приоритезация

| ID | Боль | Owner | Effort | Импакт |
|---|---|---|---|---|
| **OP-1, OP-2** | Нет ORGON_FOR_EXCHANGES.md гайда | Orgon | 2-3ч | Sales enablement — без гайда DFNS выигрывает по умолчанию |
| **OP-3** | Нет PLATFORM_API_GUIDE.md для self-provision | Orgon | 1-2ч | Эрмек разблокируется на operator-self-onboarding |
| **OP-4** | Нет sandbox runbook'а | Orgon | 2-3ч | Pilot-readiness — оператор может сам всё проверить |
| **OP-5** | Webhook-deliveries debug UI | asystem-core | — | Их зона; мы документируем endpoint в гайде |
| **EU-1, EU-2** | Pending wallet UX | asystem-core | — | Их зона |
| **EU-2 (alt)** | SLA активации задокументировать | Orgon | 30мин | Чтобы Эрмек знал что поллить |
| **EU-3** | wrong-network UX warning + lookup-доступ | asystem-core (UI) + Orgon (док) | — | Их зона + наш док |
| **EU-4** | Timeout-сигнал для клиента | asystem-core + Orgon (`wallet.deposit.pending`) | 3-4ч (Orgon) | Снизит support tickets на 30%+ |
| **EU-5** | Лейблы статусов в клиентском UI | asystem-core | — | Их зона |

### Что чисто наше (Orgon)

1. **`docs/ORGON_FOR_EXCHANGES.md`** — гайд для оператора по подключению,
   mirroring DFNS-формат. Закрывает OP-1, OP-2, OP-4.
2. **`docs/PLATFORM_API_GUIDE.md`** — self-provision API + sample
   curl/Deno для Эрмека. Закрывает OP-3.
3. **`wallet.deposit.pending` событие** в `deposit_watcher` — emit
   при mempool-detection до confirmation. Закрывает EU-4 со стороны
   контракта.
4. **`wallet.activated` SLA** задокументировать в `WEBHOOKS.md`. EU-2.

### Что зона asystem-core (передать Эрмеку)

Список выше в каждой OP-/EU- секции. Можно сделать checklist в
`ASYSTEM_CORE_INTEGRATION.md` или просто переслать этот файл.
