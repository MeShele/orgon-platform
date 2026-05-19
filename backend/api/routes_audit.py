"""API routes for audit log.

Two read surfaces live here:

* `/api/audit/logs` (offset-based, legacy) — kept for back-compat
  with the UI that uses it.
* `/api/audit/events` (keyset-based) — new, dfns-grade, intended for
  programmatic compliance integrations.

Both read from the canonical `audit_log` table. Multi-tenant
isolation is currently advisory-only because `audit_log` has no
`organization_id` column yet; access is gated by RBAC (admin /
auditor only) until a backfill migration adds it.
"""

import csv
import io
import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from fastapi.responses import StreamingResponse
from typing import AsyncIterator, Optional
from pydantic import BaseModel

from backend.services.audit_service import AuditService
from backend.rbac import require_roles

router = APIRouter(prefix="/api/audit", tags=["audit"])

_AUDIT_ROLES = ("platform_admin", "company_admin", "company_auditor")

# Public catalog of action values the audit log actually emits. Used
# only for self-documenting OpenAPI; the endpoint itself accepts any
# string so we never silently reject a freshly-added action.
_KNOWN_ACTIONS_HINT = "Examples: transaction.signed, wallet.created, organization.update, signature.approved"

# Hard ceilings to keep one slow caller from monopolizing the DB.
_LIST_HARD_MAX = 200
_CSV_HARD_MAX = 100_000


def _parse_iso(value: Optional[str], *, field: str) -> Optional[datetime]:
    if value is None or value == "":
        return None
    try:
        # Accept both "2026-05-19T10:00:00" and "...+00:00" / "...Z".
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid ISO 8601 timestamp for `{field}`: {value!r}",
        )


def _encode_cursor(created_at: datetime, row_id: int) -> str:
    """Opaque base64-friendly cursor. We use a readable JSON encoding
    rather than base64 — the cursor is server-issued anyway, so the
    obfuscation buys nothing and breaks `curl` debugging."""
    return f"{created_at.isoformat()}|{int(row_id)}"


def _decode_cursor(cursor: Optional[str]) -> Optional[tuple[datetime, int]]:
    if not cursor:
        return None
    try:
        ts_raw, id_raw = cursor.split("|", 1)
        ts = datetime.fromisoformat(ts_raw)
        return ts, int(id_raw)
    except (ValueError, AttributeError):
        raise HTTPException(
            status_code=400,
            detail="Invalid cursor — pass back the `next_cursor` value verbatim from the previous response",
        )


def _build_where(
    *,
    action: Optional[str],
    resource_type: Optional[str],
    resource_id: Optional[str],
    actor_user_id: Optional[int],
    since: Optional[datetime],
    until: Optional[datetime],
    cursor: Optional[tuple[datetime, int]],
) -> tuple[str, list]:
    """Return (where_sql, params) for the keyset query. Pure function,
    parameter-bound — no string interpolation of user input."""
    clauses: list[str] = []
    params: list = []

    def _add(clause_template: str, value):
        params.append(value)
        clauses.append(clause_template.replace("$$", f"${len(params)}"))

    if action:
        _add("action = $$", action)
    if resource_type:
        _add("resource_type = $$", resource_type)
    if resource_id:
        _add("resource_id = $$", resource_id)
    if actor_user_id is not None:
        _add("user_id = $$", actor_user_id)
    if since:
        _add("created_at >= $$", since)
    if until:
        _add("created_at <= $$", until)

    # Keyset predicate: strictly older than (created_at_cursor, id_cursor),
    # using lexicographic tuple compare so ties on created_at fall back
    # to id ordering. Composite indexes from migration 050 cover this.
    if cursor:
        cur_ts, cur_id = cursor
        params.append(cur_ts)
        params.append(cur_ts)
        params.append(cur_id)
        clauses.append(
            f"(created_at < ${len(params)-2} "
            f"OR (created_at = ${len(params)-1} AND id < ${len(params)}))"
        )

    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    return where, params


# Dependency injection helper
def get_audit_service(request: Request) -> AuditService:
    """Get AuditService from app state."""
    return request.app.state.audit_service


class AuditLogCreate(BaseModel):
    """Request model for creating an audit log entry."""
    action: str
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: Optional[dict] = None


