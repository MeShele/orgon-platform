# Partner Onboarding Guide - ASYSTEM ORGON B2B Platform

**Version:** 1.0.0  
**Last Updated:** 2026-02-08

Welcome to ASYSTEM ORGON! This guide will help you integrate our multisig wallet platform into your application.

---

## Table of Contents

1. [Overview](#overview)
2. [Account Setup](#account-setup)
3. [Authentication](#authentication)
4. [Quick Start](#quick-start)
5. [Core Workflows](#core-workflows)
6. [Webhooks](#webhooks)
7. [Error Handling](#error-handling)
8. [Rate Limits](#rate-limits)
9. [Support](#support)

---

## Overview

ASYSTEM ORGON is a Wallet-as-a-Service (WaaS) platform that provides:

✅ **Multisig wallet management** (Tron, Ethereum, Bitcoin)  
✅ **Transaction creation and approval** (threshold signatures)  
✅ **Real-time event notifications** (webhooks)  
✅ **Analytics and reporting** (USD-denominated)  
✅ **RESTful Partner API** (production-ready)

**Supported Networks:**
- Tron Mainnet (network_id: 5000)
- Tron Nile Testnet (network_id: 5010)
- Ethereum, Bitcoin (coming soon)

---

## Account Setup

### Step 1: Contact Sales

Email: sales@asystem.ai  
Telegram: @urmatdigital

**What we need:**
- Company name and website
- Use case description
- Expected transaction volume
- Desired tier (free, starter, business, enterprise)

### Step 2: Receive API Credentials

You will receive:
- **API Key** (64-char hex string)
- **API Secret** (64-char hex string)
- **Partner ID** (UUID)
- **Tier** (determines rate limits)

**Example:**
```json
{
  "partner_id": "1af82f50-ae2d-4661-b5dc-c206fb567a3d",
  "api_key": "cbf9b1782a2d62ce17f219e210f4920a0f21b9700ec01c40906fa7e7a0b9e678",
  "api_secret": "89971655acdadfbc3e37cf55b64a4a0afe2bf62ed4e0b2ec04b3eaff55697727",
  "tier": "business",
  "rate_limit_per_minute": 1000
}
```

⚠️ **Store credentials securely!** Use environment variables, never hardcode in source code.

### Step 3: Verify Access

Test your credentials:

```bash
curl -X GET https://orgon.asystem.ai/api/v1/partner/wallets \
  -H "X-API-Key: YOUR_API_KEY" \
  -H "X-API-Secret: YOUR_API_SECRET"
```

Expected response:
```json
{
  "wallets": [],
  "total": 0,
  "page": 1,
  "limit": 50
}
```

---

## Authentication

### Header-based Authentication

Every Partner API request requires two headers:

```http
X-API-Key: <your_api_key>
X-API-Secret: <your_api_secret>
```

**Example (curl):**
```bash
curl -X GET https://orgon.asystem.ai/api/v1/partner/wallets \
  -H "X-API-Key: cbf9b1782..." \
  -H "X-API-Secret: 89971655..."
```

**Example (Python):**
```python
import requests

API_KEY = "cbf9b1782a2d62ce17f219e210f4920a0f21b9700ec01c40906fa7e7a0b9e678"
API_SECRET = "89971655acdadfbc3e37cf55b64a4a0afe2bf62ed4e0b2ec04b3eaff55697727"
BASE_URL = "https://orgon.asystem.ai/api/v1/partner"

headers = {
    "X-API-Key": API_KEY,
    "X-API-Secret": API_SECRET
}

response = requests.get(f"{BASE_URL}/wallets", headers=headers)
print(response.json())
```

**Example (JavaScript/Node.js):**
```javascript
const axios = require('axios');

const API_KEY = "cbf9b1782a2d62ce17f219e210f4920a0f21b9700ec01c40906fa7e7a0b9e678";
const API_SECRET = "89971655acdadfbc3e37cf55b64a4a0afe2bf62ed4e0b2ec04b3eaff55697727";
const BASE_URL = "https://orgon.asystem.ai/api/v1/partner";

const headers = {
  "X-API-Key": API_KEY,
  "X-API-Secret": API_SECRET
};

axios.get(`${BASE_URL}/wallets`, { headers })
  .then(res => console.log(res.data))
  .catch(err => console.error(err.response.data));
```

### Error Responses

**401 Unauthorized:**
```json
{
  "error": "missing_credentials",
  "message": "X-API-Key and X-API-Secret headers are required"
}
```

**403 Forbidden:**
```json
{
  "error": "invalid_credentials",
  "message": "Invalid API key or secret"
}
```

---

## Quick Start

### Create Your First Wallet

**Request:**
```bash
curl -X POST https://orgon.asystem.ai/api/v1/partner/wallets \
  -H "X-API-Key: YOUR_KEY" \
  -H "X-API-Secret: YOUR_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-first-wallet",
    "network_id": 5010,
    "wallet_type": 1,
    "label": "Test Wallet"
  }'
```

**Response (201 Created):**
```json
{
  "name": "my-first-wallet",
  "network": 5010,
  "wallet_type": 1,
  "address": "TXYZabcd1234...",
  "label": "Test Wallet",
  "created_at": "2026-02-08T06:00:00Z"
}
```

### List Your Wallets

**Request:**
```bash
curl -X GET "https://orgon.asystem.ai/api/v1/partner/wallets?limit=10&offset=0" \
  -H "X-API-Key: YOUR_KEY" \
  -H "X-API-Secret: YOUR_SECRET"
```

**Response:**
```json
{
  "wallets": [
    {
      "name": "my-first-wallet",
      "network": 5010,
      "address": "TXYZabcd1234...",
      "label": "Test Wallet",
      "created_at": "2026-02-08T06:00:00Z"
    }
  ],
  "total": 1,
  "page": 1,
  "limit": 10
}
```

### Create a Transaction

**Request:**
```bash
curl -X POST https://orgon.asystem.ai/api/v1/partner/transactions \
  -H "X-API-Key: YOUR_KEY" \
  -H "X-API-Secret: YOUR_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "wallet_name": "my-first-wallet",
    "to_address": "TRecipient123...",
    "token": "TRX",
    "amount": "10.5"
  }'
```

**Response (201 Created):**
```json
{
  "unid": "1234567890abcdef",
  "wallet_name": "my-first-wallet",
  "to_address": "TRecipient123...",
  "token": "TRX",
  "amount": "10.5",
  "status": "pending_signatures",
  "min_signatures": 2,
  "current_signatures": 0,
  "created_at": "2026-02-08T06:05:00Z"
}
```

---

## Core Workflows

### Wallet Management

**Create Wallet:**
```
POST /api/v1/partner/wallets
{
  "name": "unique-wallet-name",
  "network_id": 5000,  // Tron Mainnet
  "wallet_type": 1,     // Multisig
  "label": "Optional label"
}
```

**List Wallets:**
```
GET /api/v1/partner/wallets?limit=50&offset=0
```

**Get Wallet Details:**
```
GET /api/v1/partner/wallets/{name}
```

### Transaction Management

**Create Transaction:**
```
POST /api/v1/partner/transactions
{
  "wallet_name": "my-wallet",
  "to_address": "TRecipient...",
  "token": "TRX",
  "amount": "100.0"
}
```

**List Transactions:**
```
GET /api/v1/partner/transactions?limit=50&offset=0&status=confirmed
```

**Get Transaction:**
```
GET /api/v1/partner/transactions/{unid}
```

### Signature Management

**List Pending Signatures:**
```
GET /api/v1/partner/signatures/pending
```

**Approve Signature:**
```
POST /api/v1/partner/signatures/approve
{
  "unid": "transaction_unid",
  "ec_address": "signer_address"
}
```

**Reject Signature:**
```
POST /api/v1/partner/signatures/reject
{
  "unid": "transaction_unid",
  "ec_address": "signer_address",
  "reason": "Optional reason"
}
```

---

## Webhooks

Receive real-time notifications for wallet and transaction events.

### Setup

**1. Configure Webhook URL (contact support):**
```json
{
  "webhook_url": "https://your-app.com/webhooks/orgon",
  "webhook_secret": "your-secret-key"
}
```

**2. Create Webhook Endpoint:**

```python
# Flask example
from flask import Flask, request
import hmac
import hashlib

app = Flask(__name__)
WEBHOOK_SECRET = "your-secret-key"

@app.route("/webhooks/orgon", methods=["POST"])
def orgon_webhook():
    # Verify signature
    signature = request.headers.get("X-Webhook-Signature")
    body = request.get_data()
    
    expected_signature = hmac.new(
        WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    
    if signature != expected_signature:
        return {"error": "Invalid signature"}, 403
    
    # Process event
    event = request.json
    print(f"Received event: {event['event_type']}")
    
    # Handle event types
    if event["event_type"] == "wallet.created":
        handle_wallet_created(event["payload"])
    elif event["event_type"] == "tx.confirmed":
        handle_transaction_confirmed(event["payload"])
    elif event["event_type"] == "signature.needed":
        handle_signature_needed(event["payload"])
    
    return {"status": "ok"}, 200
```

### Event Types

| Event Type | Trigger |
|------------|---------|
| `wallet.created` | New wallet created |
| `wallet.updated` | Wallet metadata changed |
| `tx.created` | Transaction initiated |
| `tx.pending_signatures` | Awaiting signatures |
| `tx.signed` | Signature added |
| `tx.confirmed` | Transaction confirmed on blockchain |
| `tx.failed` | Transaction failed |
| `signature.needed` | Action required from signer |

### Event Payload

```json
{
  "event_id": "uuid",
  "event_type": "tx.confirmed",
  "timestamp": "2026-02-08T06:10:00Z",
  "payload": {
    "wallet_name": "my-wallet",
    "tx_hash": "0xabcdef...",
    "unid": "1234567890",
    "status": "confirmed",
    "amount": "10.5",
    "token": "TRX"
  }
}
```

### Retry Policy

If your webhook endpoint fails (non-2xx response), we retry with exponential backoff:

1. **1 minute** later
2. **5 minutes** later
3. **15 minutes** later
4. **1 hour** later
5. **6 hours** later

After 5 failed attempts, the webhook is marked as failed and you'll receive an alert.

---

## Error Handling

### HTTP Status Codes

| Code | Meaning | Action |
|------|---------|--------|
| 200 | Success | Process response |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Check request body |
| 401 | Unauthorized | Verify API credentials |
| 403 | Forbidden | Check permissions |
| 404 | Not Found | Resource doesn't exist |
| 409 | Conflict | Resource already exists |
| 429 | Too Many Requests | Slow down, check rate limit |
| 500 | Internal Server Error | Retry with backoff |

### Error Response Format

```json
{
  "error": "error_code",
  "message": "Human-readable description",
  "details": {
    "field": "value"
  }
}
```

### Common Errors

**Wallet already exists:**
```json
{
  "error": "wallet_exists",
  "message": "Wallet with name 'my-wallet' already exists"
}
```

**Insufficient balance:**
```json
{
  "error": "insufficient_balance",
  "message": "Wallet balance (5 TRX) insufficient for transaction (10 TRX + fee)"
}
```

**Rate limit exceeded:**
```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Retry after 60 seconds."
}
```

---

## Rate Limits

### Tier Limits

| Tier | Requests/Min | Requests/Day |
|------|--------------|--------------|
| Free | 60 | 10,000 |
| Starter | 300 | 50,000 |
| Business | 1,000 | 200,000 |
| Enterprise | 5,000 | 1,000,000 |

### Rate Limit Headers

Every response includes:

```http
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 987
X-RateLimit-Reset: 1707384000
```

### Handling Rate Limits

**1. Check headers before each request:**
```python
def check_rate_limit(response):
    remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
    if remaining < 10:
        reset_time = int(response.headers.get("X-RateLimit-Reset", 0))
        sleep_seconds = reset_time - time.time()
        print(f"Rate limit low. Sleeping {sleep_seconds}s...")
        time.sleep(sleep_seconds)
```

**2. Implement exponential backoff on 429:**
```python
import time

def api_request_with_retry(url, max_retries=3):
    for attempt in range(max_retries):
        response = requests.get(url, headers=headers)
        
        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", 60))
            time.sleep(retry_after)
            continue
        
        return response
    
    raise Exception("Max retries exceeded")
```

---

## Support

### Documentation

- **API Reference:** https://orgon.asystem.ai/api/docs
- **GitHub:** https://github.com/asystem/orgon
- **Changelog:** https://github.com/asystem/orgon/releases

### Contact

- **Email:** support@asystem.ai
- **Telegram:** @urmatdigital
- **Business Hours:** Mon-Fri 09:00-18:00 GMT+6

### Upgrade Your Tier

To upgrade from Free to Business:

1. Email sales@asystem.ai
2. Include current `partner_id` and desired tier
3. Receive updated rate limits within 24 hours

---

## Next Steps

1. ✅ Test wallet creation on Testnet (network_id: 5010)
2. ✅ Integrate transaction creation into your app
3. ✅ Set up webhook endpoint for real-time events
4. ✅ Monitor analytics dashboard (contact support for access)
5. ✅ Deploy to Production (network_id: 5000)

**Questions?** Email support@asystem.ai or join our Telegram: t.me/asystem_dev

---

**Last updated:** 2026-02-08  
**Version:** 1.0.0
