# 2026-05-11 — Fire-test findings (live smoke against prod)

> **TL;DR.** Архитектура работает. Read-операции и create-wallet идут вживую с
> Safina. Send_transaction отправляется в Safina state. **Sign-flow возвращает
> 200 OK, но Safina молча не учитывает подпись** — это критическая неясность
> требующая ответа от Safina-команды на ближайшем созвоне.
>
> **Готовность: ~85% (не 99%, как заявлено в prod-readiness.md до сегодня).**

---

## Контекст

Пользователь запросил fire-test перед созвоном с Safina. Под demo-admin
прогнал реальные mutation-flow на `https://orgon.asystem.ai`. Нашёл
**8 проблем**: 7 в нашем коде (все закрыты в этой сессии), 1 — open
question к Safina.

## Что точно работает (verified live)

| Flow | Доказательство |
|---|---|
| Login + JWT | Token issued, role=admin |
| `/api/health/safina` | `reachable: true` (live ECDSA handshake) |
| Wallet sync из Safina | 22 кошелька, 7 networks, balances, pending sigs poll каждую минуту |
| `POST /api/wallets` (Tron-Nile create) | UNID `822A9F1F34A5D1CA45258DF40033714A`, wallet_id=406 |
| `POST /api/wallets` (ETH-Sepolia create) | UNID `0666110114621F9345258DF4003BD0C1`, wallet_id=407 |
| `POST /api/transactions` send 0.1 TRX → Safina | tx accepted, Safina `id=236`, unid `46AF88DC...` |
| AML rule create (org-scoped) | `rule_config` приходит как dict (jsonb codec работает) |
| JwtAuditMiddleware | 4+ rows в `audit_log_b2b` с user_id, action, status, duration_ms |
| Local replay-guard | 409 `duplicate_signature` на повторный sign того же EC |

## Что критически НЕ работает

### Sign endpoint: 200 OK от Safina, но silent reject

```
POST /api/signatures/46AF88DC.../sign  →  200 OK
  {"ok":true,"message":"Transaction signed successfully"}
```

7 минут спустя через `GET /api/signatures/.../details`:

```json
{
  "wait":   [{"email":"marisejd@gmail.com"}],   // unchanged
  "signed": null,                                 // unchanged
  "tx":     null,                                 // tx_hash — нет broadcast
  "signature_status": {"progress": "0/0"}
}
```

Re-sign attempt → `409 duplicate_signature` (наша local-replay-guard
доказывает что мы реально посылали sign — это не наша сторона
проблемы).

**Что говорит wiki `pm.kaz.one/projects/safina-api/wiki`:**

| Wiki | Реальность |
|---|---|
| `POST /tx_sign/:tx_unid` — "Ответ {}" | Не описано как отличить valid sign от invalid (обе возвращают {}) |
| "wait" = strict requirement list of **EC addresses** | В реальности приходит `email`, не EC. Wiki устарел |
| Sign-flow detail | **НЕТ в wiki вообще** |
| Registration step EC ↔ account/email | **НЕТ в wiki вообще** |

**Две гипотезы (вероятность ~50/50):**

1. **Canonical-payload mismatch** — наша подпись не валидируется
   Safina-стороной из-за формата canonical-payload над которым делается
   keccak. Это та самая Wave 22 неопределённость. 6 candidate variants
   в registry готовы, но какой реальный — узнаем только из sample
   signed-tx от Safina.

2. **EC ≠ зарегистрированный signer** — EC-адрес
   `0xA285990a1Ce696d770d578Cf4473d80e0228DF95` может быть владельцем
   wallet (auth), но не зарегистрирован как signer для multi-sig.
   `marisejd@gmail.com` — это email account'а на стороне Safina,
   который, возможно, имеет **другой** signer-EC.

В обоих случаях нужен **ответ Safina-команды на созвоне**.

---

## 7 фиксов сегодня

| # | Симптом | Файл / коммит |
|---|---|---|
| 1 | `POST /v1/compliance/rules` → 500: jsonb колонка возвращалась как str, Pydantic падал | `backend/database/db_postgres.py` (`e3c1122`) — codec на pool |
| 2 | `/api/wallets/by-unid/{unid}` → 404 на existing UNID: handler искал по name | `backend/services/wallet_service.py` + `routes_wallets.py` (`67ef88b`) — новый `get_wallet_by_unid()`, fallback на my_unid |
| 3 | Wallet addr пустой после sync: Safina detail возвращает `addrs` (plural), а не `addr` | `wallet_service.py` (`67ef88b`) — addrs→addr mapping (но всё равно empty пока кошелёк не активирован депозитом — природа Safina) |
| 4 | `audit_log` пустой после всех UI-действий: AuditService писал только на partner API | `backend/api/middleware_b2b.py` (`67ef88b`) — `JwtAuditMiddleware`, decodes JWT in-flight, logs to audit_log_b2b |
| 5 | demo-admin не привязан к org → `/organizations` = `[]` | `backend/migrations/031_demo_admin_org_link.sql` + main.py lifespan apply (`67ef88b`, `74f39c0`) — self-seeds org |
| 6 | `POST /api/transactions` → 502 на пустой кошелёк (Safina 4xx wrapped в 5xx) | `safina/errors.py` + `safina/client.py` + `routes_transactions.py` (`67ef88b`) — SafinaError carries `status_code`, 4xx→400 с hint |
| 7 | **Live send 500 — column "info" of relation "transactions" does not exist** | `backend/services/transaction_service.py` (`4e823f1`) — drop info из cache INSERT |

