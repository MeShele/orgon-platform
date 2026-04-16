"""
WebhookService - Real-time event notifications for B2B partners
Handles webhook event queuing, delivery, retry logic, and HMAC signatures
"""

import asyncio
import hmac
import hashlib
import httpx
import asyncpg
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
import json


class WebhookService:
    """
    Manage webhook delivery for B2B platform events.
    
    Features:
    - Event queuing (PostgreSQL)
    - Async HTTP delivery with timeouts
    - HMAC-SHA256 signature verification
    - Exponential backoff retry (1m, 5m, 15m, 1h, 6h)
    - Delivery statistics tracking
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        """
        Initialize WebhookService.
        
        Args:
            db_pool: asyncpg.Pool for database operations
        """
        self.db = db_pool
        self.http_client = httpx.AsyncClient(timeout=10.0)
    
    # ========================================================================
    # EVENT EMISSION
    # ========================================================================
    
    async def emit_event(
        self,
        partner_id: UUID | str,
        event_type: str,
        payload: Dict[str, Any],
        webhook_url: Optional[str] = None
    ) -> UUID:
        """
        Queue a webhook event for delivery.
        
        Args:
            partner_id: Partner UUID
            event_type: Event type (wallet.created, tx.confirmed, etc.)
            payload: Event data (JSON-serializable)
            webhook_url: Optional override webhook URL (defaults to partner config)
            
        Returns:
            event_id (UUID)
        """
        event_id = uuid4()
        
        # Convert partner_id to UUID if string
        if isinstance(partner_id, str):
            partner_id = UUID(partner_id)
        
        # Get webhook URL from partner config if not provided
        if not webhook_url:
            webhook_url = await self._get_partner_webhook_url(partner_id, event_type)
        
        if not webhook_url:
            # No webhook configured for this partner/event type
            return event_id
        
        # Insert event into queue
        query = """
            INSERT INTO webhook_events 
            (event_id, partner_id, event_type, payload, webhook_url, status, created_at)
            VALUES ($1, $2, $3, $4, $5, 'pending', NOW())
            RETURNING id
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(
                query,
                event_id,
                partner_id,
                event_type,
                json.dumps(payload),
                webhook_url
            )
        
        return event_id
    
    async def _get_partner_webhook_url(
        self,
        partner_id: UUID,
        event_type: str
    ) -> Optional[str]:
        """
        Get webhook URL for partner based on event type.
        
        Args:
            partner_id: Partner UUID
            event_type: Event type (wallet.created, etc.)
            
        Returns:
            Webhook URL or None if not configured
        """
        query = """
            SELECT url FROM partner_webhooks
            WHERE partner_id = $1 
              AND is_active = true
              AND (
                  $2 = ANY(event_types) 
                  OR EXISTS (
                      SELECT 1 FROM unnest(event_types) AS et 
                      WHERE $2 LIKE REPLACE(et, '*', '%')
                  )
              )
            LIMIT 1
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, partner_id, event_type)
            return row["url"] if row else None
    
    # ========================================================================
    # WEBHOOK DELIVERY
    # ========================================================================
    
    async def process_pending_events(self, batch_size: int = 100) -> int:
        """
        Process pending webhook events (background worker job).
        
        Args:
            batch_size: Maximum events to process in one run
            
        Returns:
            Number of events processed
        """
        # Fetch pending events ready for delivery
        query = """
            SELECT id, event_id, partner_id, event_type, payload, webhook_url, attempts, max_attempts
            FROM webhook_events
            WHERE status = 'pending'
              AND (next_retry_at IS NULL OR next_retry_at <= NOW())
            ORDER BY created_at
            LIMIT $1
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, batch_size)
        
        processed = 0
        for row in rows:
            try:
                await self.deliver_event(dict(row))
                processed += 1
            except Exception as e:
                # Log error but continue processing other events
                print(f"Error delivering event {row['event_id']}: {e}")
        
        return processed
    
    async def deliver_event(self, event: Dict[str, Any]) -> bool:
        """
        Deliver a single webhook event via HTTP POST.
        
        Args:
            event: Event record from webhook_events table
            
        Returns:
            True if delivered successfully, False otherwise
        """
        event_id = event["event_id"]
        partner_id = event["partner_id"]
        event_type = event["event_type"]
        payload = json.loads(event["payload"]) if isinstance(event["payload"], str) else event["payload"]
        webhook_url = event["webhook_url"]
        attempts = event["attempts"]
        max_attempts = event["max_attempts"]
        
        # Generate HMAC signature
        signature = await self._generate_signature(partner_id, payload)
        
        # Prepare webhook payload
        webhook_payload = {
            "event_id": str(event_id),
            "event_type": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": payload
        }
        
        # HTTP POST with signature
        headers = {
            "Content-Type": "application/json",
            "X-Webhook-Signature": signature,
            "X-Event-ID": str(event_id),
            "X-Event-Type": event_type,
            "User-Agent": "ORGON-Webhook/1.0"
        }
        
        try:
            start_time = datetime.now(timezone.utc)
            response = await self.http_client.post(
                webhook_url,
                json=webhook_payload,
                headers=headers,
                timeout=10.0
            )
            delivery_ms = int((datetime.now(timezone.utc) - start_time).total_seconds() * 1000)
            
            # Mark as delivered if 2xx status
            if 200 <= response.status_code < 300:
                await self._mark_delivered(event["id"], delivery_ms, response.status_code)
                return True
            else:
                # Non-2xx response - retry
                await self._mark_failed(
                    event["id"],
                    attempts + 1,
                    max_attempts,
                    f"HTTP {response.status_code}: {response.text[:500]}"
                )
                return False
                
        except httpx.TimeoutException as e:
            await self._mark_failed(
                event["id"],
                attempts + 1,
                max_attempts,
                f"Timeout after 10s: {str(e)}"
            )
            return False
            
        except Exception as e:
            await self._mark_failed(
                event["id"],
                attempts + 1,
                max_attempts,
                f"Error: {str(e)}"
            )
            return False
    
    async def _generate_signature(
        self,
        partner_id: UUID,
        payload: Dict[str, Any]
    ) -> str:
        """
        Generate HMAC-SHA256 signature for webhook verification.
        
        Args:
            partner_id: Partner UUID
            payload: Event payload
            
        Returns:
            Hex-encoded HMAC signature
        """
        # Get partner's API secret (or webhook secret if configured)
        secret = await self._get_partner_secret(partner_id)
        if not secret:
            raise ValueError(f"No webhook secret configured for partner {partner_id}")
        
        # Create signature: HMAC-SHA256(secret, JSON payload)
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        signature = hmac.new(
            secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    async def _get_partner_secret(self, partner_id: UUID) -> Optional[str]:
        """Get partner's webhook secret (or API secret as fallback)."""
        query = """
            SELECT COALESCE(
                (SELECT secret FROM partner_webhooks WHERE partner_id = $1 AND secret IS NOT NULL LIMIT 1),
                (SELECT api_secret FROM partners WHERE partner_id = $1)
            ) AS secret
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(query, partner_id)
            return row["secret"] if row else None
    
    async def _mark_delivered(
        self,
        event_id: int,
        delivery_ms: int,
        status_code: int
    ):
        """Mark event as successfully delivered."""
        query = """
            UPDATE webhook_events
            SET status = 'delivered',
                delivered_at = NOW(),
                response_code = $2,
                response_body = $3
            WHERE id = $1
        """
        
        async with self.db.acquire() as conn:
            await conn.execute(
                query,
                event_id,
                status_code,
                f"Delivered in {delivery_ms}ms"
            )
    
    async def _mark_failed(
        self,
        event_id: int,
        attempts: int,
        max_attempts: int,
        error_message: str
    ):
        """Mark event as failed and schedule retry with exponential backoff."""
        # Exponential backoff: 1m, 5m, 15m, 1h, 6h
        backoff_minutes = [1, 5, 15, 60, 360]
        
        if attempts >= max_attempts:
            # Max retries reached - mark as permanently failed
            query = """
                UPDATE webhook_events
                SET status = 'failed',
                    attempts = $2,
                    error_message = $3,
                    last_attempt_at = NOW()
                WHERE id = $1
            """
            
            async with self.db.acquire() as conn:
                await conn.execute(query, event_id, attempts, error_message)
        else:
            # Schedule retry with backoff
            backoff_idx = min(attempts - 1, len(backoff_minutes) - 1)
            retry_delay = timedelta(minutes=backoff_minutes[backoff_idx])
            next_retry = datetime.now(timezone.utc) + retry_delay
            
            query = """
                UPDATE webhook_events
                SET attempts = $2,
                    next_retry_at = $3,
                    error_message = $4,
                    last_attempt_at = NOW()
                WHERE id = $1
            """
            
            async with self.db.acquire() as conn:
                await conn.execute(
                    query,
                    event_id,
                    attempts,
                    next_retry,
                    error_message
                )
    
    # ========================================================================
    # WEBHOOK CONFIGURATION MANAGEMENT
    # ========================================================================
    
    async def register_webhook(
        self,
        partner_id: UUID | str,
        url: str,
        event_types: List[str],
        description: Optional[str] = None,
        secret: Optional[str] = None
    ) -> int:
        """
        Register a webhook URL for a partner.
        
        Args:
            partner_id: Partner UUID
            url: Webhook endpoint URL
            event_types: List of event type patterns (e.g., ['wallet.*', 'transaction.confirmed'])
            description: Optional description
            secret: Optional custom HMAC secret (overrides API secret)
            
        Returns:
            webhook_id
        """
        if isinstance(partner_id, str):
            partner_id = UUID(partner_id)
        
        query = """
            INSERT INTO partner_webhooks 
            (partner_id, url, event_types, description, secret, is_active, created_at, updated_at)
            VALUES ($1, $2, $3, $4, $5, true, NOW(), NOW())
            ON CONFLICT (partner_id, url) DO UPDATE
            SET event_types = EXCLUDED.event_types,
                description = EXCLUDED.description,
                secret = EXCLUDED.secret,
                updated_at = NOW()
            RETURNING id
        """
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                query,
                partner_id,
                url,
                event_types,
                description,
                secret
            )
            return row["id"]
    
    async def list_webhooks(self, partner_id: UUID | str) -> List[Dict[str, Any]]:
        """List all webhooks for a partner."""
        if isinstance(partner_id, str):
            partner_id = UUID(partner_id)
        
        query = """
            SELECT id, url, event_types, description, is_active, 
                   success_count, failure_count, created_at, updated_at
            FROM partner_webhooks
            WHERE partner_id = $1
            ORDER BY created_at DESC
        """
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, partner_id)
            return [dict(row) for row in rows]
    
    async def delete_webhook(self, webhook_id: int, partner_id: UUID | str) -> bool:
        """Delete a webhook configuration."""
        if isinstance(partner_id, str):
            partner_id = UUID(partner_id)
        
        query = """
            DELETE FROM partner_webhooks
            WHERE id = $1 AND partner_id = $2
        """
        
        async with self.db.acquire() as conn:
            result = await conn.execute(query, webhook_id, partner_id)
            return result.split()[-1] == "1"  # Check if 1 row deleted
    
    # ========================================================================
    # EVENT LOG & STATISTICS
    # ========================================================================
    
    async def get_event_log(
        self,
        partner_id: UUID | str,
        limit: int = 100,
        offset: int = 0,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get webhook event log for a partner.
        
        Args:
            partner_id: Partner UUID
            limit: Maximum events to return
            offset: Pagination offset
            status: Optional filter by status (pending, delivered, failed)
            
        Returns:
            List of event records
        """
        if isinstance(partner_id, str):
            partner_id = UUID(partner_id)
        
        query = """
            SELECT event_id, event_type, status, attempts, created_at, delivered_at, 
                   error_message, response_code
            FROM webhook_events
            WHERE partner_id = $1
        """
        
        params = [partner_id]
        if status:
            query += " AND status = $2"
            params.append(status)
        
        query += " ORDER BY created_at DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)
        
        query += " OFFSET $" + str(len(params) + 1)
        params.append(offset)
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    async def verify_signature(
        self,
        payload: Dict[str, Any],
        signature: str,
        secret: str
    ) -> bool:
        """
        Verify HMAC signature from webhook receiver.
        
        Args:
            payload: Event payload
            signature: Received signature (hex)
            secret: Partner's webhook secret
            
        Returns:
            True if signature is valid
        """
        # Compute expected signature
        payload_bytes = json.dumps(payload, sort_keys=True).encode()
        expected = hmac.new(
            secret.encode(),
            payload_bytes,
            hashlib.sha256
        ).hexdigest()
        
        # Constant-time comparison
        return hmac.compare_digest(signature, expected)
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()
