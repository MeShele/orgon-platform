"""Support tickets API endpoints."""
from fastapi import APIRouter, Depends
from backend.rbac import require_any_auth

router = APIRouter(prefix="/api/support", tags=["support"])


@router.get("/tickets")
async def get_tickets(user: dict = Depends(require_any_auth())):
    """Get support tickets for current user."""
    return {"tickets": [], "total": 0}


@router.post("/tickets")
async def create_ticket(user: dict = Depends(require_any_auth())):
    """Create a support ticket."""
    return {"id": "ticket-1", "status": "open", "message": "Ticket created"}
