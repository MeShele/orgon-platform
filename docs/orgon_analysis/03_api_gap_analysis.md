# Анализ API: Gap Analysis ORGON ↔ Safina

**Дата:** 13 февраля 2026  
**Версия:** 1.0  
**Статус:** Финальная версия  

---

## 🎯 Обзор анализа

Данный документ представляет детальный анализ текущего состояния API интеграций в ORGON Platform, сопоставление с возможностями Safina API от KAZ.ONE, выявление неиспользуемых возможностей и рекомендации по развитию API архитектуры.

### Текущее состояние

- **ORGON Backend:** 25+ API routes (FastAPI)
- **Safina API:** 17+ endpoints (KAZ.ONE)
- **Partner API:** 29 endpoints (для B2B клиентов)
- **Integration level:** ~75% (частичное использование Safina API)

---

## 📊 Сопоставление API endpoints

### 1. Safina API ↔ ORGON Routes Mapping

#### ✅ Реализованные интеграции

| Safina Endpoint | ORGON Route | Status | Coverage | Notes |
|----------------|-------------|--------|-----------|-------|
| `GET /ece/netlist/:status` | `GET /api/networks` | ✅ Full | 100% | Список доступных блокчейнов |
| `POST /ece/newWallet` | `POST /api/wallets` | ✅ Full | 95% | Создание одноподписных/мультиподписных кошельков |
| `GET /ece/wallets` | `GET /api/wallets` | ✅ Full | 90% | Список кошельков организации |
| `GET /ece/wallet/:name` | `GET /api/wallets/{name}` | ✅ Full | 100% | Детали конкретного кошелька |
| `GET /ece/wallet_tokens/:name` | `GET /api/wallets/{name}/tokens` | ✅ Full | 100% | Балансы токенов в кошельке |
| `GET /ece/tokens` | `GET /api/user/tokens` | ✅ Full | 85% | Все токены пользователя |
| `GET /ece/tokensinfo` | `GET /api/tokens/info` | ✅ Partial | 70% | Справочник токенов (не кэшируется) |
| `POST /ece/tx` | `POST /api/transactions` | ✅ Full | 95% | Создание транзакций |
| `GET /ece/tx` | `GET /api/transactions` | ✅ Full | 90% | История транзакций |
| `GET /ece/tx/:token` | `GET /api/transactions?token={token}` | ✅ Full | 100% | Транзакции по токену |
| `POST /ece/tx_sign/:tx_unid` | `POST /api/transactions/{unid}/sign` | ✅ Full | 100% | Подписание транзакций |
| `POST /ece/tx_reject/:tx_unid` | `POST /api/transactions/{unid}/reject` | ✅ Full | 100% | Отклонение транзакций |
| `GET /ece/tx_sign_wait/:tx_unid` | `GET /api/signatures/pending/{unid}` | ✅ Full | 100% | Ожидающие подписи |

#### ⚠️ Частично реализованные

| Safina Endpoint | ORGON Route | Status | Coverage | Issues |
|----------------|-------------|--------|-----------|---------|
| `GET /ece/walletbyunid/:unid` | - | ❌ Missing | 0% | Поиск кошелька по UNID не реализован |
| `GET /ece/tx_sign_signed/:tx_unid` | `GET /api/signatures/completed/{unid}` | ⚠️ Partial | 60% | Только базовая информация |
| `GET /ece/tx_sign/:tx_unid` | `GET /api/signatures/all/{unid}` | ⚠️ Partial | 50% | Нет агрегации всех подписей |
| `GET /ece/tx_by_ec` | - | ❌ Missing | 0% | Транзакции для подписания не фильтруются |

#### ❌ Не реализованные (потенциальные возможности)

