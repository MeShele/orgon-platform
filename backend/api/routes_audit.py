"""API routes for audit log."""

from fastapi import APIRouter, HTTPException, Query, Request, Depends
from typing import Optional
from datetime import datetime
from pydantic import BaseModel

from backend.services.audit_service import AuditService
from backend.rbac import require_roles

router = APIRouter(prefix="/api/audit", tags=["audit"])


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
