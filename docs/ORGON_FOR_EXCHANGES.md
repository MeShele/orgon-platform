# ORGON Custody для обменника — гайд оператору

Этот документ — пошаговая инструкция как подключить **ORGON Custody**
на ваш обменник ASystem Core. ORGON — институциональный кастодиан
криптоактивов на m-of-n подписях поверх Safina Pay. Это альтернатива
DFNS — оба модуля живут в каталоге asystem-core рядом, выбирается
один.

Симметричный документ от DFNS: `asystem-core/docs/DFNS_FOR_EXCHANGES.md`.

---

## Что вы получаете

- **Депозит-кошельки на 7 сетях** mainnet + testnet: Bitcoin, Ethereum
  (+ Sepolia), Tron (+ Nile), Orgon (+ Orgon-test). Каждый кошелёк —
  персональный per-end-user адрес.
- **Multi-signature подписи** через slist Safina Pay. Дефолт — sole-
  signatory оператора (auto-approval); опционально подключается
  m-of-n с e-mail / SMS co-signers.
- **Webhook-уведомления** о входящих депозитах и исходящих
  транзакциях в реальном времени — наш бэкенд автоматически переведёт
  sell-order в статус `paid` при приходе средств.
- **AML rule engine** уже встроен: блокировка по адресам,
  threshold/velocity limits, sanction-lists. Не нужно подключать
  отдельный compliance-модуль.
- **Append-only audit log** с DB-уровневым trigger'ом — UPDATE и
  DELETE падают. Compliance-ready для PCI DSS / SOC 2 / ISO 27001.
- **Per-tenant изоляция**: каждый обменник = отдельный `merchant_id` в
  ORGON со своими `okl_*`/`oksl_*` ключами в вашем asystem-core
  vault. Никакого пересечения данных с другими тенантами.

## Когда выбирать ORGON vs DFNS

| Критерий | ORGON | DFNS |
|---|---|---|
| Сети | Bitcoin, Ethereum, Tron, Orgon (7 включая testnet) | 80+ сетей |
| Подписи | m-of-n (multisig) поверх Safina | MPC threshold |
| AML/compliance | Встроен (rule engine, SAR, GSFR) | Через интеграцию |
| Travel Rule (FATF) | Встроен на roadmap | Через интеграцию |
| Стоимость | Партнёрский тариф (договорной) | Trial 30 дней, потом план DFNS |
| WebAuthn для клиентов | Нет | Опционально |
| Латентность активации кошелька | ~60-90с (Safina async) | ~Instant (DFNS async короче) |
| Регуляторная база | КР VASP-лицензия партнёра | Self-hosted без юрисдикции |

**Выбирайте ORGON если:**
- Вы лицензированный VASP в КР/КЗ и нужна compliance из коробки
- Готовы работать через ограниченный набор сетей (Tron/ETH/BTC покрывают
  90%+ live-tx обменника)
- Нужен встроенный AML rule engine и SAR-pipeline под Финнадзор КР

**Выбирайте DFNS если:**
- Нужно много альт-сетей (Solana, Polygon, Arbitrum, etc.)
- Нужен MPC вместо multi-sig (распределённый ключ)
- Готовы строить compliance-слой самостоятельно

ORGON и DFNS **взаимоисключающие** — оператор активирует один из них
через `exclusive_group='custody'` в `/admin/modules`. Переключение
покажет confirm-dialog «Включение ORGON отключит DFNS — продолжить?».

---

## Что нужно сделать (один раз, для каждого обменника)

### 1. Получить ORGON merchant credentials

Сейчас на самообслуживание — через `POST /platform/merchants` (см.
`PLATFORM_API_GUIDE.md` для интегратора asystem-core). Edge-функция
автоматизированного provisioning'а на стороне asystem-core пока **не
выкачена** — ждём релиза от Эрмека. До тех пор:

**Out-of-band путь (текущий):**
- Telegram: `@urmatdigital`
- Email: `sales@asystem.ai`

Что нужно сказать sales:
- Название обменника, домен (`yourname.asystem.ai`)
- Юрисдикция и тип лицензии
- Ожидаемый месячный TPV (для квоты)
- Tier: `sandbox` (бесплатный, только testnet) / `live` (партнёрский тариф)