| Safina Feature | Description | Potential Value | Priority |
|---------------|-------------|-----------------|----------|
| **Batch Transactions** | Массовые операции | Экономия gas, bulk payments | High |
| **Transaction Templates** | Шаблоны транзакций | Автоматизация повторных операций | Medium |
| **Cold Storage API** | Управление холодными кошельками | Enterprise security | High |
| **Cross-Chain Swaps** | Атомарные обмены между сетями | Расширение функционала | Low |
| **Gas Optimization** | Оптимизация комиссий | Снижение расходов | Medium |
| **Event Subscriptions** | Real-time уведомления | Улучшение UX | High |

---

## 🔍 Детальный анализ по категориям

### 2. Wallet Management APIs

#### Текущее состояние
```python
# ORGON Implementation
@router.post("/api/wallets")
async def create_wallet(request: WalletCreateRequest):
    """Создание кошелька через Safina API."""
    safina_response = await safina_client.create_wallet(
        network=request.network,
        wallet_type=request.wallet_type,
        slist=request.slist  # для multisig
    )
    
    # Сохранение в локальную БД
    wallet = await db.execute(
        "INSERT INTO wallets (name, network, wallet_type, addr, organization_id) VALUES (?, ?, ?, ?, ?)",
        (safina_response.name, request.network, request.wallet_type, safina_response.addr, request.organization_id)
    )
    
    return wallet
```

#### Gap Analysis

**Отсутствующие функции:**

1. **Wallet Templates** (не реализовано)
   ```python
   # Потенциальная реализация
   @router.post("/api/wallets/templates")
   async def create_wallet_from_template(template_id: str, params: dict):
       """Создание кошелька по шаблону."""
       template = await get_wallet_template(template_id)
       return await create_wallet_with_template(template, params)
   ```

2. **Wallet Groups** (не реализовано)
   ```python
   @router.post("/api/wallets/groups")
   async def create_wallet_group(group: WalletGroupRequest):
       """Группировка кошельков для bulk операций."""
       pass
   ```

3. **Wallet Backup/Recovery** (критический gap)
   ```python
   @router.post("/api/wallets/{wallet_id}/backup")
   async def create_wallet_backup():
       """Создание резервной копии кошелька."""
       pass
       
   @router.post("/api/wallets/recover")
   async def recover_wallet(backup_data: str):
       """Восстановление кошелька из backup."""
       pass
   ```

### 3. Transaction APIs

#### Расширенный анализ

**Текущая реализация:**
```python
@router.post("/api/transactions")
async def create_transaction(tx: TransactionRequest):
    """Базовое создание транзакции."""
    # Проверка баланса
    balance = await get_wallet_balance(tx.from_wallet)
    if balance < tx.amount:
        raise HTTPException(400, "Insufficient balance")
    
    # Отправка в Safina
    safina_response = await safina_client.create_transaction(
        wallet=tx.from_wallet,
        to_address=tx.to_address,
        amount=tx.amount,
        token=tx.token
    )
    
    return safina_response
```

**Критические gaps:**

1. **Fee Estimation** (слабая реализация)
   ```python
   # Нужно добавить
   @router.get("/api/transactions/estimate-fee")
   async def estimate_transaction_fee(
       network: str,
       token: str,
       amount: str,
       priority: str = "normal"  # low, normal, high, urgent
   ):
       """Точная оценка комиссии до создания транзакции."""
       # Интеграция с Safina для получения актуальных gas prices
       gas_price = await safina_client.get_gas_price(network, priority)
       estimated_fee = calculate_fee(amount, gas_price, token)
       
       return {
           "estimated_fee": estimated_fee,
           "confirmation_time": get_confirmation_time(priority),
           "success_probability": get_success_rate(priority)
       }
   ```

2. **Transaction Scheduling** (базовая реализация)
   ```python
   # Текущая реализация недостаточна
   @router.post("/api/transactions/scheduled")
   async def schedule_transaction(tx: ScheduledTransactionRequest):
       """Расширенная функциональность планирования."""
       if tx.frequency == "recurring":
           # Recurring payments не реализованы полностью
           return await create_recurring_transaction(tx)
       
       # Conditional transactions не реализованы
       if tx.conditions:
           return await create_conditional_transaction(tx)
   ```

