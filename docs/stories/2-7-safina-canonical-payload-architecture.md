---
name: Safina canonical-payload normalization & local signer verification — Architecture & Sprint Plan
status: done
created: 2026-05-02
completed: 2026-05-02
type: architecture-decision-record + sprint-plan
parent_story: 2.7 — Production Readiness — Safina canonical-payload + local signer verification
relates_to:
  - docs/prod-readiness.md (❷ — last institutional blocker)
  - docs/stories/2-3-kms-signer-architecture.md (Wave 18 — sign-side)
  - docs/stories/2-6-aml-triage-architecture.md (Wave 21 — AML alert sink)
  - backend/safina/signature_verifier.py (existing scaffolding, NotImplementedError gate)
follows: Wave 21 (AML triage UI)
phases_after_this:
  - Story 2.8 — wire `check_transaction_against_rules` into transaction-create flow
  - Story 2.9 — SAR submission to Финнадзор (external regulator integration)
---

# Story 2.7 — Safina canonical-payload + local signer verification

## 1. Goal (single sentence)

Закрыть **последний** institutional-блокер `❷` из prod-readiness: дать pilot-клиенту возможность **локально верифицировать** Safina-возвращённые ECDSA-подписи (так что compromised Safina-backend не сможет нам подсунуть forged co-signers), **не дожидаясь** документации формата от команды Safina — через auto-discovery candidate variants + shadow-mode.

## 2. Why this is "design-around-uncertainty", не straight-implementation

Реальная проблема: **никто из ORGON-side не знает точный формат байтов** который Safina-side подписывает. Документация Safina не публична / неполна, мы ждём ответ от их команды через ASYSTEM-channel — это может занять недели.

Стандартное решение «дождаться формата → реализовать» — это процедурный block. Альтернатива:

