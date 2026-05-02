---
name: KMS-backed signer for Safina — Architecture & Sprint Plan
status: done (2026-05-02 — implementation merged on feature/demo-simulator)
created: 2026-05-02
completed: 2026-05-02
type: architecture-decision-record + sprint-plan
parent_story: 2.3 — Production Readiness — KMS Signer Backend
relates_to: docs/prod-readiness.md (section 5 ❶), backend/safina/signer_backends.py, CHANGELOG.md (Wave 18)
sprints_completed: [2.3.1, 2.3.2, 2.3.3]
final_test_count: 167 passed, 0 skipped (was 152)
---

# Story 2.3 — KMS-backed signer for Safina

## 1. Goal (single sentence)

Реализовать `KMSSignerBackend` так чтобы приватный EC-ключ Safina **никогда не покидал AWS KMS**, а ORGON получал только подписанный результат — закрывая главный security-блокер для institutional pilot.

## 2. Why now

**Текущее состояние** (verified 2026-05-02):
- `SAFINA_EC_PRIVATE_KEY` хранится в process memory backend-контейнера (env-backend)
- Любой RCE / contianer escape / crash-dump утекает ключ
- `KMSSignerBackend` уже **scaffolded** в `backend/safina/signer_backends.py` — Protocol готов, stub класс есть, build_signer_backend() уже умеет его создавать
- 22 unit-теста зелёные, 2 из них тестируют что stub бросает `NotImplementedError`

**Что блокирует**: эта одна нерешённая задача. После неё institutional pilot становится возможен.

---

## 3. Architecture Decision Records

### ADR-1 — AWS KMS, не Vault, для первой реализации

**Decision:** Реализуем сначала `KMSSignerBackend`. Vault-stub оставляем как есть.

