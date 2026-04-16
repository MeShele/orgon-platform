"""
ORGON Webhook Receiver Example
Demonstrates how to receive and verify webhook events from ORGON Partner API
"""

import os

import hmac
import hashlib
import json
from typing import Dict, Any
from datetime import datetime

from fastapi import FastAPI, Request, HTTPException, Header
from pydantic import BaseModel


# ============================================================================
# CONFIGURATION
# ============================================================================

# Your API secret (from .test_credentials.env or partner dashboard)
API_SECRET = os.getenv("ORGON_PARTNER_API_SECRET", "SET_YOUR_API_SECRET")

# FastAPI app
app = FastAPI(
    title="ORGON Webhook Receiver",
    description="Example webhook receiver for ORGON Partner API events",
    version="1.0.0"
)


# ============================================================================
# REQUEST SCHEMAS
# ============================================================================

class WebhookPayload(BaseModel):
    """Webhook event payload."""
    event_id: str
    event_type: str
    timestamp: str
    data: Dict[str, Any]


# ============================================================================
# SIGNATURE VERIFICATION
# ============================================================================

def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify HMAC-SHA256 signature from ORGON webhook.
    
    Args:
        payload: Raw request body (bytes)
        signature: X-Webhook-Signature header value
        secret: Your API secret
        
    Returns:
        True if signature is valid
    """
    # Compute expected signature
    expected = hmac.new(
        secret.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    # Constant-time comparison
    return hmac.compare_digest(signature, expected)


# ============================================================================
# WEBHOOK ENDPOINT
# ============================================================================

@app.post("/webhooks/orgon")
async def receive_webhook(
    request: Request,
    x_webhook_signature: str = Header(..., alias="X-Webhook-Signature"),
    x_event_id: str = Header(..., alias="X-Event-ID"),
    x_event_type: str = Header(..., alias="X-Event-Type")
):
    """
    Receive webhook events from ORGON.
    
    Headers:
        X-Webhook-Signature: HMAC-SHA256 signature for verification
        X-Event-ID: Unique event identifier (for idempotency)
        X-Event-Type: Event type (wallet.created, transaction.confirmed, etc.)
    
    Body:
        JSON payload with event data
    """
    # Read raw body for signature verification
    body = await request.body()
    
    # Verify signature
    if not verify_webhook_signature(body, x_webhook_signature, API_SECRET):
        raise HTTPException(
            status_code=401,
            detail="Invalid webhook signature"
        )
    
    # Parse payload
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON payload"
        )
    
    # Log event
    print(f"[{datetime.now()}] Webhook received:")
    print(f"  Event ID: {x_event_id}")
    print(f"  Event Type: {x_event_type}")
    print(f"  Timestamp: {payload.get('timestamp')}")
    print(f"  Data: {json.dumps(payload.get('data'), indent=2)}")
    
    # Process event based on type
    event_type = payload.get("event_type")
    data = payload.get("data", {})
    
    if event_type == "wallet.created":
        handle_wallet_created(data)
    elif event_type == "transaction.created":
        handle_transaction_created(data)
    elif event_type == "transaction.confirmed":
        handle_transaction_confirmed(data)
    elif event_type == "signature.approved":
        handle_signature_approved(data)
    elif event_type == "signature.rejected":
        handle_signature_rejected(data)
    else:
        print(f"  ⚠️  Unknown event type: {event_type}")
    
    # Return 200 OK to acknowledge receipt
    return {
        "status": "received",
        "event_id": x_event_id,
        "processed_at": datetime.now().isoformat()
    }


# ============================================================================
# EVENT HANDLERS
# ============================================================================

def handle_wallet_created(data: Dict[str, Any]):
    """Handle wallet.created event."""
    print(f"  ✅ New wallet created: {data.get('wallet_name')}")
    print(f"     Network: {data.get('network_id')}")
    print(f"     Address: {data.get('address', 'N/A')}")
    
    # TODO: Add your business logic here
    # Examples:
    # - Send email notification
    # - Update internal database
    # - Trigger KYC process


def handle_transaction_created(data: Dict[str, Any]):
    """Handle transaction.created event."""
    print(f"  💸 New transaction created: {data.get('unid')}")
    print(f"     From: {data.get('wallet_name')}")
    print(f"     To: {data.get('to_address')}")
    print(f"     Amount: {data.get('amount')} {data.get('token')}")
    
    # TODO: Add your business logic here
    # Examples:
    # - Update order status
    # - Notify user of pending transaction
    # - Log to accounting system


def handle_transaction_confirmed(data: Dict[str, Any]):
    """Handle transaction.confirmed event."""
    print(f"  ✅ Transaction confirmed: {data.get('unid')}")
    print(f"     TX Hash: {data.get('tx_hash')}")
    
    # TODO: Add your business logic here
    # Examples:
    # - Mark payment as complete
    # - Release goods/services
    # - Send confirmation email


def handle_signature_approved(data: Dict[str, Any]):
    """Handle signature.approved event."""
    print(f"  ✍️  Signature approved: {data.get('unid')}")
    print(f"     Approved by: {data.get('approved_by')}")
    
    # TODO: Add your business logic here


def handle_signature_rejected(data: Dict[str, Any]):
    """Handle signature.rejected event."""
    print(f"  ❌ Signature rejected: {data.get('unid')}")
    print(f"     Rejected by: {data.get('rejected_by')}")
    print(f"     Reason: {data.get('reason', 'N/A')}")
    
    # TODO: Add your business logic here


# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": "ORGON Webhook Receiver",
        "timestamp": datetime.now().isoformat()
    }


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 80)
    print("ORGON Webhook Receiver - Example")
    print("=" * 80)
    print()
    print("Starting webhook receiver on http://localhost:9000")
    print()
    print("To test, register this webhook in ORGON:")
    print("  URL: http://localhost:9000/webhooks/orgon")
    print("  Event types: [\"wallet.*\", \"transaction.*\", \"signature.*\"]")
    print()
    print("Press Ctrl+C to stop")
    print("=" * 80)
    print()
    
    uvicorn.run(app, host="0.0.0.0", port=9000, log_level="info")
