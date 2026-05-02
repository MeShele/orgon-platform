# ORGON — Production Readiness Runbook

> **Назначение:** при подключении первого institutional-клиента (или нового pilot-окружения) этот документ — единственный источник истины для setup'а. Прошёл по чек-листу → клиент получает рабочий tenant с подставленными prod-кредами.

> **Last updated:** 2026-05-02 (после DB-split + Safina-multi-network проверки)

---

## 0. Текущее состояние одной строкой

ORGON работает в режиме **shared-test environment** с публичной test-инсталляцией на `https://orgon.asystem.ai`, демо-аккаунт `demo-admin@orgon.io / demo2026`. Все 7 поддерживаемых Safina-сетей (BTC, ETH, ETH-Sepolia, TRX, TRX-Nile, ORGON, ORGON-test) **верифицированы вживую** — кошельки реально создаются и попадают на блокчейн. Database вынесена из docker-compose в Coolify-managed standalone-postgresql с daily-backup'ами. **Готовность к pilot-launch: ~99%** — все 5 institutional-блокеров закрыты code-side: ❶ KMS (Wave 18) · ❷ Safina canonical-payload (Wave 22, pluggable variants + shadow-mode) · ❸ AML triage (Wave 19+21) · ❹ KYC (Wave 19) · ❺ KYB (Wave 20). Осталось только bring-up coordination с pilot-клиентом (env-creds + variant confirmation).

---

## 1. Архитектура — что где живёт

```
                       ┌────────────────────────────────────────┐
                       │  Cloudflare (DNS + edge cache + DDoS)   │
                       │  SSL/TLS mode: Full (per-domain rule)   │
                       └────────────────┬───────────────────────┘
                                        │ HTTPS
                       ┌────────────────▼───────────────────────┐
                       │  Hetzner dedicated #2985431            │
                       │  65.21.205.230 · coolify-orion          │
                       │  ┌──────────────────────────────────┐   │
                       │  │ systemd Caddy on :443             │   │
                       │  │ /etc/caddy/conf.d/*.conf per host │   │
                       │  │ /ws/* + /api/* → 127.0.0.1:18890  │   │
                       │  │ everything else → 127.0.0.1:13000 │   │
                       │  └──────────────────────────────────┘   │
                       │  ┌──────────────────────────────────┐   │
                       │  │ Coolify v4 (control plane)        │   │
                       │  │ panel: c.asystem.ai                │   │
                       │  │ project ORGON / env production     │   │
                       │  └──────────────────────────────────┘   │
                       │  ┌──────────────────────────────────┐   │
                       │  │ Docker network "coolify"          │   │
                       │  │  ├─ orgon-stack (app)             │   │
                       │  │  │   ├─ backend  :18890→8890      │   │
                       │  │  │   ├─ frontend :13000→3000      │   │
                       │  │  │   └─ caddy-bootstrap (sidecar) │   │
                       │  │  └─ orgon-pg (Coolify-managed)    │   │
                       │  │      uuid: zbezy4vjauvrsp...      │   │
                       │  └──────────────────────────────────┘   │
                       └────────────────────────────────────────┘
                                        │  HTTPS + ECDSA-signed
                       ┌────────────────▼───────────────────────┐
                       │  Safina Pay (custody / signing)         │
                       │  https://my.safina.pro/ece/             │
                       └────────────────────────────────────────┘
```

---

## 2. Среды и их идентификация

| Окружение | URL | Coolify uuid (app) | DB uuid | Branch | Назначение |
|---|---|---|---|---|---|
| **production** | `https://orgon.asystem.ai` | `nw5o0foj43w96q9upluxnr0l` | `zbezy4vjauvrsp9p78w4ayxl` | `feature/demo-simulator` | shared-test, демо-walkthrough, sales |
| **client-pilot** *(когда будет)* | `https://<client>.asystem.ai` | новый | новый | client branch / main tag | первый institutional pilot |

Каждый клиент получает **отдельный orgon-stack** + **отдельный Coolify-managed Postgres**. Никакого shared-DB.

---

## 3. Полная env-матрица backend

