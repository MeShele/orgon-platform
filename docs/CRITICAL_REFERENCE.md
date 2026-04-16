# Критическая Справка: Safina Pay API

**⚠️ ВАЖНО: Читать ПЕРЕД началом работы с Safina API**

---

## 🔴 Критические Ошибки (вызывают падение подписи)

### 1. Decimal Separator — ЗАПЯТАЯ, НЕ ТОЧКА

```python
# ❌ НЕПРАВИЛЬНО — вызовет ошибку подписи
{
  "value": "10.5"  # Точка!
}

# ✅ ПРАВИЛЬНО
{
  "value": "10,5"  # Запятая!
}
```

**Почему:** Safina использует запятую как десятичный разделитель во всех числовых полях.

**Решение:**
```python
def to_safina_decimal(value: str) -> str:
    """Convert decimal point to comma for Safina."""
    return value.replace(".", ",")

# Использование
safina_value = to_safina_decimal("10.5")  # "10,5"
```

---

### 2. JSON Formatting — БЕЗ ПРОБЕЛОВ

```python
# ❌ НЕПРАВИЛЬНО — вызовет ошибку подписи
data = json.dumps({"network": "5010", "info": "Test"})
# Результат: '{"network": "5010", "info": "Test"}'  # Пробелы после ":"

# ✅ ПРАВИЛЬНО
data = json.dumps(
    {"network": "5010", "info": "Test"},
    separators=(",", ":"),
    ensure_ascii=False
)
# Результат: '{"network":"5010","info":"Test"}'  # Без пробелов
```

**Почему:** Подпись вычисляется на точной строке JSON. Любой пробел изменит подпись.

---

### 3. Token Format — ПОЛНЫЙ ФОРМАТ

```python
# ❌ НЕПРАВИЛЬНО
token = "TRX"  # Не полный формат

# ✅ ПРАВИЛЬНО
token = "5010:::TRX###945C6F4C54B3921F4625890300235114"
#        network:::TOKEN###wallet_name
```

**Формат:** `{network_id}:::{token_symbol}###{wallet_name}`

**Пример формирования:**
```python
def format_token(network_id: str, token_symbol: str, wallet_name: str) -> str:
    """Format token for Safina API."""
    return f"{network_id}:::{token_symbol}###{wallet_name}"

# Использование
token = format_token("5010", "TRX", "945C6F4C54B3921F4625890300235114")
# "5010:::TRX###945C6F4C54B3921F4625890300235114"
```

---

### 4. Signature Headers — ВСЕ С ПРЕФИКСОМ 0x

```python
# ✅ ПРАВИЛЬНО
headers = {
    "x-app-ec-from": "0xA285990a1Ce696d770d578Cf4473d80e0228DF95",  # 0x prefix
    "x-app-ec-sign-r": "0xdb07295a5f780159d51c4872a104e6e486428942db38ea3b7d91433c38658c0b",
    "x-app-ec-sign-s": "0x3a64d736044d63cff3713b85aa2a2fad902c080c2b64acfcdbee7ce9e20cae0e",
    "x-app-ec-sign-v": "0x1b"  # 0x1b (27) или 0x1c (28)
}
```

**v component:** Должен быть 0x1b (27) или 0x1c (28), НЕ 0/1!

```python
# Конвертация v
v_ethereum = signature.v  # 0 или 1
v_safina = hex(v_ethereum + 27)  # "0x1b" или "0x1c"
```

---

### 5. GET vs POST Signing

```python
# GET requests — подписывать "{}"
if method == "GET":
    message = b"{}"
    signature = sign_message(message)

# POST requests — подписывать compact JSON body
if method == "POST":
    message = json.dumps(body, separators=(",", ":"), ensure_ascii=False).encode()
    signature = sign_message(message)
```

---

## ⚠️ Частые Ошибки

### Ошибка: "Ошибка подписи"

**Причины:**
1. JSON с пробелами
2. Decimal separator — точка вместо запятой
3. Подписан неправильный payload
4. v component неправильный (не 0x1b/0x1c)

**Решение:**
```python
# Проверить payload
print(repr(message))  # Должно быть без пробелов

# Проверить decimal
assert "." not in body.get("value", ""), "Use comma, not period!"

# Проверить v
assert signature_v in ["0x1b", "0x1c"], f"Invalid v: {signature_v}"
```

---

### Ошибка: "Недостаточно средств"

**Причина:** Баланс < сумма транзакции

**Решение:**
```python
# Всегда проверять баланс ПЕРЕД отправкой
tokens = await client.get_wallet_tokens(wallet_name)
token_balance = next(t for t in tokens if t.token == token_symbol)

amount_decimal = Decimal(amount.replace(",", "."))
balance_decimal = token_balance.value_decimal

if amount_decimal > balance_decimal:
    raise ValueError(f"Insufficient balance: {balance_decimal} < {amount_decimal}")
```

---

### Ошибка: Transaction "tx": null долгое время

**Причина:** Ожидание подписей (multi-sig wallet)

