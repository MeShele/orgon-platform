# ORGON Webhook Receiver Example

Example FastAPI application that demonstrates how to receive and verify webhook events from ORGON Partner API.

## Features

- ✅ HMAC-SHA256 signature verification
- ✅ Event type routing
- ✅ Idempotency support (Event ID)
- ✅ Error handling
- ✅ Logging

## Installation

```bash
# Install dependencies (if not already installed)
pip install fastapi uvicorn

# Or use the existing ORGON environment
cd /Users/urmatmyrzabekov/AGENT/ORGON
source venv/bin/activate  # if using virtualenv
```

## Configuration

Edit `webhook_receiver.py` and set your API secret:

```python
API_SECRET = "your_api_secret_here"  # From .test_credentials.env
```

## Running

```bash
# Start the webhook receiver
python3 backend/examples/webhook_receiver.py

# Or with uvicorn directly
uvicorn backend.examples.webhook_receiver:app --host 0.0.0.0 --port 9000
```

The receiver will start on `http://localhost:9000`

## Testing

### 1. Register Webhook URL

Using cURL:

```bash
curl -X POST http://localhost:8890/api/v1/partner/webhooks \
  -H "X-API-Key: your_api_key" \
  -H "X-API-Secret: your_api_secret" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "http://localhost:9000/webhooks/orgon",
    "event_types": ["wallet.*", "transaction.*", "signature.*"],
    "description": "Test webhook receiver"
  }'
```

Using Python SDK:

```python
from partner_api_client import ORGONPartnerClient

client = ORGONPartnerClient(
    api_key="your_key",
    api_secret="your_secret"
)

webhook_id = client.register_webhook(
    url="http://localhost:9000/webhooks/orgon",
    event_types=["wallet.*", "transaction.*", "signature.*"],
    description="Test webhook receiver"
)
```

### 2. Trigger Events

Create a wallet via Partner API:

```bash
curl -X POST http://localhost:8890/api/v1/partner/wallets \
  -H "X-API-Key: your_api_key" \
  -H "X-API-Secret: your_api_secret" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "test-webhook-wallet",
    "network_id": 5010,
    "wallet_type": 1
  }'
```

Watch the webhook receiver logs - you should see:

```
[2026-02-08 06:00:00] Webhook received:
  Event ID: 550e8400-e29b-41d4-a716-446655440000
  Event Type: wallet.created
  Timestamp: 2026-02-08T00:00:00Z
  Data: {
    "wallet_name": "test-webhook-wallet",
    "network_id": 5010,
    "wallet_type": 1,
    "address": "",
    "created_at": "2026-02-08T00:00:00Z"
  }
  ✅ New wallet created: test-webhook-wallet
     Network: 5010
     Address: N/A
```

## Event Types

The receiver handles these event types:

### wallet.created
Triggered when a new wallet is created via Partner API.

**Payload:**
```json
{
  "event_id": "uuid",
  "event_type": "wallet.created",
  "timestamp": "2026-02-08T00:00:00Z",
  "data": {
    "wallet_name": "string",
    "network_id": 5010,
    "wallet_type": 1,
    "address": "string",
    "label": "string",
    "created_at": "2026-02-08T00:00:00Z"
  }
}
```

### transaction.created
Triggered when a new transaction is initiated.

**Payload:**
```json
{
  "event_id": "uuid",
  "event_type": "transaction.created",
  "timestamp": "2026-02-08T00:00:00Z",
  "data": {
    "unid": "string",
    "wallet_name": "string",
    "token": "TRX",
    "to_address": "string",
    "amount": "100.50",
    "status": "pending",
    "created_at": "2026-02-08T00:00:00Z"
  }
}
```

### signature.approved
Triggered when a transaction signature is approved.

**Payload:**
```json
{
  "event_id": "uuid",
  "event_type": "signature.approved",
  "timestamp": "2026-02-08T00:00:00Z",
  "data": {
    "unid": "string",
    "approved_by": "0xAddress",
    "approved_at": "2026-02-08T00:00:00Z"
  }
}
```

