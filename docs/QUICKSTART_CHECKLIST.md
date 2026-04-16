# Quickstart Checklist: Внедрение Safina API

**Цель:** Полная интеграция всех 19 методов Safina Pay API в ORGON
**Фреймворк:** GOTCHA (Goals, Orchestration, Tools, Context, Hardprompts, Args, Experts)
**Дата начала:** 2026-02-05

---

## Phase 1: Service Layer (День 1-2)

### NetworkService
- [ ] Создать `backend/services/network_service.py`
- [ ] Метод `get_networks(status)` с кешированием (TTL 1h)
- [ ] Метод `get_tokens_info()` с кешированием
- [ ] Background refresh task каждый час
- [ ] Unit тесты
- [ ] Добавить в `tools/manifest.md`

### SignatureService
- [ ] Создать `backend/services/signature_service.py`
- [ ] Метод `get_pending_signatures(user_address)`
- [ ] Метод `sign_transaction(tx_unid, user_address)`
- [ ] Метод `reject_transaction(tx_unid, reason)`
- [ ] Telegram notification integration
- [ ] Unit тесты
- [ ] Добавить в `tools/manifest.md`

### TransactionService (улучшения)
- [ ] Открыть `backend/services/transaction_service.py`
- [ ] Добавить `validate_transaction()` helper
  - Проверка баланса
  - Проверка формата адреса
  - Конвертация decimal separator (. → ,)
- [ ] Добавить `format_token()` helper
  - Конвертация в `network:::TOKEN###wallet_name`
- [ ] Добавить `send_transaction()` метод
- [ ] Добавить `get_transactions()` метод
- [ ] Unit тесты для новых методов

**Acceptance:**
- [ ] Все сервисы возвращают type-safe responses
- [ ] Error handling покрывает auth/network/validation
- [ ] >80% code coverage

---

## Phase 2: REST API Endpoints (День 3)

### Transaction Endpoints
- [ ] Создать `backend/api/routes_transactions.py`
- [ ] `GET /api/transactions` — список всех транзакций
- [ ] `GET /api/transactions/{tx_unid}` — детали транзакции
- [ ] `POST /api/transactions` — создать транзакцию
  - Request body: `{"token", "to_address", "value", "info"}`
  - Response: `{"tx_unid": "..."}`
- [ ] Подключить router в `backend/main.py`

### Signature Endpoints
- [ ] Создать `backend/api/routes_signatures.py`
- [ ] `GET /api/signatures/pending` — ожидающие подписи
- [ ] `POST /api/signatures/{tx_unid}/sign` — утвердить
- [ ] `POST /api/signatures/{tx_unid}/reject` — отклонить
  - Request body: `{"reason": "..."}`
- [ ] `GET /api/signatures/history` — история подписаний
- [ ] Подключить router в `backend/main.py`

### Network Endpoints
- [ ] Создать `backend/api/routes_networks.py`
- [ ] `GET /api/networks` — список сетей
- [ ] `GET /api/networks/{network_id}/tokens` — токены сети
- [ ] `GET /api/tokens/info` — информация о комиссиях
- [ ] Подключить router в `backend/main.py`

**Acceptance:**
- [ ] OpenAPI docs auto-generated (Swagger UI)
- [ ] All endpoints возвращают правильные HTTP статусы
- [ ] Request/Response validation через Pydantic

---

## Phase 3: Frontend Components (День 4-6)

### Transaction Components
- [ ] Создать `frontend/components/transactions/TransactionList.tsx`
  - Table с колонками: tx_unid, token, amount, to, status, date
  - Фильтры: по токену, по дате, по статусу
  - Пагинация
- [ ] Создать `frontend/components/transactions/TransactionForm.tsx`
  - NetworkSelector dropdown
  - TokenSelector с балансом
  - AddressInput с валидацией
  - AmountInput с конвертацией (. → ,)
  - InfoTextarea
  - Submit button с loading state
- [ ] Создать `frontend/components/transactions/TransactionDetail.tsx`
  - Детали транзакции
  - Signature progress (если multi-sig)
  - Timeline событий
- [ ] Создать страницу `frontend/app/transactions/page.tsx`