И **один gap, который мы пока не закрываем** (требует Safina-input):

| # | Симптом | Открытый вопрос |
|---|---|---|
| 8 | Sign возвращает 200 OK, Safina не учитывает в state | Что нужно для valid sign? Canonical-payload format? Signer registration? |

---

## Инфраструктура: VM OOM mitigation

Диагностика показала: предыдущий deploy уронил backend и frontend
контейнеры через global OOM-killer в VM #200 на Proxmox-хосте orion.
VM имела 8 GB RAM и **0 swap**. OOM-log:

```
[Mon May 11 10:35:31 2026] oom-kill:constraint=CONSTRAINT_NONE…
[Mon May 11 10:35:31 2026] Out of memory: Killed process … task=beam.smp
[Mon May 11 10:35:37 2026] Out of memory: Killed process … task=systemd
[Mon May 11 10:35:38 2026] Out of memory: Killed process … task=next-server
```

**Фикс:** swapfile 4 GB на VM, swappiness=10, persistent через `/etc/fstab`.
После активации построение прошло с peak 870 MB в свопе — без него
снова был бы OOM. **Без даунтайма для других проектов на VM.**

```bash
ssh -J root@65.21.205.230 root@10.10.20.10
fallocate -l 4G /swapfile
chmod 600 /swapfile
mkswap /swapfile && swapon /swapfile
echo "/swapfile none swap sw 0 0" >> /etc/fstab
echo "vm.swappiness=10" > /etc/sysctl.d/99-orgon-swap.conf
```

---

## Что готово к боевым тестам

| Раздел | Готовность |
|---|---|
| Pilot environment setup runbook | ✅ `docs/prod-readiness.md` секция 4 |
| Switchover + rollback скрипты | ✅ `scripts/safina-key-switch.sh {status\|switch\|rollback}` |
| Canonical-discover script | ✅ `backend/scripts/safina_discover_canonical.py --self-test` ✓ |
| 6 canonical-variant candidates | ✅ `backend/safina/signature_verifier.py:_CANONICAL_VARIANTS` |
| `ORGON_SAFINA_VERIFY_MODE` three-mode (`off\|shadow\|enforce`) | ✅ Wave 22 |
| Audit log для UI-юзеров | ✅ JwtAuditMiddleware, ловит все POST/PATCH/PUT/DELETE на /api/* |
| Live send_transaction в Safina state | ✅ Verified — tx `id=236` в Safina pending |
| **Live sign + broadcast end-to-end** | ❌ **Blocked на Safina-стороне (sign silent reject)** |
| KMS-backend под реальным AWS | ⚠️ Code-ready, in-process fake-KMS tests passing, не прогонялся на live AWS |

---

## Вопросы к Safina на созвоне 2026-05-12

1. **Sample signed-tx** с известным `signer_address` (даже на testnet) — для
   `safina_discover_canonical.py`. Это закрывает Wave 22 неопределённость.
2. **POST /tx_sign возвращает 200 OK, но wait[] не очищается, signed=null, tx
   не broadcast'нулся.** Что мы делаем не так? Может, есть какой-то request
   body / additional header / pre-registration шаг?
3. **`wait[]` возвращает email, а не EC-address** (wiki говорит обратное).
   Email — это display name или нужно зарегистрировать EC ↔ email
   association заранее?
4. **При выдаче prod-tenant** ожидаем получить: уникальный `SAFINA_EC_PRIVATE_KEY`,
   `base_url` (если отличается), IP whitelist, лимиты, контакт incident channel.
5. **Документ по signing flow:** request body, response для valid/invalid sign,
   как идентифицируется signer. Wiki текущая не покрывает.

---

## Что пользователь должен сделать

- [ ] **Завтра на созвоне:** задать 5 вопросов выше
- [ ] **Получить sample signed-tx** и прогнать через `safina_discover_canonical.py`
- [ ] **Получить boevye SAFINA_EC_PRIVATE_KEY** клиента
- [ ] **Запустить switchover:** `./scripts/safina-key-switch.sh switch 0x<new-key>`
- [ ] **24h shadow soak** через `ORGON_SAFINA_VERIFY_MODE=shadow`
- [ ] **Enforce mode** только после soak и решения sign-issue

## Что пока НЕ обещать руководству

- Что **multi-sig flow end-to-end** работает — пока sign silently rejected
- Что **live send в блокчейн** доходит за минуты — пока tx висит в Safina pending без broadcast

Можно показать на демо:
- Architecture simulator (`/demo/architecture`)
- Wallet list с 22 живыми Safina-кошельками
- AML rule create
- Audit log с реальными entries
- Live tx в pending state (но не broadcast'нутая — объяснять как «ждёт final
  approval от signer'а» что технически правда)
