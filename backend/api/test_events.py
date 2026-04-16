"""Test endpoints for WebSocket events (development only)."""

import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from backend.events.manager import get_event_manager, EventType

logger = logging.getLogger("orgon.api.test_events")

router = APIRouter(prefix="/test/events", tags=["test"])


class TestEventRequest(BaseModel):
    """Request to emit a test event."""
    event_type: str
    data: dict = {}


@router.post("/emit")
async def emit_test_event(request: TestEventRequest):
    """
    Emit a test event (for development/testing).
    
    Example:
    ```json
    {
      "event_type": "transaction.created",
      "data": {
        "unid": "test-123",
        "value": "100",
        "status": "pending"
      }
    }
    ```
    """
    try:
        event_type = EventType(request.event_type)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid event type: {request.event_type}"
        )
    
    event_manager = get_event_manager()
    await event_manager.emit(event_type, request.data)
    
    logger.info("Test event emitted: %s", request.event_type)
    
    return {
        "status": "ok",
        "event_type": request.event_type,
        "data": request.data
    }


@router.get("/history")
async def get_event_history(limit: int = 20):
    """Get recent event history."""
    event_manager = get_event_manager()
    history = event_manager.get_history(limit=limit)
    
    return {
        "total": len(history),
        "events": [
            {
                "type": e.type.value,
                "data": e.data,
                "timestamp": e.timestamp,
                "id": e.id
            }
            for e in history
        ]
    }
