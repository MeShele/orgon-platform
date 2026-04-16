# ORGON API Documentation

**Base URL:** https://orgon.asystem.ai  
**Swagger UI:** https://orgon.asystem.ai/api/docs  
**ReDoc:** https://orgon.asystem.ai/api/redoc  
**OpenAPI JSON:** https://orgon.asystem.ai/api/openapi.json

---

## 📋 Table of Contents

1. [Health & Status](#health--status)
2. [Wallets](#wallets)
3. [Transactions](#transactions)
4. [Scheduled Transactions](#scheduled-transactions)
5. [Signatures (Multi-Sig)](#signatures-multi-sig)
6. [Networks & Tokens](#networks--tokens)
7. [Dashboard](#dashboard)
8. [Export](#export)

---

## Health & Status

### GET /api/health
Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "orgon",
  "last_sync": "2026-02-06T09:18:40.536438+00:00"
}
```

---

## Wallets

### GET /api/wallets
List all wallets.

**Response:**
```json
{
  "wallets": [
    {
      "wallet_id": 123,
      "name": "my-wallet",
      "network": 1,
      "wallet_type": "multi",
      "addr": "TYourAddress...",
      "token_short_names": ["TRX", "USDT"],
      ...
    }
  ]
}
```

### GET /api/wallets/{name}
Get wallet details by name.

**Response:**
```json
{
  "name": "my-wallet",
  "network": 1,
  "addr": "TYourAddress...",
  "wallet_type": "multi",
  ...
}
```

### POST /api/wallets
Create a new wallet.

**Request:**
```json
{
  "network": "1",
  "info": "My new wallet",
  "slist": ["0xAddress1", "0xAddress2"]
}
```

**Response:**
```json
{
  "unid": "wallet-unique-id",
  "message": "Wallet creation requested"
}
```

---

## Transactions

### GET /api/transactions
List transactions with optional filters.

**Query Params:**
- `limit` (int) — Max results (default 50)
- `offset` (int) — Pagination offset
- `wallet_name` (string) — Filter by wallet
- `status` (string) — pending, signed, confirmed, rejected
- `network` (int) — Filter by network ID

**Response:**
```json
{
  "total": 42,
  "transactions": [
    {
      "unid": "tx-123",
      "token": "USDT",
      "to_addr": "TRecipient...",
      "value": "100.50",
      "status": "confirmed",
      "tx_hash": "0x...",
      ...
    }
  ]
}
```

### GET /api/transactions/{unid}
Get transaction details.

**Response:**
```json
{
  "unid": "tx-123",
  "token": "USDT",
  "value": "100.50",
  "status": "confirmed",
  "signatures": [...],
  ...
}
```

### POST /api/transactions
Send a new transaction.

**Request:**
```json
{
  "token": "TRX:::1###my-wallet",
  "to_address": "TRecipientAddress...",
  "value": "100.50",
  "info": "Payment for services"
}
```

**Response:**
```json
{
  "unid": "tx-new-123",
  "status": "pending"
}
```

### POST /api/transactions/validate
Validate a transaction before sending.

**Request:**
```json
{
  "token": "USDT",
  "to_address": "TAddress...",
  "value": "100.50",
  "check_balance": true
}
```

**Response:**
```json
{
  "valid": true,
  "errors": [],
  "warnings": ["Gas price is high"],
  "details": {
    "current_balance": "500.00",
    "required_balance": "100.50",
    "sufficient_balance": true
  }
}
```

---

## Scheduled Transactions

### POST /api/scheduled
Create a scheduled transaction (one-time or recurring).

**Request (One-Time):**
```json
{
  "token": "TRX:::1###my-wallet",
  "to_address": "TRecipient...",
  "value": "100.50",
  "scheduled_at": "2026-02-07T10:00:00Z",
  "info": "Payment tomorrow"
}
```

**Request (Recurring):**
```json
{
  "token": "TRX:::1###my-wallet",
  "to_address": "TRecipient...",
  "value": "5000",
  "scheduled_at": "2026-02-07T10:00:00Z",
  "recurrence_rule": "0 10 1 * *",
  "info": "Monthly salary"
}
```

**Cron Examples:**
- `0 10 * * *` — Every day at 10:00
- `0 10 * * MON` — Every Monday at 10:00
- `0 10 1 * *` — 1st of month at 10:00
- `0 */6 * * *` — Every 6 hours

**Response:**
```json
{
  "id": 1,
  "status": "pending",
  "scheduled_at": "2026-02-07T10:00:00Z",
  "recurring": false
}
```

### GET /api/scheduled
List scheduled transactions.

**Query Params:**
- `status` — pending, sent, failed, cancelled
- `limit` — Max results (1-200)

**Response:**
```json
{
  "total": 5,
  "transactions": [
    {
      "id": 1,
      "token": "TRX:::1###my-wallet",
      "to_address": "TRecipient...",
      "value": "100.50",
      "scheduled_at": "2026-02-07T10:00:00+00:00",
      "status": "pending",
      "recurrence_rule": null,
      ...
    }
  ]
}
```

### GET /api/scheduled/upcoming
Get transactions scheduled in next N hours.

**Query Params:**
- `hours` — Look ahead (1-168, default 24)

**Response:**
```json
{
  "total": 3,
  "hours": 24,
  "transactions": [...]
}
```

### GET /api/scheduled/{id}
Get scheduled transaction by ID.

### DELETE /api/scheduled/{id}
Cancel a pending scheduled transaction.

**Response:**
```json
{
  "id": 1,
  "status": "cancelled",
  "message": "Scheduled transaction cancelled"
}
```

---

## Signatures (Multi-Sig)

### GET /api/signatures/pending
Get transactions awaiting your signature.

**Response:**
```json
{
  "pending": [
    {
      "unid": "tx-123",
      "token": "USDT",
      "value": "1000",
      "to_addr": "TRecipient...",
      "min_sign": 2,
      "signed": [],
      "wait": ["0xAddress1", "0xAddress2"]
    }
  ]
}
```

### GET /api/signatures/history
Get signature history with filters.

**Query Params:**
- `limit` — Max results
- `status` — signed, rejected

### POST /api/signatures/{tx_unid}/sign
Sign (approve) a transaction.

**Response:**
```json
{
  "status": "signed",
  "message": "Transaction approved"
}
```

### POST /api/signatures/{tx_unid}/reject
Reject a transaction.

**Request:**
```json
{
  "reason": "Amount too high"
}
```

**Response:**
```json
{
  "status": "rejected",
  "message": "Transaction rejected"
}
```

---

## Networks & Tokens

### GET /api/networks
List available networks.

**Query Params:**
- `status` — 1 (active), 0 (disabled)

**Response:**
```json
{
  "networks": [
    {
      "network_id": 1,
      "network_name": "TRX",
      "link": "https://...",
      "address_explorer": "https://tronscan.org/#/address/{address}",
      "tx_explorer": "https://tronscan.org/#/transaction/{hash}",
      "status": 1
    }
  ]
}
```

### GET /api/networks/tokens-info
Get token commission info.

**Response:**
```json
{
  "tokens_info": [
    {
      "token": "USDT",
      "commission": "1.5",
      "commission_min": "1.0",
      "commission_max": "10.0"
    }
  ]
}
```

---

## Dashboard

### GET /api/dashboard/stats
Get dashboard statistics.

**Response:**
```json
{
  "total_wallets": 4,
  "total_balance_usd": "1234.56",
  "transactions_24h": 12,
  "pending_signatures": 2,
  "networks_active": 7,
  "cache_stats": {
    "networks_age_seconds": 3600,
    "networks_fresh": false,
    "networks_count": 7,
    "tokens_info_count": 15
  },
  "last_sync": "2026-02-06T10:00:00+00:00"
}
```

### GET /api/dashboard/overview
Legacy endpoint - token summary.

**Response:**
```json
{
  "tokens": [
    {
      "token": "TRX",
      "total_value": "1000.50",
      "wallet_count": 3
    }
  ]
}
```

### GET /api/dashboard/recent
Get recent activity.

**Query Params:**
- `limit` — Max results (default 20)

**Response:**
```json
{
  "recent": [
    {
      "type": "transaction",
      "unid": "tx-123",
      "action": "sent",
      "token": "USDT",
      "value": "100",
      "timestamp": "2026-02-06T10:00:00+00:00"
    }
  ]
}
```

### GET /api/dashboard/alerts
Get system alerts and warnings.

**Response:**
```json
{
  "alerts": {
    "low_balances": [
      {
        "wallet": "my-wallet",
        "token": "TRX",
        "current": "50",
        "threshold": "100"
      }
    ],
    "pending_signatures": [],
    "failed_transactions": [],
    "cache_warnings": []
  }
}
```

---

## Export

### GET /api/export/transactions
Export transactions to CSV or JSON.

**Query Params:**
- `format` — csv, json
- `wallet_name` — Filter
- `from_date` — ISO timestamp
- `to_date` — ISO timestamp

**Response:** File download

### GET /api/export/wallets
Export wallets to CSV or JSON.

**Query Params:**
- `format` — csv, json

**Response:** File download

---

## WebSocket (Real-Time Updates)

### WS /ws/updates
WebSocket endpoint for live updates.

**Connection:**
```javascript
const ws = new WebSocket('wss://orgon.asystem.ai/ws/updates');

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event:', data.type, data.data);
};
```

**Events:**
- `connected` — Connection established
- `transaction.created` — New transaction sent
- `transaction.confirmed` — Transaction confirmed
- `transaction.failed` — Transaction failed
- `signature.pending` — New signature request
- `signature.approved` — Signature approved
- `signature.rejected` — Signature rejected
- `balance.updated` — Balance changed
- `wallet.created` — New wallet created
- `sync.completed` — Sync finished

**Client Commands:**
- Send `"ping"` → Receive `{"type":"pong"}`
- Send `"history"` → Receive recent event history

---

## Authentication

**Current:** Most endpoints are public (no auth required).

**Exempt Paths:**
- `/api/health`
- `/api/dashboard/*`
- `/api/wallets/*`
- `/api/transactions/*`
- `/api/signatures/*`
- `/api/scheduled/*`
- `/api/networks/*`

**Future:** Bearer token authentication may be added for write operations.

---

## Rate Limiting

**Current:** No rate limiting.

**Recommendation:** Client-side implement retry with exponential backoff for 5xx errors.

---

## CORS

**Allowed Origins:**
- `http://localhost:3000` (dev)
- `https://orgon.asystem.ai` (prod)
- `*` (for development)

**Allowed Methods:** GET, POST, PUT, DELETE, OPTIONS

---

## Error Responses

**Format:**
```json
{
  "detail": "Error message here"
}
```

**Common Status Codes:**
- `200` — Success
- `400` — Bad Request (invalid input)
- `404` — Not Found
- `500` — Internal Server Error

---

## Examples

### Full Transaction Flow

1. **Validate transaction:**
```bash
curl -X POST https://orgon.asystem.ai/api/transactions/validate \
  -H "Content-Type: application/json" \
  -d '{
    "token": "USDT",
    "to_address": "TRecipient...",
    "value": "100",
    "check_balance": true
  }'
```

2. **Send transaction:**
```bash
curl -X POST https://orgon.asystem.ai/api/transactions \
  -H "Content-Type: application/json" \
  -d '{
    "token": "TRX:::1###my-wallet",
    "to_address": "TRecipient...",
    "value": "100",
    "info": "Payment"
  }'
```

3. **Check status:**
```bash
curl https://orgon.asystem.ai/api/transactions/tx-123
```

### Schedule Monthly Payment

```bash
curl -X POST https://orgon.asystem.ai/api/scheduled \
  -H "Content-Type: application/json" \
  -d '{
    "token": "TRX:::1###my-wallet",
    "to_address": "TRecipient...",
    "value": "5000",
    "scheduled_at": "2026-02-07T10:00:00Z",
    "recurrence_rule": "0 10 1 * *",
    "info": "Monthly salary"
  }'
```

---

## Interactive Documentation

**Best way to explore:** Visit https://orgon.asystem.ai/docs

**Features:**
- Try all endpoints directly from browser
- See request/response schemas
- Auto-generated from code
- Always up-to-date

---

**Version:** 1.1.0  
**Last Updated:** 2026-02-06  
**Contact:** GitHub Issues / Telegram