3. **Batch Processing** (отсутствует)
   ```python
   # Критически важно для обменников
   @router.post("/api/transactions/batch")
   async def create_batch_transaction(batch: BatchTransactionRequest):
       """Массовая отправка (зарплаты, dividends)."""
       # Проверка лимитов
       total_amount = sum(tx.amount for tx in batch.transactions)
       await validate_batch_limits(batch.organization_id, total_amount)
       
       # Атомарное создание всех транзакций
       results = []
       async with transaction():
           for tx in batch.transactions:
               result = await create_single_transaction(tx)
               results.append(result)
       
       return {"batch_id": batch.id, "results": results}
   ```

### 4. Multi-signature APIs

#### Текущая реализация vs Возможности

**Реализовано:**
- Создание мультиподписных кошельков
- Подписание/отклонение транзакций
- Просмотр статуса подписей

**Gaps:**

1. **Signature Policies** (не реализовано)
   ```python
   @router.post("/api/signatures/policies")
   async def create_signature_policy(policy: SignaturePolicyRequest):
       """Гибкие правила подписания."""
       # Примеры:
       # - Разные схемы для разных сумм (малые суммы: 1/3, крупные: 2/3)
       # - Временные ограничения (автоотклонение через 24ч)
       # - Географические ограничения (подписанты из разных стран)
       pass
   ```

2. **Signature Delegation** (отсутствует)
   ```python
   @router.post("/api/signatures/delegate")
   async def delegate_signature_rights(delegation: DelegationRequest):
       """Делегирование прав подписи."""
       # Временная передача прав (отпуск, болезнь)
       # Ограниченное делегирование (только определенные суммы)
       pass
   ```

3. **Signature Analytics** (базовые)
   ```python
   @router.get("/api/signatures/analytics")
   async def get_signature_analytics(org_id: str, period: str):
       """Углубленная аналитика подписей."""
       return {
           "approval_rate": await calculate_approval_rate(org_id, period),
           "average_signing_time": await calculate_avg_signing_time(org_id),
           "slowest_signers": await get_slowest_signers(org_id),
           "signature_patterns": await analyze_signature_patterns(org_id),
           "risk_correlations": await analyze_risk_correlations(org_id)
       }
   ```

---

## 🚀 Неиспользуемые возможности Safina API

### 1. Advanced Wallet Features

#### Cold Storage Management
```python
# Safina поддерживает, ORGON не использует
class ColdStorageAPI:
    """API для управления холодными кошельками."""
    
    @router.post("/api/wallets/cold-storage/create")
    async def create_cold_wallet(request: ColdWalletRequest):
        """Создание cold wallet с offline подписанием."""
        # Генерация ключей offline
        # Экспорт публичных ключей для мониторинга
        # Создание watch-only wallet
        pass
    
    @router.post("/api/wallets/cold-storage/sweep")
    async def sweep_hot_to_cold(sweep_request: SweepRequest):
        """Автоматическое перемещение средств hot → cold."""
        # Правила: если баланс hot wallet > X, переместить в cold
        # Оставить operational minimum в hot wallet
        pass
```

#### Multi-Chain Bridge Operations
```python
# Safina поддерживает cross-chain, ORGON не реализует
@router.post("/api/transactions/cross-chain")
async def create_cross_chain_transaction(request: CrossChainRequest):
    """Атомарный обмен между сетями."""
    # BTC → WBTC на Ethereum
    # ETH → BNB через bridge
    # Автоматический swapping через DEX
    pass
```

### 2. Advanced Transaction Features

#### Gas Optimization Engine
```python
@router.post("/api/transactions/optimize-gas")
async def optimize_transaction_gas(tx_request: TransactionRequest):
    """Оптимизация gas fees."""
    # Анализ network congestion
    # Подбор оптимального времени отправки
    # Batch similar transactions
    # Dynamic fee adjustment
    
    optimizations = await analyze_gas_optimization(tx_request)
    
    return {
        "original_fee": tx_request.estimated_fee,
        "optimized_fee": optimizations.optimized_fee,
        "savings": optimizations.savings_percent,
        "delay_recommendation": optimizations.optimal_send_time,
        "batch_opportunities": optimizations.batch_suggestions
    }
```