**Rationale:** Пользователь явно выбрал «B» (KMS). AWS KMS — managed-сервис, нет операционного оверхеда (Vault нужно self-host'ить, обновлять, бэкапить unsealing keys). Для большинства institutional-клиентов AWS уже в стеке.

**Trade-offs:**
- ✓ Managed, no ops burden
- ✓ Hardware HSM (FIPS 140-2 L3) под капотом
- ✓ Audit log в CloudTrail из коробки
- ✗ Vendor lock на AWS (для клиентов в KZ/UZ некоторые требуют local cloud — выпустим Vault-impl потом, отдельный story)
- ✗ Latency network-call (50-200ms p99 vs ~1ms in-process)

### ADR-2 — boto3 синхронный, без aiobotocore

**Decision:** Используем `boto3` (sync). Не оборачиваем в async.

**Rationale:** Существующий `SignerBackend.sign_msg_hash` имеет sync-сигнатуру. Менять это означает переписать `EnvSignerBackend` + `SafinaSigner._eth_sign` + все callsites. Много инвазий ради чего? KMS-call блокирует ~100ms — это всё равно меньше чем full Safina round-trip (~300-800ms). FastAPI route-handlers asynс, но они уже не блокируют event-loop потому что `signer.sign_post()` синхронный — Python запустит его в default thread pool через `run_in_executor`.

**Trade-offs:**
- ✓ Минимум изменений в коде, sub-classing only
- ✓ Тесты остаются sync
- ✗ Threading-cost при высокой concurrency (но мы не в hot-loop, signer вызывается раз на Safina-call)
- ✗ Если когда-то перейдём на native async — придётся всё переделывать

### ADR-3 — Bootstrap address один раз в `__init__`, в memory cache

**Decision:** При создании `KMSSignerBackend.__init__()` мы:
1. Создаём boto3 KMS client
2. Делаем `kms.get_public_key(KeyId)` (один раз)
3. Декодируем DER pubkey → keccak256 → address
4. Кешируем `self._address` и `self._public_key_bytes` (для последующего v-recovery)

**Rationale:** Address не меняется в течение жизни процесса. KMS GetPublicKey — отдельный billed-call, нет смысла дёргать на каждую подпись. Кешируем pubkey в bytes (64 байт) для v-recovery — без него каждый sign-call делал бы лишний GetPublicKey.

**Failure mode:** Если bootstrap fails (KMS unreachable, IAM denied, KeyId не существует, DER парсится неправильно) — бросаем исключение **из `__init__`**. `build_signer_backend()` пробрасывает наверх, ORGON отказывается стартовать. Это **fail-fast** — лучше не запускать backend с silently-broken signer.

### ADR-4 — Низкоуровневые DER-операции через `cryptography.hazmat`

**Decision:**
- DER pubkey decode: `cryptography.hazmat.primitives.serialization.load_der_public_key`
- DER signature decode: `cryptography.hazmat.primitives.asymmetric.utils.decode_dss_signature`

**Rationale:** Эти модули уже косвенно установлены через `python-jose[cryptography]`. Они audited, well-tested, обрабатывают edge cases (leading zeros, ASN.1 encoding nuances) которые мы бы случайно пропустили в ручной реализации.

**Trade-off:** `cryptography` не возвращает raw 64-byte uncompressed pubkey напрямую — приходится извлекать `x` и `y` через `public_numbers()` и упаковывать вручную. Документировано в impl-секции ниже.

### ADR-5 — Low-s normalization до v-recovery

**Decision:** Если KMS вернул high-s (`s > n/2` где `n` — порядок secp256k1), нормализуем `s = n - s` **перед** попыткой recover.

**Rationale:**
1. Ethereum-tooling (включая `eth_keys`) ожидает canonical low-s по BIP-62
2. Если оставить high-s, recover может дать невалидный address и v-recovery упадёт
3. Это бесплатная нормализация — не стоит ничего и устраняет реальную ловушку

**Curve order constant:** `SECP256K1_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141`

### ADR-6 — v-recovery: пробуем 27 и 28, fail explicit если ни один не сошёлся

**Decision:**
```python
for v_candidate in (0, 1):  # eth_keys uses 0/1 internally; we add 27 in headers later
    sig = Signature(vrs=(v_candidate, r, s))
    if sig.recover_public_key_from_msg_hash(msg_hash).to_canonical_address() == self._address_bytes:
        return sig
raise RuntimeError("v-recovery failed: neither 0 nor 1 matched cached address")
```

**Rationale:** Это фундаментальный invariant. Если сломается, значит:
- `_public_key_bytes` неправильно декодирован (bug в нашем DER-парсинге)
- Или `r/s` неправильно декодированы из DER signature
- Или KMS вернул не-SECP256K1-подпись (wrong key spec)

Все три случая = критический баг. Лучше упасть с понятной ошибкой чем вернуть невалидную подпись.

### ADR-7 — Тесты через `moto[kms]`, без живых AWS-creds в CI

**Decision:** Добавляем `moto[kms]>=5.0` в test-deps. Все unit-тесты используют `@mock_aws` decorator — moto эмулирует KMS API в памяти.

**Rationale:**
- moto умеет SECP256K1 (`KeySpec=ECC_SECG_P256K1`) с real ECDSA round-trip начиная с v4.x — verified
- CI не требует AWS creds, secrets, billing
- Локальная разработка не нужна-AWS-подключение

**Risk + mitigation:** moto's SECP256K1 implementation МОЖЕТ иметь edge case differences от реального KMS. **Mitigation**: Sprint 3 включает один опциональный smoke-test против реального AWS sandbox key (если у пользователя есть AWS-account; мы не блокируем merge на отсутствие).

### ADR-8 — VaultSignerBackend stub НЕ трогаем

**Decision:** Этот ADR — про скоп. Vault-stub остаётся `raise NotImplementedError`, тесты на NotImplementedError остаются. Vault — отдельная stories в будущем.

**Rationale:** Не размывать скоп. Один backend — один merge. После KMS станет проще делать Vault (паттерн отлажен, тесты есть, можно скопировать).

---

## 4. Component diagram

```
┌──────────────────────────────────────────────────────────────────┐
│  ORGON backend container                                         │
│                                                                   │
│  routes_*.py                                                      │
│      │                                                            │
│      │  await safina_client.create_wallet(...)                   │
│      ▼                                                            │
│  SafinaClient (async wrapper)                                     │
│      │                                                            │
│      │  signer.sign_post(body) → headers dict                     │
│      ▼                                                            │
│  SafinaSigner._eth_sign(message)                                  │
│      │                                                            │
│      │  msg_hash = keccak256("\x19Ethereum Signed…" + message)    │
│      │  return self._backend.sign_msg_hash(msg_hash)              │
│      ▼                                                            │
│  KMSSignerBackend.sign_msg_hash(msg_hash)        ← NEW IMPL      │
│      │                                                            │
│      │  1. kms_client.sign(KeyId=…, Message=msg_hash,             │
│      │                     MessageType='DIGEST',                  │
│      │                     SigningAlgorithm='ECDSA_SHA_256')      │
│      │  2. decode_dss_signature(der_bytes) → (r, s)               │
│      │  3. if s > n/2: s = n - s     # low-s norm                 │
│      │  4. for v in (0, 1):                                       │
│      │       sig = Signature(vrs=(v, r, s))                       │
│      │       if sig.recover…() == self._address_bytes: return sig │
│      │  5. raise RuntimeError("v-recovery failed")                │
│      ▼                                                            │
│  eth_keys.datatypes.Signature (canonical low-s, v∈{0,1})          │
│                                                                   │
└──────────────┬───────────────────────────────────────────────────┘
               │  HTTPS, SigV4-signed
               ▼
       ┌──────────────────────┐
       │  AWS KMS (region)    │
       │  ECC_SECG_P256K1 key │
       │  (private key never  │
       │  leaves the HSM)     │
       └──────────────────────┘
```

Bootstrap (один раз при `__init__`):
```
KMSSignerBackend.__init__(key_id, region)
  │
  └─ kms.get_public_key(KeyId=key_id)
     └─ DER SubjectPublicKeyInfo
        └─ load_der_public_key(...) → EllipticCurvePublicKey
           └─ public_numbers() → (x, y) coordinates
              └─ raw_pubkey = x.to_bytes(32) + y.to_bytes(32)  # 64 bytes
                 ├─ self._public_key_bytes = raw_pubkey   # для v-recovery
                 └─ keccak256(raw_pubkey)[-20:] → checksum_address
                    └─ self._address = checksum
                    └─ self._address_bytes = bytes.fromhex(address)
```

---

## 5. Interface contracts

### 5.1 Public interface — что снаружи не меняется

```python
class KMSSignerBackend:  # implements SignerBackend Protocol
    @property
    def address(self) -> str: ...
    def sign_msg_hash(self, msg_hash: bytes) -> Signature: ...
```

То же самое что у `EnvSignerBackend`. `SafinaSigner` ничего не знает про backend — просто вызывает `.sign_msg_hash(...)`.

### 5.2 Constructor

```python
def __init__(self, key_id: str, region: str = "eu-central-1") -> None:
    """
    Args:
        key_id: KMS KeyId — ARN, Alias (`alias/...`), or KeyId UUID.
        region: AWS region where the KMS key lives.

    Raises:
        ValueError: if key_id is empty.
        botocore.exceptions.ClientError: KMS API errors propagated as-is
            (KeyNotFound, IAM denied, region misconfig, etc.).
        ValueError: if KMS returns a non-SECP256K1 key (`KeySpec` mismatch).
        ValueError: if DER pubkey can't be parsed.

    All exceptions propagate up — backend init MUST fail fast on any
    misconfiguration. ORGON should not start with a broken signer.
    """
```

### 5.3 sign_msg_hash

```python
def sign_msg_hash(self, msg_hash: bytes) -> Signature:
    """
    Args:
        msg_hash: 32-byte digest already computed by SafinaSigner
            (keccak256 of the eth-personal-sign prefixed message).

    Returns:
        eth_keys.datatypes.Signature with canonical low-s and v ∈ {0, 1}.
        SafinaSigner adds 27 to v in the final headers.

    Raises:
        ValueError: msg_hash is not exactly 32 bytes.
        botocore.exceptions.ClientError: transient KMS errors (network,
            throttling). Caller should NOT retry inside backend — let
            SafinaClient retry policy own that.
        RuntimeError: v-recovery failed (neither 0 nor 1 matched). This is
            a critical bug — likely DER parsing wrong or wrong key spec.
    """
```

### 5.4 Internal helpers (private)

```python
# Module-private — not exported. Tested through KMSSignerBackend.

_SECP256K1_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141

def _der_to_raw_pubkey(der_bytes: bytes) -> bytes:
    """DER SubjectPublicKeyInfo → 64-byte raw uncompressed (x || y)."""

def _normalize_low_s(s: int) -> int:
    """If s > n/2, return n - s; else return s. BIP-62 canonical."""

def _pubkey_to_address(raw_pubkey: bytes) -> str:
    """64-byte (x||y) → 0x-prefixed checksum-encoded Ethereum address."""
```

---

## 6. Implementation walkthrough — gnarly bits

### 6.1 DER pubkey extraction

KMS returns:
```
SubjectPublicKeyInfo SEQUENCE {
    AlgorithmIdentifier {
        algorithm OID 1.2.840.10045.2.1 (ecPublicKey)
        parameters OID 1.3.132.0.10 (secp256k1)
    }
    BIT STRING {
        04 || x (32 bytes) || y (32 bytes)   # uncompressed point, total 65 bytes
    }
}
```

Code:
```python
from cryptography.hazmat.primitives.serialization import load_der_public_key

def _der_to_raw_pubkey(der_bytes: bytes) -> bytes:
    pub = load_der_public_key(der_bytes)
    nums = pub.public_numbers()  # type: ignore[attr-defined]
    x = nums.x.to_bytes(32, "big")
    y = nums.y.to_bytes(32, "big")
    return x + y  # 64 bytes
```

Edge cases handled by `to_bytes(32, "big")`:
- Leading zero in x or y (cryptography returns int, we pad to 32)
- Big-endian normalization
- Curve mismatch — `load_der_public_key` raises if wrong curve

### 6.2 DER signature decoding

```python
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature

der_sig = response["Signature"]
r, s = decode_dss_signature(der_sig)
```

`decode_dss_signature` returns ints, handles ASN.1 encoding properly.

### 6.3 Low-s normalization

```python
def _normalize_low_s(s: int) -> int:
    return _SECP256K1_N - s if s > _SECP256K1_N // 2 else s
```

### 6.4 v-recovery

```python
from eth_keys.datatypes import Signature

# Build candidate signatures for v=0 and v=1, find the one whose
# recovered pubkey matches our cached bootstrap pubkey.
for v in (0, 1):
    sig = Signature(vrs=(v, r, s))
    recovered_pub_bytes = sig.recover_public_key_from_msg_hash(msg_hash).to_bytes()
    if recovered_pub_bytes == self._public_key_bytes:
        return sig

raise RuntimeError(
    f"v-recovery failed for KMS key {self._key_id}: neither v=0 nor v=1 "
    f"recovered the bootstrap address. Likely DER parse or key-spec mismatch."
)
```

Why we compare full pubkey not just address: address comparison is correct but pubkey comparison gives a stronger error message if there's a deep bug (caller sees what got recovered).

### 6.5 boto3 client init

```python
import boto3
from botocore.config import Config

self._kms = boto3.client(
    "kms",
    region_name=region,
    config=Config(
        retries={"max_attempts": 3, "mode": "adaptive"},
        connect_timeout=5,
        read_timeout=10,
    ),
)
```

Adaptive retries for transient throttling. 5s/10s timeouts so we don't hang the request handler indefinitely.

### 6.6 Logging

```python
logger = logging.getLogger("orgon.safina.signer_backends.kms")

# In __init__:
logger.info("KMSSignerBackend initialised: address=%s, key_id=%s",
            self._address, self._key_id)

# In sign_msg_hash:
# Do NOT log msg_hash, r, s, v, or any signature material at any level.
# Log only: KMS-call latency on warning if > 500ms.
```

---

## 7. Test strategy

### 7.1 Sprint 2 — moto-based unit tests

Add `moto[kms]>=5.0` to `backend/requirements.txt` (or separate `requirements-test.txt`).

```python
# backend/tests/test_kms_signer_backend.py

from moto import mock_aws
import boto3, pytest
from backend.safina.signer_backends import KMSSignerBackend, build_signer_backend

@pytest.fixture
def kms_test_key():
    """moto creates a real SECP256K1 keypair in-memory."""
    with mock_aws():
        client = boto3.client("kms", region_name="us-east-1")
        resp = client.create_key(
            KeySpec="ECC_SECG_P256K1",
            KeyUsage="SIGN_VERIFY",
        )
        yield resp["KeyMetadata"]["KeyId"]

def test_kms_backend_init_derives_address(kms_test_key):
    with mock_aws():
        b = KMSSignerBackend(kms_test_key, region="us-east-1")
        assert b.address.startswith("0x")
        assert len(b.address) == 42  # 0x + 40 hex chars

def test_kms_backend_sign_round_trip(kms_test_key):
    with mock_aws():
        b = KMSSignerBackend(kms_test_key, region="us-east-1")
        msg_hash = b"\x42" * 32
        sig = b.sign_msg_hash(msg_hash)
        # Verify signature recovers to backend's address
        recovered = sig.recover_public_key_from_msg_hash(msg_hash).to_checksum_address()
        assert recovered == b.address

def test_kms_backend_low_s_canonical(kms_test_key):
    """All signatures must be canonical low-s (BIP-62)."""
    with mock_aws():
        b = KMSSignerBackend(kms_test_key, region="us-east-1")
        # Sign 32 different digests — find at least one that would produce
        # high-s without normalization. We check that the returned s is
        # always <= n/2.
        n = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
        for i in range(32):
            sig = b.sign_msg_hash(bytes([i]) * 32)
            assert sig.s <= n // 2

def test_kms_backend_msg_hash_must_be_32_bytes(kms_test_key):
    with mock_aws():
        b = KMSSignerBackend(kms_test_key, region="us-east-1")
        with pytest.raises(ValueError, match="32 bytes"):
            b.sign_msg_hash(b"\x00" * 31)

def test_kms_backend_init_fails_on_missing_key():
    with mock_aws():
        with pytest.raises(Exception):  # boto3 ClientError
            KMSSignerBackend("alias/does-not-exist", region="us-east-1")

def test_kms_backend_signature_compatible_with_safina_signer(kms_test_key):
    """End-to-end: KMS-backed SafinaSigner produces valid Safina headers."""
    from backend.safina.signer import SafinaSigner
    with mock_aws():
        signer = SafinaSigner(backend=KMSSignerBackend(kms_test_key, region="us-east-1"))
        headers = signer.sign_get()
        assert headers["x-app-ec-from"] == signer.address
        assert headers["x-app-ec-sign-v"] in {"0x1b", "0x1c"}
        # self-verify
        assert signer.verify_signature(b"{}") is True
```

### 7.2 Updates to existing test_signer_backends.py

Two tests need updating:
- `test_kms_backend_raises_not_implemented` → DELETE (no longer raises)
- `test_build_kms_propagates_stub` → REWRITE: verify build_signer_backend with kms+real KeyId returns real KMSSignerBackend

```python
def test_build_kms_with_moto(monkeypatch):
    monkeypatch.setenv("ORGON_SIGNER_BACKEND", "kms")
    with mock_aws():
        client = boto3.client("kms", region_name="us-east-1")
        key = client.create_key(KeySpec="ECC_SECG_P256K1", KeyUsage="SIGN_VERIFY")
        monkeypatch.setenv("AWS_KMS_KEY_ID", key["KeyMetadata"]["KeyId"])
        monkeypatch.setenv("AWS_REGION", "us-east-1")
        backend = build_signer_backend()
        assert isinstance(backend, KMSSignerBackend)
        assert backend.address.startswith("0x")
```

### 7.3 Coverage targets

- **`KMSSignerBackend.__init__`** — 100% (success + error paths)
- **`sign_msg_hash`** — 100% (round-trip + low-s + msg_hash validation + v-recovery happy path)
- **DER helpers** — 100% (success + malformed input)
- **v-recovery failure path** — covered via mock that returns wrong pubkey deliberately

### 7.4 Sprint 3 — optional live AWS smoke test

If user provides AWS sandbox creds + sandbox KMS key:
```bash
AWS_KMS_KEY_ID=alias/orgon-sandbox \
AWS_REGION=eu-central-1 \
AWS_ACCESS_KEY_ID=... \
AWS_SECRET_ACCESS_KEY=... \
ORGON_SIGNER_BACKEND=kms \
SAFINA_STUB=1 \
.venv/bin/python -c "
from backend.safina.signer_backends import build_signer_backend
b = build_signer_backend()
print('address:', b.address)
sig = b.sign_msg_hash(b'\\x00' * 32)
print('sig:', hex(sig.r), hex(sig.s), sig.v)
"
```

Ожидаемо: address printed, signature returned. Ничего больше — это smoke, не функциональный тест.

**Если smoke не идёт** — мы НЕ блокируем merge. Production-pilot пройдёт через эту проверку всё равно.

---

## 8. Sprint breakdown

### Sprint 2.3.1 — Core implementation

**Acceptance criteria:**
- `boto3>=1.34,<2` добавлен в `backend/requirements.txt`
- `backend/safina/signer_backends.py` — `KMSSignerBackend` имплементирован per ADRs выше
- Helper функции `_der_to_raw_pubkey`, `_normalize_low_s`, `_pubkey_to_address` написаны
- `python -m compileall backend/safina/` — exit 0
- `ORGON_SIGNER_BACKEND=kms` + `AWS_KMS_KEY_ID=fake` пытается init и падает с clear KMS-error message (не silent fail)
- Никаких изменений в `signer.py` или `build_signer_backend()` selector — только новый класс наполняется

**Файлы:**
- `backend/requirements.txt` (+1 line)
- `backend/safina/signer_backends.py` (~150 lines added: helpers + class methods)

### Sprint 2.3.2 — Tests

**Acceptance criteria:**
- `moto[kms]>=5.0` добавлен в test-deps
- Новый файл `backend/tests/test_kms_signer_backend.py` с 7+ тестами:
  - init_derives_address
  - sign_round_trip
  - low_s_canonical (32 iterations)
  - msg_hash_validation (must be 32 bytes)
  - init_fails_on_missing_key
  - signature_compatible_with_safina_signer (end-to-end)
  - v_recovery_explicit_failure (mock-based: force pubkey mismatch)
- Существующие 2 теста в `test_signer_backends.py` обновлены (NotImplementedError → real impl)
- `pytest backend/tests/ -v` — 100% pass, **152+7 = 159 tests**, 0 skipped

**Файлы:**
- `backend/requirements.txt` (or test-requirements.txt) — +1 line
- `backend/tests/test_kms_signer_backend.py` (new, ~120 lines)
- `backend/tests/test_signer_backends.py` — 2 line edits (delete + rewrite tests)

### Sprint 2.3.3 — Integration + docs

**Acceptance criteria:**
- `docs/prod-readiness.md` секция 5 ❶ обновлена: переведена с TODO на DONE, добавлены конкретные Coolify-env vars (`AWS_KMS_KEY_ID`, `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`)
- `docker-compose.yml` — комментарий-подсказка над `ORGON_SIGNER_BACKEND` про доступные значения и какие env vars нужны для каждого
- `CHANGELOG.md` — секция Wave/Sprint **Wave 18** (next available) описывает что сделано
- Опционально: smoke-test против реального AWS KMS sandbox key (если у пользователя есть доступ)
- PR description содержит:
  - Summary
  - Перед/после security comparison
  - How to test (с moto)
  - How to deploy на pilot (последовательность Coolify env-vars)

**Файлы:**
- `docs/prod-readiness.md` — обновление
- `docker-compose.yml` — добавить block с KMS-env-vars (закомментированный — клиент раскомментирует)
- `CHANGELOG.md` — новый sprint entry
- (No PR yet — мы на feature/demo-simulator branch, доделываем к PR на main позже)

---

## 9. Risk register

| ID | Риск | Вероятность | Mitigation |
|---|---|---|---|
| R1 | moto's SECP256K1 имплементация имеет edge cases отличные от реального KMS | Medium | Smoke-test против реального AWS sandbox в Sprint 3. Не блокирует merge но даёт сигнал до prod. |
| R2 | DER pubkey decoding падает на некоторых KMS-возвращаемых форматах (leading-zero coordinates, etc.) | Low | `cryptography.load_der_public_key` хорошо тестирован upstream. Наша обёртка `_der_to_raw_pubkey` использует `to_bytes(32, "big")` который правильно padding-ует. |
| R3 | v-recovery: оба candidate (v=0, v=1) дают неправильный pubkey | Low (если только bug) | Explicit `RuntimeError` с диагностической информацией. CI ловит через `test_kms_backend_sign_round_trip` на 32 разных digest'ах. |
| R4 | Low-s normalization меняет valid sig на invalid (двойная нормализация) | Very low | Применяется один раз в `sign_msg_hash`. Тест `test_kms_backend_low_s_canonical` проверяет на 32 итерациях что s ВСЕГДА <= n/2. |
| R5 | boto3 image bloat (~30MB добавляется к backend image) | Low | Acceptable. Backend image сейчас ~600MB (Python 3.12 + FastAPI + asyncpg + cryptography). +5% не критично. |
| R6 | KMS rate limits в проде (5000 req/sec hard cap) | Very low | Наш use-case: max ~10 sign-ops/sec в пиках на одного клиента. Запас x500. |
| R7 | AWS creds в Coolify env могут утечь через Coolify-API leak | Medium | Mitigation в самой архитектуре: KMS sign-permission ограничен **только этим one KeyId** через IAM policy. Утечка creds = доступ к sign только. Невозможно exfiltrate private key (это вся суть KMS). |
| R8 | Latency overhead 100-200ms на каждый Safina-call | Low | Acceptable для institutional use case. Для retail — too slow, но retail у нас не таргет на 2026. |
| R9 | KMS region-eviction (e.g. `eu-central-1` outage) | Very low | Документировано в section 7.3 prod-readiness.md (DR procedures). Multi-region replication — отдельный story. |
| R10 | Pilot-клиент даёт KMS KeyId но не SECP256K1 (например ECC_NIST_P256) | Low | Bootstrap fail-fast — при `__init__` `decode_dss_signature` или `load_der_public_key` либо падает либо возвращает not-secp256k1 pubkey. Можно добавить explicit `KeySpec` check через `kms.describe_key()` если это reasonably expected. |

---

## 10. Open questions for user

Эти решения нужно зафиксировать **до** начала implementation:

1. **AWS account**: уже есть прод-AWS-account для ASYSTEM? Нам нужен только для unit-тестов (через moto) и опционального smoke-теста. Если account существует и у тебя есть IAM permission создать sandbox KMS key — используем для smoke. Если нет — пропускаем smoke, merge'имся на moto-tests only.

2. **Region preference**: я ставил default `eu-central-1` (Frankfurt — EU data residency). Большинство наших клиентов CIS/EAEU. Менять на `eu-north-1` (Stockholm) или `us-east-1` (cheaper)? Default остаётся настраиваемым через env var, поэтому это лишь default value в коде.

3. **moto vs real-AWS strategy в CI**: я предлагаю **moto** для unit-tests + опциональный smoke-test против реального AWS вручную перед каждым pilot-deploy. Альтернатива: mark live-test как `@pytest.mark.live_aws` и запускать только когда AWS_LIVE_TEST=1 в env. Какой предпочитаешь?

4. **Failure mode на init**: я выбрал **fail-fast** (если bootstrap address не получается, ORGON отказывается стартовать). Альтернатива: silent fallback на stub-mode (как сейчас при отсутствии EC key). Fail-fast — мой recommendation для prod-pilot. Confirmation?

5. **Когда ставить `ORGON_SIGNER_BACKEND=kms` на текущей prod-инсталляции (`orgon.asystem.ai`)?** Никогда — это shared test environment, тут env-key достаточно. KMS включается только на per-client pilot. Confirmation?

6. **Smoke test with real AWS** в Sprint 3: нужен ли? Если да — давай AWS access key + sandbox KMS Key Id, я прогоню один скрипт. Если нет — пропускаем, тесты на moto-only.

---

## 11. Definition of done — для всей stories 2.3

- [ ] Все 3 sprint'а выполнены, каждый со своими AC
- [ ] `python -m pytest backend/tests/ -v` — 159+ tests pass, 0 skipped, 0 failed
- [ ] `python -m compileall backend/` — exit 0
- [ ] `cd frontend && npx tsc --noEmit` — exit 0 (если случайно тронули — нет, не тронем)
- [ ] `docs/prod-readiness.md` обновлён, section 5 ❶ переведена в DONE
- [ ] `CHANGELOG.md` новая секция Wave 18
- [ ] Story file (этот) обновлён со статусом `done` в frontmatter
- [ ] Коммит на feature branch, push, PR description написан, **НЕ merge на main без явного одобрения**

---

## 12. Estimated execution time

С учётом BMAD-style decomposition + careful tests + smoke + docs:

- Sprint 2.3.1 (impl): несколько часов
- Sprint 2.3.2 (tests): несколько часов
- Sprint 2.3.3 (docs/integration): час

Realistic полный цикл = **одна рабочая сессия** при условии что moto работает с SECP256K1 без сюрпризов. Если smoke-test покажет проблему — добавляем итерацию debug.

---

## 13. Что мне нужно от тебя ДО старта

Минимум:
- ✓/✗ approval этого плана как написан
- Ответы на open questions 1-6 (либо «по дефолту, я не специалист — решай сам»)

Идеально (необязательно):
- AWS sandbox creds + KMS key для Sprint 3 smoke-test

После approval — запускаю Sprint 2.3.1, дальше по плану. Между sprint'ами буду фиксировать `tsc/lint/test` чек-поинты чтобы не было дрейфа.
