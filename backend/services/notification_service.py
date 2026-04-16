"""
Unified notification service.

Sends notifications via:
1. WebSocket (real-time, per-user)
2. Email (async, with templates)
3. Telegram (existing TelegramNotifier)
4. EventManager (broadcast for dashboard)
"""

import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger("orgon.notifications")


class NotificationService:
    def __init__(self, db_pool, ws_manager, email_service, event_manager, telegram_notifier=None):
        self.db = db_pool
        self.ws = ws_manager
        self.email = email_service
        self.events = event_manager
        self.telegram = telegram_notifier

    # ---- Helper: get org admins ----
    async def _get_org_admin_ids(self, org_id: int) -> List[str]:
        """Get user IDs of company_admin+ for an organization."""
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                """SELECT id, email FROM users 
                   WHERE organization_id = $1 
                   AND role IN ('company_admin', 'platform_admin', 'super_admin', 'admin')
                   AND is_active = true""",
                org_id
            )
            return [{"id": str(r["id"]), "email": r["email"]} for r in rows]

    async def _get_user_email(self, user_id: int) -> Optional[str]:
        async with self.db.acquire() as conn:
            row = await conn.fetchrow("SELECT email FROM users WHERE id = $1", user_id)
            return row["email"] if row else None

    # ---- Notification Methods ----

    async def notify_transaction_created(self, transaction: dict, creator_id: int, org_id: int):
        """Notify org admins about new transaction."""
        from backend.events.manager import EventType

        # Broadcast via EventManager (existing behavior)
        await self.events.emit(EventType.TRANSACTION_CREATED, transaction)

        # Per-user WS + Email to org admins
        admins = await self._get_org_admin_ids(org_id)
        admin_ids = [a["id"] for a in admins]
        
        ws_msg = {
            "type": "notification",
            "event": "transaction.created",
            "title": "New Transaction",
            "message": f"New transaction for {transaction.get('amount', '?')} {transaction.get('currency', '')}",
            "data": transaction,
        }
        await self.ws.send_to_users(admin_ids, ws_msg)

        # Email admins
        for admin in admins:
            try:
                await self.email.send_template(
                    admin["email"], "transaction_created",
                    tx_id=str(transaction.get("id", "")),
                    amount=str(transaction.get("amount", "")),
                    currency=transaction.get("currency", ""),
                    to_address=transaction.get("to_address", ""),
                    created_by=transaction.get("created_by_name", str(creator_id)),
                )
            except Exception as e:
                logger.error("Email notify failed for %s: %s", admin["email"], e)

    async def notify_transaction_signed(self, transaction: dict, signer_name: str, creator_id: int):
        """Notify transaction creator that someone signed."""
        from backend.events.manager import EventType

        await self.events.emit(EventType.SIGNATURE_APPROVED, transaction)

        ws_msg = {
            "type": "notification",
            "event": "transaction.signed",
            "title": "Transaction Signed",
            "message": f"Transaction signed by {signer_name}",
            "data": transaction,
        }
        await self.ws.send_to_user(str(creator_id), ws_msg)

        email = await self._get_user_email(creator_id)
        if email:
            try:
                await self.email.send_template(
                    email, "transaction_signed",
                    tx_id=str(transaction.get("id", "")),
                    signer=signer_name,
                    status=transaction.get("status", ""),
                    signatures_count=str(transaction.get("signatures_count", 0)),
                    signatures_required=str(transaction.get("signatures_required", 0)),
                )
            except Exception as e:
                logger.error("Email notify failed: %s", e)

    async def notify_transaction_status(self, transaction: dict, user_ids: List[int], new_status: str):
        """Notify relevant users about transaction status change."""
        ws_msg = {
            "type": "notification",
            "event": "transaction.status_changed",
            "title": f"Transaction {new_status.title()}",
            "message": f"Transaction status changed to {new_status}",
            "data": transaction,
        }
        await self.ws.send_to_users([str(uid) for uid in user_ids], ws_msg)

    async def notify_user_added(self, new_user: dict, org_id: int):
        """Notify org admins when a new user is added."""
        admins = await self._get_org_admin_ids(org_id)
        admin_ids = [a["id"] for a in admins]

        ws_msg = {
            "type": "notification",
            "event": "user.added",
            "title": "New Team Member",
            "message": f"{new_user.get('full_name', '')} joined as {new_user.get('role', '')}",
            "data": new_user,
        }
        await self.ws.send_to_users(admin_ids, ws_msg)

        # Send welcome email to new user
        try:
            await self.email.send_template(
                new_user["email"], "welcome",
                full_name=new_user.get("full_name", ""),
                email=new_user["email"],
                role=new_user.get("role", ""),
                organization=new_user.get("organization_name", "ORGON"),
            )
        except Exception as e:
            logger.error("Welcome email failed: %s", e)


# Global instance (initialized in main.py)
_notification_service: Optional[NotificationService] = None


def get_notification_service() -> Optional[NotificationService]:
    return _notification_service


def init_notification_service(db_pool, ws_manager, email_service, event_manager, telegram_notifier=None):
    global _notification_service
    _notification_service = NotificationService(db_pool, ws_manager, email_service, event_manager, telegram_notifier)
    return _notification_service
