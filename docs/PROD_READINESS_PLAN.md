# ORGON — Production-Readiness Plan

> **Что это.** Форвард-роадмап от «задеплоено и работает для pilot» к
> «institutional GA-ready с реальными деньгами клиентов». Не setup-
> рунбук (тот — `prod-readiness.md`), а список работ с приоритетами,
> критериями приёмки и владельцами.
>
> **Состояние на 2026-06-03 (honest baseline).** ORGON живёт в проде на
> `orgon.asystem.ai` (single-node Coolify). Headless **single-EC**
> custody-флоу проверен end-to-end вживую: deposits (Tron/BTC/ETH),
> **payouts broadcast'ятся on-chain** (ETH-Sepolia + Tron, нативка +
> TRC20 USDT), вебхуки broadcasted/real-confirmed/failed/canceled,
> HMAC/RLS/pgcrypto/replay/квоты. Старый блокер «sign-but-no-broadcast»
> закрыт для single-EC (Safina починила эфир; Tron работает на
> зачисленных кошельках). **DFNS-паритет на ORGON-стороне готов.**

---

## Две планки готовности

- **Phase A — Pilot-ready** (single-EC headless custody для asystem-core):
  **достигнута.** Платёжный путь доказан, контракт для интегратора готов.
- **Phase B — Institutional GA-ready** (реальные деньги, регулируемый
  запуск, SLA): **5 треков ниже.**

---

## Трек P0 — Custody ключей: KMS/Vault (security-долг №1)

**Проблема.** `EnvSignerBackend` live; `KMSSignerBackend`/`VaultSignerBackend`
— заглушки. Per-org `safina_ec_private_key` лежит в Postgres в открытом
виде (достаётся из бэкапа за минуту). Для реальных денег это
неприемлемо.

**Шаги (ORGON):**
1. Завести AWS KMS asymmetric `ECC_SECG_P256K1` key (или Vault Transit
   `ecdsa-p256k1`) per-окружение.
2. Дореализовать `KMSSignerBackend.sign_msg_hash` по 6-шаговому чек-листу
   в `backend/safina/signer_backends.py` (DER→canonical-low-s→recover→
   verify-address); прогнать против **реального** AWS (сейчас только
   in-process fake-KMS в юнит-тестах).
3. Миграция секретов: per-org EC → KMS key id (а не raw hex в БД).
   Колонку `safina_ec_private_key` → депрекейт/зашифровать pgcrypto как
   переходный шаг.
4. `ORGON_SIGNER_BACKEND=kms` на проде; smoke: создать кошелёк + подписать
   tx KMS-ключом, broadcast on-chain.

**Acceptance.** Ни один приватный ключ подписи не хранится в БД/env в
открытом виде; payout подписан KMS/Vault и ушёл on-chain; ключ не
покидает HSM. **Effort: L. Владелец: ORGON. Зависимости: AWS/Vault
доступ.**

---

## Трек P1 — Зависимость от Safina (внешний риск №1)