#### Transaction Monitoring & Acceleration
```python
@router.post("/api/transactions/{tx_id}/accelerate") 
async def accelerate_transaction(tx_id: str, new_gas_price: float):
    """Ускорение застрявших транзакций."""
    # Replace-by-fee (RBF) для Bitcoin
    # Gas price increase для Ethereum
    # Resubmit с higher priority
    pass

@router.get("/api/transactions/{tx_id}/monitoring")
async def get_transaction_monitoring(tx_id: str):
    """Детальный мониторинг транзакции."""
    return {
        "current_status": "pending",
        "confirmations": "3/6",
        "estimated_completion": "5 minutes",
        "gas_price_comparison": "above_average",
        "acceleration_options": ["increase_gas", "rbf"],
        "risk_assessment": "low"
    }
```

### 3. Enterprise Features

#### Compliance Automation
```python
@router.post("/api/compliance/auto-screening")
async def setup_auto_compliance_screening():
    """Автоматический compliance screening."""
    # Интеграция с Chainalysis/Elliptic через Safina
    # Автоматическое блокирование high-risk транзакций
    # Real-time санкционные списки
    pass

@router.get("/api/compliance/regulatory-reports") 
async def generate_regulatory_reports(jurisdiction: str, period: str):
    """Автогенерация регуляторных отчетов."""
    # Поддержка разных юрисдикций
    # Автоматическое заполнение форм
    # Цифровые подписи отчетов
    pass
```

---

## 📚 Рекомендации по дополнению API

### 1. Критичные добавления (Phase 1 - 2 недели)

#### Enhanced Error Handling
```python
# Стандартизация ошибок
class ORGONAPIError(Exception):
    def __init__(self, code: str, message: str, details: dict = None):
        self.code = code
        self.message = message
        self.details = details or {}

# Error codes
ERROR_CODES = {
    "WALLET_001": "Insufficient balance",
    "WALLET_002": "Invalid address format", 
    "TX_001": "Transaction timeout",
    "TX_002": "Gas price too low",
    "SAFINA_001": "Safina API unavailable",
    "COMPLIANCE_001": "Transaction blocked by AML"
}

@app.exception_handler(ORGONAPIError)
async def handle_api_error(request: Request, exc: ORGONAPIError):
    return JSONResponse(
        status_code=400,
        content={
            "error": {
                "code": exc.code,
                "message": exc.message,
                "details": exc.details,
                "trace_id": request.headers.get("X-Trace-ID"),
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    )
```

#### Comprehensive Validation
```python
from pydantic import BaseModel, validator
import re

class TransactionRequest(BaseModel):
    from_wallet: str
    to_address: str  
    amount: str
    token: str
    organization_id: str
    
    @validator('to_address')
    def validate_address(cls, v, values):
        """Валидация адреса получателя."""
        network = get_network_by_token(values.get('token'))
        
        if network == 'bitcoin':
            if not re.match(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$|^bc1[a-z0-9]{39,59}$', v):
                raise ValueError('Invalid Bitcoin address format')
        elif network == 'ethereum':
            if not re.match(r'^0x[a-fA-F0-9]{40}$', v):
                raise ValueError('Invalid Ethereum address format')
                
        return v
    
    @validator('amount')
    def validate_amount(cls, v):
        """Валидация суммы."""
        try:
            amount_float = float(v)
            if amount_float <= 0:
                raise ValueError('Amount must be positive')
            if len(v.split('.')[-1]) > 8:  # Max 8 decimal places
                raise ValueError('Too many decimal places')
            return v
        except ValueError:
            raise ValueError('Invalid amount format')
```

### 2. API Versioning Strategy

