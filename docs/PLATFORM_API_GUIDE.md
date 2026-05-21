# ORGON Platform API — self-service merchant provisioning

> **Audience.** Эрмек / любой другой автоматизатор на стороне
> asystem-core'а, который хочет дать оператору обменника возможность
> **сам активировать ORGON Custody** через `/admin/modules` без
> участия sales-человека из ORGON.
>
> **Не для оператора обменника.** Оператор не вызывает `/platform/*`
> напрямую. Это API между control-plane'ом asystem-core'а и нашим
> бэкендом. Гайд для оператора — `docs/ORGON_FOR_EXCHANGES.md`.

Закрывает OP-3 из `docs/CUSTDEV_OPERATOR_END_USER.md`: «нет
self-service ORGON merchant provisioning UX».

---

## TL;DR

```bash
curl -X POST https://orgon.asystem.ai/platform/merchants \
  -H "Authorization: Bearer ${ORGON_PLATFORM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Kiril Exchange",
    "slug": "kiril-asystem-2026",
    "merchant_kind": "exchanger",
    "pricing_plan": "sandbox",
    "sandbox": true,
    "label": "Operator: Kiril Petrov"
  }'
```

Возвращает атомарно: новый merchant + первая ключ-пара. **`secret_once`
отдаётся ОДИН раз — сохранить сразу.**

---

## Auth

`/platform/*` живёт за отдельным middleware
(`PlatformMasterAuthMiddleware`). НЕ HMAC `/v1/*`, НЕ JWT `/api/*`.

```
Authorization: Bearer <ORGON_PLATFORM_MASTER_KEY>
```

Token — opaque random bytes (64-hex), `hmac.compare_digest` сравнение
с env-var на нашей стороне. Где взять токен:

- Sales / `@urmatdigital` отдают один раз при подключении тенанта
  asystem-core'а
- На нашей стороне живёт в Coolify env как `ORGON_PLATFORM_MASTER_KEY`,
  UUID Coolify `m1065anf11ax5ucowqs4nqto`
- На вашей стороне — Supabase Secret / Edge env. Ротация: запросить у
  нас, flip с обеих сторон одновременно

### Что happens при ошибках auth

| Состояние | Ответ |
|---|---|
| `ORGON_PLATFORM_MASTER_KEY` не выставлен на нашей стороне | `503` с подсказкой «Platform API is disabled on this deployment» |
| Authorization header отсутствует / не Bearer | `401 "Bearer token required"` |
| Bearer token не совпадает | `401 "Unauthorized"` (без подсказки какая сторона неправильная — anti-probing) |

---

## `POST /platform/merchants`

Создаёт merchant + первую API-пару в одной транзакции.

### Request

```jsonc
{
  "name": "Kiril Exchange",            // 2..200 chars, отображаемое имя
  "slug": "kiril-asystem-2026",        // [a-z0-9-]+, 2..60, ИДЕМПОТЕНТНОСТЬ — см. ниже
  "merchant_kind": "exchanger",        // exchanger|bank|exchange|internal
  "pricing_plan": "sandbox",           // sandbox|starter|growth|enterprise
  "sandbox": true,                     // true → выпускается okt_*/okst_* пара (testnet-only)
  "label": "Operator: Kiril Petrov"    // опционально, ≤120 chars, видно в нашем admin UI
}
```

**Slug — это идемпотентность.** Повторный POST с тем же `slug`
возвращает `409` с явным сообщением:

```json
{"detail": "Slug 'kiril-asystem-2026' already taken (merchant_id=<uuid>)"}
```