**Проблема.** Safina — единственный upstream custody с известными
странностями: lazy-balance (кошелёк `TPbpD74y`/`082A21BD` так и не
broadcast'ит — Safina не реконсилила внутренний баланс), display-лаг
`wallet_tokens`, ORGON-chain (5800/5810) watcher не готов. Single point
of failure для всех денег.

**Шаги:**
1. **Подтвердить M-of-N multi-sig вживую (ORGON).** Сейчас доказан только
   single-EC (`min_sign=1`). Создать 2-of-3 кошелёк со slist из ECs,
   которыми мы владеем, подписать двумя, убедиться что broadcast
   происходит только при достижении порога. Если не работает — это
   блокер для продажи M-of-N (или явно не продаём).
2. **Добить с Safina (бизнес-канал):** (а) lazy-balance/reconcile для
   TRC20-депозитов и «битых» кошельков; (б) ORGON-chain explorer API
   (для 5800/5810 deposit watcher); (в) **SLA + контакт инцидентов +
   выделенный prod-tenant** (сейчас общий тестовый ключ со страницы
   примеров их wiki).
3. **Снизить связанность:** наш `deposit_watcher` уже независимо детектит
   депозиты через публичные эксплореры — рассмотреть, чтобы он же
   служил источником истины по балансу (а не Safina display).

**Acceptance.** M-of-N подтверждён или явно out-of-scope; Safina выдала
prod-tenant + SLA; lazy-balance закрыт или обойдён нашим watcher'ом.
**Effort: M (наша часть) + внешнее. Владелец: ORGON + Safina + бизнес.**

---

## Трек P2 — Комплаенс-минимум (гейт регулируемого запуска)

**Проблема.** Sumsub pre-launch (чистый 503 без 3 env); KYC/KYB document
upload — `placeholder://`; AML-движок есть (threshold/velocity/blacklist/
geo/recipient-whitelist), но внешних детекторов (Chainalysis) и Travel
Rule — только модель данных; лицензия НБ КР in progress.

**Шаги (ORGON + бизнес):**
1. KYC/KYB document upload → реальный S3/R2 (заменить `placeholder://`),
   + подать Sumsub creds (3 env) → снять 503.
2. Хотя бы один боевой AML-детектор поверх существующего rule-engine
   (Chainalysis screening на адреса, или подтвердить, что in-house
   threshold/velocity достаточно для лицензии).
3. Travel Rule: решить VASP-ID вопрос (O-5) — юр. сначала.
4. Footer/статусы: не показывать сертификации, которых нет (уже так);
   обновлять по мере получения.

**Acceptance.** KYC/KYB сабмит работает end-to-end (не placeholder); AML
даёт реальный сигнал на боевых данных; лицензионный статус явный.
**Effort: M-L. Владелец: ORGON + Legal/Compliance.**

---

## Трек P3 — Инфраструктура и операционка

**Проблема.** Single-node Coolify, один Postgres/env; бэкап-скрипт есть,
но cron/off-site «to install»; `POST /api/health/run-migrations` залочен
(нет super_admin — `asystem-admin` понижен до admin); нет резерва БД.

**Шаги (ORGON):**
1. **Бэкапы на проде:** `scripts/backup_pg.sh` в systemd-timer + off-site
   S3/R2 (`ORGON_BACKUP_S3_BUCKET`), проверить restore.
2. **Вернуть super_admin** (ручной рычаг миграций) — апдейт роли в БД
   через окно обслуживания. Entrypoint уже укреплён (per-file try/except,
   commit e2639cf), но ручной fallback нужен.
3. **Резерв БД** (managed Postgres с репликой / PITR) — для денег
   single-instance рискован.
4. **Observability on:** `ORGON_JSON_LOGS=1` + `SENTRY_DSN` на проде
   (код готов, флаги off по умолчанию).
5. **Preview/prod разделение** окружений и их БД (сейчас де-факто одна
   ветка `feature/demo-simulator`).

**Acceptance.** Ночные бэкапы идут + restore проверён; super_admin есть;
Sentry/JSON-логи активны; план на резерв БД. **Effort: M. Владелец: ORGON.**

---

## Трек P4 — Релизная полировка

**Шаги (ORGON):**
1. Опубликовать SDK: `@orgon/sdk` (npm, workflow `sdk-publish.yml` по
   тегу `sdk-v*`) + `orgon-sdk` (PyPI).
2. Закрыть 57 baseline-падений тестов (нужен Postgres в CI + AML-wireup
   фикс) — чтобы «зелёный» значил зелёный.
3. Слить `feature/demo-simulator` → `main` как канонический prod-бранч
   (или обновить deploy-таргеты под текущую реальность).
4. `fees_estimate` endpoint (asystem-core попросит перед payout'ами) —
   когда понадобится.

**Acceptance.** SDK в реестрах; CI без baseline-провалов; ясный prod-бранч.
**Effort: S-M. Владелец: ORGON.**

---

## Go-live gate (Institutional GA)

Не запускать на реальные деньги клиента, пока:
- [ ] P0: ключи в KMS/Vault, ни одного raw-ключа в БД/env.
- [ ] P1: M-of-N подтверждён (или явно out-of-scope) + Safina prod-tenant + SLA.
- [ ] P2: KYC/KYB не-placeholder + AML-сигнал + лицензионный статус ясен.
- [ ] P3: бэкапы+restore проверены, observability on, план резерва БД.
- [ ] P4: (желательно) SDK опубликованы, CI чистый.

**Порядок атаки:** P0 и P1.1 (M-of-N) параллельно — это и есть «можно ли
вообще доверить деньги». Дальше P2 (под лицензию) ‖ P3 (операционка),
P4 — фоном.

---

## Что для pilot (asystem-core) НЕ блокер

Single-EC headless модель, которую потребляет asystem-core, **уже
prod-функциональна**. Для их интеграции хватает текущего состояния +
их собственной wire-up части (см. `ASYSTEM_CORE_PHASE4_SPEC.md`). Phase B
выше — про institutional-запуск с реальными деньгами, не про pilot.