**Решение:**
```python
# Проверить статус подписей
signatures = await client.get_tx_signatures_all(tx_unid)

waiting = [s for s in signatures if "wait" in s]
signed = [s for s in signatures if "signed" in s]

print(f"Progress: {len(signed)}/{len(signed) + len(waiting)}")

if waiting:
    print(f"Waiting for: {[s['wait']['ecaddress'] for s in waiting]}")
```

---

## 📋 Cheat Sheet

### Создание Single-Sig Wallet
```python
unid = await client.create_wallet(
    network="5010",
    info="My Wallet"
    # slist отсутствует → single-sig
)
```

### Создание Multi-Sig Wallet (2/3)
```python
unid = await client.create_wallet(
    network="5010",
    info="Treasury",
    slist={
        "min_signs": "2",  # нужно минимум 2 подписи
        "0": {"type": "all", "ecaddress": "0xAAA..."},
        "1": {"type": "all", "ecaddress": "0xBBB..."},
        "2": {"type": "all", "ecaddress": "0xCCC..."}
    }
)
```

### Отправка Транзакции
```python
# 1. Проверить баланс
tokens = await client.get_wallet_tokens(wallet_name)

# 2. Сформировать token
token_full = f"{network_id}:::{token_symbol}###{wallet_name}"

# 3. Конвертировать value
value_safina = amount.replace(".", ",")

# 4. Отправить
tx_unid = await client.send_transaction(
    token=token_full,
    to_address="TRx6xXChS5sXz3mpvLSNfKuL6w3PBdMZzL",
    value=value_safina,
    info="Payment description"
)
```

### Утверждение Транзакции
```python
# Получить ожидающие подписи
pending = await client.get_pending_signatures()

# Утвердить
await client.sign_transaction(tx_unid)

# Или отклонить
await client.reject_transaction(tx_unid, reason="Invalid amount")
```

### Проверка Статуса
```python
# Получить транзакцию
transactions = await client.get_transactions()
tx = next(t for t in transactions if t.unid == tx_unid)

if tx.tx is None:
    print("Pending (not yet broadcast)")
    # Проверить подписи
    sigs = await client.get_tx_signatures_all(tx_unid)
else:
    print(f"Broadcast: {tx.tx}")
```

---

## 🔧 Debugging

### Включить Логи
```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("orgon.safina")
logger.setLevel(logging.DEBUG)
```

### Проверить Подпись
```python
from backend.safina.signer import SafinaSigner

signer = SafinaSigner(private_key_hex)

# Проверить GET
message = b"{}"
assert signer.verify_signature(message)

# Проверить POST
message = json.dumps(data, separators=(",", ":")).encode()
assert signer.verify_signature(message)
```

### Проверить Формат JSON
```python
body = {"network": "5010", "value": "10,5"}

# Должно быть БЕЗ пробелов
compact = json.dumps(body, separators=(",", ":"), ensure_ascii=False)
assert " " not in compact, f"JSON has spaces: {repr(compact)}"

# Должна быть запятая
assert "," in body["value"], "Value must use comma separator"
```

---

## 📚 Quick Links

**API Base URL:**
```
https://my.safina.pro/ece/
```

**Networks:**
- 1000 — Bitcoin (BTC)
- 3000 — Ethereum (ETH)
- 5000 — Tron (TRX)
- 5010 — Tron Nile TestNet (TRX) ← **используем для разработки**

**Common Tokens:**
- BTC — Bitcoin
- ETH — Ethereum
- TRX — Tron
- USDT — Tether USD (токен на всех сетях)

**Token IDs (для H2K Pay виджета):**
- 59 — USDT на Tron Nile TestNet
- 47 — USDT на Tron Mainnet

---

## 🆘 Если Ничего Не Работает

1. **Проверить подпись:**
   ```python
   # Вывести payload и подпись
   print(f"Message: {repr(message)}")
   print(f"Headers: {headers}")
   ```

2. **Проверить decimal separator:**
   ```python
   # Должна быть запятая
   assert "," in value and "." not in value
   ```

3. **Проверить token format:**
   ```python
   # Должен быть полный формат
   assert ":::" in token and "###" in token
   ```

4. **Проверить JSON compact:**
   ```python
   # Не должно быть пробелов
   assert " " not in json_string
   ```

5. **Проверить v component:**
   ```python
   # Должен быть 0x1b или 0x1c
   assert headers["x-app-ec-sign-v"] in ["0x1b", "0x1c"]
   ```

6. **Проверить network connectivity:**
   ```python
   # Простой health check
   healthy = await client.check_health()
   assert healthy, "Safina API unavailable"
   ```

---

## 📞 Support

**Safina API Issues:**
- Проверить [документацию](./safina.html)
- Проверить [примеры](./Examples.html)

**ORGON Implementation Issues:**
- Проверить [GOTCHA Plan](./GOTCHA_API_IMPLEMENTATION_PLAN.md)
- Проверить [Visual Guide](./API_IMPLEMENTATION_VISUAL.md)

**ASAGENT Issues:**
- Проверить `/Users/macbook/AGENT/CLAUDE.md`
- Проверить `/Users/macbook/AGENT/asagent/` документацию

---

**Последнее обновление:** 2026-02-05
**Версия:** 1.0.0
