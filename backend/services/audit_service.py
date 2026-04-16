"""
Audit Service - Comprehensive Audit Logging
Tracks all partner API operations for compliance and security
"""

import asyncpg
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from uuid import UUID


class AuditService:
    """
    Manage comprehensive audit trail for B2B platform.
    
    Logs all partner actions (wallet create, tx send, signature approve, etc.)
    for compliance (SOC2, ISO27001, GDPR) and security forensics.
    """
    
    def __init__(self, db_pool: asyncpg.Pool = None, db = None):
        """
        Initialize AuditService.
        
        Args:
            db_pool: asyncpg.Pool for B2B async operations (preferred)
            db: Legacy database connection (for backward compatibility)
        """
        if db_pool:
            self.db = db_pool
        elif db:
            self.db = db
        else:
            raise ValueError("Either db_pool or db must be provided")
    
    # ========================================================================
    # CORE LOGGING
    # ========================================================================
    
    async def log_action(
        self,
        partner_id: Optional[str],
        user_id: Optional[str],
        action: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        result: str = "success",
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log a partner action to audit trail.
        
        Args:
            partner_id: UUID of partner (None for system actions)
            user_id: EC address or user identifier
            action: Action performed (e.g., "wallet.create", "tx.send")
            resource_type: Type of resource (wallet, transaction, signature)
            resource_id: Resource identifier (wallet name, tx UNID, etc.)
            ip_address: Client IP address
            user_agent: Client user agent
            request_id: Request correlation ID
            changes: Before/after state ({"before": {...}, "after": {...}})
            result: Result status (success, failure)
            error_message: Error details if result=failure
            metadata: Additional context (JSON)
        
        Returns:
            Audit log entry ID (UUID)
        """
        async with self.db.acquire() as conn:
            log_id = await conn.fetchval("""
                INSERT INTO audit_log_b2b (
                    partner_id, user_id, action, resource_type, resource_id,
                    ip_address, user_agent, request_id, changes, result,
                    error_message, metadata
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9::jsonb, $10, $11, $12::jsonb)
                RETURNING id
            """, 
                UUID(partner_id) if partner_id else None,
                user_id,
                action,
                resource_type,
                resource_id,
                ip_address,
                user_agent,
                request_id,
                json.dumps(changes or {}),
                result,
                error_message,
                json.dumps(metadata or {})
            )
            
            return str(log_id)
    
    async def log_wallet_action(
        self,
        partner_id: str,
        user_id: str,
        action: str,  # "wallet.create", "wallet.update", "wallet.delete"
        wallet_name: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        result: str = "success",
        error_message: Optional[str] = None
    ) -> str:
        """Convenience method for wallet actions."""
        return await self.log_action(
            partner_id=partner_id,
            user_id=user_id,
            action=action,
            resource_type="wallet",
            resource_id=wallet_name,
            ip_address=ip_address,
            user_agent=user_agent,
            changes=changes,
            result=result,
            error_message=error_message
        )
    
    async def log_transaction_action(
        self,
        partner_id: str,
        user_id: str,
        action: str,  # "tx.create", "tx.send", "tx.cancel"
        tx_unid: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        result: str = "success",
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Convenience method for transaction actions."""
        return await self.log_action(
            partner_id=partner_id,
            user_id=user_id,
            action=action,
            resource_type="transaction",
            resource_id=tx_unid,
            ip_address=ip_address,
            user_agent=user_agent,
            changes=changes,
            result=result,
            error_message=error_message,
            metadata=metadata
        )
    
    async def log_signature_action(
        self,
        partner_id: str,
        user_id: str,
        action: str,  # "signature.approve", "signature.reject"
        tx_unid: str,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        result: str = "success",
        error_message: Optional[str] = None
    ) -> str:
        """Convenience method for signature actions."""
        return await self.log_action(
            partner_id=partner_id,
            user_id=user_id,
            action=action,
            resource_type="signature",
            resource_id=tx_unid,
            ip_address=ip_address,
            user_agent=user_agent,
            result=result,
            error_message=error_message
        )
    
    # ========================================================================
    # QUERY & REPORTING
    # ========================================================================
    
    async def get_audit_log(
        self,
        partner_id: Optional[str] = None,
        user_id: Optional[str] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        result: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Query audit log with filters.
        
        Args:
            partner_id: Filter by partner
            user_id: Filter by user
            action: Filter by action type
            resource_type: Filter by resource type
            result: Filter by result (success/failure)
            start_date: Filter by start timestamp
            end_date: Filter by end timestamp
            limit: Max results (default 100)
            offset: Pagination offset
        
        Returns:
            List of audit log entries
        """
        query = """
            SELECT id, partner_id, user_id, action, resource_type, resource_id,
                   ip_address, user_agent, request_id, changes, result,
                   error_message, metadata, timestamp
            FROM audit_log_b2b
            WHERE 1=1
        """
        params = []
        
        if partner_id:
            query += f" AND partner_id = ${len(params) + 1}"
            params.append(UUID(partner_id))
        
        if user_id:
            query += f" AND user_id = ${len(params) + 1}"
            params.append(user_id)
        
        if action:
            query += f" AND action = ${len(params) + 1}"
            params.append(action)
        
        if resource_type:
            query += f" AND resource_type = ${len(params) + 1}"
            params.append(resource_type)
        
        if result:
            query += f" AND result = ${len(params) + 1}"
            params.append(result)
        
        if start_date:
            query += f" AND timestamp >= ${len(params) + 1}"
            params.append(start_date)
        
        if end_date:
            query += f" AND timestamp <= ${len(params) + 1}"
            params.append(end_date)
        
        query += f" ORDER BY timestamp DESC LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
        params.extend([limit, offset])
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    async def get_user_activity(
        self,
        user_id: str,
        period: str = "today",
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get activity timeline for specific user.
        
        Args:
            user_id: EC address or user identifier
            period: Time period (today, week, month, all)
            limit: Max results
        
        Returns:
            List of user actions
        """
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
            rows = await conn.fetch("""
                SELECT id, action, resource_type, resource_id, result,
                       ip_address, timestamp
                FROM audit_log_b2b
                WHERE user_id = $1 AND timestamp >= $2
                ORDER BY timestamp DESC
                LIMIT $3
            """, user_id, start, limit)
            
            return [dict(row) for row in rows]
    
    async def get_resource_history(
        self,
        resource_type: str,
        resource_id: str
    ) -> List[Dict[str, Any]]:
        """
        Get audit trail for specific resource.
        
        Args:
            resource_type: Type of resource (wallet, transaction, etc.)
            resource_id: Resource identifier
        
        Returns:
            Chronological list of actions on resource
        """
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, partner_id, user_id, action, changes, result,
                       error_message, timestamp
                FROM audit_log_b2b
                WHERE resource_type = $1 AND resource_id = $2
                ORDER BY timestamp ASC
            """, resource_type, resource_id)
            
            return [dict(row) for row in rows]
    
    async def get_failed_actions(
        self,
        partner_id: Optional[str] = None,
        hours: int = 24,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent failed actions for alerting/monitoring.
        
        Args:
            partner_id: Optional filter by partner
            hours: Time window (default 24h)
            limit: Max results
        
        Returns:
            List of failed actions
        """
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        query = """
            SELECT id, partner_id, user_id, action, resource_type, resource_id,
                   error_message, ip_address, timestamp
            FROM audit_log_b2b
            WHERE result = 'failure' AND timestamp >= $1
        """
        params = [start_time]
        
        if partner_id:
            query += f" AND partner_id = ${len(params) + 1}"
            params.append(UUID(partner_id))
        
        query += f" ORDER BY timestamp DESC LIMIT ${len(params) + 1}"
        params.append(limit)
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
    
    # ========================================================================
    # ANALYTICS & AGGREGATIONS
    # ========================================================================
    
    async def get_action_counts(
        self,
        partner_id: str,
        period: str = "today"
    ) -> Dict[str, int]:
        """
        Get count of each action type for partner.
        
        Args:
            partner_id: UUID of partner
            period: Time period (today, week, month, all)
        
        Returns:
            Dict mapping action → count
        """
        now = datetime.utcnow()
        if period == "today":
            start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        elif period == "week":
            start = now - timedelta(days=7)
        elif period == "month":
            start = now - timedelta(days=30)
        else:
            start = datetime(2000, 1, 1)
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT action, COUNT(*) as count
                FROM audit_log_b2b
                WHERE partner_id = $1 AND timestamp >= $2
                GROUP BY action
                ORDER BY count DESC
            """, UUID(partner_id), start)
            
            return {row["action"]: row["count"] for row in rows}
    
    async def get_error_rate(
        self,
        partner_id: str,
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Calculate error rate for partner.
        
        Args:
            partner_id: UUID of partner
            hours: Time window
        
        Returns:
            Dict with total, failed, error_rate
        """
        start_time = datetime.utcnow() - timedelta(hours=hours)
        
        async with self.db.acquire() as conn:
            stats = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN result = 'failure' THEN 1 ELSE 0 END) as failed
                FROM audit_log_b2b
                WHERE partner_id = $1 AND timestamp >= $2
            """, UUID(partner_id), start_time)
            
            total = stats["total"]
            failed = stats["failed"]
            error_rate = (failed / total * 100) if total > 0 else 0
            
            return {
                "total_actions": total,
                "failed_actions": failed,
                "error_rate_percent": round(error_rate, 2),
                "period_hours": hours
            }
    
    # ========================================================================
    # EXPORT & COMPLIANCE
    # ========================================================================
    
    async def export_audit_log(
        self,
        partner_id: str,
        start_date: datetime,
        end_date: datetime,
        format: str = "json"
    ) -> str:
        """
        Export audit log for compliance reporting.
        
        Args:
            partner_id: UUID of partner
            start_date: Start of export range
            end_date: End of export range
            format: Export format (json, csv)
        
        Returns:
            Serialized data (JSON string or CSV string)
        
        Note:
            For production, implement CSV format and streaming for large exports
        """
        logs = await self.get_audit_log(
            partner_id=partner_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000  # TODO: implement streaming for larger exports
        )
        
        if format == "json":
            # Convert datetime objects to ISO strings
            def serialize(obj):
                if isinstance(obj, datetime):
                    return obj.isoformat()
                elif isinstance(obj, UUID):
                    return str(obj)
                return obj
            
            return json.dumps(logs, default=serialize, indent=2)
        
        elif format == "csv":
            # TODO: Implement CSV export
            raise NotImplementedError("CSV export not yet implemented")
        
        else:
            raise ValueError(f"Unsupported format: {format}")
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get audit log statistics.
        
        Returns:
            Dict with:
            - total: Total log count
            - recent_24h: Logs in last 24 hours
            - by_action: Count by action type
            - by_resource: Count by resource type
        """
        now = datetime.utcnow()
        day_ago = now - timedelta(hours=24)
        
        async with self.db.acquire() as conn:
            # Total count
            total = await conn.fetchval("SELECT COUNT(*) FROM audit_log_b2b")
            
            # Recent 24h count
            recent_24h = await conn.fetchval(
                "SELECT COUNT(*) FROM audit_log_b2b WHERE timestamp >= $1",
                day_ago
            )
            
            # Count by action
            action_rows = await conn.fetch("""
                SELECT action, COUNT(*) as count
                FROM audit_log_b2b
                GROUP BY action
                ORDER BY count DESC
            """)
            by_action = {row["action"]: row["count"] for row in action_rows}
            
            # Count by resource type
            resource_rows = await conn.fetch("""
                SELECT resource_type, COUNT(*) as count
                FROM audit_log_b2b
                WHERE resource_type IS NOT NULL
                GROUP BY resource_type
                ORDER BY count DESC
            """)
            by_resource = {row["resource_type"]: row["count"] for row in resource_rows}
            
            return {
                "total": total or 0,
                "recent_24h": recent_24h or 0,
                "by_action": by_action,
                "by_resource": by_resource
            }
    
    async def search_logs(
        self,
        query: str,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search audit logs by resource_id or action.
        
        Args:
            query: Search query string
            limit: Max results
        
        Returns:
            List of matching log entries
        """
        search_pattern = f"%{query}%"
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, partner_id, user_id, action, resource_type, resource_id,
                       ip_address, user_agent, result, error_message, timestamp
                FROM audit_log_b2b
                WHERE 
                    resource_id ILIKE $1
                    OR action ILIKE $1
                    OR CAST(user_id AS TEXT) ILIKE $1
                ORDER BY timestamp DESC
                LIMIT $2
            """, search_pattern, limit)
            
            return [dict(row) for row in rows]
    
    async def cleanup_old_logs(self, days: int = 90) -> int:
        """
        Archive or delete old audit logs (optional, for storage management).
        
        Args:
            days: Age threshold (logs older than this will be deleted)
        
        Returns:
            Number of logs deleted
        
        Warning:
            Use with caution! May violate compliance requirements.
            Consider archiving to cold storage instead.
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        
        async with self.db.acquire() as conn:
            deleted = await conn.fetchval("""
                DELETE FROM audit_log_b2b
                WHERE timestamp < $1
                RETURNING COUNT(*)
            """, cutoff)
            
            return deleted or 0
