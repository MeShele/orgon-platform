"""
Partner Service - B2B Partner Management
Handles partner lifecycle, API keys, tier management
"""

import secrets
import bcrypt
import asyncpg
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import UUID

class PartnerService:
    """
    Manage B2B partners and their API access.
    
    Partners represent external organizations using ASYSTEM/ORGON platform
    via REST API. Each partner has API keys, tier limits, and webhook config.
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    # ========================================================================
    # PARTNER CRUD
    # ========================================================================
    
    async def create_partner(
        self,
        name: str,
        ec_address: str,
        tier: str = "free",
        webhook_url: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Create new B2B partner with auto-generated API key.
        
        Args:
            name: Partner organization name
            ec_address: Partner's Ethereum-compatible address (unique identifier)
            tier: Subscription tier (free, starter, business, enterprise)
            webhook_url: Optional webhook endpoint for events
            webhook_secret: Optional secret for webhook HMAC
            metadata: Additional partner data (JSON)
        
        Returns:
            Dict with partner_id, api_key, api_secret (plaintext, one-time)
        
        Raises:
            ValueError: Invalid tier or duplicate ec_address
        """
        # Validate tier
        valid_tiers = ["free", "starter", "business", "enterprise"]
        if tier not in valid_tiers:
            raise ValueError(f"Invalid tier: {tier}. Must be one of {valid_tiers}")
        
        # Generate API credentials
        api_key = self._generate_api_key()
        api_secret = self._generate_api_secret()
        api_secret_hash = self._hash_secret(api_secret)
        
        # Default rate limits per tier
        rate_limits = {
            "free": 60,        # 60 req/min
            "starter": 300,    # 300 req/min
            "business": 1000,  # 1000 req/min
            "enterprise": 5000 # 5000 req/min
        }
        
        try:
            async with self.db.acquire() as conn:
                partner = await conn.fetchrow("""
                    INSERT INTO partners (
                        name, api_key, api_secret_hash, tier, rate_limit_per_minute,
                        webhook_url, webhook_secret, ec_address, metadata, status
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, 'active')
                    RETURNING id, name, tier, ec_address, rate_limit_per_minute, 
                              webhook_url, created_at
                """, name, api_key, api_secret_hash, tier, rate_limits[tier],
                    webhook_url, webhook_secret, ec_address, 
                    json.dumps(metadata or {}))
                
                return {
                    "partner_id": str(partner["id"]),
                    "name": partner["name"],
                    "tier": partner["tier"],
                    "ec_address": partner["ec_address"],
                    "api_key": api_key,  # ⚠️ Show only once!
                    "api_secret": api_secret,  # ⚠️ Show only once!
                    "rate_limit_per_minute": partner["rate_limit_per_minute"],
                    "webhook_url": partner["webhook_url"],
                    "created_at": partner["created_at"].isoformat()
                }
        
        except asyncpg.UniqueViolationError as e:
            if "ec_address" in str(e):
                raise ValueError(f"Partner with EC address {ec_address} already exists")
            elif "api_key" in str(e):
                # Extremely unlikely (64-char random), but handle anyway
                raise ValueError("API key collision, please retry")
            else:
                raise
    
    async def get_partner(self, partner_id: str) -> Optional[Dict[str, Any]]:
        """
        Get partner details by ID.
        
        Args:
            partner_id: UUID of partner
        
        Returns:
            Partner dict or None if not found
        """
        async with self.db.acquire() as conn:
            partner = await conn.fetchrow("""
                SELECT id, name, tier, ec_address, rate_limit_per_minute,
                       webhook_url, status, metadata, created_at, updated_at
                FROM partners
                WHERE id = $1
            """, UUID(partner_id))
            
            if not partner:
                return None
            
            return dict(partner)
    
    async def get_partner_by_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Get partner details by API key (for authentication).
        
        Args:
            api_key: API key from request header
        
        Returns:
            Partner dict or None if not found/suspended
        """
        async with self.db.acquire() as conn:
            partner = await conn.fetchrow("""
                SELECT id, name, tier, ec_address, api_secret_hash, 
                       rate_limit_per_minute, status, metadata
                FROM partners
                WHERE api_key = $1 AND status = 'active'
            """, api_key)
            
            if not partner:
                return None
            
            return dict(partner)
    
    async def get_partner_by_ec_address(self, ec_address: str) -> Optional[Dict[str, Any]]:
        """
        Get partner by their EC address.
        
        Args:
            ec_address: Ethereum-compatible address
        
        Returns:
            Partner dict or None
        """
        async with self.db.acquire() as conn:
            partner = await conn.fetchrow("""
                SELECT id, name, tier, ec_address, rate_limit_per_minute,
                       webhook_url, status, metadata, created_at
                FROM partners
                WHERE ec_address = $1
            """, ec_address)
            
            if not partner:
                return None
            
            return dict(partner)
    
    async def list_partners(
        self,
        status: Optional[str] = None,
        tier: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        List all partners with optional filters.
        
        Args:
            status: Filter by status (active, suspended, deleted)
            tier: Filter by tier
            limit: Max results (default 50)
            offset: Pagination offset
        
        Returns:
            List of partner dicts
        """
        query = """
            SELECT id, name, tier, ec_address, rate_limit_per_minute,
                   webhook_url, status, created_at, updated_at
            FROM partners
            WHERE 1=1
        """
        params = []
        
        if status:
            query += f" AND status = ${len(params) + 1}"
            params.append(status)
        
        if tier:
            query += f" AND tier = ${len(params) + 1}"
            params.append(tier)
        
        query += f" ORDER BY created_at DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
        params.extend([limit, offset])
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    async def update_partner(
        self,
        partner_id: str,
        **updates
    ) -> Dict[str, Any]:
        """
        Update partner details.
        
        Args:
            partner_id: UUID of partner
            **updates: Fields to update (tier, webhook_url, metadata, etc.)
        
        Returns:
            Updated partner dict
        
        Raises:
            ValueError: Partner not found or invalid update
        """
        allowed_fields = ["name", "tier", "webhook_url", "webhook_secret", 
                          "rate_limit_per_minute", "metadata"]
        
        # Filter valid updates and serialize metadata if present
        valid_updates = {}
        for k, v in updates.items():
            if k in allowed_fields:
                if k == "metadata" and isinstance(v, dict):
                    valid_updates[k] = json.dumps(v)
                else:
                    valid_updates[k] = v
        
        if not valid_updates:
            raise ValueError("No valid fields to update")
        
        # Build dynamic UPDATE query
        set_clauses = [f"{field} = ${i+2}" for i, field in enumerate(valid_updates.keys())]
        query = f"""
            UPDATE partners
            SET {', '.join(set_clauses)}, updated_at = NOW()
            WHERE id = $1
            RETURNING id, name, tier, ec_address, rate_limit_per_minute,
                      webhook_url, status, metadata, updated_at
        """
        
        params = [UUID(partner_id)] + list(valid_updates.values())
        
        async with self.db.acquire() as conn:
            partner = await conn.fetchrow(query, *params)
            
            if not partner:
                raise ValueError(f"Partner {partner_id} not found")
            
            return dict(partner)
    
    async def suspend_partner(self, partner_id: str, reason: str) -> None:
        """
        Suspend partner (disable API access).
        
        Args:
            partner_id: UUID of partner
            reason: Suspension reason (stored in metadata)
        """
        async with self.db.acquire() as conn:
            suspension_data = json.dumps({
                "reason": reason,
                "suspended_at": datetime.utcnow().isoformat()
            })
            
            await conn.execute("""
                UPDATE partners
                SET status = 'suspended',
                    metadata = jsonb_set(
                        COALESCE(metadata, '{}'::jsonb),
                        '{suspension}',
                        $2::jsonb
                    ),
                    updated_at = NOW()
                WHERE id = $1
            """, UUID(partner_id), suspension_data)
    
    async def reactivate_partner(self, partner_id: str) -> None:
        """
        Reactivate suspended partner.
        
        Args:
            partner_id: UUID of partner
        """
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE partners
                SET status = 'active',
                    metadata = metadata - 'suspension',
                    updated_at = NOW()
                WHERE id = $1
            """, UUID(partner_id))
    
    async def delete_partner(self, partner_id: str, hard: bool = False) -> None:
        """
        Delete partner (soft by default, hard if specified).
        
        Args:
            partner_id: UUID of partner
            hard: If True, physically delete from DB (⚠️ irreversible)
        """
        async with self.db.acquire() as conn:
            if hard:
                # Hard delete: remove from DB (CASCADE will delete related data)
                await conn.execute("DELETE FROM partners WHERE id = $1", UUID(partner_id))
            else:
                # Soft delete: mark as deleted
                await conn.execute("""
                    UPDATE partners
                    SET status = 'deleted', updated_at = NOW()
                    WHERE id = $1
                """, UUID(partner_id))
    
    # ========================================================================
    # API KEY MANAGEMENT
    # ========================================================================
    
    async def rotate_api_key(
        self,
        partner_id: str,
        name: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Generate new API key for partner (allows multiple keys).
        
        Args:
            partner_id: UUID of partner
            name: Optional key name ("Production", "Staging", etc.)
        
        Returns:
            Dict with new api_key and api_secret (plaintext, one-time)
        """
        api_key = self._generate_api_key()
        api_secret = self._generate_api_secret()
        api_secret_hash = self._hash_secret(api_secret)
        
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO partner_api_keys (
                    partner_id, api_key, api_secret_hash, name
                ) VALUES ($1, $2, $3, $4)
            """, UUID(partner_id), api_key, api_secret_hash, name)
            
            return {
                "api_key": api_key,
                "api_secret": api_secret,
                "name": name
            }
    
    async def revoke_api_key(self, api_key: str) -> None:
        """
        Revoke API key (mark as revoked, keep for audit trail).
        
        Args:
            api_key: API key to revoke
        """
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE partner_api_keys
                SET revoked_at = NOW()
                WHERE api_key = $1
            """, api_key)
    
    async def list_api_keys(self, partner_id: str) -> List[Dict[str, Any]]:
        """
        List all API keys for partner (active and revoked).
        
        Args:
            partner_id: UUID of partner
        
        Returns:
            List of API key dicts (without secrets)
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, api_key, name, expires_at, last_used_at, 
                       created_at, revoked_at
                FROM partner_api_keys
                WHERE partner_id = $1
                ORDER BY created_at DESC
            """, UUID(partner_id))
            
            return [dict(row) for row in rows]
    
    # ========================================================================
    # USAGE STATISTICS
    # ========================================================================
    
    async def get_usage_stats(
        self,
        partner_id: str,
        period: str = "today"
    ) -> Dict[str, Any]:
        """
        Get API usage statistics for partner.
        
        Args:
            partner_id: UUID of partner
            period: Time period (today, week, month, all)
        
        Returns:
            Dict with request counts, rate limit info, etc.
        """
        # Define time ranges
        now = datetime.utcnow()
        if period == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start = now - timedelta(days=7)
        elif period == "month":
            start = now - timedelta(days=30)
        else:
            start = datetime(2000, 1, 1)  # All time
        
        async with self.db.acquire() as conn:
            # Get partner info
            partner = await conn.fetchrow("""
                SELECT tier, rate_limit_per_minute, status
                FROM partners
                WHERE id = $1
            """, UUID(partner_id))
            
            if not partner:
                raise ValueError(f"Partner {partner_id} not found")
            
            # Count API requests from rate_limit_tracking
            request_count = await conn.fetchval("""
                SELECT COALESCE(SUM(request_count), 0)
                FROM rate_limit_tracking
                WHERE partner_id = $1 AND window_start >= $2
            """, UUID(partner_id), start)
            
            # Count webhooks sent
            webhook_count = await conn.fetchval("""
                SELECT COUNT(*)
                FROM webhook_events
                WHERE partner_id = $1 AND created_at >= $2 AND status = 'sent'
            """, UUID(partner_id), start)
            
            # Count transactions (from analytics)
            tx_count = await conn.fetchval("""
                SELECT COUNT(*)
                FROM transaction_analytics
                WHERE partner_id = $1 AND timestamp >= $2
            """, UUID(partner_id), start)
            
            return {
                "partner_id": partner_id,
                "tier": partner["tier"],
                "rate_limit_per_minute": partner["rate_limit_per_minute"],
                "status": partner["status"],
                "period": period,
                "start_date": start.isoformat(),
                "api_requests": request_count,
                "webhooks_sent": webhook_count,
                "transactions_processed": tx_count
            }
    
    # ========================================================================
    # AUTHENTICATION HELPERS
    # ========================================================================
    
    def verify_api_secret(self, plaintext: str, hashed: str) -> bool:
        """
        Verify API secret against hash.
        
        Args:
            plaintext: API secret from request
            hashed: Stored hash from database
        
        Returns:
            True if valid, False otherwise
        """
        import hashlib
        
        # Apply same pre-hash logic as _hash_secret if needed
        if len(plaintext.encode("utf-8")) > 72:
            plaintext = hashlib.sha256(plaintext.encode("utf-8")).hexdigest()
        
        return bcrypt.checkpw(plaintext.encode("utf-8"), hashed.encode("utf-8"))
    
    # ========================================================================
    # PRIVATE HELPERS
    # ========================================================================
    
    def _generate_api_key(self) -> str:
        """Generate secure random API key (64 chars hex)."""
        return secrets.token_hex(32)
    
    def _generate_api_secret(self) -> str:
        """Generate secure random API secret (64 chars hex = 32 bytes)."""
        return secrets.token_hex(32)  # 64 chars hex (within bcrypt 72 byte limit)
    
    def _hash_secret(self, secret: str) -> str:
        """
        Hash API secret with bcrypt.
        
        For secrets >72 bytes, use SHA256 pre-hash then bcrypt.
        This is secure because:
        - SHA256 provides 256-bit security
        - Bcrypt provides slow hashing (anti-brute-force)
        """
        import hashlib
        
        # If secret is longer than 72 bytes, pre-hash with SHA256
        if len(secret.encode("utf-8")) > 72:
            secret = hashlib.sha256(secret.encode("utf-8")).hexdigest()
        
        return bcrypt.hashpw(secret.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