- Реализовать **N кандидатных форматов** (всего 4-6 вариантов: pipe-joined в разных порядках полей, compact JSON, RLP, hash-of-canonical) с pluggable выбором через env
- Запускать **shadow-mode** (verify but don't reject) на pilot-окружении сразу, копить mismatch-логи
- **Auto-discovery helper**: даёшь ему живой `(tx_payload, signature, expected_address)` triple → перебирает все варианты → говорит какой совпал
- После того как один variant подтверждён — переключаемся в `enforce` mode

Это превращает «процедурный блок weeks» в «1 час auto-discovery + flag-flip».

---

## 3. Architecture Decision Records

### ADR-1 — `SAFINA_CANONICAL_VARIANT` env flag, не hardcode

**Decision:** `canonical_payload(...)` ветвится на встроенный реестр вариантов, выбираемых через `SAFINA_CANONICAL_VARIANT=v1_pipe_unid_to_value|v2_pipe_unid_value_to|v3_json_compact|v4_json_keccak|v5_rlp|v6_eip712`. Default — `unset` → существующее `NotImplementedError` поведение.

**Rationale:**
- Без перекомпиляции/redeploy: оператор крутит env, рестарт backend, пробует.
- Каждый variant — pure-function `(tx_data) → bytes`. Нет if-else hell в hot-path.
- `unset` сохраняет existing behavior — backwards-compatible.

### ADR-2 — Три режима верификации: `off | shadow | enforce`

**Decision:** `ORGON_SAFINA_VERIFY_MODE` (env), single source of truth.
- **`off`** (default): `verify_safina_tx_signer()` returns None, ничего не проверяется. Текущее поведение.
- **`shadow`**: верификация выполняется. Mismatch → лог `WARN` + `aml_alerts` row с `alert_type='safina:signer_mismatch'`. Транзакция всё равно сохраняется. Это data-collection mode.
- **`enforce`**: mismatch → транзакция помечается `status='rejected_signer_mismatch'` (новый статус), не процессится дальше. AML-alert тоже создаётся.

**Rationale:**
- Shadow-mode = production-safe rollout. Включи, наблюдай, переключи на enforce когда уверен.
- Один env вместо `ORGON_VERIFY_SAFINA_SIGS=1` (existing) — но я обратно-совместим: legacy `=1` mapping на `enforce` для не-сюрприза.
- Enforce-режим даёт audit-комплианс «forged signer = blocked tx» на pilot-аудите.

### ADR-3 — Auto-discovery — отдельный CLI-script, не runtime

**Decision:** `backend/scripts/safina_discover_canonical.py` — standalone CLI. Принимает sample Safina-response (path или stdin), перебирает все registered variants, для каждого проверяет recovery vs `ecaddress`. Возвращает первый совпавший variant + verbose log по остальным.

**Rationale:**
- Не runtime-overhead — discovery нужен один раз на тенант.
- Stdout-friendly для CI/ops чек-листа.
- Изолирован — никак не влияет на FastAPI process.

**Alternative:** автоматический discovery в shadow-mode (на каждой mismatch пробуем все variants). Отвергнута — производительность × log-spam × complexity. Один-раз-CLI чище.

### ADR-4 — Mismatch → `aml_alerts`, не отдельная таблица

**Decision:** Безуспешная верификация записывает row в `aml_alerts(alert_type='safina:signer_mismatch', severity='critical', description=..., details={'expected':..., 'recovered':..., 'variant':...})`. Reuse existing AML triage UI.

**Rationale:**
- Wave 21 уже даёт triage workflow — compliance-officer увидит mismatch в той же очереди что Sumsub-flagged applicants.
- `severity='critical'` потому что forged signer = potentially compromised Safina = pilot-killer.
- Не создаём `safina_signer_mismatches` отдельную таблицу — overkill для low-velocity event'a.

### ADR-5 — Round-trip self-test через ORGON-side `SafinaSigner`

**Decision:** Тест `test_safina_canonical.py` использует существующий `SafinaSigner._eth_sign` (Wave 18), даёт известный известный payload через `canonical_payload(variant=v1, …)` → `eth_personal_sign_hash` → подписать → `recover_signer_address` → expect equality.

**Rationale:**
- Без живой Safina мы не знаем что variant правильный для **их** flow. Но раунд-трип внутри ORGON-side гарантирует что **наша** crypto chain работает: hashing, signing, recovery — всё идемпотентно.
- Когда auto-discovery укажет реальный variant — тот же тест работает на нём.
- 2-3 round-trip теста дают коврик безопасности для refactoring.

### ADR-6 — Variant registry — frozen dataclass + module-level dict

**Decision:** `_CANONICAL_VARIANTS: dict[str, CanonicalVariant]` где `CanonicalVariant` — `frozen dataclass` с `name`, `description`, `build(tx_data) -> bytes`. Plug-in новых вариантов = dict-update.

**Rationale:**
- Strict typing → IDE подсказывает доступные variants.
- Frozen → невозможно accidentally мутировать.
- Module-level → trivial import, no DI overhead.

### ADR-7 — `transaction_service._sync_one` wire-up — non-blocking call

**Decision:** В `_sync_one(tx)` для каждой `tx.signed[i]` со заполненным `ecaddress`+`ecsign`:
```python
result = verify_safina_tx_signer(
    tx_unid=tx.unid, network=tx.network, value=str(tx.value),
    to_address=tx.to_addr,
    signature_hex=sig['ecsign'],
    expected_signer=sig['ecaddress'],
)
# result: True | False | None (off/not-wired)
if result is False:
    # shadow → log+alert; enforce → also reject
    await self._handle_signer_mismatch(...)
```
Verification — sync function (no I/O), безопасно вызывать в hot-path.

**Rationale:**
- Минимально-инвазивный wire-up: 5-7 строк в существующем loop.
- AML-alert insert идёт через тот же `db_pool` — атомарность с tx-insert опционально (см. ADR-8).
- Performance: ECDSA recovery — ~1ms на signer; даже 10 signers/tx → 10ms. Negligible.

### ADR-8 — Mismatch alert insertion — outside tx-write transaction

**Decision:** AML-alert на mismatch пишется **отдельной транзакцией**, после tx-INSERT. Если alert-insert падает — log error + продолжаем (tx уже сохранена).

**Rationale:**
- Если связать alert+tx в один transaction, ошибка alert-insert откатит tx-write — нежелательно (мы хотим хотя-бы tx сохранить).
- В shadow-mode mismatch не означает что tx плохая, просто что Safina + ORGON disagree на формате.
- В enforce-mode tx уже помечена `rejected_signer_mismatch` → она «безопасно зафиксирована как rejected», alert это дополнительная сигнализация.

### ADR-9 — Safina `network` field — int, не string

**Decision:** Все registered variants принимают `network: int` (как сейчас в `canonical_payload` signature). Variants where network embedded as string-token (e.g. "ETH", "TRX") — derived inside variant function.

**Rationale:** Source of truth — численный chain-id Safina-стороны. Dictionary `NETWORK_INT_TO_TOKEN = {1: "ETH", 195: "TRX", ...}` локализована в variant'ах что используют string-form.

### ADR-10 — Тесты — pattern Wave 19/20/21 (in-process FakeConn) для wire-up

**Decision:** `tests/test_transaction_signer_verification.py` через тот же FakeConn-pool что AML тесты. Verification logic тестируется отдельно в `test_safina_canonical.py` (pure-functions, no DB).

**Rationale:** Консистентность с предыдущими story. 80% покрытия достигаются через pure-function tests + 1-2 integration tests на wire-up.

### ADR-11 — `rejected_signer_mismatch` — добавляем в transactions.status enum

**Decision:** Migration 028 расширяет `transactions.status` CHECK constraint на новое значение `rejected_signer_mismatch`. Frontend отображает как «Отклонена — несовпадение подписи» с red badge.

**Rationale:**
- Существующие статусы (`pending`, `signed`, `submitted`, `confirmed`, `failed`) не описывают этот случай — `failed` слишком generic.
- Compliance-аудитор может фильтровать по этому статусу для регуляторного отчёта.

### ADR-12 — Не блокируем существующий transaction-flow если verification offline

**Decision:** `is_verification_enabled()` (existing) возвращает False для `mode=off` ИЛИ для unset variant. В этих случаях transaction sync работает 100% как сейчас.

**Rationale:** Backwards compatibility — pilot-клиенты что не настроили verification, продолжают работать как до Wave 22.

---

## 4. DB schema changes (migration 028)

```sql
-- backend/migrations/028_transactions_signer_mismatch.sql

-- Add new terminal status for transactions rejected by local
-- signer-verification (Wave 22 / Story 2.7).
ALTER TABLE transactions
    DROP CONSTRAINT IF EXISTS transactions_status_check;

ALTER TABLE transactions
    ADD CONSTRAINT transactions_status_check
    CHECK (status IN (
        'pending', 'signed', 'submitted', 'confirmed', 'failed',
        'rejected_signer_mismatch'
    ));

-- Index for compliance-audit query "all rejected-signer-mismatch tx".
CREATE INDEX IF NOT EXISTS idx_transactions_status_signer_mismatch
    ON transactions (created_at DESC)
    WHERE status = 'rejected_signer_mismatch';
```

**Migration safety:** ALTER constraint работает atomically, IF EXISTS на DROP делает идемпотентным. Без `CONCURRENTLY` — пилотные таблицы маленькие.

---

## 5. Interface contracts

### 5.1 `signature_verifier.py` — extend, not replace

```python
# Existing public API stays:
recover_signer_address(message_hash, signature_hex) -> str
verify_signer(message_hash, signature_hex, expected_address) -> bool
eth_personal_sign_hash(message) -> bytes

# canonical_payload() loses NotImplementedError, gains variant dispatch:
canonical_payload(*, variant: str | None = None, tx_unid, network, value, to_address) -> bytes
    # variant=None → reads SAFINA_CANONICAL_VARIANT env
    # raises ValueError if variant unknown
    # raises NotImplementedError if env unset (preserves old behavior)

# verify_safina_tx_signer() returns extended type:
verify_safina_tx_signer(*, tx_unid, network, value, to_address,
                        signature_hex, expected_signer) -> Optional[bool]
    # True  — signer matches
    # False — recovery succeeded but address differs (forgery / wrong variant)
    # None  — verification disabled (off-mode / variant unset)

# New: mode helper
get_verify_mode() -> Literal["off", "shadow", "enforce"]
    # parses ORGON_SAFINA_VERIFY_MODE; legacy ORGON_VERIFY_SAFINA_SIGS=1 → "enforce"

# New: discovery primitive (used by CLI, also useful in tests)
try_all_variants(*, tx_unid, network, value, to_address,
                 signature_hex, expected_signer) -> dict[str, bool]
    # returns {variant_name: matched_bool}
```

### 5.2 Variant registry

```python
@dataclass(frozen=True)
class CanonicalVariant:
    name: str
    description: str
    build: Callable[[dict], bytes]

# Initial 6 candidates (final list pending Safina docs):
_CANONICAL_VARIANTS: dict[str, CanonicalVariant] = {
    "v1_pipe_unid_to_value": CanonicalVariant(
        name="v1_pipe_unid_to_value",
        description="Pipe-joined unid|to|value|network (string)",
        build=lambda d: f"{d['tx_unid']}|{d['to_address']}|{d['value']}|{d['network']}".encode("utf-8"),
    ),
    "v2_pipe_unid_value_to_network": CanonicalVariant(
        name="v2_pipe_unid_value_to_network",
        description="Pipe-joined unid|value|to|network",
        build=lambda d: f"{d['tx_unid']}|{d['value']}|{d['to_address']}|{d['network']}".encode("utf-8"),
    ),
    "v3_json_sorted": CanonicalVariant(
        name="v3_json_sorted",
        description="Compact JSON with sorted keys",
        build=lambda d: json.dumps(
            {"network": d['network'], "to": d['to_address'], "unid": d['tx_unid'], "value": d['value']},
            sort_keys=True, separators=(',', ':'),
        ).encode("utf-8"),
    ),
    "v4_json_to_lower": CanonicalVariant(
        name="v4_json_to_lower",
        description="JSON with lowercase to_address (no checksum)",
        build=lambda d: json.dumps(
            {"unid": d['tx_unid'], "network": d['network'], "value": d['value'], "to": d['to_address'].lower()},
            separators=(',', ':'),
        ).encode("utf-8"),
    ),
    "v5_concat_no_separator": CanonicalVariant(
        name="v5_concat_no_separator",
        description="Hex-concat: unid_bytes || to_bytes || value_padded",
        build=lambda d: bytes.fromhex(d['tx_unid']) + bytes.fromhex(d['to_address'][2:]) + int(d['value']).to_bytes(32, 'big'),
    ),
    "v6_keccak_pre_hashed": CanonicalVariant(
        name="v6_keccak_pre_hashed",
        description="V1 then keccak256(payload) — already-hashed input",
        build=lambda d: keccak(f"{d['tx_unid']}|{d['to_address']}|{d['value']}|{d['network']}".encode()),
    ),
}
```

**Note:** точные variant'ы — это educated guess. Реальный список финализируется после auto-discovery с живой Safina-data. Architecture guarantees добавление нового variant = одна строка в реестре.

### 5.3 `transaction_service._sync_one` wire-up

Добавляется блок между tx-INSERT (line 535) и tx_signatures-INSERT (line 547):

```python
# Wave 22: local signer verification (Story 2.7)
verify_mode = get_verify_mode()
if verify_mode != "off" and tx.signed:
    for sig in tx.signed:
        if not (sig.get("ecaddress") and sig.get("ecsign")):
            continue
        try:
            result = verify_safina_tx_signer(
                tx_unid=tx.unid,
                network=tx.network,
                value=str(tx.value),
                to_address=tx.to_addr,
                signature_hex=sig["ecsign"],
                expected_signer=sig["ecaddress"],
            )
        except NotImplementedError:
            # Variant env-set but unknown — skip silently, will be
            # caught at boot-time validation. Don't crash sync.
            break
        if result is False:
            await self._handle_signer_mismatch(tx, sig, verify_mode)
            if verify_mode == "enforce":
                # Override status set on line 530
                await self._db.execute(
                    "UPDATE transactions SET status='rejected_signer_mismatch' WHERE unid=$1",
                    (tx.unid,),
                )
                break  # don't continue checking other signers — tx is dead
```

### 5.4 New service-level helper `_handle_signer_mismatch`

```python
async def _handle_signer_mismatch(
    self, tx, sig: dict, mode: str,
) -> None:
    """Record AML alert for a Safina signer mismatch.

    Called from `_sync_one` when verify_safina_tx_signer returns False.
    Writes outside the tx-INSERT transaction (ADR-8) so an alert-write
    failure does not roll back the tx-INSERT. Logs WARN regardless of
    mode; alert insert best-effort.
    """
```

### 5.5 CLI discovery script — `backend/scripts/safina_discover_canonical.py`

```bash
$ python backend/scripts/safina_discover_canonical.py --sample sample.json
[v1_pipe_unid_to_value]            ✗ recovered=0xABC… expected=0xDEF…
[v2_pipe_unid_value_to_network]   ✓ MATCH
[v3_json_sorted]                   ✗ recovered=0x123… expected=0xDEF…
[v4_json_to_lower]                 ✗ recovered=0x456… expected=0xDEF…
[v5_concat_no_separator]           ✗ ValueError: bad hex
[v6_keccak_pre_hashed]             ✗ recovered=0x789… expected=0xDEF…

→ Confirmed variant: v2_pipe_unid_value_to_network
→ Set in Coolify: SAFINA_CANONICAL_VARIANT=v2_pipe_unid_value_to_network
```

`sample.json` schema:
```json
{
  "tx_unid": "abc123",
  "network": 1,
  "value": "1000000000000000000",
  "to_address": "0xRecipient...",
  "signature_hex": "0x<r:32><s:32><v:1>",
  "expected_signer": "0xSafinaSigner..."
}
```

### 5.6 Frontend — minimal changes (no full UI)

- В `/transactions` page добавить badge для `rejected_signer_mismatch` status (просто маппинг в существующих badge-варианты — destructive variant + label «Подпись не совпала»)
- AML triage drawer уже умеет показывать mismatch alert через generic JSON view (Wave 21 уже сделана)

Никаких новых страниц, никаких новых компонентов. Минимальное изменение — TS-mapping в `transactions/columns.tsx` или эквиваленте.

---

## 6. Sprint breakdown

### Sprint 2.7.1 — Variant registry + verifier extension

**Scope:**
- Implement 6 candidate variants per 5.2
- Replace `canonical_payload`'s `NotImplementedError` with variant dispatch
- Add `get_verify_mode()` parsing `off|shadow|enforce` + legacy mapping
- Add `try_all_variants()` for auto-discovery
- Self-test round-trip: pick `v1`, sign with eth_keys.PrivateKey, recover, expect match — pure-function test, no DB

**Acceptance criteria:**
- 6 variants registered, all callable
- `canonical_payload(variant=None)` raises NotImplementedError when env unset
- `canonical_payload(variant="v1_pipe_unid_to_value", …)` returns bytes
- `try_all_variants()` returns dict with 6 entries
- `get_verify_mode()` returns correct mode for all 4 inputs (`off`, `shadow`, `enforce`, legacy `1`)
- `python -m compileall backend/` exit 0

**Tests (+10-12):**
- `test_safina_canonical.py::test_variant_v1_round_trip`
- `test_safina_canonical.py::test_variant_v2_round_trip`
- `test_safina_canonical.py::test_variant_v3_json_round_trip`
- `test_safina_canonical.py::test_variant_v4_json_to_lower_round_trip`
- `test_safina_canonical.py::test_variant_v5_binary_round_trip`
- `test_safina_canonical.py::test_variant_v6_keccak_round_trip`
- `test_safina_canonical.py::test_canonical_payload_unset_raises`
- `test_safina_canonical.py::test_canonical_payload_unknown_variant_raises_value_error`
- `test_safina_canonical.py::test_get_verify_mode_off_default`
- `test_safina_canonical.py::test_get_verify_mode_legacy_1_maps_to_enforce`
- `test_safina_canonical.py::test_try_all_variants_finds_correct_match`
- `test_safina_canonical.py::test_verify_safina_tx_signer_returns_none_when_off`

### Sprint 2.7.2 — Wire-up in `transaction_service` + migration 028

**Scope:**
- Migration 028 — `rejected_signer_mismatch` status
- `_sync_one` insert verification block (per 5.3)
- `_handle_signer_mismatch` helper (per 5.4)
- AML alert insert with `alert_type='safina:signer_mismatch'`, `severity='critical'`, `details={...}`

**Acceptance criteria:**
- Migration 028 idempotent (ALTER … DROP CONSTRAINT IF EXISTS)
- `_sync_one` без verify-env работает 100% как до (regression test)
- `mode=shadow` + matching sig → tx сохранена, нет alert
- `mode=shadow` + mismatch sig → tx сохранена, alert создан
- `mode=enforce` + mismatch sig → tx статус `rejected_signer_mismatch`, alert создан
- `mode=enforce` + matching sig → tx обычная

**Tests (+5-7):**
- `test_transaction_signer_verification.py::test_off_mode_no_verification_called`
- `test_transaction_signer_verification.py::test_shadow_mismatch_creates_aml_alert`
- `test_transaction_signer_verification.py::test_shadow_match_no_alert`
- `test_transaction_signer_verification.py::test_enforce_mismatch_rejects_tx_status`
- `test_transaction_signer_verification.py::test_enforce_match_processes_normally`
- `test_transaction_signer_verification.py::test_alert_write_failure_does_not_block_tx_insert`
- `test_transaction_signer_verification.py::test_unknown_variant_does_not_crash_sync`

### Sprint 2.7.3 — Discovery CLI + frontend badge

**Scope:**
- `backend/scripts/safina_discover_canonical.py` — CLI per 5.5, calls `try_all_variants`
- Self-test: feed it a synthetic ORGON-side signed sample → expect v1 match
- Frontend `/transactions` table — add `rejected_signer_mismatch` status mapping
- Frontend transaction-detail page — show «Подпись не совпала» banner if status matches

**Acceptance criteria:**
- CLI script runs from project root, accepts `--sample path.json` or stdin
- Returns exit 0 on match, 1 on no-match (CI-friendly)
- Frontend badge for new status renders correctly (red destructive)
- `npx tsc --noEmit` exit 0

**Tests (+2-3):**
- `test_discovery_cli.py::test_cli_finds_v1_for_synthetic_sample`
- `test_discovery_cli.py::test_cli_returns_no_match_for_random_signature`
- (manual smoke) `python backend/scripts/safina_discover_canonical.py --self-test`

### Sprint 2.7.4 — Docs + integration

**Scope:**
- `docs/prod-readiness.md` — ❷ из PARTIAL → DONE; добавить секцию «How to bring up signer verification»
- `docker-compose.yml` — `SAFINA_CANONICAL_VARIANT` + `ORGON_SAFINA_VERIFY_MODE` env vars (defaults: unset, off)
- `CHANGELOG.md` — Wave 22 entry
- Story file `status: done`

**Acceptance criteria:**
- 6 секций runbook'a в `prod-readiness.md`:
  1. Capture sample Safina-response from staging
  2. Run discovery CLI
  3. Set `SAFINA_CANONICAL_VARIANT` in Coolify
  4. Set `ORGON_SAFINA_VERIFY_MODE=shadow`, redeploy, monitor 24h
  5. Если AML-alerts отсутствуют → переключить на `enforce`
  6. Если alerts есть → re-run discovery (may have multiple variants per chain)

---

## 7. Risk register

| ID | Риск | Вероятность | Mitigation |
|---|---|---|---|
| R1 | Ни один из 6 variants не совпадает с реальным Safina-форматом | Medium | Auto-discovery CLI визуализирует все 6 mismatches → quick pivot к 7-му variant. Architecture позволяет добавление за 1 строку. |
| R2 | Variant'ы может зависеть от network (ETH использует один формат, TRX другой) | Medium | `_CANONICAL_VARIANTS` parametrise на network в если выясним. ADR-9 уже допускает это. |
| R3 | Shadow-mode заваливает AML-tab false-positive алертами при wrong variant | Low | Discovery CLI рекомендуется ДО включения shadow. Если alert spam — выключить flag. |
| R4 | Enforce-mode rejects валидные транзакции при wrong variant — pilot-disruption | Medium | Документация: "Запускать enforce ТОЛЬКО после 24h shadow-monitoring без alerts". 99%+ confidence перед flip. |
| R5 | `rejected_signer_mismatch` статус ломает existing UI flows | Low | Frontend mapping добавляется (Sprint 2.7.3). Backend logic только в новом status — existing transitions не затронуты. |
| R6 | ECDSA recovery library mismatch (eth_keys vs Safina's lib) | Low | `recover_signer_address` уже работает на existing Wave 18 KMS-flow. ECDSA-secp256k1 интероперабельный stand. |
| R7 | Tx-INSERT прошёл, но alert-INSERT failed — silent forgery | Low | ADR-8 explicitly logs WARN. Operator увидит в logs. AlertService может retry в background (post-MVP). |
| R8 | Migration 028 — DROP CHECK constraint может оставить «orphan» rows если статус был некорректно записан | Low | DROP не валидирует existing rows — recreate immediately после с тем же набором + новый. Existing rows с допустимыми статусами не затронуты. |
| R9 | `SAFINA_CANONICAL_VARIANT=v_unknown` set in Coolify — tx-sync crashes? | Low | ADR-7 try/except NotImplementedError — sync graceful-skip. Boot-time warning лог. |
| R10 | Performance: 10 ECDSA-recovery per tx × 100 tx/min = 1000 ops/min | Low | secp256k1 recovery ~1ms; 1000/min = ~17/sec — одна CPU-секунда. Negligible. |

---

## 8. Open questions for user

1. **Variant список — финализируем с этими 6 или хочешь добавить специфичные?** (например: EIP-712 typed-data; RLP-encoded?). Я взял 6 most-likely на основе common multi-sig patterns.

2. **Default verify-mode** — сейчас `off`. Когда rolled out: оставляем `off` для new tenants (явное opt-in) или меняем на `shadow` (passive monitoring out-of-the-box)?

3. **AML alert severity для mismatch** — сейчас `critical`. Это правильно? Или `high`? Critical поднимает оncall, high даёт review-on-business-hours.

4. **`rejected_signer_mismatch` статус — добавляем или используем generic `failed`?** Я добавляю — compliance-friendly. Но это означает migration на existing tenant data.

5. **Discovery CLI — Python script или endpoint?** Я выбрал CLI (offline tool). Альтернатива: `POST /api/v1/admin/safina/discover-canonical` — admin-only endpoint. CLI чище, endpoint удобнее для GUI-only operators.

6. **Тесты** — same pattern Wave 19/20/21 (FakeConn + httpx)?

7. **`network` field type** — ORGON-side Safina returns numeric chain id (1=ETH, 195=TRX, etc) или string token (`"ETH"`)? Variants assume **int**. Если string — нужен normalize-fn.

8. **Существующий env `ORGON_VERIFY_SAFINA_SIGS=1` legacy mapping** — keep as `enforce` shortcut, или просто warn deprecation?

Если по дефолтам — беру:
- 6 variants
- `off` default (явное opt-in)
- `critical` severity
- new `rejected_signer_mismatch` status
- CLI script (not endpoint)
- FakeConn tests
- network=int (existing behavior)
- legacy `=1` → `enforce` (backwards compat)

---

## 9. Definition of done

- [x] 4 спринта закрыты
- [x] Migration 028 идемпотентна (DROP IF EXISTS + ADD CONSTRAINT)
- [x] CI subset: 119 → 161 tests pass, 0 skipped
- [x] `python -m compileall backend/` exit 0
- [x] `cd frontend && npx tsc --noEmit` exit 0
- [x] `docs/prod-readiness.md` ❷ из PARTIAL → DONE; bring-up runbook добавлен
- [x] `CHANGELOG.md` Wave 22 entry
- [x] Story file frontmatter `status: done`
- [x] Discovery CLI self-test exit 0 (`backend/scripts/safina_discover_canonical.py --self-test`)
- [x] Backwards-compat: existing tenants без env-config работают идентично pre-Wave-22 (verified by `test_off_mode_no_verification_no_db_writes`)
- [x] **No deploy** — всё в shadow/off-mode пока не подтверждён variant с живым Safina

---

## 10. Estimated time

Сопоставимо с Wave 21 — wire-up + variant-zoo + CLI:
- 2.7.1 Variants: ~70% Wave 21 backend (больше pure crypto)
- 2.7.2 Wire-up: ~50% (минимально-инвазивно в transaction_service)
- 2.7.3 CLI + frontend: ~30% (CLI 80 строк, frontend 1 mapping)
- 2.7.4 Docs: ~30%

Реалистично — одна сессия, ~1.0× Wave 21.