### Signature Components
- [ ] Создать `frontend/components/signatures/PendingSignaturesList.tsx`
  - Список ожидающих подписей
  - Карточка с деталями: token, amount, to, from, info
  - Кнопки Approve/Reject
- [ ] Создать `frontend/components/signatures/SignatureApprovalModal.tsx`
  - Modal с деталями транзакции
  - Confirmation checkbox
  - Approve/Reject buttons
- [ ] Создать `frontend/components/signatures/SignatureProgress.tsx`
  - Progress bar (e.g., "2/3 signed")
  - Список подписантов с статусом (✅ signed, ⏳ waiting)
- [ ] Создать страницу `frontend/app/signatures/page.tsx`

### Network/Token Components
- [ ] Создать `frontend/components/networks/NetworkSelector.tsx`
  - Dropdown с логотипами сетей
  - Кеширование списка
- [ ] Создать `frontend/components/tokens/TokenSelector.tsx`
  - Dropdown с токенами и балансами
  - Показать комиссию
- [ ] Создать `frontend/components/tokens/TokenInfo.tsx`
  - Tooltip с деталями токена
  - Commission info (c, cMin, cMax)

### Multi-Sig Components
- [ ] Создать `frontend/components/wallets/MultiSigSetup.tsx`
  - Форма создания multi-sig кошелька
  - Список подписантов
  - min_signs input
  - type selector (all/any) для каждого подписанта
- [ ] Обновить `frontend/components/wallets/WalletCreateForm.tsx`
  - Добавить checkbox "Multi-signature wallet"
  - Показать MultiSigSetup если checked

**Acceptance:**
- [ ] Все операции доступны через UI
- [ ] Loading states для всех async операций
- [ ] Error handling с user-friendly messages
- [ ] Dark mode по умолчанию
- [ ] Mobile responsive

---

## Phase 4: Integrations (День 7-8)

### Telegram Integration
- [ ] Открыть `backend/integrations/telegram_notifier.py`
- [ ] Добавить метод `notify_pending_signature(tx_unid, details)`
  - Формат сообщения с деталями транзакции
  - Inline кнопки "Approve" / "Reject"
- [ ] Обновить `asagent/gateway/skills/builtin.py`
  - Добавить команду `/approve {tx_unid}`
  - Добавить команду `/reject {tx_unid} {reason}`
- [ ] Протестировать уведомления

### ASAGENT Auto-Approve
- [ ] Создать `asagent/workflows/safina_auto_approve.py`
- [ ] Метод `auto_approve_trusted_transactions()`
  - Проверка whitelist адресов
  - Проверка max amount (из args)
  - Автоутверждение если условия выполнены
- [ ] Добавить в `asagent/autonomy/task_generator.py`
  - Периодическая проверка pending signatures (каждые 5 минут)
- [ ] Создать `args/safina_auto_approve.yaml`
  - trusted_addresses: []
  - max_amount: "100,0"
  - enabled: false

### Vault Integration
- [ ] Открыть `backend/integrations/vault_adapter.py`
- [ ] Добавить метод `get_safina_signing_key() -> str`
  - Fetch private key из ASAGENT Vault
  - Decrypt и вернуть hex
- [ ] Обновить `backend/config.py`
  - Добавить `SAFINA_USE_VAULT: bool`
  - Если True → использовать vault, иначе → .env
- [ ] Обновить инициализацию SafinaSigner в `backend/main.py`

**Acceptance:**
- [ ] Telegram уведомления работают
- [ ] ASAGENT может автономно утверждать trusted транзакции
- [ ] Private keys НЕ хранятся в коде/конфиге
- [ ] Vault integration опциональна (fallback to .env)

---

## Phase 5: Testing & Docs (День 9-10)

### Unit Tests
- [ ] Тесты для NetworkService
- [ ] Тесты для SignatureService
- [ ] Тесты для TransactionService
- [ ] Тесты для API endpoints
- [ ] Запустить `pytest --cov` → >80% coverage

### Integration Tests
- [ ] Тест: полный flow создания транзакции
  1. Create wallet
  2. Get balance
  3. Send transaction
  4. Verify tx_unid created
- [ ] Тест: multi-sig workflow
  1. Create multi-sig wallet (min_signs=2)
  2. Send transaction
  3. Sign with 1st signer
  4. Verify status: partially signed
  5. Sign with 2nd signer
  6. Verify status: ready to broadcast