| Переменная | Где задаётся | Значение для prod | Кто меняет на pilot | Можно ли пустым |
|---|---|---|---|---|
| `DATABASE_URL` | docker-compose, использует `${SERVICE_PASSWORD_PG}` | `postgresql://orgon:<pwd>@<db-uuid>:5432/orgon` | Coolify сам — при создании DB | ✗ обязательно |
| `JWT_SECRET_KEY` | `${SERVICE_PASSWORD_64_JWT}` (Coolify auto-managed) | 64-char hex, persistent | Coolify сам | ✗ обязательно (иначе auto-rotate каждый restart выкидывает всех users) |
| `ORGON_ENV` | hardcoded в compose | `production` | — | ✗ |
| `ORGON_PUBLIC_URL` | `${SERVICE_URL_FRONTEND}` (Coolify auto) | `https://<client>.asystem.ai` | Coolify сам | ✗ |
| `CORS_ORIGINS` | `${SERVICE_URL_FRONTEND}` | то же что PUBLIC_URL | Coolify сам | ✗ |
| `ORGON_AUTO_MIGRATE` | hardcoded `1` | `1` (apply canonical schema) | — | можно `0` после первого boot |
| `ORGON_AUTO_SEED` | hardcoded `1` | **для prod-pilot → `0`** (не сидим демо-юзеров на проде клиента) | YES | да |
| **`SAFINA_STUB`** | Coolify env | **`0`** (live mode) | при создании окружения | если `1` — все Safina-вызовы пойдут в stub-клиент (для local dev) |
| **`SAFINA_BASE_URL`** | Coolify env | `https://my.safina.pro/ece/` *(или клиентский endpoint если у Safina много инстансов)* | при создании окружения | ✗ обязательно |
| **`SAFINA_EC_PRIVATE_KEY`** | Coolify env | **EC-ключ prod-аккаунта клиента у Safina** | YES — выдаёт Safina при создании prod tenant | ✗ обязательно |
| `ORGON_SIGNER_BACKEND` | hardcoded `env` | для **pilot < 1М$ AUM** — `env` (приемлемо). Для **банка / >1М$** — `kms` или `vault` (требует написать backend, см. ❶) | конфиг в Coolify | можно опустить (default `env`) |
| `ORGON_VERIFY_SAFINA_SIGS` | env, по умолчанию `0` | пока не подтверждён canonical-payload format у Safina (Wave 13 gate), оставить `0` | оставить как есть | да |
| `ORGON_JSON_LOGS` | hardcoded `1` | `1` | — | да (но рекомендуется prod=`1`) |
| `SENTRY_DSN` | Coolify env (опционально) | DSN из Sentry-проекта клиента | YES если клиент хочет error-tracking | да (off → no Sentry init) |
| `SMTP_HOST` / `SMTP_USER` / `SMTP_PASS` / `SMTP_FROM` | Coolify env (опционально) | SMTP клиента (Sendgrid/SES/Mailgun/корп. Postfix) | YES если нужны email-flows (password reset, 2FA, invites) | да (fallback в `/tmp/orgon_emails.log`) |
| `STRIPE_API_KEY` + `STRIPE_WEBHOOK_SECRET` + `STRIPE_PRICE_STARTER/_BASIC/_PRO` | Coolify env (опционально) | если у клиента Stripe-billing | enterprise-клиент = manual invoice = НЕ нужно | да (billing → 503 clean) |
| `ORGON_PARTNER_REPLAY_OFF` | env (default `0`) | `0` (replay-protection on). `1` только при инциденте | оставить `0` | да |
| `ORGON_BACKUP_S3_BUCKET` + AWS creds | env (опционально) | для off-site PG-бэкапа в S3/R2/Wasabi | recommended for prod | да (Coolify уже делает локальные daily-backup'ы) |
| `TELEGRAM_BOT_TOKEN` | env (опционально) | bot-token для notify-канала | nice-to-have | да |

---

## 4. Pilot setup — пошаговый runbook

> **Время: ~30 минут.** Выполняется по шагам, не пропуская.

### 4.1 Получить креды от Safina

Связаться с командой Safina (через бизнес-канал группы ASYSTEM) и попросить:
- `SAFINA_EC_PRIVATE_KEY` — EC private key prod-аккаунта **именно для этого клиента** (нельзя переиспользовать ключи между клиентами!)
- `SAFINA_BASE_URL` — обычно `https://my.safina.pro/ece/`, но если Safina даст dedicated endpoint — взять его

### 4.2 Создать новое Coolify-приложение

В `c.asystem.ai`:
1. Project **ORGON** → Environment → **«Add new environment»** → имя `pilot-<client>` (например `pilot-bcc`)
2. Add new resource → **Public Repository** → `https://github.com/MeShele/orgon-platform.git` → branch `main` (или tag типа `v1.0.0` — заморозить версию)
3. Build pack: **Docker Compose**, location: `/docker-compose.yml`
4. Domain: `https://<client>.asystem.ai` (поставить orange-cloud в Cloudflare DNS, SSL mode = **Full**)

### 4.3 Создать отдельный Postgres

1. В том же environment → Add new resource → **PostgreSQL** (standalone-postgresql)
2. Name: `<client>-pg`
3. Image: `postgres:16-alpine`
4. После создания — скопировать internal_db_url. **НЕ** включать `is_public` — БД должна быть только внутри `coolify` network.

### 4.4 Заполнить env

В Coolify UI новой app → **Environment Variables**:

```
SAFINA_STUB=0
SAFINA_BASE_URL=https://my.safina.pro/ece/
SAFINA_EC_PRIVATE_KEY=<ключ от Safina, ШАГ 4.1>
ORGON_AUTO_SEED=0                   # ВАЖНО — не сидим demo-юзеров на проде клиента
JWT_SECRET_KEY=<openssl rand -hex 32>  # ОДИН раз сгенерировать, больше не менять
SENTRY_DSN=<если хотят>
SMTP_HOST=...
SMTP_USER=...
SMTP_PASS=...
SMTP_FROM=noreply@<client>.com
ORGON_BACKUP_S3_BUCKET=...           # если хотят off-site бэкап
```

В `docker-compose.yml` обновить `DATABASE_URL` под uuid нового Postgres из шага 4.3.

### 4.5 Включить scheduled backups

В Coolify UI новой PG → **Backups** → Add backup config:
- frequency: `daily`
- save_s3: false (или true если выставлен `ORGON_BACKUP_S3_BUCKET`)
- retention: 14 дампов / 7 дней (или больше — institutional клиент захочет 30 дней)

Альтернатива через API:
```bash
curl -X POST -H "Authorization: Bearer $COOLIFY_TOKEN" \
  https://c.asystem.ai/api/v1/databases/<db-uuid>/backups \
  -d '{"frequency":"daily"}'
```
потом PATCH с retention/`save_s3`.

### 4.6 Cloudflare DNS + SSL

В CF dashboard:
1. DNS → новая A-запись `<client>` → IP `65.21.205.230` → orange cloud (proxied)
2. SSL/TLS → Overview → mode = **Full** (НЕ Full Strict — у нас self-signed-resilient origin)
3. Если есть Configuration Rule на `orgon.asystem.ai` с `Flexible` SSL — **повторить тот же rule для `<client>.asystem.ai` с `Full`** (или удалить старый — zone default уже Full)

### 4.7 Установить Caddy vhost на хосте

`caddy-bootstrap` sidecar в нашем docker-compose автоматически дроп-пнёт `<client>.asystem.ai.conf` в `/etc/caddy/conf.d/` если в compose добавим конфиг — **OR** руками через SSH:
```bash
ssh root@coolify-orion 'cat > /etc/caddy/conf.d/<client>.asystem.ai.conf <<EOF
<client>.asystem.ai {
  encode gzip zstd
  header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
  handle /ws/* { reverse_proxy 127.0.0.1:<NEW_BACKEND_PORT> }
  handle /api/* { reverse_proxy 127.0.0.1:<NEW_BACKEND_PORT> }
  handle { reverse_proxy 127.0.0.1:<NEW_FRONTEND_PORT> }
}
EOF
systemctl reload caddy'
```

⚠ Каждое окружение должно использовать **уникальные host-loopback порты** (не 13000/18890 которые заняты orgon production). Поменять в новом docker-compose.yml: `127.0.0.1:23000:3000` и `127.0.0.1:28890:8890` (например).

### 4.8 Force redeploy

Coolify UI → **Deploy** (или `POST /api/v1/deploy?uuid=<new-app-uuid>&force=true`). Подождать `finished`. Проверить `https://<client>.asystem.ai` → 200.

### 4.9 Создать первого админ-юзера клиента

Сидеры мы отключили (`ORGON_AUTO_SEED=0`). Первого юзера добавить вручную через `psql`:

```bash
docker exec <db-container> psql -U orgon -d orgon -c "
INSERT INTO users (email, full_name, role, password_hash, is_active, email_verified)
VALUES ('admin@<client>.com', 'Admin', 'admin',
        '<bcrypt('TemporaryPassword123!') >',
        true, true);
"
```

При первом логине клиент сам сменит пароль.

### 4.10 Smoke-тест

```bash
curl https://<client>.asystem.ai/api/health   # → {"status":"ok"}
curl -X POST https://<client>.asystem.ai/api/auth/login \
  -d '{"email":"admin@<client>.com","password":"TemporaryPassword123!"}'
# → access_token

# Проверить Safina-связь под токеном
curl -H "Authorization: Bearer $TOKEN" \
  https://<client>.asystem.ai/api/health/safina
# → {"safina_reachable":true}
```

Если все 3 ✓ — pilot-окружение готово. Передавать клиенту.

---

## 5. Что ОБЯЗАТЕЛЬНО доделать перед pilot ОТ ИНСТИТУЦИОНАЛЬНОГО клиента

> Эти 4 пункта — единственное что отделяет нас от «точно готовы к банку/фонду». Текущие demo / agent / OTC клиенты могут стартовать **без них**.

### ❶ HSM/KMS-backend для signer-key — **DONE 2026-05-02** (Wave 18)

**Файл:** `backend/safina/signer_backends.py:KMSSignerBackend`. Реализован per ADRs из `docs/stories/2-3-kms-signer-architecture.md`. 17 unit-тестов в `backend/tests/test_kms_signer_backend.py` через in-process fake KMS (отказались от moto из-за SECP256K1 DIGEST-mode баги). Total backend test count: **167 passed, 0 skipped**.

**Что нужно для prod-pilot с AWS KMS:**

1. **AWS-side setup:**
   ```bash
   aws kms create-key \
     --key-spec ECC_SECG_P256K1 \
     --key-usage SIGN_VERIFY \
     --description "ORGON Safina signer — pilot <client>"
   # Note the KeyId. Optionally:
   aws kms create-alias --alias-name alias/orgon-safina-<client> --target-key-id <key-id>
   ```

2. **IAM-policy** для backend-роли — ТОЛЬКО эти два action на ТОЛЬКО этот KeyId:
   ```json
   {"Version": "2012-10-17", "Statement": [{
     "Effect": "Allow",
     "Action": ["kms:Sign", "kms:GetPublicKey"],
     "Resource": "<key-arn>"
   }]}
   ```

3. **Coolify env vars:**
   ```
   ORGON_SIGNER_BACKEND=kms
   AWS_KMS_KEY_ID=alias/orgon-safina-<client>     # или ARN, или KeyId UUID
   AWS_REGION=eu-central-1                          # где создали ключ
   AWS_ACCESS_KEY_ID=<service account access key>
   AWS_SECRET_ACCESS_KEY=<service account secret>
   # Можно убрать SAFINA_EC_PRIVATE_KEY — больше не используется в kms-режиме
   ```

4. **Smoke-test после deploy:**
   - `/api/health/safina` → `safina_reachable: true`
   - В логах backend: `KMSSignerBackend initialised: address=0x... key_id=alias/...`
   - Создать тестовый кошелёк через `/api/wallets` → success → подпись прошла через KMS

**Vault** (`VaultSignerBackend`) остаётся stub — отдельная stories когда понадобится. Stub поднимает `NotImplementedError` если выставить `ORGON_SIGNER_BACKEND=vault`.

**Почему был блокер (теперь решён):** хранение private-key в process memory непереживёт аудита institutional-клиента (PCI DSS, ISO 27001, SOC 2). С KMS приватный ключ генерируется в AWS HSM (FIPS 140-2 L3) и НИКОГДА не покидает его — даже наш процесс не имеет доступа.

### ❷ Safina canonical sign-payload + local verification — **DONE 2026-05-02** (Wave 22, Story 2.7)

**Решение:** вместо ожидания формата от Safina (процедурный block недели) — реализовали 6 candidate variants в registry + auto-discovery CLI + три-mode runtime (`off|shadow|enforce`). Pilot-клиент сам подтверждает variant за 1 час offline-теста и переключает enforce без ожидания их docs.

**Архитектура:**
- `backend/safina/signature_verifier.py` — pluggable `_CANONICAL_VARIANTS` registry. Текущие 6 кандидатов: `v1_pipe_unid_to_value`, `v2_pipe_unid_value_to_network`, `v3_json_sorted`, `v4_json_to_lower`, `v5_concat_no_separator`, `v6_keccak_pre_hashed`.
- `ORGON_SAFINA_VERIFY_MODE` (env): `off` (default, no verification), `shadow` (verify, log+alert на mismatch, не блокирует tx), `enforce` (verify, mismatch → `transactions.status='rejected_signer_mismatch'`).
- `SAFINA_CANONICAL_VARIANT` (env): имя variant'a из registry. Без него верификация автоматически отключена даже при mode≠off.
- Legacy `ORGON_VERIFY_SAFINA_SIGS=1` маппится на `enforce` для backwards compat.
- Mismatch → INSERT в `aml_alerts(alert_type='safina:signer_mismatch', severity='critical')` — попадает в Wave 21 triage queue.
- Migration 028 — расширяет `transactions.status` enum на новый статус, добавляет partial index для compliance-audit.
- Frontend `StatusBadge` показывает «Подпись не совпала» с red-styling для нового статуса.

**Bring-up runbook (1 час офлайн + 24h soak):**

1. **Capture sample:** оператор с прав admin'a получает один known-good Safina-подписанный transaction:
   ```bash
   # Поднять production-prefixed staging Safina (или test-mode tenant) и
   # выгрузить /api/transactions/sync ответ. Для одной transaction-row
   # извлечь signed[i].ecaddress + signed[i].ecsign плюс tx core fields.
   cat > sample.json <<'EOF'
   {
     "tx_unid": "<tx.unid>",
     "network": <chain_id>,
     "value": "<tx.value as decimal string>",
     "to_address": "<tx.to_addr>",
     "signature_hex": "<signed[i].ecsign>",
     "expected_signer": "<signed[i].ecaddress>"
   }
   EOF
   ```

2. **Run discovery CLI:**
   ```bash
   docker exec orgon-backend python backend/scripts/safina_discover_canonical.py --sample sample.json
   ```
   Output: per-variant ✓/✗ + строка `Confirmed variant: vN_...`. Если `no variant matched` — увеличить candidate-zoo (новый variant в registry → один pull-request).

3. **Set Coolify env (shadow first):**
   ```
   SAFINA_CANONICAL_VARIANT=<имя из шага 2>
   ORGON_SAFINA_VERIFY_MODE=shadow
   ```
   Redeploy backend.

4. **24h soak:** мониторить `/compliance` AML tab. Открытых alerts типа `safina:signer_mismatch` быть не должно. Если есть — variant неверный (multi-network setup может требовать разные variants per chain — добавить branching).

5. **Switch to enforce:**
   ```
   ORGON_SAFINA_VERIFY_MODE=enforce
   ```
   Redeploy. Теперь любая forged подпись от compromised Safina → tx rejected + critical alert в triage.

6. **Compliance-audit demo:** показать аудитору `/compliance` AML с filter `alert_type=safina:signer_mismatch` и `/transactions?status=rejected_signer_mismatch` (когда они есть) + лог `audit_log` action `aml.alert.resolve`.

**Почему ранее был блокер (теперь решён):** без локальной верификации compromised Safina принял бы forged co-signers как валидные на multi-sig. Wave 22 даёт independent ECDSA-recovery — приватный ключ Safina не нужен, recovery работает offline.

### ❸ AML rule engine — **DONE 2026-05-02** (Wave 19+21, Sumsub bridge + triage UI)

**Wave 19 — write path (Sumsub bridge):**
- Webhook handler ловит `applicantOnHold` и события с `rejectLabels` содержащими `SANCTIONS` / `AML_RISK` / `PEP`
- Записывает в `aml_alerts` таблицу с severity (`high` для sanctions/AML, `medium` для остальных)
- Идемпотентен через `correlation_id` (Wave 19, ADR-10)
- KYB-flow (Wave 20) пишет alerts с `organization_id` напрямую (без users-JOIN)

**Wave 21 — triage UI / read+resolve path (Story 2.6):**
- Backend endpoints `/api/v1/compliance/aml/*`: list (cursor pagination), stats, get, claim, resolve, notes
- Conditional UPDATE для claim — двое compliance-officers одновременно жмут «Взять» → один 200, второй 409 с `current_state` для UI
- Atomic UPDATE+audit_log via `conn.transaction()` — каждое claim/resolve/note пишется в `public.audit_log` с `resource_type='aml_alert'`
- `reported` is terminal: после установки SAR-номера alert immutable, любые post-actions → 409
- RBAC: `super_admin` / `company_admin` / `company_auditor` only; `company_operator` исключён (separation of duties)
- Frontend: `/compliance` AML-tab показывает реальную очередь, click → side-drawer с claim/resolve/notes, PII-фильтр на `details` JSON (скрывает `passport_number`/`national_id`/`inn`/`dob`/`taxId`)
- Migration 027 — composite indexes для filter+keyset pagination

**Что отложено на post-MVP:**
- In-house transaction-rule alerts (`compliance_service.check_transaction_against_rules` уже существует, но wire-up в transaction-create flow — Story 2.7)
- SAR submission API в Финнадзор — текущий flow останавливается на manual `report_reference`
- Bulk operations / CSV export — повседневная очередь не нужна
- Custom rule-builder UI — `transaction_monitoring_rules` editable через DB вручную; полноценный UI — отдельный story
- Travel Rule (FATF) — отдельный Sumsub product, отдельная конфигурация

**Smoke-flow (manual после prod-deploy):**
1. KYC-applicant получает RED reviewAnswer → webhook → INSERT в `aml_alerts`
2. compliance_admin открывает `/compliance` → видит KPI «Открытых: 1» + строку в списке
3. Click → drawer показывает details (PII скрыта), нажимает «Взять в работу»
4. Добавляет note, выбирает «Закрыть как решённое» → confirm → `status='resolved'`, `audit_log` row создан с `action='aml.alert.resolve'`

### ❹ KYC document upload — **DONE 2026-05-02** (Wave 19, через Sumsub)

**Решение:** вместо собственного S3-bucket + ClamAV + drag-drop UI — подключили Sumsub WebSDK. Документы загружаются прямо в защищённый сервис Sumsub (FedRAMP-compliant, ISO 27001), нам приходит только ID applicant'a + статус через webhook.

**Что нужно для prod-pilot с Sumsub:**

1. **Зарегистрировать Sumsub аккаунт.** Sales-цикл — 3-5 рабочих дней (NDA + MSA + DPA по GDPR/152-ФЗ). Sandbox доступен сразу для разработки.

2. **В Sumsub Dashboard:**
   - Создать **verification level** (default name `basic-kyc-level` — passport + selfie + liveness). Custom levels для retail vs institutional — настраиваются позже.
   - Получить:
     - **Production app token** (`SUMSUB_APP_TOKEN`) — формат `prd:abcd1234...`
     - **Production secret key** (`SUMSUB_SECRET_KEY`)
     - **Webhook secret** (`SUMSUB_WEBHOOK_SECRET`) — отдельный, под Webhooks tab
   - Настроить webhook URL: `https://<client>.asystem.ai/api/v1/webhooks/sumsub`

3. **Coolify env vars** для backend-service:
   ```
   SUMSUB_APP_TOKEN=prd:...
   SUMSUB_SECRET_KEY=...
   SUMSUB_WEBHOOK_SECRET=...
   SUMSUB_LEVEL_NAME=basic-kyc-level         # опционально, default basic-kyc-level
   SUMSUB_BASE_URL=https://api.sumsub.com    # опционально, default
   ```

4. **Smoke-test после deploy:**
   - Login → `/compliance/kyc` — баннер «pre-launch» исчезает, появляется CTA «Начать верификацию»
   - Click → загружается Sumsub WebSDK iframe
   - Backend log: `Sumsub enabled: level=...` при boot

**Pre-launch (без аккаунта):** все backend endpoints (`/sumsub/access-token`, `/sumsub/applicant-status`, `/webhooks/sumsub`) возвращают чистый **503 Service Unavailable**. Frontend `/compliance/kyc` показывает баннер «Платформа в режиме pre-launch — свяжитесь с support@... для подключения». Никаких 5xx-ошибок при отсутствии кредов.

**Почему ранее был блокер (теперь решён):** KYB-документы (passports, learner-faces, proof-of-address) не отправляются по email — нужен secure upload + virus-scan + audit. Sumsub WebSDK делает всё это сам, без нашего S3 / ClamAV.

### ❺ KYB (бизнесы) — **DONE 2026-05-02** (Wave 20, через Sumsub)

**Решение:** тот же Sumsub WebSDK, но separate `levelName` (`basic-kyb-level` по умолчанию) и отдельная таблица `sumsub_kyb_applicants`. KYB-applicant привязан к организации, не пользователю — `externalUserId = orgon-org-{organization_uuid}`. Webhook handler ветвится по префиксу: `orgon-user-...` → KYC, `orgon-org-...` → KYB. Frontend на `/compliance/kyb`.

**Что нужно для prod-pilot с KYB:**

1. **В Sumsub Dashboard** создать второй verification level — `basic-kyb-level` (или своё имя). Sumsub iframe сам соберёт UBO (Ultimate Beneficial Owners), учредительные документы, lookup в торговых реестрах.
2. **Coolify env var** (опционально — default `basic-kyb-level`):
   ```
   SUMSUB_KYB_LEVEL_NAME=basic-kyb-level
   ```
   Остальные `SUMSUB_*` те же что для KYC (один app_token, один secret, один webhook).
3. **RBAC:** только `super_admin` или `company_admin` своей организации может стартовать KYB. Любой member организации может прочитать статус. Endpoints:
   - `POST /api/v1/kyc-kyb/sumsub/kyb/access-token?organization_id=<uuid>` → mint WebSDK token
   - `GET  /api/v1/kyc-kyb/sumsub/kyb/applicant-status?organization_id=<uuid>` → текущий статус
4. **Smoke-test после deploy:**
   - Login как `company_admin` → `/compliance/kyb` → `Начать верификацию организации`
   - Iframe Sumsub поднимается, статус идёт через тот же webhook
   - В админке (Story 2.6) AML-alerts по KYB видны с `organization_id` ссылкой

**Pre-launch (без аккаунта):** оба endpoints возвращают 503, frontend показывает тот же «pre-launch»-баннер что и KYC.

---

## 6. Безопасность — checklist на launch-day

- [ ] `JWT_SECRET_KEY` выставлен в Coolify env, persistent через restart (test: рестарт backend → токен доadmin не invalidate-нулся)
- [ ] `SAFINA_EC_PRIVATE_KEY` — **НЕ** test-key из docker-compose. Получен от Safina, уникален для tenant'а.
- [ ] `ORGON_PARTNER_REPLAY_OFF` = `0` (HMAC-replay-guard включён)
- [ ] CF DNS — orange-cloud, SSL mode = **Full** (не Flexible — иначе loop)
- [ ] Coolify-managed PG **НЕ** public (нет `is_public: true`)
- [ ] Backup config = enabled, frequency=daily, retention >= 7 дней
- [ ] `SENTRY_DSN` выставлен — иначе никаких алертов на 5xx
- [ ] `ORGON_AUTO_SEED` = `0` — не сидим demo-юзеров
- [ ] `/api/health/detailed` под admin-auth → `safina_api: healthy`
- [ ] `tronscan.org` или соответствующий explorer показывает реальный адрес созданного prod-кошелька
- [ ] WS-канал онлайн (`Header → "Синхронизация · Онлайн"` зелёная точка)
- [ ] Audit-log получает write на каждое action (login, wallet create, sign tx)
- [ ] Если `❶ KMS` сделана — `ORGON_SIGNER_BACKEND=kms` + AWS-creds выставлены, ключ в KMS create-нут как asymmetric SECP256K1
- [ ] Если `❹ S3 upload` сделана — bucket доступен, signed URL'ы проверяются ClamAV-хуком

---

## 7. Disaster recovery

### 7.1 PG corruption / disaster

```bash
# Coolify UI → DB → Backups → Latest → Restore
# Или вручную:
docker exec <db-container> psql -U orgon -c "DROP DATABASE orgon;"
docker exec <db-container> psql -U orgon -c "CREATE DATABASE orgon;"
gunzip -c /var/lib/coolify/backups/<db-uuid>/<latest>.sql.gz | \
  docker exec -i <db-container> psql -U orgon -d orgon
# Restart backend
```

### 7.2 Server down (как сегодня в 15:36)

- Hetzner Robot → Server → Reset → **Hardware reset**
- Через 1-3 минуты: SSH, Coolify auto-start, контейнеры поднимутся
- Если не поднялись: `coolify-orion # systemctl status coolify` — посмотреть в логи
- Если кошельки/sync встали — `docker exec <backend> python3 -c "import asyncio; from backend.services.sync_service import sync_all; asyncio.run(sync_all())"`

### 7.3 Safina API down

- ORGON режим деградации: backend кеширует networks/tokens (TTL 1 час). Read-операции работают.
- Sign-операции вернут `502 Bad Gateway` — клиент ретраит.
- Cron `signature_service.check_new_pending_signatures` ловит и шлёт алерт в Telegram (если настроен).

### 7.4 Cloudflare incident

- DNS меняем на серый-cloud (DNS-only) — request идёт прямо на 65.21.205.230. Нужен публичный cert на origin (Caddy LE auto-renews). Должно работать.

---

## 8. Что мониторить

| Метрика | Где | Алерт-порог |
|---|---|---|
| `/api/health/safina.safina_reachable` | curl, опционально UptimeRobot | `false` 2 минуты подряд |
| `services.database.status` в `/api/health/detailed` | то же | != `healthy` |
| Coolify-managed PG disk usage | Coolify UI или `df -h` | > 80% |
| audit_log row count за последний час | SQL query | > 0 (дроп = что-то не пишется) |
| 5xx на nginx/Caddy | Sentry / Caddy access log | > 10/min |
| Backup execution (daily) | Coolify UI Backups tab | last_run > 26 hours ago |

---

## 9. Что точно НЕ делать на проде

- ❌ Не использовать `demo-admin@orgon.io / demo2026` (захардкоженные test-юзеры)
- ❌ Не выставлять `ORGON_AUTO_SEED=1` на pilot env (сидится test-data поверх клиентских)
- ❌ Не использовать тот же `SAFINA_EC_PRIVATE_KEY` между разными клиентами (изоляция кастоди-доступа)
- ❌ Не выставлять `is_public: true` на standalone-postgresql (БД доступна только через `coolify` docker network)
- ❌ Не делать > 2 деплоев в течение 5 минут — Next.js build пиковая нагрузка по RAM, может уронить хост (см. инцидент 2026-05-02 15:30)
- ❌ Не редактировать `backend/migrations/000_canonical_schema.sql` in-place — добавлять `025_*.sql` overlay
- ❌ Не запускать миграции из `backend/migrations/_historical/` — там legacy-chain
- ❌ Не пушить в `main` напрямую — feature branch + PR

---

## 10. Контакты

- Safina API support: *(заполнить — внутренний канал ASYSTEM)*
- Hetzner Robot: `robot.hetzner.com` (доступ у Урмата)
- Cloudflare zone admin: `urmatdigital@`
- Coolify panel: `https://c.asystem.ai` (auth через Authentik)
- Repo: `https://github.com/MeShele/orgon-platform`
- Telegram emergency channel: *(заполнить)*

---

_Этот файл живой. После каждого pilot-launch обновлять разделы 4 и 6 на основе того что реально потребовалось._