### signature.rejected
Triggered when a transaction signature is rejected.

**Payload:**
```json
{
  "event_id": "uuid",
  "event_type": "signature.rejected",
  "timestamp": "2026-02-08T00:00:00Z",
  "data": {
    "unid": "string",
    "rejected_by": "0xAddress",
    "reason": "Insufficient funds",
    "rejected_at": "2026-02-08T00:00:00Z"
  }
}
```

## Signature Verification

All webhooks include an `X-Webhook-Signature` header with HMAC-SHA256 signature.

**Verification algorithm:**

```python
import hmac
import hashlib

def verify_signature(payload_bytes: bytes, signature: str, secret: str) -> bool:
    expected = hmac.new(
        secret.encode(),
        payload_bytes,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected)
```

**Always verify signatures** to prevent spoofing!

## Idempotency

Each event has a unique `event_id` (UUID). Use this to detect and skip duplicate deliveries:

```python
# Store processed event IDs in database or cache
processed_events = set()

if event_id in processed_events:
    return {"status": "duplicate", "event_id": event_id}

# Process event...
processed_events.add(event_id)
```

## Error Handling

- Return `200 OK` to acknowledge successful receipt
- Return `4xx/5xx` to trigger retry with exponential backoff
- ORGON will retry failed webhooks: 1m, 5m, 15m, 1h, 6h (max 5 attempts)

## Production Deployment

### Security

1. **Use HTTPS** - ORGON validates webhook URLs in production
2. **Verify signatures** - Always check `X-Webhook-Signature`
3. **Validate payload** - Use Pydantic models or JSON schema
4. **Rate limiting** - Protect against webhook floods
5. **Secrets management** - Store API secret in environment variables

### Reliability

1. **Idempotency** - Track `event_id` to handle duplicates
2. **Async processing** - Queue events for background processing
3. **Monitoring** - Log all webhook receipts and errors
4. **Alerting** - Alert on webhook failures

### Example Production Setup

```python
import os
from fastapi import FastAPI, BackgroundTasks
from redis import Redis

app = FastAPI()
redis = Redis.from_url(os.getenv("REDIS_URL"))

@app.post("/webhooks/orgon")
async def receive_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_webhook_signature: str = Header(...),
    x_event_id: str = Header(...)
):
    # Verify signature
    body = await request.body()
    if not verify_signature(body, x_webhook_signature, os.getenv("API_SECRET")):
        raise HTTPException(401, "Invalid signature")
    
    # Check idempotency
    if redis.exists(f"webhook:{x_event_id}"):
        return {"status": "duplicate"}
    
    # Mark as processed (24h TTL)
    redis.setex(f"webhook:{x_event_id}", 86400, "1")
    
    # Queue for background processing
    payload = json.loads(body)
    background_tasks.add_task(process_webhook, payload)
    
    return {"status": "queued"}
```

## Troubleshooting

### Webhook not received

1. Check if webhook is registered:
   ```bash
   curl http://localhost:8890/api/v1/partner/webhooks \
     -H "X-API-Key: your_key" \
     -H "X-API-Secret: your_secret"
   ```

2. Check event log:
   ```bash
   curl http://localhost:8890/api/v1/partner/webhooks/events \
     -H "X-API-Key: your_key" \
     -H "X-API-Secret: your_secret"
   ```

3. Verify receiver is running:
   ```bash
   curl http://localhost:9000/health
   ```

### Signature verification failed

1. Ensure you're using the correct API secret
2. Verify you're hashing the raw request body (not parsed JSON)
3. Check for encoding issues (UTF-8)

### Events arriving out of order

This is normal - use `timestamp` field to order events if needed.

## Support

- Documentation: https://docs.orgon.asystem.ai
- Issues: https://github.com/asystem/orgon/issues
- Email: support@asystem.ai