```python
# Версионирование API
from fastapi import APIRouter
from enum import Enum

class APIVersion(str, Enum):
    V1 = "v1"
    V2 = "v2"
    BETA = "beta"

# v1 (current, deprecated in 6 months)
v1_router = APIRouter(prefix="/api/v1", tags=["v1"])

@v1_router.get("/wallets")
async def get_wallets_v1():
    """Legacy endpoint - будет удален в Q3 2026."""
    pass

# v2 (current recommended)  
v2_router = APIRouter(prefix="/api/v2", tags=["v2"])

@v2_router.get("/wallets")
async def get_wallets_v2(
    organization_id: str,
    limit: int = 20,
    offset: int = 0,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    filter_by_network: Optional[str] = None,
    filter_by_balance_min: Optional[float] = None
):
    """Enhanced wallets endpoint с расширенной функциональностью."""
    pass

# Beta (experimental features)
beta_router = APIRouter(prefix="/api/beta", tags=["beta"])

@beta_router.post("/wallets/ai-optimize")
async def ai_optimize_wallet_structure():
    """AI-powered оптимизация структуры кошельков."""
    pass
```

### 3. Rate Limiting & Security

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# Гибкие лимиты по ролям
limiter = Limiter(key_func=get_remote_address)

RATE_LIMITS = {
    "super_admin": "10000/hour",
    "platform_admin": "5000/hour", 
    "company_admin": "2000/hour",
    "company_operator": "1000/hour",
    "company_auditor": "500/hour",
    "end_user": "200/hour"
}

@limiter.limit(lambda: get_user_rate_limit())
@router.post("/api/v2/transactions")
async def create_transaction_v2(request: Request):
    pass

def get_user_rate_limit() -> str:
    """Динамический лимит на основе роли пользователя."""
    user_role = get_current_user_role()
    return RATE_LIMITS.get(user_role, "100/hour")
```

### 4. Real-time Updates (WebSocket/SSE)

```python
from fastapi import WebSocket
import asyncio
import json

class ConnectionManager:
    """Менеджер WebSocket соединений."""
    
    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, organization_id: str):
        await websocket.accept()
        if organization_id not in self.active_connections:
            self.active_connections[organization_id] = []
        self.active_connections[organization_id].append(websocket)
    
    async def disconnect(self, websocket: WebSocket, organization_id: str):
        self.active_connections[organization_id].remove(websocket)
    
    async def broadcast_to_organization(self, organization_id: str, data: dict):
        """Отправка данных всем подключенным клиентам организации."""
        if organization_id in self.active_connections:
            for connection in self.active_connections[organization_id]:
                await connection.send_text(json.dumps(data))

manager = ConnectionManager()

@app.websocket("/ws/{organization_id}")
async def websocket_endpoint(websocket: WebSocket, organization_id: str):
    await manager.connect(websocket, organization_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle client messages (ping/pong, subscriptions)
            await handle_websocket_message(data, organization_id)
    except WebSocketDisconnect:
        await manager.disconnect(websocket, organization_id)

# Event broadcasting
async def broadcast_transaction_update(transaction: Transaction):
    """Рассылка обновления транзакции."""
    await manager.broadcast_to_organization(
        transaction.organization_id,
        {
            "type": "transaction_update",
            "data": {
                "id": transaction.id,
                "status": transaction.status,
                "confirmations": transaction.confirmations,
                "updated_at": transaction.updated_at.isoformat()
            }
        }
    )
```

---

## 🔗 Webhooks Architecture

### Исходящие webhooks (ORGON → Клиенты)

```python
class WebhookService:
    """Сервис для отправки webhooks клиентам."""
    
    WEBHOOK_EVENTS = [
        "wallet.created",
        "wallet.updated", 
        "transaction.created",
        "transaction.confirmed",
        "transaction.failed",
        "signature.required",
        "signature.approved",
        "signature.rejected",
        "compliance.alert",
        "balance.updated"
    ]
    
    async def send_webhook(self, organization_id: str, event: str, data: dict):
        """Отправка webhook с retry logic."""
        webhooks = await self.get_org_webhooks(organization_id, event)
        
        for webhook in webhooks:
            await self.attempt_webhook_delivery(webhook, event, data)
    
    async def attempt_webhook_delivery(self, webhook: Webhook, event: str, data: dict):
        """Отправка с exponential backoff retry."""
        payload = {
            "event": event,
            "timestamp": datetime.utcnow().isoformat(),
            "data": data,
            "organization_id": webhook.organization_id
        }
        
        # HMAC подпись
        signature = hmac.new(
            webhook.secret.encode(),
            json.dumps(payload).encode(),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            "X-ORGON-Signature": f"sha256={signature}",
            "X-ORGON-Event": event,
            "Content-Type": "application/json"
        }
        
        max_attempts = 5
        backoff_base = 2  # seconds
        
        for attempt in range(max_attempts):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        webhook.url,
                        json=payload,
                        headers=headers,
                        timeout=30
                    )
                    
                    if 200 <= response.status_code < 300:
                        await self.mark_delivery_success(webhook.id, payload)
                        return
                        
            except Exception as e:
                logger.warning(f"Webhook delivery attempt {attempt + 1} failed: {e}")
                
                if attempt < max_attempts - 1:
                    sleep_time = backoff_base ** attempt
                    await asyncio.sleep(sleep_time)
                else:
                    await self.mark_delivery_failed(webhook.id, payload, str(e))
