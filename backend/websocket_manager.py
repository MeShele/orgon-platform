"""
WebSocket Connection Manager with per-user routing.

Extends the existing EventManager broadcast model with user-targeted notifications.
"""

import json
import logging
from typing import Dict, List, Any, Optional
from fastapi import WebSocket

logger = logging.getLogger("orgon.websocket")


class ConnectionManager:
    """Manages per-user WebSocket connections for targeted notifications."""

    def __init__(self):
        self.active_connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, user_id: str):
        """Accept and register a WebSocket connection for a user."""
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)
        logger.info("User %s connected (total connections: %d)", user_id, self._total())

    async def disconnect(self, websocket: WebSocket, user_id: str):
        """Remove a WebSocket connection for a user."""
        if user_id in self.active_connections:
            try:
                self.active_connections[user_id].remove(websocket)
            except ValueError:
                pass
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]
        logger.info("User %s disconnected (total connections: %d)", user_id, self._total())

    async def send_to_user(self, user_id: str, message: dict):
        """Send a message to all connections of a specific user."""
        if user_id not in self.active_connections:
            return
        dead = []
        for ws in self.active_connections[user_id]:
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            try:
                self.active_connections[user_id].remove(ws)
            except ValueError:
                pass

    async def send_to_users(self, user_ids: List[str], message: dict):
        """Send a message to multiple users."""
        for uid in user_ids:
            await self.send_to_user(uid, message)

    async def broadcast(self, message: dict):
        """Send a message to all connected users."""
        for user_id in list(self.active_connections.keys()):
            await self.send_to_user(user_id, message)

    def is_online(self, user_id: str) -> bool:
        return user_id in self.active_connections and len(self.active_connections[user_id]) > 0

    def _total(self) -> int:
        return sum(len(v) for v in self.active_connections.values())


# Global instance
ws_manager = ConnectionManager()