Получите по защищённому каналу:
- `ORGON_KEY` — `okl_…` для live, `okt_…` для sandbox (32 hex chars)
- `ORGON_SECRET` — `oksl_…` для live, `okst_…` для sandbox (64 hex chars)
- `merchant_id` — UUID вашей записи в ORGON
- Подтверждение `pricing_plan` и enabled networks

⚠️ **`ORGON_SECRET` показывается ОДИН раз.** Положите его сразу в
secure vault. Восстановить нельзя — только rotation через выпуск
новой пары.

### 2. Активировать модуль в asystem-core

В админке вашего обменника (`https://<your-domain>.asystem.ai`):

1. `/admin/modules` → найти **ORGON Custody** в каталоге
2. Активировать модуль (если активен DFNS — confirm-dialog отключит его)
3. Открыть форму ключей → вписать 4 значения:

| Поле в форме | Значение |
|---|---|
| `ORGON_KEY` | `okt_*` / `okl_*` из шага 1 (полностью) |
| `ORGON_SECRET` | `okst_*` / `oksl_*` из шага 1 (полностью) |
| `ORGON_BASE_URL` | `https://orgon.asystem.ai` (single shared prod) |
| `ORGON_ENV` | `sandbox` (для тестов) или `live` |

`ORGON_WEBHOOK_SECRET` — НЕ нужен на этом шаге, генерируется
автоматически на следующем.

### 3. Проверить подключение

Нажмите **«Проверить подключение»** в карточке модуля. Edge-функция
asystem-core'а `orgon-ping` дёрнет `GET /v1/ping` у нас и должна
вернуть:

```json
{
  "ok": true,
  "merchant_id": "<ваш UUID>",
  "scopes": ["read", "write"],
  "api_key_id": "<UUID ключа>"
}
```

Если ошибка — см. раздел «Если не работает» внизу.

### 4. Зарегистрировать webhook

После того как ping прошёл, нужно сообщить ORGON куда слать события
о депозитах. Нажмите **«Зарегистрировать webhook»** в карточке модуля.

Что произойдёт автоматически:
- asystem-core генерирует случайный 32-byte hex `ORGON_WEBHOOK_SECRET`
- Пишет в ваш vault как `ORGON_WEBHOOK_SECRET`
- Дёргает `PUT /v1/webhooks/config` у нас с URL приёмника +
  сгенерированным secret'ом
- Возвращает успех

Если когда-то понадобится ротация (compromised secret) — повторно
нажать ту же кнопку. Старый secret замещается новым, replay-attacks
со старым secret'ом сразу отбиваются (`X-ORGON-Webhook-Signature` не
сходится).

### 5. Готово — но проверьте sandbox end-to-end

См. следующий раздел.

---

## End-to-end sandbox-проверка

**Перед пуском живых клиентов** обязательно прогоните полный flow на
sandbox. Это страхует от ситуации когда живой клиент отправляет
крипту, а у вас не настроены manual-wallets для fallback'а.

### Sandbox-кошельки оператора (faucet'ы)

| Сеть | Chain ID | Faucet |
|---|---|---|
| Tron Nile | `5010` | https://nileex.io/join/getJoinPage |
| Ethereum Sepolia | `3040` | https://sepoliafaucet.com / https://www.alchemy.com/faucets/ethereum-sepolia |
| Orgon Testnet | `5810` | связаться `@urmatdigital` — наш собственный testnet |
| Bitcoin Testnet3 | (на roadmap) | https://coinfaucet.eu/en/btc-testnet/ |

### Сценарий

1. **Создайте тестового пользователя** в вашем обменнике (можно через
   admin-импорт без живого KYC, или включить KYC `manual` провайдер
   для sandbox-flow).
2. **Создайте sell-order** через ваш UI или прямо в БД:
   - `from_currency = USDT`, `from_amount = 10`, `network = tron-nile`
   - `wallet_address` (куда вы хотите получить деньги) — любой ваш
     test-Tron-адрес из шага faucet