```

### Входящие webhooks (Safina → ORGON)

```python
@router.post("/api/webhooks/safina")
async def receive_safina_webhook(request: Request):
    """Получение webhooks от Safina API."""
    
    # Верификация подписи
    signature = request.headers.get("X-Safina-Signature")
    if not await verify_safina_signature(signature, await request.body()):
        raise HTTPException(401, "Invalid signature")
    
    payload = await request.json()
    event_type = payload.get("event")
    
    # Обработка событий
    if event_type == "transaction.confirmed":
        await handle_transaction_confirmed(payload["data"])
    elif event_type == "transaction.failed":
        await handle_transaction_failed(payload["data"])
    elif event_type == "wallet.balance_updated":
        await handle_balance_updated(payload["data"])
    elif event_type == "compliance.high_risk_detected":
        await handle_compliance_alert(payload["data"])
    
    return {"status": "processed"}

async def handle_transaction_confirmed(data: dict):
    """Обработка подтверждения транзакции."""
    tx_unid = data["transaction_unid"]
    confirmations = data["confirmations"]
    
    # Обновление статуса в БД
    await db.execute(
        "UPDATE transactions SET status = 'confirmed', confirmations = ? WHERE unid = ?",
        (confirmations, tx_unid)
    )
    
    # Уведомление клиентов через WebSocket
    transaction = await get_transaction_by_unid(tx_unid)
    await broadcast_transaction_update(transaction)
    
    # Отправка webhook организации
    await webhook_service.send_webhook(
        transaction.organization_id,
        "transaction.confirmed", 
        {"transaction_id": transaction.id, "confirmations": confirmations}
    )
```

---

## 📊 API Analytics & Monitoring

### 1. API Usage Analytics

```python
@router.get("/api/analytics/usage")
async def get_api_usage_analytics(
    organization_id: str,
    period: str = "month",
    endpoint_filter: Optional[str] = None
):
    """Аналитика использования API."""
    
    usage_data = await analytics_service.get_api_usage(
        organization_id, period, endpoint_filter
    )
    
    return {
        "period": period,
        "total_requests": usage_data.total_requests,
        "average_response_time": usage_data.avg_response_time,
        "error_rate": usage_data.error_rate,
        "top_endpoints": usage_data.top_endpoints,
        "usage_by_day": usage_data.daily_breakdown,
        "rate_limit_hits": usage_data.rate_limit_violations,
        "billing_impact": {
            "current_tier": usage_data.current_tier,
            "next_tier_threshold": usage_data.next_tier_threshold,
            "estimated_overage_cost": usage_data.overage_cost
        }
    }
```

### 2. Performance Monitoring

```python
from prometheus_client import Counter, Histogram
import time