@router.get("/logs")
async def get_audit_logs(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    user: dict = Depends(require_roles("platform_admin", "company_admin", "company_auditor")), service: AuditService = Depends(get_audit_service)
):
    """
    Get audit logs with optional filtering.
    
    Query parameters:
    - limit: Maximum number of logs (1-500, default: 50)
    - offset: Pagination offset (default: 0)
    - action: Filter by action type
    - resource_type: Filter by resource type
    - from_date: Filter by start date (ISO format)
    - to_date: Filter by end date (ISO format)
    """
    try:
        
        # Parse dates if provided
        from_dt = datetime.fromisoformat(from_date) if from_date else None
        to_dt = datetime.fromisoformat(to_date) if to_date else None
        
        logs = await service.get_audit_log(
            limit=limit,
            offset=offset,
            action=action,
            resource_type=resource_type,
            start_date=from_dt,
            end_date=to_dt
        )
        
        return {
            "total": len(logs),
            "logs": logs
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/resource/{resource_type}/{resource_id}")
async def get_resource_history(
    resource_type: str,
    resource_id: str,
    limit: int = Query(50, ge=1, le=100),
    user: dict = Depends(require_roles("platform_admin", "company_admin", "company_auditor")), service: AuditService = Depends(get_audit_service)
):
    """
    Get audit history for a specific resource.
    
    Path parameters:
    - resource_type: Resource type (wallet/transaction/contact/etc)
    - resource_id: Resource identifier
    
    Query parameters:
    - limit: Maximum entries (1-100, default: 50)
    """
    try:
        history = await service.get_resource_history(
            resource_type=resource_type,
            resource_id=resource_id,
            limit=limit
        )
        
        return {
            "resource_type": resource_type,
            "resource_id": resource_id,
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_audit_stats(user: dict = Depends(require_roles("platform_admin", "company_admin", "company_auditor")), service: AuditService = Depends(get_audit_service)):
    """
    Get audit log statistics.
    
    Returns:
    - total: Total log entries
    - recent_24h: Entries in last 24 hours
    - by_action: Count by action type
    - by_resource: Count by resource type
    """
    try:
        stats = await service.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
async def search_audit_logs(
    q: str = Query(..., min_length=1),
    limit: int = Query(50, ge=1, le=500),
    user: dict = Depends(require_roles("platform_admin", "company_admin", "company_auditor")), service: AuditService = Depends(get_audit_service)
):
    """
    Search audit logs by resource ID or details.
    
    Query parameters:
    - q: Search query (required)
    - limit: Maximum results (1-500, default: 50)
    """
    try:
        results = await service.search_logs(query=q, limit=limit)
        
        return {
            "query": q,
            "total": len(results),
            "results": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _serialize_row(row) -> dict:
    """Stable shape for both /events and /events.csv. Keeps the
    serialization contract in one place."""
    details = row["details"]
    if isinstance(details, str):
        try:
            details = json.loads(details)
        except Exception:
            pass
    return {
        "id": int(row["id"]),
        "user_id": int(row["user_id"]) if row["user_id"] is not None else None,
        "action": row["action"],
        "resource_type": row["resource_type"],
        "resource_id": row["resource_id"],
        "details": details if details is not None else {},
        "ip_address": row["ip_address"],
        "user_agent": row["user_agent"],
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
    }


@router.get("/events")
async def list_audit_events(
    request: Request,
    cursor: Optional[str] = Query(default=None, description="Pass `next_cursor` from previous response"),
    limit: int = Query(default=50, ge=1, le=_LIST_HARD_MAX),
    action: Optional[str] = Query(default=None, description=_KNOWN_ACTIONS_HINT),
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    actor_user_id: Optional[int] = Query(default=None, description="users.id of the actor"),
    since: Optional[str] = Query(default=None, description="ISO 8601 lower bound, inclusive"),
    until: Optional[str] = Query(default=None, description="ISO 8601 upper bound, inclusive"),
    user: dict = Depends(require_roles(*_AUDIT_ROLES)),
    service: AuditService = Depends(get_audit_service),
):
    """Keyset-paginated audit feed.

    Returns `{events, next_cursor, count}`. `next_cursor` is null
    when there are no further pages. Pass it back verbatim as the
    `cursor` query param to fetch the next slice. Filtering rules:

    * `action` is an exact match.
    * `resource_type` + `resource_id` are exact matches.
    * `since` / `until` are ISO 8601, inclusive on both ends.
    * `actor_user_id` matches `users.id` of the originator.

    Time-ordered DESC, ties broken by `id DESC` so the cursor is
    deterministic even when two events share a millisecond.
    """
    since_dt = _parse_iso(since, field="since")
    until_dt = _parse_iso(until, field="until")
    cursor_pair = _decode_cursor(cursor)

    where, params = _build_where(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        actor_user_id=actor_user_id,
        since=since_dt,
        until=until_dt,
        cursor=cursor_pair,
    )
    # Fetch limit+1 to detect whether there is a next page without a
    # second COUNT roundtrip.
    params.append(limit + 1)
    sql = (
        "SELECT id, user_id, action, resource_type, resource_id, "
        "details, ip_address, user_agent, created_at "
        f"FROM audit_log{where} "
        "ORDER BY created_at DESC, id DESC "
        f"LIMIT ${len(params)}"
    )

    async with service.db.acquire() as conn:
        rows = await conn.fetch(sql, *params)

    has_more = len(rows) > limit
    page = rows[:limit]
    events = [_serialize_row(r) for r in page]
    next_cursor = (
        _encode_cursor(page[-1]["created_at"], int(page[-1]["id"]))
        if has_more and page else None
    )
    return {
        "events": events,
        "count": len(events),
        "next_cursor": next_cursor,
    }


@router.get("/events.csv")
async def export_audit_events_csv(
    request: Request,
    limit: int = Query(default=_CSV_HARD_MAX, ge=1, le=_CSV_HARD_MAX),
    action: Optional[str] = None,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    actor_user_id: Optional[int] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
    user: dict = Depends(require_roles(*_AUDIT_ROLES)),
    service: AuditService = Depends(get_audit_service),
):
    """Streaming CSV export of audit events.

    Same filters as `/events`. No cursor — caller picks a time range
    and walks the result with `since` / `until`. Hard-capped at
    100k rows per request to keep one slow consumer from monopolizing
    the connection pool; for bigger exports, split by date range.
    """
    since_dt = _parse_iso(since, field="since")
    until_dt = _parse_iso(until, field="until")

    where, params = _build_where(
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        actor_user_id=actor_user_id,
        since=since_dt,
        until=until_dt,
        cursor=None,
    )
    params.append(limit)
    sql = (
        "SELECT id, user_id, action, resource_type, resource_id, "
        "details, ip_address, user_agent, created_at "
        f"FROM audit_log{where} "
        "ORDER BY created_at DESC, id DESC "
        f"LIMIT ${len(params)}"
    )

    pool = service.db  # asyncpg pool
    columns = [
        "id", "created_at", "user_id", "action", "resource_type",
        "resource_id", "ip_address", "user_agent", "details_json",
    ]

    async def _stream() -> AsyncIterator[bytes]:
        # Header.
        buf = io.StringIO()
        writer = csv.writer(buf, lineterminator="\n")
        writer.writerow(columns)
        yield buf.getvalue().encode()

        async with pool.acquire() as conn:
            async with conn.transaction():
                # Server-side cursor — never materializes the full
                # result set in memory regardless of `limit`.
                async for r in conn.cursor(sql, *params):
                    buf = io.StringIO()
                    w = csv.writer(buf, lineterminator="\n")
                    details = r["details"]
                    if isinstance(details, (dict, list)):
                        details = json.dumps(details, ensure_ascii=False, sort_keys=True)
                    elif details is None:
                        details = ""
                    w.writerow([
                        r["id"],
                        r["created_at"].isoformat() if r["created_at"] else "",
                        r["user_id"] if r["user_id"] is not None else "",
                        r["action"] or "",
                        r["resource_type"] or "",
                        r["resource_id"] or "",
                        r["ip_address"] or "",
                        r["user_agent"] or "",
                        details,
                    ])
                    yield buf.getvalue().encode()

    filename_ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return StreamingResponse(
        _stream(),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f'attachment; filename="audit-events-{filename_ts}.csv"',
        },
    )


@router.post("/log")
async def create_audit_log(
    data: AuditLogCreate, 
    request: Request,
    user: dict = Depends(require_roles("platform_admin", "company_admin", "company_auditor")), service: AuditService = Depends(get_audit_service)
):
    """
    Create a new audit log entry.
    
    Request body:
    - action: Action type (required)
    - resource_type: Resource type (optional)
    - resource_id: Resource ID (optional)
    - details: Additional details (optional)
    
    Note: This endpoint is for manual logging. Most logging should be automatic via middleware.
    """
    try:
        
        # Extract request metadata
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")
        
        audit_id = await service.log_action(
            action=data.action,
            resource_type=data.resource_type,
            resource_id=data.resource_id,
            details=data.details,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        return {
            "id": audit_id,
            "action": data.action,
            "resource_type": data.resource_type,
            "resource_id": data.resource_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
