"""Event manager for real-time updates."""

import asyncio
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Optional, Set
from dataclasses import dataclass, asdict

logger = logging.getLogger("orgon.events")


class EventType(str, Enum):
    """Event types for real-time updates."""
    
    # Balance events
    BALANCE_UPDATED = "balance.updated"
    BALANCE_LOW = "balance.low"
    
    # Transaction events
    TRANSACTION_CREATED = "transaction.created"
    TRANSACTION_SENT = "transaction.sent"
    TRANSACTION_CONFIRMED = "transaction.confirmed"
    TRANSACTION_FAILED = "transaction.failed"
    
    # Signature events
    SIGNATURE_PENDING = "signature.pending"
    SIGNATURE_APPROVED = "signature.approved"
    SIGNATURE_REJECTED = "signature.rejected"
    
    # Wallet events
    WALLET_CREATED = "wallet.created"
    WALLET_UPDATED = "wallet.updated"
    
    # Network events
    NETWORK_FEE_SPIKE = "network.fee_spike"
    NETWORK_CONGESTION = "network.congestion"
    
    # System events
    SYNC_STARTED = "sync.started"
    SYNC_COMPLETED = "sync.completed"
    SYNC_FAILED = "sync.failed"


@dataclass
class Event:
    """Event data structure."""
    
    type: EventType
    data: dict
    timestamp: str
    id: Optional[str] = None
    
    def to_json(self) -> str:
        """Serialize to JSON."""
        return json.dumps({
            "type": self.type.value,
            "data": self.data,
            "timestamp": self.timestamp,
            "id": self.id
        })
    
    @staticmethod
    def create(event_type: EventType, data: dict, event_id: Optional[str] = None) -> "Event":
        """Create a new event."""
        return Event(
            type=event_type,
            data=data,
            timestamp=datetime.now(timezone.utc).isoformat(),
            id=event_id
        )


class EventManager:
    """
    Centralized event manager for real-time updates.
    
    Features:
    - WebSocket broadcasting
    - Event filtering by type
    - Event history (last N events)
    - Webhook delivery (future)
    """
    
    def __init__(self, history_size: int = 100):
        self._ws_connections: Set[Any] = set()  # WebSocket connections
        self._event_history: list[Event] = []
        self._history_size = history_size
        self._handlers: dict[EventType, list[Callable]] = {}
        logger.info("EventManager initialized (history: %d)", history_size)
    
    def add_connection(self, websocket: Any):
        """Add WebSocket connection."""
        self._ws_connections.add(websocket)
        logger.info("WebSocket connected (total: %d)", len(self._ws_connections))
    
    def remove_connection(self, websocket: Any):
        """Remove WebSocket connection."""
        self._ws_connections.discard(websocket)
        logger.info("WebSocket disconnected (remaining: %d)", len(self._ws_connections))
    
    async def emit(self, event_type: EventType, data: dict, event_id: Optional[str] = None):
        """
        Emit an event to all subscribers.
        
        Args:
            event_type: Type of event
            data: Event payload
            event_id: Optional unique event ID
        """
        event = Event.create(event_type, data, event_id)
        
        # Add to history
        self._event_history.append(event)
        if len(self._event_history) > self._history_size:
            self._event_history.pop(0)
        
        # Broadcast to WebSocket clients
        await self._broadcast_ws(event)
        
        # Call registered handlers
        await self._call_handlers(event)
        
        logger.debug("Event emitted: %s", event_type.value)
    
    async def _broadcast_ws(self, event: Event):
        """Broadcast event to all WebSocket clients."""
        if not self._ws_connections:
            return
        
        message = event.to_json()
        disconnected = set()
        
        for ws in self._ws_connections:
            try:
                await ws.send_text(message)
            except Exception as e:
                logger.warning("Failed to send to WebSocket: %s", e)
                disconnected.add(ws)
        
        # Remove disconnected clients
        self._ws_connections -= disconnected
    
    async def _call_handlers(self, event: Event):
        """Call registered event handlers."""
        handlers = self._handlers.get(event.type, [])
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error("Event handler failed: %s", e)
    
    def on(self, event_type: EventType, handler: Callable):
        """
        Register an event handler.
        
        Args:
            event_type: Event type to listen for
            handler: Callback function (sync or async)
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        
        self._handlers[event_type].append(handler)
        logger.info("Handler registered for %s", event_type.value)
    
    def get_history(self, event_type: Optional[EventType] = None, limit: int = 50) -> list[Event]:
        """
        Get event history.
        
        Args:
            event_type: Filter by event type (None = all)
            limit: Max number of events
        
        Returns:
            List of recent events
        """
        events = self._event_history
        
        if event_type:
            events = [e for e in events if e.type == event_type]
        
        return events[-limit:]


# Global event manager instance
_event_manager: Optional[EventManager] = None


def get_event_manager() -> EventManager:
    """Get the global event manager instance."""
    global _event_manager
    if _event_manager is None:
        _event_manager = EventManager()
    return _event_manager


def init_event_manager(history_size: int = 100) -> EventManager:
    """Initialize the global event manager."""
    global _event_manager
    _event_manager = EventManager(history_size)
    return _event_manager