3. Frontend дёрнет `orgon-provision-wallet` edge → получит
   `deposit_address`. Запомните этот адрес — туда придёт депозит.
   - **Ожидание pending.** Если ORGON вернул `pending=true,
     deposit_address=null` — это нормально. Safina активирует кошелёк
     за 60-90 секунд. Текущий asystem-core flow упадёт в manual
     fallback; полностью корректная активация-poll реализуется
     отдельно (см. EU-1 в `CUSTDEV_OPERATOR_END_USER.md`).
4. **Отправьте 1 USDT-TRC20** с вашего test-кошелька на полученный
   `deposit_address`.
5. **Подождите ~30 секунд.** Наш `deposit_watcher` обнаруживает
   confirmed транзакции (`only_confirmed=true` — mempool не
   ловится). Когда увидит — эмитнет `wallet.deposit.detected`
   webhook → ваш asystem-core примет, найдёт ордер по
   `wallet_address`, флипнет статус в `paid`, запустит AML chain.
6. **Зайдите в `/admin/orders`**. Ордер должен быть в статусе
   `paid`. Нажмите **«Подтвердить выплату»** через
   `PayoutConfirmDialog`. На sandbox можно завершить кликом без
   реальной отправки KGS.
7. **Зайдите в `/admin/custody-wallets`**. Должны увидеть выданный
   ORGON-кошелёк с провайдер-баджем `ORGON`, статус `Active`, адрес
   активирован.

Если что-то не сработало — debug-таблица `orgon_webhook_deliveries`
в вашем Supabase покажет последние ~100 webhook'ов с payload, HMAC
verify status, response. UI к ней пока нет (TODO Эрмек).

---

## Что хранится у нас vs у ORGON vs у Safina

| Что | Где |
|---|---|
| `ORGON_KEY` (публичный идентификатор) | У вас (vault) + у нас (ORGON DB) |
| `ORGON_SECRET` (для HMAC) | У вас (vault) + у нас (at-rest encrypted) |
| `ORGON_WEBHOOK_SECRET` | У вас (vault) + у нас |
| Маппинг ваш user → ORGON end_user | `orgon_user_links` в вашей БД + `end_users` у нас |
| Маппинг (user + network) → wallet + address | `orgon_wallets` у вас + `wallets` у нас |
| Приватные ключи кошельков | **На стороне Safina** под их кастоди. Ни мы, ни вы их не видим. |
| Журнал событий | `orgon_webhook_deliveries` у вас + `webhook_deliveries` у нас |
| Audit-trail | `signature_history` + `audit_log` у нас (append-only triggers) |

---

## Безопасность

- **`ORGON_SECRET`** — это ключ к `/v1/*` API. Если утечёт, атакующий
  может создать кошельки и инициировать tx от вашего имени, но
  **средства на существующих кошельках достать не сможет** (это
  потребует Safina-side signatures, которые делает наш бэкенд).
  Ротация: через нашу sales-команду; в admin UI ORGON-стороны можно
  выпустить новый key-pair + revoke старый (`POST
  /api/admin/merchants/{id}/api-keys`).

- **`ORGON_WEBHOOK_SECRET`** — секрет верификации входящих webhook'ов
  от ORGON. Если утечёт — атакующий может подделать fake-депозиты,
  что приведёт к ложным `paid` статусам ордеров. Регулярно
  ротируйте кнопкой «Зарегистрировать webhook» (overwrite).

- **Sandbox vs Live.** Sandbox ключи (`okt_*`/`okst_*`) **физически не
  принимают** mainnet chain_id (1000, 3000, 5000, 5800) — возвращают
  400 c явной ошибкой. Так что случайно потратить mainnet через
  sandbox-keys невозможно. Перед mainnet — отдельный key-pair с
  префиксом `okl_*`/`oksl_*`.

- **Append-only audit.** На `audit_log` и `signature_history` стоит
  trigger `orgon_immutable_*` — UPDATE и DELETE падают с явной
  ошибкой. Compliance-аудитор может опираться на эту гарантию.

---

## Поддерживаемые сети (на 2026-05-21)

Whitelist в нашем `merchant_wallet_service.TESTNET_NETWORKS`:

**Mainnet** (chain_id):
- `1000` — Bitcoin Mainnet
- `3000` — Ethereum Mainnet
- `5000` — Tron Mainnet
- `5800` — Orgon Mainnet