Каноничная стратегия: используйте `${operator_id}` (UUID оператора
asystem-core'а) как часть slug. Тогда retry безопасен — `409` значит
«мы уже подняли этот merchant раньше, иди ищи его id у себя в
`operator_api_keys` или в нашем `/api/admin/merchants/${id}`».

### Response 201

```jsonc
{
  "merchant": {
    "id": "<uuid>",                    // merchant_id у нас, использовать в /v1/* HMAC headers как X-ORGON-... контекст
    "name": "Kiril Exchange",
    "slug": "kiril-asystem-2026",
    "merchant_kind": "exchanger",
    "pricing_plan": "sandbox",
    "sandbox": true,
    "status": "active",
    "provisioning_source": "api",      // distinguishes from manual UI flows in audit_log
    "created_at": "2026-05-21T..."
  },
  "api_key": {
    "id": "<uuid>",                    // обращайтесь к нашему /api/admin для управления
    "key_pub": "okt_abcd1234...",      // X-ORGON-Key header value, можно показать оператору в UI
    "secret_once": "okst_secret...",   // ⚠️ ОТДАЁТСЯ ОДИН РАЗ — pipe сразу в operator_api_keys vault
    "label": "Operator: Kiril Petrov"
  }
}
```

### Что делать с response

```ts
// Псевдокод asystem-core edge function `orgon-provision-merchant`
async function provisionOrgonForOperator(operatorId: string, operatorName: string) {
  const slug = `op-${operatorId.replace(/-/g, "").slice(0, 24)}`
  const masterKey = Deno.env.get("ORGON_PLATFORM_MASTER_KEY")!

  const r = await fetch("https://orgon.asystem.ai/platform/merchants", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${masterKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      name: operatorName,
      slug,
      merchant_kind: "exchanger",
      pricing_plan: "sandbox",
      sandbox: true,
      label: `asystem-core operator ${operatorId}`,
    }),
  })

  if (r.status === 409) {
    // Already provisioned — caller's retry, just continue.
    // Look up the merchant_id via slug if we don't have it cached.
    return { status: "already_provisioned" }
  }
  if (!r.ok) {
    throw new Error(`ORGON platform error ${r.status}: ${await r.text()}`)
  }
  const data = await r.json()

  // Write all 4 keys to vault — these are exactly what the operator
  // would have typed manually if going through the out-of-band path.
  for (const [key, value] of [
    ["ORGON_KEY", data.api_key.key_pub],
    ["ORGON_SECRET", data.api_key.secret_once],
    ["ORGON_BASE_URL", "https://orgon.asystem.ai"],
    ["ORGON_ENV", "sandbox"],
  ]) {
    await supabaseAdmin.rpc("set_operator_api_key", {
      _operator_id: operatorId,
      _module_id: "orgon-custody",
      _key_name: key,
      _value: value,
    })
  }

  return {
    status: "provisioned",
    orgon_merchant_id: data.merchant.id,
    key_pub: data.api_key.key_pub,
  }
}
```

После этого оператор в `/admin/modules` нажимает «Активировать
ORGON Custody» → видит что 4 ключа уже там (visual hint в UI), нажимает
«Проверить подключение» → ping → «Зарегистрировать webhook» → готов.

---

## Error responses

| HTTP | Случай | Ответ |
|---|---|---|
| `400` | Pydantic-валидация (slug regex, name length, неизвестный merchant_kind) | `{"detail": "validation error", ...}` |
| `401` | Bearer token отсутствует / неправильный | `{"detail": "..."}` |
| `403` | (не используется на `/platform/*`) | — |
| `409` | `slug` уже занят | `{"detail": "Slug 'X' already taken (merchant_id=<uuid>)"}` |
| `500` | Внутренняя ошибка после создания merchant'а но при выпуске ключа | `{"detail": "Merchant <id> created but key issuance failed..."}` — **в этом случае merchant в БД есть, ключа нет**; retry через JWT admin: `POST /api/admin/merchants/{id}/api-keys` |
| `503` | Master-key не сконфигурирован на нашей стороне | `{"error": "Platform API is disabled on this deployment. Set the ORGON_PLATFORM_MASTER_KEY env var to enable."}` |

---

## Audit trail

Каждое успешное создание merchant'а пишет в наш `audit_log`:

```sql
SELECT
  action,           -- 'merchant_self_provisioned'
  resource_type,    -- 'organization'
  resource_id,      -- new merchant UUID
  details,          -- JSON: { source: 'platform_api', slug, name, sandbox, ... }
  organization_id,  -- new merchant UUID (TD-1 Phase A, since 2026-05-21)
  created_at
FROM audit_log
WHERE action = 'merchant_self_provisioned'
ORDER BY created_at DESC;
```

`user_id` всегда `NULL` (machine-driven, нет человека-actor'а).
`details.source='platform_api'` отличает от manual /api/admin/merchants
human-flow'а. Этот audit-tag упомянут в `routes_platform_admin.py`
comments как контракт ревьюера.

---

## Что НЕ умеет `/platform/*` (на 2026-05-21)

- **Не обновляет merchant.** Изменить `pricing_plan`, `merchant_kind`,
  имя — нет. Только через `/api/admin/merchants/{id}` JWT-flow на
  ORGON-стороне.
- **Не реактивирует приостановленного merchant'а.** Если status стал
  `suspended` — только через наш admin UI.
- **Не ротирует API-key.** Через `POST /api/admin/merchants/{id}/api-keys`
  JWT-route (нет master-key пути). Это намеренно — ротация ключей —
  более чувствительная операция чем создание нового merchant'а.
- **Не выпускает scoped sub-keys** (например read-only). Только первая
  пара с дефолтными scope'ами `["read","write"]`. Merchant'у нужны
  scoped — сам или через admin UI.

Если что-то из этого окажется нужно для self-service flow — расширим
`/platform/*` дополнительными endpoint'ами по запросу.

---

## Тестирование

`/platform/merchants` принимается на проде (`orgon.asystem.ai`).
Sandbox-merchant можно создавать сколько угодно — они в `sandbox=true`,
ключи `okt_*`/`okst_*`, изолированы от mainnet.

Smoke-curl:

```bash
# Ваш master-token
export ORGON_PLATFORM_MASTER_KEY="..."

# Тестовый merchant
curl -X POST https://orgon.asystem.ai/platform/merchants \
  -H "Authorization: Bearer ${ORGON_PLATFORM_MASTER_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Smoke Test",
    "slug": "smoke-'$(date +%s)'",
    "merchant_kind": "exchanger",
    "pricing_plan": "sandbox",
    "sandbox": true
  }' | jq .

# Проверка что ping работает с возвращёнными ключами
KEY=$(echo "$response" | jq -r '.api_key.key_pub')
SECRET=$(echo "$response" | jq -r '.api_key.secret_once')
TS=$(($(date +%s%N) / 1000000))
NONCE=$(uuidgen | tr 'A-Z' 'a-z')
BODY=""
MSG="${TS}\n${NONCE}\nGET\n/v1/ping\n${BODY}"
SIG=$(printf "%b" "$MSG" | openssl dgst -sha256 -hmac "$SECRET" | awk '{print $2}')

curl https://orgon.asystem.ai/v1/ping \
  -H "X-ORGON-Key: ${KEY}" \
  -H "X-ORGON-Timestamp: ${TS}" \
  -H "X-ORGON-Nonce: ${NONCE}" \
  -H "X-ORGON-Signature: ${SIG}"
```

Должно вернуть `{ok: true, merchant_id: "<новый uuid>", scopes: ["read","write"], api_key_id: "<uuid>"}`.

---

## Cleanup тестовых merchant'ов

Sandbox-merchant'ы накапливаются. Снести через JWT admin UI на
`orgon.asystem.ai/admin/merchants/<id>` → Suspend → Delete. Cron'а
автоочистки нет (намеренно — slug-uniqueness mitigation: смузнули и
сразу retry с тем же slug'ом получит 409 от удалённой записи через
soft-delete-pattern; пока soft-delete не реализован, hard delete
освобождает slug).

Smoke-merchant из деплоя 2026-05-20 (`smoke-1779266544`) до сих пор
живёт — sandbox, безвреден, можно снести когда удобно.
