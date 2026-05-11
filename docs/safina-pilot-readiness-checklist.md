# ORGON — Чек-лист к боевым тестам с Safina

**Дата:** 2026-05-11
**Цель:** свести в одну страницу всё, что нужно сделать/запросить/проверить
перед тем как переключить ORGON с тестового Safina-ключа на prod-tenant
конкретного клиента.

---

## A. Что запросить у Safina (через бизнес-канал ASYSTEM)

⚠️ **Самый критический пункт (2026-05-11 fire-test):** `POST /tx_sign`
возвращает 200 OK, но Safina **молча не учитывает подпись** —
`wait[]` не очищается, tx не broadcast'ится в блокчейн. Wiki это
поведение не описывает. **До разрешения этого вопроса live multi-sig
flow невозможен.** Подробности — `docs/SESSION_2026-05-11_FIRE_TEST_FINDINGS.md`.

| # | Артефакт / вопрос | Зачем | Можно ли без него |
|---|---|---|---|
| **0** | **Объяснить почему `POST /tx_sign` возвращает 200 OK, но подпись не учитывается** | **Блокер end-to-end multi-sig flow**. Возможные причины (наша гипотеза): canonical-payload mismatch ИЛИ EC-key не зарегистрирован как signer для email-account | ✗ **обязательно перед реальными деньгами** |
| 1 | **Один sample signed-tx** с известным `signer_address` + полный JSON request body POST /tx_sign который сделал valid signature | Прогнать `backend/scripts/safina_discover_canonical.py --sample sample.json` → выбрать canonical-variant из 6 кандидатов | ✗ обязательно |
| 2 | `SAFINA_EC_PRIVATE_KEY` для prod-tenant клиента | Уникальный ключ под одного клиента. Текущий в `.env` — общий test-keypair с Examples-страницы wiki pm.kaz.one, для prod **не использовать** | ✗ обязательно |
| 3 | **Объяснить семантику `wait: [{email: ...}]` поля** | В реальном API responses приходит `email`, а в wiki написано "EC-addresses". Это расхождение нужно понять: email = display name? required registration EC↔email? | ✗ обязательно |
| 4 | Подтверждение base URL | По wiki — `my.safina.pro/ece/` универсальный. Уточнить нужен ли клиенту dedicated endpoint | можно с default |
| 5 | IP whitelist (если есть) | Safina может ограничивать source-IP. Узнать заранее, потому что наш egress = `coolify-orion` VM (через outbound NAT хоста orion `65.21.205.230`) | nice-to-have |
| 6 | Лимиты tenant (TPS / daily cap / per-tx) | Чтобы не упереться в первые часы | желательно |
| 7 | Контакт incident channel | На случай нештатной ситуации в нерабочее время | желательно |

**Где запрашивать:** через внутренний канал группы ASYSTEM (Урмат знает контакт). В коде/доках Orgon публичного email/Telegram Safina-команды нет.

---

## B. От клиента / инфры

| # | Что | Зачем | Если нет |
|---|---|---|---|
| 1 | AWS-аккаунт + KMS-ключ (`ECC_SECG_P256K1`, `SIGN_VERIFY`) | Production-grade signer вместо env-key. Wave 18 уже code-ready | остаёмся на `ORGON_SIGNER_BACKEND=env`, **приемлемо для pilot < 1М$ AUM** |
| 2 | Sumsub MSA/DPA + 3 env-var (`SUMSUB_APP_TOKEN/SECRET_KEY/WEBHOOK_SECRET`) | KYC/KYB. Wave 19+20 уже code-ready | endpoints отдают 503 `pre-launch` баннер, демо без KYC |
| 3 | SMTP creds (`SMTP_HOST/USER/PASS/FROM`) | password reset / 2FA / invites | пишет в `/tmp/orgon_emails.log` fallback |
| 4 | `SENTRY_DSN` | error tracking + alerts | error-id'ы только в логах Coolify |
| 5 | Cloudflare DNS A-record на `<client>.asystem.ai` → `65.21.205.230` (orange-cloud, SSL=Full) | публичный URL для клиента | без него нет prod URL |

---

## C. Что у нас уже готово (verified 2026-05-11)

### Код / прод

- ✅ Live Safina-связка работает: `/api/health/safina` reachable, 22 кошелька синканы, 1 реальная Tron-tx в БД (`safina_id=230`)
- ✅ 6 fire-test багов, найденных в этой сессии, **починены и задеплоены** (`67ef88b`, `74f39c0`):
  - jsonb codec на pool (rule create больше не 500)
  - `/wallets/by-unid/{unid}` (правильный lookup по my_unid)
  - `addrs → addr` mapping в sync_wallets (но Safina не даёт addr до активации кошелька в блокчейне)
  - `JwtAuditMiddleware` — UI-mutations теперь пишутся в audit_log_b2b
  - migration 031 — demo-users привязаны к Safina Exchange KG
  - Safina 4xx → 400 с понятным hint вместо 502
- ✅ 239 backend unit-тестов pass
- ✅ Wave 18 KMS-backend: реализован, 17 unit-тестов через fake-KMS
- ✅ Wave 22 canonical-variant: 6 кандидатов в registry, three-mode runtime (`off|shadow|enforce`), CLI discovery скрипт
- ✅ Wave 19+20 Sumsub KYC/KYB: code-ready, в pre-launch до подачи кредов
- ✅ Wave 21 AML triage UI: live на `/compliance`
- ✅ Wave 23-26: rule engine, admin UI, SAR submission, release-from-hold

### Инфра