**Testnet** (chain_id):
- `1010` — Bitcoin Testnet3
- `3010` — (reserved)
- `3040` — Ethereum Sepolia
- `5010` — Tron Nile
- `5810` — Orgon Testnet

Подробное соответствие со slug'ами asystem-core'а — в
`docs/ASYSTEM_CORE_INTEGRATION.md` и memory
`reference_chain_id_mapping.md`.

Если нужна сеть не из списка — sales@asystem.ai с указанием
chain_id (если ваш сложный кейс) или slug (если стандарт). Добавление
новой сети — миграция + новый файл в `backend/services/deposit_sources/`.

---

## Phase 4 — outgoing payouts (исходящие транзакции)

**На ORGON-стороне готово**: `POST /v1/transactions` + `POST
/v1/transactions/{id}/sign` + webhook'и `transaction.broadcasted /
confirmed / failed`.

**На asystem-core стороне** — Phase 4 пока реализован только для
DFNS-провайдера (`dfns-create-transfer` edge function +
`useCustodyCanPayout` хук). ORGON-аналог `orgon-create-transfer` —
TODO Эрмека. Спека готова: `docs/ASYSTEM_CORE_PHASE4_SPEC.md` с
готовым Deno-snippet'ом.

До реализации Phase 4 на их стороне:
- Депозиты (incoming, sell-order'ы) — работают полностью через ORGON
- Выплаты (outgoing, buy-order'ы) — **только вручную через
  PayoutConfirmDialog** или через ORGON's own admin UI на
  `orgon.asystem.ai`. Автоматического payout'а из asystem-core нет.

---

## Если не работает

| Ошибка | Что делать |
|---|---|
| `Invalid signature` или `403` на ping | HMAC формат: проверить что `ORGON_BASE_URL` без trailing slash, что `ORGON_SECRET` скопировался полностью (64 hex chars, не split на строки). |
| `Sandbox merchant cannot use mainnet network` (400) | Использовали `okl_*` ключ против sandbox networks или наоборот. Проверить `ORGON_ENV` соответствует префиксу ключа (`okt_*` ↔ `sandbox`, `okl_*` ↔ `live`). |
| Ping ОК, но `wallet.deposit.detected` не приходит | Webhook secret не настроен или истёк. Жмите «Зарегистрировать webhook» повторно. Проверьте что фасадный URL Supabase доступен извне (наш bot шлёт с `orgon.asystem.ai` IP — IP whitelist на вашем Supabase fcuncts должен пропускать или быть выключен). |
| Wallet висит в `status='pending'` без `address` >5 минут | Safina не активировала. Возможные причины: их API временно недоступен (`/api/health/safina` показал бы), или дубль `wallet_id` (rare). Связаться `@urmatdigital`. |
| `Cross-merchant wallet access` (403) | Frontend asystem-core'а спутал operator_id при вызове edge-функции. Это их сторона; проверьте что `useOperatorId()` возвращает ваш operator_id для текущего пользователя. |
| Депозит ушёл на адрес но `wallet.deposit.detected` не пришёл | Скорее всего wrong-network (USDT-ERC20 на TRC20-адрес или наоборот). `/v1/deposits/lookup?tx_hash=...` найдёт транзакцию в нашей БД если она была. Если её нет — значит наш watcher тоже не видит её, она ушла «в никуда» в чужой сети. См. EU-3 в `CUSTDEV_OPERATOR_END_USER.md`. |

---

## Что дальше (вне scope этой версии)

- **Phase 4 wire-up в asystem-core** — outgoing payouts через ORGON
  (TODO Эрмек, спека есть)
- **`wallet.deposit.pending` webhook** — mempool-сигнал «видим вашу
  транзакцию, ждём подтверждений». Требует архитектурного изменения
  всех 3 deposit-sources (`only_confirmed=true` хардкоднут). Phase 5
  или ad-hoc по запросу.
- **Multi-region deploy** — per-jurisdiction ORGON-инстансы. Не
  блокирует никого сегодня; planned когда появится оператор с RU/KZ
  data residency.
- **WebAuthn pass-keys для клиентов** — каждый клиент сам подписывает
  свои tx. Не в roadmap, требует переработки multi-sig модели.