- [ ] Тест: error scenarios
  - Invalid signature → 401
  - Insufficient balance → 400
  - Network error → 502 with retry

### Documentation
- [ ] OpenAPI/Swagger docs актуальны
- [ ] Создать `ORGON/docs/USER_GUIDE_MULTISIG.md`
  - Как создать multi-sig wallet
  - Как утвердить транзакцию
  - Troubleshooting
- [ ] Создать `ORGON/docs/DEVELOPER_GUIDE_INTEGRATIONS.md`
  - Как добавить новую интеграцию
  - Как использовать SafinaClient
  - Примеры кода
- [ ] Обновить `README.md` с новыми фичами

**Acceptance:**
- [ ] >80% code coverage
- [ ] All critical paths протестированы
- [ ] Документация актуальна и полная

---

## Критерии Завершения

### Must Have (блокирует запуск)
- [ ] Все 19 API методов реализованы в client ✅ (уже готово)
- [ ] Service layer покрывает все операции
- [ ] REST API endpoints для transactions/signatures/networks
- [ ] Frontend UI для send/list/approve транзакций
- [ ] Decimal separator обработка (. → ,)
- [ ] Error handling для auth/network/validation
- [ ] Unit tests >80% coverage

### Should Have (важно, но не блокирует)
- [ ] Multi-sig wallet creation UI
- [ ] Signature status real-time updates
- [ ] Telegram notifications
- [ ] Кеширование справочников
- [ ] Transaction history с фильтрами

### Nice to Have (будущие улучшения)
- [ ] ASAGENT автономное утверждение
- [ ] Vault integration
- [ ] Transaction scheduling
- [ ] CSV export
- [ ] Mobile app

---

## Важные Напоминания

### 🔴 CRITICAL: Decimal Separator
```python
# ❌ НЕПРАВИЛЬНО
value = "10.5"  # Safina вернет ошибку подписи!

# ✅ ПРАВИЛЬНО
value = "10,5"  # Safina примет
```

### 🔴 CRITICAL: Token Format
```python
# ❌ НЕПРАВИЛЬНО
token = "TRX"

# ✅ ПРАВИЛЬНО
token = "5010:::TRX###945C6F4C54B3921F4625890300235114"
#        network:::TOKEN###wallet_name
```

### 🔴 CRITICAL: JSON Compact Signing
```python
# ❌ НЕПРАВИЛЬНО
body = json.dumps(data)  # может добавить пробелы!

# ✅ ПРАВИЛЬНО
body = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
```

---

## Tracking Progress

**Started:** 2026-02-05
**Target Completion:** 2026-02-15 (10 дней)

**Phase Status:**
- [ ] Phase 1: Service Layer (Day 1-2)
- [ ] Phase 2: REST API (Day 3)
- [ ] Phase 3: Frontend (Day 4-6)
- [ ] Phase 4: Integrations (Day 7-8)
- [ ] Phase 5: Testing & Docs (Day 9-10)

**Daily Standup Questions:**
1. Что было завершено вчера?
2. Что будет сделано сегодня?
3. Есть ли блокеры?

**Blocker Escalation:**
- Safina API issues → проверить signature, формат данных
- Integration issues → проверить ASAGENT/Telegram/Vault доступность
- Frontend issues → проверить API endpoint responses

---

## Resources

**Documentation:**
- [Safina API Reference](./safina.html)
- [Code Examples](./Examples.html)
- [GOTCHA Implementation Plan](./GOTCHA_API_IMPLEMENTATION_PLAN.md)
- [Visual Architecture](./API_IMPLEMENTATION_VISUAL.md)

**Code Locations:**
- Backend: `/Users/macbook/AGENT/ORGON/backend/`
- Frontend: `/Users/macbook/AGENT/ORGON/frontend/`
- ASAGENT: `/Users/macbook/AGENT/asagent/`

**Support:**
- GOTCHA Framework: `/Users/macbook/AGENT/CLAUDE.md`
- Memory: `/Users/macbook/.claude/projects/-Users-macbook-AGENT/memory/MEMORY.md`

---

**Next Action:** Начать с Phase 1, создать NetworkService. Удачи! 🚀