# Метрики для мониторинга
API_REQUESTS = Counter('orgon_api_requests_total', 'Total API requests', ['endpoint', 'method', 'status'])
API_DURATION = Histogram('orgon_api_duration_seconds', 'API request duration', ['endpoint'])
SAFINA_INTEGRATION = Counter('orgon_safina_calls_total', 'Safina API calls', ['endpoint', 'status'])

@app.middleware("http")
async def monitoring_middleware(request: Request, call_next):
    """Middleware для мониторинга API."""
    start_time = time.time()
    
    response = await call_next(request)
    
    duration = time.time() - start_time
    endpoint = request.url.path
    method = request.method
    status = str(response.status_code)
    
    # Запись метрик
    API_REQUESTS.labels(endpoint=endpoint, method=method, status=status).inc()
    API_DURATION.labels(endpoint=endpoint).observe(duration)
    
    # Логирование медленных запросов
    if duration > 5.0:  # > 5 seconds
        logger.warning(f"Slow API request: {method} {endpoint} took {duration:.2f}s")
    
    return response
```

### 3. API Documentation Enhancement

```python
from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

def custom_openapi():
    """Кастомная OpenAPI схема с расширенной документацией."""
    if app.openapi_schema:
        return app.openapi_schema
        
    openapi_schema = get_openapi(
        title="ORGON Platform API",
        version="2.0.0",
        description="""
        # ORGON Platform API
        
        Crypto Wallet-as-a-Service API для B2B клиентов.
        
        ## Аутентификация
        
        API использует Bearer token аутентификацию:
        ```
        Authorization: Bearer YOUR_JWT_TOKEN
        ```
        
        ## Rate Limiting
        
        Лимиты зависят от тарифного плана:
        - **Tier A**: 1000 запросов/час
        - **Tier B**: 5000 запросов/час  
        - **Tier C**: 20000 запросов/час
        
        ## Webhooks
        
        Для real-time уведомлений настройте webhooks:
        ```python
        POST /api/webhooks
        {
            "url": "https://yourapp.com/webhook",
            "events": ["transaction.confirmed", "wallet.created"]
        }
        ```
        
        ## Error Handling
        
        Все ошибки возвращаются в стандартном формате:
        ```json
        {
            "error": {
                "code": "WALLET_001",
                "message": "Insufficient balance", 
                "details": {"current_balance": 0.001, "required": 0.005}
            }
        }
        ```
        """,
        routes=app.routes,
        contact={
            "name": "ASYSTEM Support",
            "email": "support@asystem.kg",
            "url": "https://asystem.kg"
        },
        license_info={
            "name": "Proprietary",
            "url": "https://asystem.kg/license"
        }
    )
    
    # Добавление security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        },
        "apiKeyAuth": {
            "type": "apiKey",
            "in": "header",
            "name": "X-API-Key"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app.openapi = custom_openapi
```

---

## 🎯 Roadmap развития API

### Phase 1 (2 недели) - Критические доработки
- ✅ Улучшение error handling и validation
- ✅ Реализация missing Safina endpoints
- ✅ WebSocket для real-time updates
- ✅ Enhanced API documentation

### Phase 2 (4 недели) - Advanced Features  
- ✅ Batch transaction processing
- ✅ Cold storage management APIs
- ✅ Advanced signature policies
- ✅ Comprehensive webhook system

### Phase 3 (4 недели) - Enterprise Features
- ✅ Cross-chain transaction support
- ✅ Advanced compliance automation
- ✅ AI-powered gas optimization
- ✅ Enterprise reporting APIs

### Phase 4 (4 недели) - Platform Optimization
- ✅ GraphQL endpoint для complex queries
- ✅ API caching layer (Redis)
- ✅ Advanced rate limiting per endpoint
- ✅ API analytics dashboard

Данный gap analysis показывает, что ORGON уже имеет сильную базу интеграций с Safina API (~75% покрытие), но есть значительные возможности для расширения функционала, особенно в области enterprise features, batch операций и compliance automation.