- ✅ Coolify-orion VM (Proxmox VM #200): RAM 8 GB + **4 GB swap** (новый, persistent в `/etc/fstab`, swappiness=10). OOM-killer теперь не сработает на типичных деплоях
- ✅ Backup config: daily, retention 7 дней / 14 дампов, save_s3=false
- ✅ PG `zbezy4vjauvrsp9p78w4ayxl` (Coolify-managed), сетево изолирован

---

## D. Pre-flight чек-лист (за день до боевых тестов)

```
□ Получены все 6 артефактов из секции A
□ Получены все необходимые из секции B (минимум: AWS KMS если institutional)
□ Создан новый Coolify environment `pilot-<client>` (НЕ переиспользовать orgon-stack)
□ Создан отдельный standalone-Postgres под этого клиента
□ Уникальные host-loopback порты в docker-compose.yml (не 13000/18890 чтоб не конфликтовать)
□ CF DNS + SSL=Full настроены
□ Caddy vhost на orion поднят
□ ORGON_AUTO_SEED=0 в Coolify env (НЕ сидим демо-юзеров на проде клиента)
□ JWT_SECRET_KEY сгенерирован один раз, persistent
□ Если KMS — AWS creds + ORGON_SIGNER_BACKEND=kms выставлены
□ Если Sumsub — 3 env-var + webhook URL зарегистрирован в Sumsub dashboard
□ Smoke: /api/health 200, /api/health/safina reachable=true под новыми кредами
```

---

## E. Sequence боевого теста (рекомендуемый)

### Этап 1: Read-only verification (5 минут)
1. `curl https://<client>.asystem.ai/api/health/safina` → `reachable: true`
2. Логин под admin клиента → `/api/wallets` → должен вернуть пусто (новый tenant) или клиентские
3. `/api/networks` → 7 сетей (стандартный Safina-набор)

### Этап 2: Wallet create на testnet (10 минут)
1. `POST /api/wallets` с `network=5010` (Tron-Nile) или `3040` (ETH-Sepolia)
2. Проверить что в БД появилась запись + Safina вернула `myUNID`
3. Через 5 минут (после sync) — проверить что `addr` подтянулся (если активирован депозитом из faucet)

### Этап 3: Canonical-variant discovery (1 час)
1. Запросить у Safina один **sample signed-tx** на новом ключе
2. `docker exec orgon-backend python backend/scripts/safina_discover_canonical.py --sample sample.json`
3. Должен найти конкретный variant из 6
4. Выставить `SAFINA_CANONICAL_VARIANT=<имя>` + `ORGON_SAFINA_VERIFY_MODE=shadow`
5. Redeploy

### Этап 4: 24h shadow soak
- Никаких новых alerts типа `safina:signer_mismatch` в `/compliance` AML tab
- Если есть mismatch — variant неверный, увеличить кандидатов в registry

### Этап 5: Enforce
- `ORGON_SAFINA_VERIFY_MODE=enforce` → redeploy
- Compromised Safina-подписи теперь отвергаются на нашей стороне

### Этап 6: KMS swap (опционально, для institutional)
- AWS KMS create-key + IAM policy
- `ORGON_SIGNER_BACKEND=kms` + KMS-id в env
- Redeploy
- Verify: log должен сказать `KMSSignerBackend initialised: address=0x...`
- Тест-кошелёк → создание → должно пройти через KMS

---

## F. Known limitations (честно)

1. ⚠️ **`POST /tx_sign` возвращает 200 OK, но Safina silent-rejects подпись** (open question, 2026-05-11). End-to-end multi-sig flow не работает до получения объяснения от Safina. Tx висит в `pending` без broadcast.
2. **Wallet `addr` появляется только после депозита** — природа Safina API на всех сетях (Tron-Nile, ETH-Sepolia, mainnet). Для демо без живых денег `/wallets` будет показывать пустые addr. Это **не баг**.
3. **`addr` vs `addrs` field name mismatch** — Safina detail-endpoint `/wallet/:name` возвращает `addrs` (plural, multi-sig list), наш list-endpoint `/wallets` — `addr` (singular). Mapping добавлен в `wallet_service.py` после fire-test 2026-05-11. Но для unactivated кошельков обе формы пустые.
4. **Audit log хранится в двух таблицах:** `audit_log_b2b` (UI mutations через JwtAuditMiddleware + B2B partner API через AuditLoggingMiddleware) и `audit_log` (AML/rule actions через ComplianceService). `/api/audit/logs` читает только `audit_log_b2b`. AML actions через UI не видны в основном feed'е. Закрытие — отдельная story (UNION view).
5. **Canonical-variant НЕ подтверждён** — `ORGON_SAFINA_VERIFY_MODE=off` на проде. Без sample signed-tx от Safina переключить в enforce невозможно. **6 кандидатов** в registry, скрипт `safina_discover_canonical.py --self-test` проходит — ждём sample-tx.
6. **KMS не прогонялся против реального AWS** — только in-process fake-KMS (17 unit tests passing). Первый live-sign будет на pilot. Закладывать 1 день AWS-sandbox для smoke-теста перед production-данными.
7. **Замена `SAFINA_EC_PRIVATE_KEY`** через прямое редактирование `.env` в VM (script `scripts/safina-key-switch.sh switch <key>` — auto-rollback при failed smoke) применяется мгновенно через `docker restart`, но Coolify на следующем full redeploy перезапишет из своей БД. Для persistence — параллельно обновить через Coolify UI (Environment Variables tab).

---

## G. Контакты

- Safina API support: через **бизнес-канал ASYSTEM** (Урмат)
- Safina wiki (публичная): `https://pm.kaz.one/projects/safina-api/wiki`
- Hetzner Robot: `robot.hetzner.com` (доступ у Урмата)
- Coolify panel: `https://c.asystem.ai`
- Repo: `https://github.com/MeShele/orgon-platform`
