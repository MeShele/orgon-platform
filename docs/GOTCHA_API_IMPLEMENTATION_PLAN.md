# GOTCHA Framework: План Полного Внедрения Safina Pay API

**Дата создания:** 2026-02-05
**Проект:** ORGON Wallet Management Dashboard
**API:** Safina Pay (https://my.safina.pro/ece/)
**Фреймворк:** GOTCHA (Goals, Orchestration, Tools, Context, Hardprompts, Args, Experts)

---

## Содержание

1. [Текущий Статус](#текущий-статус)
2. [Слой 1: GOALS — Цели](#слой-1-goals--цели)
3. [Слой 2: ORCHESTRATION — Оркестрация](#слой-2-orchestration--оркестрация)
4. [Слой 3: TOOLS — Инструменты](#слой-3-tools--инструменты)
5. [Слой 4: CONTEXT — Контекст](#слой-4-context--контекст)
6. [Слой 5: HARDPROMPTS — Шаблоны](#слой-5-hardprompts--шаблоны)
7. [Слой 6: ARGS — Аргументы](#слой-6-args--аргументы)
8. [Слой 7: EXPERTS — Эксперты](#слой-7-experts--эксперты)
9. [План Реализации](#план-реализации)
10. [Критерии Приемки](#критерии-приемки)

---

## Текущий Статус

### ✅ Уже Реализовано

**Backend Components:**
- ✅ `backend/safina/signer.py` — EC SECP256k1 подписание (eth_keys)
- ✅ `backend/safina/client.py` — Async HTTP клиент с retry logic
- ✅ `backend/safina/models.py` — Pydantic модели для всех API endpoints
- ✅ `backend/safina/errors.py` — Типизированные исключения

**Реализованные API Methods в Client:**
- ✅ Networks: `get_networks(status)`
- ✅ Wallets: `get_wallets()`, `get_wallet(name)`, `get_wallet_by_unid(unid)`, `create_wallet()`
- ✅ Tokens: `get_tokens()`, `get_wallet_tokens()`, `get_tokens_info()`, `get_user_tokens()`
- ✅ Transactions: `get_transactions()`, `get_token_transactions()`, `send_transaction()`
- ✅ Signatures: `sign_transaction()`, `reject_transaction()`, `get_tx_signatures_*()`, `get_pending_signatures()`

**REST API Endpoints:**
- ✅ `/api/wallets` — CRUD для кошельков
- ✅ `/api/dashboard/stats` — статистика
- ⚠️ Transactions endpoints — частично

### ❌ Требует Реализации

1. **Frontend Components:**
   - ❌ Компоненты для транзакций
   - ❌ UI для мультиподписей
   - ❌ Визуализация ожидающих подписей

2. **Service Layer:**
   - ⚠️ TransactionService — базовая реализация есть, нужны улучшения
   - ❌ SignatureService — для управления мультиподписями
   - ❌ NetworkService — кеширование справочников

3. **REST API Endpoints:**
   - ❌ `/api/transactions/*` — полный CRUD
   - ❌ `/api/signatures/*` — управление подписями
   - ❌ `/api/networks` — справочник сетей и токенов

4. **Integration:**
   - ❌ Telegram уведомления для ожидающих подписей
   - ❌ ASAGENT интеграция для автономных операций
   - ❌ Vault интеграция для безопасного хранения приватных ключей

---

## Слой 1: GOALS — Цели

### Goal 1: Полная Интеграция API Методов

**Файл:** `/Users/macbook/AGENT/goals/orgon_api_integration.md`

```markdown
# Goal: Полная Интеграция Safina Pay API

## Objective
Внедрить все 19 методов Safina Pay API в систему ORGON с полным покрытием:
Backend Service → REST API → Frontend UI → Интеграции (Telegram, ASAGENT, Vault)

## Inputs
- Документация API: `/Users/macbook/AGENT/ORGON/docs/safina.html`
- Примеры кода: `/Users/macbook/AGENT/ORGON/docs/Examples.html`
- Текущая реализация: `backend/safina/client.py`

## Process

### Phase 1: Networks & Reference Data
1. Создать NetworkService для кеширования справочников
2. Реализовать `/api/networks` endpoints
3. Frontend компоненты для отображения сетей и токенов

### Phase 2: Transaction Management
1. Улучшить TransactionService
2. Реализовать `/api/transactions/*` endpoints
3. Frontend: компоненты для отправки и списка транзакций

### Phase 3: Multi-Signature Support
1. Создать SignatureService
2. Реализовать `/api/signatures/*` endpoints
3. Frontend: UI для ожидающих подписей и утверждения

### Phase 4: Integrations
1. Telegram notifications для pending signatures
2. ASAGENT автономное утверждение транзакций
3. Vault безопасное хранение ключей подписи

## Expected Outputs
- Все 19 API методов доступны через REST API
- Frontend покрывает все операции
- Интеграции работают автономно

## Edge Cases
- Обработка ошибок подписи
- Rate limiting на Safina API
- Decimal separator (запятая vs точка)
- Token format: `network:::TOKEN###wallet_name`
```

---

### Goal 2: Service Layer Architecture

**Файл:** `/Users/macbook/AGENT/goals/orgon_service_layer.md`

```markdown
# Goal: Unified Service Layer

## Objective
Создать единообразный слой сервисов для всех доменных операций

## Services to Implement

### 1. NetworkService
- Кеширование `get_networks()` и `get_tokens_info()`
- TTL: 1 час для справочников
- Обновление по расписанию

### 2. TransactionService
- Send/list/get transactions
- Валидация формата value (comma decimal)
- Конвертация token format

### 3. SignatureService
- Pending signatures список
- Sign/reject transactions
- Уведомления при новых ожидающих подписях

### 4. WalletService (уже существует)
- Расширить функционал для multi-sig wallets

## Tools to Use
- `backend/database/db.py` для кеша
- `backend/safina/client.py` как основной клиент
- `backend/integrations/telegram_notifier.py` для уведомлений

## Success Criteria
- DRY: нет дублирования логики
- Single Responsibility: каждый сервис делает одно
- Testable: легко покрывается unit тестами
```

---

### Goal 3: Frontend Integration

**Файл:** `/Users/macbook/AGENT/goals/orgon_frontend_ui.md`

```markdown
# Goal: Complete Frontend UI for All API Operations

## Objective
Полное покрытие UI для всех операций Safina API

## Components to Build

### 1. Transaction Components
- TransactionList — список всех транзакций
- TransactionForm — форма отправки
- TransactionDetail — детали с signatures
- TransactionFilters — фильтры по токенам/датам

### 2. Signature Components
- PendingSignaturesList — ожидающие подписи
- SignatureApprovalModal — модальное окно утверждения
- SignatureStatusBadge — статус подписей

### 3. Network/Token Components
- NetworkSelector — выбор сети
- TokenSelector — выбор токена с балансом
- TokenInfo — информация о комиссиях

### 4. Multi-Sig Components
- MultiSigSetup — настройка при создании кошелька
- SignerList — список подписантов
- SignatureProgress — прогресс подписания (2/3)

## Design Principles
- Все компоненты темные (dark mode by default)
- Tooltips для всех полей
- Loading states для async операций
- Error boundaries
```

---

## Слой 2: ORCHESTRATION — Оркестрация

### Workflow Manager

**Роль AI Manager:**

1. **При создании транзакции:**
   ```
   1. Читать goal: orgon_api_integration.md
   2. Вызвать TransactionService.send_transaction()
   3. Если multi-sig → уведомить через Telegram
   4. Обновить UI через WebSocket
   ```

2. **При утверждении подписи:**
   ```
   1. Проверить права пользователя
   2. Вызвать SignatureService.sign_transaction()
   3. Если все подписи собраны → финальная отправка
   4. Уведомить инициатора
   ```

3. **При ошибке API:**
   ```
   1. Проверить тип ошибки (auth/network/validation)
   2. Если auth → проверить подпись
   3. Если network → retry с backoff
   4. Если validation → показать пользователю
   ```

### Error Handling Strategy

```python
# Deterministic error handling в tools
try:
    result = await safina_client.send_transaction(...)
except SafinaAuthError:
    # Проблема с подписью - исправить signer
    raise HTTPException(401, "Invalid signature")
except SafinaNetworkError:
    # Сетевая проблема - retry автоматически
    raise HTTPException(502, "Safina API unavailable")
except SafinaError as e:
    # Бизнес-ошибка - показать пользователю
    raise HTTPException(400, str(e))
```

---

## Слой 3: TOOLS — Инструменты

### Существующие Tools

**Путь:** `/Users/macbook/AGENT/tools/`

#### 1. Safina Client Tool
**Файл:** Использует напрямую `backend/safina/client.py`

**Функции:**
- Все 19 API методов как async функции
- Retry logic встроен
- Type-safe через Pydantic

#### 2. Database Tool
**Файл:** `backend/database/db.py`

**Функции:**
- Кеширование справочников
- Хранение локальных меток кошельков
- История синхронизации

### Новые Tools (требуется создать)

#### 3. Transaction Validator Tool
**Файл:** `/Users/macbook/AGENT/tools/safina/validate_transaction.py`

```python
"""
Transaction validation tool.

Validates:
- Token format: network:::TOKEN###wallet_name
- Value format: decimal with comma separator
- Address format per network
- Sufficient balance
"""

def validate_transaction(
    token: str,
    to_address: str,
    value: str,
    from_wallet: str,
) -> dict:
    """Returns {valid: bool, errors: list[str]}"""
    # Deterministic validation logic
    pass
```

#### 4. Signature Orchestrator Tool
**Файл:** `/Users/macbook/AGENT/tools/safina/signature_orchestrator.py`

```python
"""
Multi-signature orchestration tool.

Manages:
- Tracking pending signatures
- Notifying signers
- Auto-approval for trusted sources
- Signature collection status
"""

async def orchestrate_signatures(tx_unid: str) -> dict:
    """Returns {status: str, progress: str, next_signers: list}"""
    pass
```

#### 5. Network Cache Tool
**Файл:** `/Users/macbook/AGENT/tools/safina/network_cache.py`

```python
"""
Network and token reference cache.

Features:
- 1-hour TTL cache
- Background refresh
- Fallback to stale data if API down
"""

async def get_cached_networks() -> list[Network]:
    pass

async def get_cached_tokens_info() -> list[TokenInfo]:
    pass
```

### Tools Manifest Update

**Файл:** `/Users/macbook/AGENT/tools/manifest.md`

Добавить:
```markdown
## Safina API Tools

### safina/client
Async HTTP client для Safina Pay API с EC подписями (используется напрямую)

### safina/validate_transaction
Валидация транзакций перед отправкой (формат, баланс, адрес)

### safina/signature_orchestrator
Управление мультиподписями и уведомлениями подписантов

### safina/network_cache
Кеширование справочников сетей и токенов с TTL 1 час
```

---

## Слой 4: CONTEXT — Контекст

### Структура Контекста

**Директория:** `/Users/macbook/AGENT/ORGON/context/`

#### 1. API Reference
**Файл:** `context/safina_api_reference.md`

```markdown
# Safina Pay API Reference

## Base URL
https://my.safina.pro/ece/

## Authentication
EC SECP256k1 signatures в headers:
- x-app-ec-from: публичный адрес (0x...)
- x-app-ec-sign-r: R component (0x...)
- x-app-ec-sign-s: S component (0x...)
- x-app-ec-sign-v: V component (0x1b или 0x1c)

## Data Formats

### Token Format
`network:::TOKEN###wallet_name`
Example: `5010:::TRX###945C6F4C54B3921F4625890300235114`

### Value Format
⚠️ КРИТИЧНО: Safina использует ЗАПЯТУЮ как decimal separator!
- Правильно: "1,005" (one point zero zero five)
- Неправильно: "1.005" (вызовет ошибку подписи)

### Signing
- GET: подписывать `{}`
- POST: подписывать compact JSON (no whitespace)
```

#### 2. Common Patterns
**Файл:** `context/safina_patterns.md`

```markdown
# Safina API Patterns

## Pattern 1: Creating Standard Wallet
```python
unid = await client.create_wallet(
    network="5010",  # Tron Nile Testnet
    info="My Test Wallet"
)
# slist отсутствует → single-sig wallet
```

## Pattern 2: Creating Multi-Sig Wallet
```python
unid = await client.create_wallet(
    network="5010",
    info="Multi-Sig Treasury",
    slist={
        "min_signs": "2",
        "0": {"type": "all", "ecaddress": "0xAAA..."},
        "1": {"type": "any", "email": "user@example.com", "sms": "+1234567890"},
        "2": {"type": "all", "ecaddress": "0xBBB..."}
    }
)
```

## Pattern 3: Sending Transaction
```python
# 1. Validate balance
tokens = await client.get_wallet_tokens(wallet_name)
# 2. Format value with comma
value_safina = "10,5"  # NOT "10.5"!
# 3. Send
tx_unid = await client.send_transaction(
    token="5010:::TRX###" + wallet_name,
    to_address="TRx6xXChS5sXz3mpvLSNfKuL6w3PBdMZzL",
    value=value_safina,
    info="Payment for order #123"
)
```
```

#### 3. Error Scenarios
**Файл:** `context/safina_error_scenarios.md`

```markdown
# Safina API Error Scenarios

## Signature Errors
```json
{"ERROR": "Ошибка подписи", "LINE": "125"}
```
**Причины:**
- Неправильный формат JSON (есть пробелы)
- Decimal separator: точка вместо запятой
- Подписан не тот payload

**Решение:**
- Использовать `json.dumps(data, separators=(",", ":"))`
- Конвертировать "." → ","
- Проверить signer.address совпадает с x-app-ec-from

## Network Errors
**Причины:**
- Safina API недоступен
- Timeout

**Решение:**
- Retry с exponential backoff (встроено в client)
- Max 3 retries

## Business Errors
```json
{"ERROR": "Недостаточно средств"}
```
**Решение:**
- Показать пользователю
- Предложить пополнить баланс
```

---

## Слой 5: HARDPROMPTS — Шаблоны

### Hardprompt Templates

**Директория:** `/Users/macbook/AGENT/hardprompts/safina/`

#### 1. Transaction Creation Prompt
**Файл:** `hardprompts/safina/create_transaction.md`

```markdown
# Template: Create Transaction

## Role
You are a transaction creation assistant for ORGON Wallet.

## Task
Help user send cryptocurrency using Safina Pay API.

## Steps
1. Verify wallet has sufficient balance
2. Validate destination address format
3. Convert decimal point to comma for value
4. Confirm transaction details with user
5. Execute transaction
6. Return tx_unid for tracking

## Critical Rules
- ALWAYS use comma "," as decimal separator (Safina requirement)
- NEVER send without user confirmation
- ALWAYS check balance first
- Token format: `network:::TOKEN###wallet_name`

## Example Interaction
User: "Send 10.5 TRX to TRx6xXChS5sXz3mpvLSNfKuL6w3PBdMZzL"

Assistant steps:
1. Check balance: "You have 154,254 TRX. Proceeding..."
2. Convert: 10.5 → "10,5"
3. Confirm: "Sending 10,5 TRX to TRx6xX...MZzL. Confirm?"
4. Send: await client.send_transaction(...)
5. Result: "Transaction created. ID: FA581E..."
```

#### 2. Signature Approval Prompt
**Файл:** `hardprompts/safina/approve_signature.md`

```markdown
# Template: Approve Multi-Sig Transaction

## Role
You are a signature approval assistant for multi-sig wallets.

## Task
Help user review and approve pending transactions.

## Steps
1. Fetch pending signatures for user
2. Display transaction details (amount, recipient, initiator)
3. Show current signature status (e.g., "2/3 signed")
4. Get user decision (approve/reject/defer)
5. Execute signature
6. Notify if transaction now complete

## Safety Checks
- ALWAYS show full transaction details before approval
- NEVER auto-approve without user consent (unless ASAGENT automation enabled)
- Show who already signed
- Highlight unusual patterns (large amounts, new recipients)

## Example
Transaction: FA581E...
- From: Multi-Sig Treasury (min 2/3 signatures)
- To: TRx6xX...MZzL
- Amount: 1000,0 USDT
- Info: "Monthly contractor payment"
- Status: 1/3 signed (0xAAA... approved)

Your decision? [Approve / Reject / View Details]
```

---

## Слой 6: ARGS — Аргументы

### Configuration Files

**Директория:** `/Users/macbook/AGENT/args/`

#### 1. Safina Behavior Args
**Файл:** `args/safina_behavior.yaml`

```yaml
# Safina API Behavior Configuration

safina:
  # API Settings
  base_url: "https://my.safina.pro/ece"
  timeout: 30
  max_retries: 3
  retry_backoff: 1.5

  # Cache Settings
  cache_ttl_networks: 3600  # 1 hour
  cache_ttl_tokens: 3600

  # Signature Settings
  signature_timeout_alert: 3600  # Alert if signature pending > 1h
  auto_approve_enabled: false  # ASAGENT auto-approval
  auto_approve_max_amount: "100,0"  # Max auto-approve amount

  # Decimal Settings
  decimal_separator: ","  # Safina requirement
  decimal_precision: 6

  # Notification Settings
  notify_telegram_on_pending: true
  notify_telegram_on_complete: true
  notify_email_on_large_tx: true
  large_tx_threshold: "10000,0"

  # Network Defaults
  default_network: "5010"  # Tron Nile Testnet
  default_token: "TRX"

  # UI Settings
  transactions_per_page: 20
  refresh_interval_ms: 30000  # 30s
```

#### 2. Safina Private Key Args
**Файл:** `args/safina_keys.yaml` (⚠️ добавить в .gitignore)

```yaml
# Safina EC Signing Keys
# ⚠️ NEVER commit to git!

safina:
  # Option 1: Direct private key (dev only)
  private_key_hex: null  # Set in .env instead

  # Option 2: Vault reference (production)
  vault_key_id: "safina_main_signer"
  vault_integration: true

  # Public address (for verification)
  public_address: "0xA285990a1Ce696d770d578Cf4473d80e0228DF95"
```

---

## Слой 7: EXPERTS — Эксперты

### Expert Domain Knowledge

**Директория:** `/Users/macbook/AGENT/experts/`

#### 1. Safina API Expert
**Файл:** `experts/domains/safina_api/expertise.yaml`

```yaml
domain: safina_api
version: 1.0.0
last_updated: 2026-02-05

knowledge:
  # Core Concepts
  concepts:
    - name: EC_Signing
      description: "Safina uses Ethereum-compatible SECP256k1 signatures"
      details:
        - "Sign with eth_keys library"
        - "Message format: keccak256(prefix + len + message)"
        - "v component adjusted to 27/28"

    - name: Decimal_Separator
      description: "Safina uses COMMA as decimal separator"
      importance: CRITICAL
      common_mistake: "Using period '.' causes signature errors"
      correct_format: "10,5 not 10.5"

    - name: Token_Format
      description: "network:::TOKEN###wallet_name"
      examples:
        - "5010:::TRX###945C6F4C54B3921F4625890300235114"
        - "3000:::ETH###6E879E7AC87C6B00462589020067E03D"

  # API Methods (19 total)
  api_methods:
    - endpoint: "GET /netlist/{status}"
      purpose: "Get network directory"
      params: {status: "1=active, 0=disabled"}
      implemented: true

    - endpoint: "POST /newWallet"
      purpose: "Create wallet (single or multi-sig)"
      body_params: ["network", "info", "slist?"]
      returns: {myUNID: "unique wallet creation ID"}
      implemented: true

    # ... (all 19 methods documented)

  # Common Patterns
  patterns:
    - name: Multi_Sig_Creation
      when: "Creating wallet requiring multiple approvers"
      structure:
        slist:
          min_signs: "2"  # minimum signatures required
          "0": {type: "all", ecaddress: "0x..."}  # must sign with EC
          "1": {type: "any", email: "...", sms: "..."}  # can sign via any method

    - name: Transaction_Flow
      steps:
        1. "Check balance"
        2. "Convert value decimal"
        3. "Send transaction (returns tx_unid)"
        4. "If multi-sig: collect signatures"
        5. "Transaction auto-broadcasts when min_signs reached"

  # Known Issues
  issues:
    - problem: "Signature error with correct data"
      cause: "JSON has whitespace"
      solution: "Use json.dumps(separators=(',', ':'))"

    - problem: "Transaction stuck in pending"
      cause: "Waiting for signatures"
      solution: "Check GET /tx_sign/{tx_unid} for status"

# Self-improvement prompts
questions:
  - "What happens if signature timeout exceeds 24h?"
  - "Can multi-sig settings be modified after creation?"
  - "What is the rate limit for API requests?"

# Learning log
learned:
  - date: 2026-02-05
    lesson: "Safina comma decimal separator is non-negotiable"
    impact: "All value formatting must convert . → ,"
```

#### 2. Multi-Signature Expert
**Файл:** `experts/domains/multisig/expertise.yaml`

```yaml
domain: multisig_workflows
version: 1.0.0
last_updated: 2026-02-05

knowledge:
  # Signature Types
  signature_types:
    - type: "all"
      description: "Signer must approve via ALL specified methods"
      example: {type: "all", email: "...", sms: "...", ecaddress: "..."}
      use_case: "High security, require multiple factors"

    - type: "any"
      description: "Signer can approve via ANY specified method"
      example: {type: "any", email: "...", sms: "..."}
      use_case: "Convenience, multiple approval options"

  # Workflow States
  transaction_states:
    - state: pending
      description: "Awaiting signatures"
      api_field: {wait: ["0xAAA...", "0xBBB..."]}

    - state: partially_signed
      description: "Some signatures collected, below min_signs"
      api_field: {signed: ["0xAAA..."], wait: ["0xBBB...", "0xCCC..."]}

    - state: ready_to_broadcast
      description: "min_signs reached, awaiting broadcast"
      api_field: {tx: null, min_sign: 2, signed: [...]}

    - state: broadcasted
      description: "Sent to blockchain"
      api_field: {tx: "0xDEADBEEF..."}

  # Best Practices
  best_practices:
    - rule: "Always set min_signs"
      reason: "Without it, ALL signers must approve (can cause deadlock)"
      recommendation: "min_signs = ceil(signers / 2) for majority vote"

    - rule: "Use ecaddress for automation"
      reason: "Email/SMS require manual action"
      recommendation: "Automated signers use ecaddress only"

    - rule: "Set timeouts"
      reason: "Prevent stuck transactions"
      recommendation: "Alert if pending > 1 hour"

# Decision Trees
decision_trees:
  - question: "How many signers for this wallet?"
    options:
      - answer: "1"
        action: "Create standard wallet (no slist)"
      - answer: "2-3"
        action: "Use simple majority (min_signs = 2)"
      - answer: "4+"
        action: "Use quorum (min_signs = ceil(n/2) or custom)"
```

---

## План Реализации

### Фаза 1: Service Layer (2-3 дня)

**Задачи:**
1. ✅ Создать `backend/services/network_service.py`
   - Cache networks and tokens_info
   - Background refresh every hour
   - Fallback to stale cache if API down

2. ✅ Улучшить `backend/services/transaction_service.py`
   - Validation helper (value format, token format, balance)
   - History tracking in local DB
   - Send/list/get operations

3. ✅ Создать `backend/services/signature_service.py`
   - Get pending signatures for user
   - Sign/reject with notifications
   - Status polling for frontend

**Инструменты:**
- `backend/safina/client.py` — уже готов
- `backend/database/db.py` — для кеша
- `backend/integrations/telegram_notifier.py` — для уведомлений

**Acceptance:**
- Unit tests для каждого сервиса
- All services return type-safe responses
- Error handling covers auth/network/validation errors

---

### Фаза 2: REST API (1-2 дня)

**Задачи:**
1. ✅ Создать `/api/transactions` endpoints
   ```python
   GET  /api/transactions              # List all
   GET  /api/transactions/{tx_unid}    # Get details
   POST /api/transactions              # Send new
   POST /api/transactions/{tx_unid}/sign    # Approve
   POST /api/transactions/{tx_unid}/reject  # Reject
   ```

2. ✅ Создать `/api/signatures` endpoints
   ```python
   GET  /api/signatures/pending        # What user must sign
   GET  /api/signatures/history        # What user signed
   ```

3. ✅ Создать `/api/networks` endpoints
   ```python
   GET  /api/networks                  # List networks
   GET  /api/networks/{id}/tokens      # Tokens for network
   GET  /api/tokens/info               # Commission info
   ```

**Инструменты:**
- FastAPI routers
- Pydantic request/response models
- Service layer для логики

**Acceptance:**
- OpenAPI docs auto-generated
- All endpoints return 200/400/401/404/502 properly
- Request validation через Pydantic

---

### Фаза 3: Frontend UI (3-4 дня)

**Задачи:**
1. ✅ Transaction Components
   - `components/TransactionList.tsx` — table с фильтрами
   - `components/TransactionForm.tsx` — send form с validation
   - `components/TransactionDetail.tsx` — детали с signatures progress

2. ✅ Signature Components
   - `components/PendingSignatures.tsx` — список ожидающих
   - `components/SignatureApprovalModal.tsx` — approve/reject modal
   - Badge компонент для статуса (pending/signed/rejected)

3. ✅ Network/Token Components
   - `components/NetworkSelector.tsx` — dropdown
   - `components/TokenBalance.tsx` — показать баланс + комиссию
   - `components/TokenInfo.tsx` — tooltip с деталями

4. ✅ Multi-Sig Components
   - `components/MultiSigSetup.tsx` — форма при создании кошелька
   - `components/SignersList.tsx` — кто должен подписать
   - `components/SignatureProgress.tsx` — progress bar (2/3 signed)

**Инструменты:**
- Next.js 16 + React 19
- Tailwind CSS (dark mode)
- shadcn/ui компоненты
- SWR для data fetching

**Acceptance:**
- Все операции доступны через UI
- Loading states для всех async операций
- Error handling с user-friendly messages
- Mobile responsive

---

### Фаза 4: Integrations (2-3 дня)

**Задачи:**
1. ✅ Telegram Notifications
   ```python
   # backend/integrations/telegram_notifier.py
   async def notify_pending_signature(tx_unid, details):
       """Send Telegram message with approve/reject buttons"""
   ```

2. ✅ ASAGENT Autonomous Operations
   ```python
   # asagent/workflows/safina_auto_approve.py
   async def auto_approve_trusted_transactions():
       """Auto-approve transactions from trusted sources"""
   ```

3. ✅ Vault Integration
   ```python
   # backend/integrations/vault_adapter.py
   async def get_signing_key() -> str:
       """Fetch EC private key from ASAGENT vault"""
   ```

**Инструменты:**
- `asagent/gateway/skills/builtin.py` — добавить /approve команду
- `asagent/security/vault/vault.py` — безопасное хранилище
- `backend/integrations/telegram_notifier.py` — уведомления

**Acceptance:**
- Telegram bot отправляет уведомления для pending signatures
- ASAGENT может автономно утверждать trusted транзакции
- Private keys НЕ хранятся в коде/конфиге

---

### Фаза 5: Testing & Documentation (1-2 дня)

**Задачи:**
1. ✅ Unit Tests
   - Service layer tests
   - API endpoint tests
   - Signature validation tests

2. ✅ Integration Tests
   - Full transaction flow (create → sign → broadcast)
   - Multi-sig workflow (2/3 signatures)
   - Error scenarios (invalid signature, insufficient balance)

3. ✅ Documentation
   - API documentation (OpenAPI/Swagger)
   - User guide для multi-sig wallets
   - Developer guide для интеграций

**Инструменты:**
- pytest для backend
- Jest для frontend
- Postman/Insomnia коллекции

**Acceptance:**
- >80% code coverage
- All critical paths tested
- Documentation актуальна

---

## Критерии Приемки

### Must Have (MVP)

- [x] Все 19 API методов реализованы в client
- [ ] Service layer покрывает все операции
- [ ] REST API endpoints для transactions/signatures/networks
- [ ] Frontend UI для send/list/approve транзакций
- [ ] Decimal separator обработка (точка → запятая)
- [ ] Error handling для auth/network/validation

### Should Have (Enhanced)

- [ ] Multi-sig wallet creation UI
- [ ] Signature status real-time updates (WebSocket/polling)
- [ ] Telegram notifications для pending signatures
- [ ] Кеширование справочников (networks, tokens_info)
- [ ] Transaction history с фильтрами

### Nice to Have (Future)

- [ ] ASAGENT автономное утверждение
- [ ] Vault integration для ключей
- [ ] Transaction scheduling
- [ ] CSV export для истории
- [ ] Mobile app (React Native)

---

## Appendix A: API Coverage Matrix

| # | Endpoint | Method | Client | Service | REST API | Frontend | Status |
|---|----------|--------|--------|---------|----------|----------|--------|
| 1 | `/netlist/{status}` | GET | ✅ | ⚠️ | ❌ | ❌ | Partial |
| 2 | `/newWallet` | POST | ✅ | ✅ | ✅ | ⚠️ | Partial |
| 3 | `/wallets` | GET | ✅ | ✅ | ✅ | ✅ | Complete |
| 4 | `/wallet/{name}` | GET | ✅ | ✅ | ✅ | ✅ | Complete |
| 5 | `/walletbyunid/{unid}` | GET | ✅ | ✅ | ❌ | ❌ | Partial |
| 6 | `/tokens` | GET | ✅ | ⚠️ | ⚠️ | ⚠️ | Partial |
| 7 | `/wallet_tokens/{name}` | GET | ✅ | ✅ | ✅ | ✅ | Complete |
| 8 | `/tokensinfo` | GET | ✅ | ❌ | ❌ | ❌ | Partial |
| 9 | `/user_tokens/` | GET | ✅ | ❌ | ❌ | ❌ | Partial |
| 10 | `/tx` | GET | ✅ | ⚠️ | ❌ | ❌ | Partial |
| 11 | `/tx` | POST | ✅ | ⚠️ | ❌ | ❌ | Partial |
| 12 | `/tx/{token}` | GET | ✅ | ❌ | ❌ | ❌ | Partial |
| 13 | `/tx_sign/{tx_unid}` | POST | ✅ | ❌ | ❌ | ❌ | Partial |
| 14 | `/tx_reject/{tx_unid}` | POST | ✅ | ❌ | ❌ | ❌ | Partial |
| 15 | `/tx_sign_wait/{tx_unid}` | GET | ✅ | ❌ | ❌ | ❌ | Partial |
| 16 | `/tx_sign_signed/{tx_unid}` | GET | ✅ | ❌ | ❌ | ❌ | Partial |
| 17 | `/tx_sign/{tx_unid}` | GET | ✅ | ❌ | ❌ | ❌ | Partial |
| 18 | `/tx_by_ec` | GET | ✅ | ❌ | ❌ | ❌ | Partial |
| 19 | `/tx_sign_signed/` | GET | ✅ | ❌ | ❌ | ❌ | Partial |

**Legend:**
- ✅ Complete — Fully implemented
- ⚠️ Partial — Basic implementation, needs enhancement
- ❌ Missing — Not implemented

---

## Appendix B: File Structure

```
/Users/macbook/AGENT/ORGON/
├── backend/
│   ├── safina/
│   │   ├── client.py          ✅ Complete
│   │   ├── signer.py          ✅ Complete
│   │   ├── models.py          ✅ Complete
│   │   └── errors.py          ✅ Complete
│   ├── services/
│   │   ├── wallet_service.py  ✅ Complete
│   │   ├── transaction_service.py  ⚠️ TODO: Enhance
│   │   ├── signature_service.py    ❌ TODO: Create
│   │   └── network_service.py      ❌ TODO: Create
│   ├── api/
│   │   ├── routes_wallets.py       ✅ Complete
│   │   ├── routes_transactions.py  ❌ TODO: Create
│   │   ├── routes_signatures.py    ❌ TODO: Create
│   │   └── routes_networks.py      ❌ TODO: Create
│   ├── integrations/
│   │   ├── vault_adapter.py        ⚠️ TODO: Add key fetching
│   │   ├── telegram_notifier.py    ⚠️ TODO: Add signature alerts
│   │   └── asagent_bridge.py       ⚠️ TODO: Add auto-approve
│   └── database/
│       └── db.py                   ✅ Complete
├── frontend/
│   └── components/
│       ├── wallets/               ✅ Complete
│       ├── transactions/          ❌ TODO: Create
│       ├── signatures/            ❌ TODO: Create
│       └── networks/              ❌ TODO: Create
├── docs/
│   ├── safina.html                ✅ API Reference
│   ├── Examples.html              ✅ Code Examples
│   └── GOTCHA_API_IMPLEMENTATION_PLAN.md  ✅ This file
├── goals/
│   ├── orgon_api_integration.md   ❌ TODO: Create
│   ├── orgon_service_layer.md     ❌ TODO: Create
│   └── orgon_frontend_ui.md       ❌ TODO: Create
├── context/
│   ├── safina_api_reference.md    ❌ TODO: Create
│   ├── safina_patterns.md         ❌ TODO: Create
│   └── safina_error_scenarios.md  ❌ TODO: Create
├── hardprompts/safina/
│   ├── create_transaction.md      ❌ TODO: Create
│   └── approve_signature.md       ❌ TODO: Create
├── args/
│   ├── safina_behavior.yaml       ❌ TODO: Create
│   └── safina_keys.yaml           ❌ TODO: Create (.gitignore!)
└── experts/domains/
    ├── safina_api/
    │   └── expertise.yaml         ❌ TODO: Create
    └── multisig/
        └── expertise.yaml         ❌ TODO: Create
```

---

## Заключение

Этот план обеспечивает полное внедрение Safina Pay API в проект ORGON согласно фреймворку GOTCHA. Каждый слой фреймворка покрыт:

1. **Goals** — четко определены цели и процессы
2. **Orchestration** — AI manager координирует выполнение
3. **Tools** — детерминистические скрипты для всех операций
4. **Context** — референсы, паттерны, примеры
5. **Hardprompts** — шаблоны для типовых задач
6. **Args** — настройки поведения системы
7. **Experts** — накапливаемые знания о домене

**Следующий шаг:** Начать с Фазы 1 (Service Layer), затем последовательно выполнять фазы 2-5.

**Важно:** Обновлять experts/expertise.yaml по мере обнаружения новых паттернов и проблем.
