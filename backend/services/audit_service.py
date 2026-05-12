"""Audit Service — write + read for the single `audit_log` table.

Schema (canonical migration 000):
    id           serial / integer PK
    user_id      integer (FK to users.id, nullable for system actions)
    action       text NOT NULL
    resource_type text
    resource_id  text
    details      jsonb
    ip_address   text
    user_agent   text
    created_at   timestamptz default now()

Why a single table:
There used to be a parallel `audit_log_b2b` table for the B2B partner
HMAC stack — wider schema (partner_id, changes, result, etc.) with
string-keyed user_id. When the partner subsystem was removed (Wave 28),
audit_log_b2b was dropped and this service was rewritten to talk to
`audit_log` only. The richer fields (partner_id, request_id, result,
error_message, the prior `changes` and `metadata` blobs) all collapse
into the `details` jsonb here.

Triggers: `audit_log` is append-only at the DB level (UPDATE / DELETE
raise from a trigger). This service only ever INSERTs and SELECTs.
"""

import asyncpg
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta


class AuditService:
    """Read/write helper for the audit_log append-only table."""

    def __init__(self, db_pool: asyncpg.Pool = None, db=None):
        if db_pool:
            self.db = db_pool
        elif db:
            self.db = db
        else:
            raise ValueError("Either db_pool or db must be provided")

    # ------------------------------------------------------------------
    # WRITE
    # ------------------------------------------------------------------

    async def log_action(
        self,
        user_id: Optional[Any] = None,
        action: str = "",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        request_id: Optional[str] = None,
        changes: Optional[Dict[str, Any]] = None,
        result: str = "success",
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        partner_id: Optional[str] = None,  # legacy kwarg from B2B days, kept so
                                            # callers don't break; folded into details
    ) -> str:
        """Insert a single audit row. Returns the new row id as string.

        `user_id` may be int (modern), string-integer (legacy) or None.
        Non-integer strings are coerced to NULL so the FK to users.id holds.
        The richer B2B fields (partner_id, request_id, result, error_message,
        metadata) collapse into the `details` jsonb so we don't lose data
        even though `audit_log` has a narrower column set.
        """
        uid: Optional[int]
        if user_id is None:
            uid = None
        elif isinstance(user_id, int):
            uid = user_id
        else:
            s = str(user_id).strip()
            uid = int(s) if s.isdigit() else None

        details: Dict[str, Any] = {}
        if changes:
            details["changes"] = changes
        if metadata:
            details["metadata"] = metadata
        if result and result != "success":
            details["result"] = result
        if error_message:
            details["error_message"] = error_message
        if partner_id:
            details["partner_id"] = str(partner_id)
        if request_id:
            details["request_id"] = request_id

        async with self.db.acquire() as conn:
            log_id = await conn.fetchval(
                """
                INSERT INTO audit_log (
                    user_id, action, resource_type, resource_id,
                    details, ip_address, user_agent
                ) VALUES ($1, $2, $3, $4, $5::jsonb, $6, $7)
                RETURNING id
                """,
                uid,
                action,
                resource_type,
                resource_id,
                json.dumps(details) if details else None,
                ip_address,
                user_agent,
            )
            return str(log_id)

    # ------------------------------------------------------------------
    # READ
    # ------------------------------------------------------------------

    async def get_audit_log(
        self,
        user_id: Optional[Any] = None,
        action: Optional[str] = None,
        resource_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0,
        # legacy kwargs from the B2B days — accepted but currently no-op
        partner_id: Optional[str] = None,
        result: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        query = (
            "SELECT id, user_id, action, resource_type, resource_id, "
            "details, ip_address, user_agent, created_at "
            "FROM audit_log WHERE 1=1"
        )
        params: list = []

        if user_id is not None:
            params.append(int(user_id) if str(user_id).isdigit() else None)
            query += f" AND user_id = ${len(params)}"
        if action:
            params.append(action)
            query += f" AND action = ${len(params)}"
        if resource_type:
            params.append(resource_type)
            query += f" AND resource_type = ${len(params)}"
        if start_date:
            params.append(start_date)
            query += f" AND created_at >= ${len(params)}"
        if end_date:
            params.append(end_date)
            query += f" AND created_at <= ${len(params)}"

        query += " ORDER BY created_at DESC"
        params.append(limit)
        query += f" LIMIT ${len(params)}"
        params.append(offset)
        query += f" OFFSET ${len(params)}"

        async with self.db.acquire() as conn:
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]

    async def get_resource_history(
        self, resource_type: str, resource_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, action, resource_type, resource_id,
                       details, ip_address, user_agent, created_at
                FROM audit_log
                WHERE resource_type = $1 AND resource_id = $2
                ORDER BY created_at DESC
                LIMIT $3
                """,
                resource_type,
                resource_id,
                limit,
            )
            return [dict(r) for r in rows]

    async def search_logs(self, query: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Substring search across `action` and `resource_type`."""
        pattern = f"%{query}%"
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, user_id, action, resource_type, resource_id,
                       details, ip_address, user_agent, created_at
                FROM audit_log
                WHERE action ILIKE $1 OR resource_type ILIKE $1
                ORDER BY created_at DESC
                LIMIT $2
                """,
                pattern,
                limit,
            )
            return [dict(r) for r in rows]

    async def get_stats(self) -> Dict[str, Any]:
        async with self.db.acquire() as conn:
            total = await conn.fetchval("SELECT COUNT(*) FROM audit_log")
            since = datetime.utcnow() - timedelta(hours=24)
            recent = await conn.fetchval(
                "SELECT COUNT(*) FROM audit_log WHERE created_at >= $1", since
            )
            by_action_rows = await conn.fetch(
                """
                SELECT action, COUNT(*) AS n
                FROM audit_log
                GROUP BY action
                ORDER BY n DESC
                LIMIT 20
                """
            )
            by_resource_rows = await conn.fetch(
                """
                SELECT resource_type, COUNT(*) AS n
                FROM audit_log
                WHERE resource_type IS NOT NULL
                GROUP BY resource_type
                ORDER BY n DESC
                LIMIT 20
                """
            )
            return {
                "total": int(total or 0),
                "recent_24h": int(recent or 0),
                "by_action": {r["action"]: int(r["n"]) for r in by_action_rows},
                "by_resource": {
                    r["resource_type"]: int(r["n"]) for r in by_resource_rows
                },
            }
