# API Reference: Billing & Compliance

**Version:** 2.0 (Phase 2 complete)  
**Base URL:** `/api/v1`  
**Authentication:** JWT Bearer token  
**Last Updated:** 2026-02-12

---

## Table of Contents

1. [Billing API](#billing-api)
   - Subscription Plans
   - Subscriptions
   - Invoices
   - Payments
   - Transaction Fees
   - Billing Dashboard

2. [Compliance API](#compliance-api)
   - KYC Records
   - AML Alerts
   - Compliance Reports
   - Sanctioned Addresses
   - Transaction Monitoring

---

## Billing API

### Subscription Plans

#### List Plans
```http
GET /api/v1/billing/plans
```

**Query Parameters:**
- `is_active` (boolean, optional) - Filter by active status
- `is_public` (boolean, optional) - Filter by public visibility

**Response:**
```json
{
  "plans": [
    {
      "id": "uuid",
      "name": "Starter",
      "slug": "starter",
      "description": "Perfect for small crypto exchanges",
      "price_monthly": 99.00,
      "price_yearly": 990.00,
      "currency": "USD",
      "features": {
        "max_users": 10,
        "max_wallets": 50,
        "max_transactions_per_month": 1000
      },
      "trial_days": 14,
      "is_active": true,
      "is_public": true
    }
  ]
}
```

---

### Subscriptions

#### Create Subscription
```http
POST /api/v1/billing/subscriptions
```

**Headers:**
- `Authorization: Bearer <token>`

**Request Body:**
```json
{
  "organization_id": "uuid",
  "plan_id": "uuid",
  "billing_cycle": "monthly",  // or "yearly"
  "start_trial": true
}
```

**Response:**
```json
{
  "subscription": {
    "id": "uuid",
    "organization_id": "uuid",
    "plan_id": "uuid",
    "status": "trial",
    "trial_start_date": "2026-02-12T00:00:00Z",
    "trial_end_date": "2026-02-26T00:00:00Z",
    "start_date": "2026-02-12T00:00:00Z",
    "current_period_start": "2026-02-12T00:00:00Z",
    "current_period_end": "2026-02-26T00:00:00Z",
    "billing_cycle": "monthly",
    "next_billing_date": "2026-02-26T00:00:00Z",
    "created_at": "2026-02-12T00:00:00Z"
  }
}
```

---

#### Get Subscription
```http
GET /api/v1/billing/subscriptions/{subscription_id}
```

**Headers:**
- `Authorization: Bearer <token>`

**Response:**
```json
{
  "subscription": {
    "id": "uuid",
    "organization_id": "uuid",
    "plan": {
      "id": "uuid",
      "name": "Professional",
      "price_monthly": 299.00
    },
    "status": "active",
    "current_period_start": "2026-02-12T00:00:00Z",
    "current_period_end": "2026-03-12T00:00:00Z",
    "current_usage": {
      "users": 5,
      "wallets": 20,
      "transactions": 450
    }
  }
}
```

---

#### Update Subscription (Upgrade/Downgrade)
```http
PUT /api/v1/billing/subscriptions/{subscription_id}
```

**Request Body:**
```json
{
  "plan_id": "uuid",  // New plan
  "billing_cycle": "yearly"  // Optional: change cycle
}
```

---

#### Cancel Subscription
```http
POST /api/v1/billing/subscriptions/{subscription_id}/cancel
```

**Request Body:**
```json
{
  "reason": "Switching to competitor",
  "cancel_at_period_end": true  // If false, cancel immediately
}
```

**Response:**
```json
{
  "subscription": {
    "id": "uuid",
    "status": "cancelled",
    "cancelled_at": "2026-02-12T00:40:00Z",
    "ended_at": null  // If cancel_at_period_end, this is period_end
  }
}
```

---

### Invoices

#### List Invoices
```http
GET /api/v1/billing/invoices
```

**Query Parameters:**
- `organization_id` (uuid, required) - Filter by organization
- `status` (string, optional) - Filter by status (draft/open/paid/void)
- `from_date` (date, optional) - Filter from date
- `to_date` (date, optional) - Filter to date
- `limit` (int, optional) - Page size (default: 20)
- `offset` (int, optional) - Pagination offset

**Response:**
```json
{
  "invoices": [
    {
      "id": "uuid",
      "invoice_number": "INV-2026-001234",
      "organization_id": "uuid",
      "subscription_id": "uuid",
      "status": "open",
      "total": 99.00,
      "amount_due": 99.00,
      "currency": "USD",
      "issue_date": "2026-02-12",
      "due_date": "2026-02-19",
      "period_start": "2026-02-12",
      "period_end": "2026-03-12"
    }
  ],
  "total": 45,
  "limit": 20,
  "offset": 0
}
```

---

#### Get Invoice Details
```http
GET /api/v1/billing/invoices/{invoice_id}
```

**Response:**
```json
{
  "invoice": {
    "id": "uuid",
    "invoice_number": "INV-2026-001234",
    "status": "open",
    "subtotal": 99.00,
    "tax": 0.00,
    "discount": 0.00,
    "total": 99.00,
    "amount_paid": 0.00,
    "amount_due": 99.00,
    "currency": "USD",
    "line_items": [
      {
        "id": "uuid",
        "description": "Starter Plan - February 2026",
        "item_type": "subscription",
        "quantity": 1,
        "unit_price": 99.00,
        "amount": 99.00
      }
    ]
  }
}
```

---

#### Pay Invoice
```http
POST /api/v1/billing/invoices/{invoice_id}/pay
```

**Request Body:**
```json
{
  "amount": 99.00,
  "payment_method": "card",
  "payment_gateway": "stripe",
  "gateway_transaction_id": "ch_3Abc123..."
}
```

**Response:**
```json
{
  "payment": {
    "id": "uuid",
    "payment_number": "PAY-2026-001234",
    "invoice_id": "uuid",
    "amount": 99.00,
    "status": "succeeded",
    "paid_at": "2026-02-12T00:45:00Z"
  },
  "invoice": {
    "id": "uuid",
    "status": "paid"
  }
}
```

---

### Transaction Fees

#### Record Transaction Fee
```http
POST /api/v1/billing/fees
```

**Request Body:**
```json
{
  "organization_id": "uuid",
  "transaction_type": "withdrawal",
  "transaction_id": "uuid",
  "fee_type": "percentage",
  "fee_amount": 25.00,
  "currency": "USD",
  "base_amount": 1000.00,
  "fee_rate": 0.025
}
```

---

#### Get Fees Summary
```http
GET /api/v1/billing/fees/summary
```

**Query Parameters:**
- `organization_id` (uuid, required)
- `period_start` (date, optional)
- `period_end` (date, optional)

**Response:**
```json
{
  "summary": {
    "organization_id": "uuid",
    "period_start": "2026-02-01",
    "period_end": "2026-02-28",
    "total_fees": 450.50,
    "fees_by_type": {
      "withdrawal": 250.00,
      "exchange": 150.50,
      "deposit": 50.00
    },
    "pending_fees": 100.00,
    "invoiced_fees": 350.50,
    "paid_fees": 0.00
  }
}
```

---

### Billing Dashboard

#### Get Billing Dashboard
```http
GET /api/v1/billing/dashboard/{organization_id}
```

**Response:**
```json
{
  "dashboard": {
    "organization_id": "uuid",
    "current_subscription": {
      "id": "uuid",
      "plan": {
        "name": "Professional",
        "price_monthly": 299.00
      },
      "status": "active",
      "next_billing_date": "2026-03-12T00:00:00Z"
    },
    "account_balance": 0.00,
    "pending_invoices_count": 0,
    "pending_invoices_total": 0.00,
    "last_payment": {
      "id": "uuid",
      "amount": 299.00,
      "paid_at": "2026-02-12T00:45:00Z"
    },
    "usage_this_month": {
      "users": 5,
      "wallets": 20,
      "transactions": 450
    }
  }
}
```

---

## Compliance API

### KYC Records

#### Submit KYC Record
```http
POST /api/v1/compliance/kyc
```

**Request Body:**
```json
{
  "organization_id": "uuid",
  "customer_id": "CUST-12345",
  "customer_name": "John Doe",
  "customer_email": "john@example.com",
  "customer_phone": "+1234567890",
  "kyc_provider": "manual",
  "documents_submitted": {
    "passport": {"provided": true, "verified": false},
    "address_proof": {"provided": true, "verified": false}
  }
}
```

**Response:**
```json
{
  "kyc_record": {
    "id": "uuid",
    "customer_id": "CUST-12345",
    "status": "pending",
    "risk_level": "unknown",
    "submitted_at": "2026-02-12T00:50:00Z"
  }
}
```

---

#### List KYC Records
```http
GET /api/v1/compliance/kyc
```

**Query Parameters:**
- `organization_id` (uuid, required)
- `status` (string, optional) - pending/in_review/approved/rejected/expired
- `risk_level` (string, optional) - low/medium/high
- `limit`, `offset` - Pagination

**Response:**
```json
{
  "kyc_records": [
    {
      "id": "uuid",
      "customer_id": "CUST-12345",
      "customer_name": "John Doe",
      "status": "approved",
      "risk_level": "low",
      "verified_at": "2026-02-12T01:00:00Z"
    }
  ]
}
```

---

#### Update KYC Status
```http
PUT /api/v1/compliance/kyc/{kyc_id}/status
```

**Request Body:**
```json
{
  "status": "approved",  // approved/rejected
  "risk_level": "low",
  "verified_by": "compliance_officer_1",
  "risk_factors": {
    "identity_verified": true,
    "sanctions_check": "clear"
  },
  "rejection_reason": null  // If rejected
}
```

---

### AML Alerts

#### List AML Alerts
```http
GET /api/v1/compliance/aml/alerts
```

**Query Parameters:**
- `organization_id` (uuid, required)
- `status` (string, optional) - open/investigating/resolved/blocked
- `severity` (string, optional) - low/medium/high/critical
- `alert_type` (string, optional)

**Response:**
```json
{
  "alerts": [
    {
      "id": "uuid",
      "alert_type": "high_value",
      "severity": "high",
      "status": "open",
      "amount": 150000.00,
      "description": "Large transaction detected",
      "detected_at": "2026-02-12T01:05:00Z"
    }
  ]
}
```

---

#### Resolve AML Alert
```http
PUT /api/v1/compliance/aml/alerts/{alert_id}/resolve
```

**Request Body:**
```json
{
  "resolution": "false_positive",  // false_positive/legitimate_concern/escalated
  "investigation_notes": "Verified legitimate business transaction",
  "requires_sar": false,
  "resolved_by": "investigator_1"
}
```

---

### Compliance Reports

#### Generate Report
```http
POST /api/v1/compliance/reports/generate
```

**Request Body:**
```json
{
  "organization_id": "uuid",
  "report_type": "monthly_transactions",
  "period_start": "2026-02-01",
  "period_end": "2026-02-28",
  "export_format": "pdf"  // pdf/excel/xml
}
```

**Response:**
```json
{
  "report": {
    "id": "uuid",
    "report_number": "COMP-202602-ABC123",
    "status": "draft",
    "generated_at": "2026-02-12T01:10:00Z"
  }
}
```

---

#### List Reports
```http
GET /api/v1/compliance/reports
```

**Query Parameters:**
- `organization_id` (uuid, required)
- `report_type` (string, optional)
- `status` (string, optional)

---

#### Download Report
```http
GET /api/v1/compliance/reports/{report_id}/download
```

**Response:**
- Content-Type: application/pdf (or excel/xml)
- Content-Disposition: attachment; filename="COMP-202602-ABC123.pdf"

---

## Error Responses

### Standard Error Format
```json
{
  "error": {
    "code": "INVALID_REQUEST",
    "message": "Subscription plan not found",
    "details": {
      "plan_id": "uuid"
    }
  }
}
```

### HTTP Status Codes
- `200 OK` - Success
- `201 Created` - Resource created
- `400 Bad Request` - Invalid request
- `401 Unauthorized` - Missing/invalid authentication
- `403 Forbidden` - Insufficient permissions
- `404 Not Found` - Resource not found
- `409 Conflict` - Resource conflict (e.g., duplicate subscription)
- `422 Unprocessable Entity` - Validation error
- `500 Internal Server Error` - Server error

---

## Rate Limiting

- **Limit:** 100 requests per minute per organization
- **Headers:**
  - `X-RateLimit-Limit: 100`
  - `X-RateLimit-Remaining: 95`
  - `X-RateLimit-Reset: 1707705600`

---

## Webhooks (Future Feature)

### Supported Events
- `subscription.created`
- `subscription.cancelled`
- `invoice.generated`
- `invoice.paid`
- `payment.succeeded`
- `payment.failed`
- `aml.alert.created`
- `kyc.status.changed`

---

## SDK Examples

### cURL
```bash
# Create subscription
curl -X POST https://api.orgon.example.com/api/v1/billing/subscriptions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "organization_id": "uuid",
    "plan_id": "uuid",
    "billing_cycle": "monthly"
  }'
```

### Python
```python
import requests

url = "https://api.orgon.example.com/api/v1/billing/subscriptions"
headers = {
    "Authorization": "Bearer YOUR_TOKEN",
    "Content-Type": "application/json"
}
data = {
    "organization_id": "uuid",
    "plan_id": "uuid",
    "billing_cycle": "monthly"
}

response = requests.post(url, headers=headers, json=data)
subscription = response.json()
```

### JavaScript
```javascript
const response = await fetch('https://api.orgon.example.com/api/v1/billing/subscriptions', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer YOUR_TOKEN',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    organization_id: 'uuid',
    plan_id: 'uuid',
    billing_cycle: 'monthly'
  })
});

const subscription = await response.json();
```

---

## Support

- **Documentation:** https://docs.orgon.example.com
- **API Status:** https://status.orgon.example.com
- **Support:** support@orgon.example.com

---

**Last Updated:** 2026-02-12  
**Version:** 2.0 (Phase 2 complete)
