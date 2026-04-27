"""Multi-signature transaction management service."""

import logging
from typing import Optional
from datetime import datetime, timezone

import asyncpg

from backend.safina.client import SafinaPayClient
from backend.safina.models import PendingSignature, Transaction
from backend.database.db_postgres import AsyncDatabase
from backend.events.manager import get_event_manager, EventType

logger = logging.getLogger("orgon.services.signature")


class DuplicateSignatureError(Exception):
    """Raised when a signer tries to sign or reject the same tx twice."""


class SignatureService:
    """
    Multi-signature transaction management.

    Features:
    - Get pending signatures for a user
    - Sign (approve) transactions
    - Reject transactions with reason
    - Track signature status and progress
    - Telegram notifications (optional)
    """

    def __init__(
        self,
        client: SafinaPayClient,
        db: AsyncDatabase,
        telegram_notifier=None
    ):
        self._client = client
        self._db = db
        self._telegram = telegram_notifier

    async def get_pending_signatures(
        self,
        user_address: Optional[str] = None
    ) -> list[PendingSignature]:
        """
        Get transactions awaiting signature from user.

        Args:
            user_address: EC address filter. If None, uses client's signer address.

        Returns:
            List of pending signature requests
        """
        # If no address provided, use the client's signer address
        if not user_address:
            user_address = self._client._signer.address

        try:
            pending = await self._client.get_pending_signatures()
            logger.info(
                "Found %d pending signatures for address %s",
                len(pending), user_address
            )
            return pending

        except Exception as e:
            logger.error("Failed to fetch pending signatures: %s", e)
            raise

    async def sign_transaction(
        self,
        tx_unid: str,
        user_address: Optional[str] = None
    ) -> dict:
        """
        Sign (approve) a transaction.

        Args:
            tx_unid: Transaction unique ID
            user_address: EC address of signer (for logging)

        Returns:
            API response (typically empty dict on success)
        """
        if not user_address:
            user_address = self._client._signer.address

        logger.info(
            "Signing transaction %s by address %s",
            tx_unid, user_address
        )

        # Replay guard: refuse if this signer already has a 'signed' or
        # 'rejected' row for this tx. We check before calling Safina so a
        # replayed request is a cheap 409, not a Safina round-trip.
        prior = await self._db.fetchrow(
            """SELECT action FROM signature_history
                WHERE tx_unid = $1 AND signer_address = $2
                  AND action IN ('signed', 'rejected')
                LIMIT 1""",
            params=(tx_unid, user_address),
        )
        if prior:
            raise DuplicateSignatureError(
                f"Signer {user_address} already {prior['action']} tx {tx_unid}"
            )

        try:
            result = await self._client.sign_transaction(tx_unid)

            # Record signature — UNIQUE index on (tx_unid, signer, action)
            # is the second line of defense against a race-condition replay.
            try:
                await self._db.execute(
                    """INSERT INTO signature_history
                       (tx_unid, signer_address, action, signed_at)
                       VALUES ($1, $2, $3, $4)""",
                    (tx_unid, user_address, "signed", datetime.now(timezone.utc))
                )
            except asyncpg.UniqueViolationError as exc:
                raise DuplicateSignatureError(
                    f"Signer {user_address} already signed tx {tx_unid}"
                ) from exc

            # Check if transaction is now complete
            status = await self.get_signature_status(tx_unid)

            # Send notifications if configured
            if status.get("is_complete"):
                await self._notify_transaction_complete(tx_unid, status)
            else:
                await self._notify_signature_added(tx_unid, status)

            logger.info(
                "Transaction %s signed successfully. Progress: %s",
                tx_unid, status.get("progress", "unknown")
            )

            return result

        except Exception as e:
            logger.error("Failed to sign transaction %s: %s", tx_unid, e)
            raise

    async def reject_transaction(
        self,
        tx_unid: str,
        reason: str = "",
        user_address: Optional[str] = None
    ) -> dict:
        """
        Reject a transaction.

        Args:
            tx_unid: Transaction unique ID
            reason: Rejection reason (optional)
            user_address: EC address of rejector (for logging)

        Returns:
            API response (typically empty dict on success)
        """
        if not user_address:
            user_address = self._client._signer.address

        logger.info(
            "Rejecting transaction %s by address %s (reason: %s)",
            tx_unid, user_address, reason or "not provided"
        )

        # Same replay guard as sign_transaction.
        prior = await self._db.fetchrow(
            """SELECT action FROM signature_history
                WHERE tx_unid = $1 AND signer_address = $2
                  AND action IN ('signed', 'rejected')
                LIMIT 1""",
            params=(tx_unid, user_address),
        )
        if prior:
            raise DuplicateSignatureError(
                f"Signer {user_address} already {prior['action']} tx {tx_unid}"
            )

        try:
            result = await self._client.reject_transaction(tx_unid, reason)

            try:
                await self._db.execute(
                    """INSERT INTO signature_history
                       (tx_unid, signer_address, action, reason, signed_at)
                       VALUES ($1, $2, $3, $4, $5)""",
                    (
                        tx_unid,
                        user_address,
                        "rejected",
                        reason,
                        datetime.now(timezone.utc)
                    )
                )
            except asyncpg.UniqueViolationError as exc:
                raise DuplicateSignatureError(
                    f"Signer {user_address} already rejected tx {tx_unid}"
                ) from exc

            # Notify rejection
            await self._notify_transaction_rejected(tx_unid, user_address, reason)

            logger.info("Transaction %s rejected successfully", tx_unid)
            return result

        except Exception as e:
            logger.error("Failed to reject transaction %s: %s", tx_unid, e)
            raise

    async def get_signature_status(self, tx_unid: str) -> dict:
        """
        Get detailed signature status for a transaction.

        Args:
            tx_unid: Transaction unique ID

        Returns:
            Dict with:
                - signed: List of addresses that signed
                - waiting: List of addresses waiting to sign
                - progress: "N/M" format (e.g., "2/3")
                - is_complete: Boolean indicating if min_signs reached
        """
        try:
            # Get both signed and waiting signatures
            all_sigs = await self._client.get_tx_signatures_all(tx_unid)

            signed = []
            waiting = []

            for sig in all_sigs:
                if "signed" in sig and sig["signed"]:
                    addr = sig["signed"].get("ecaddress")
                    if addr:
                        signed.append(addr)
                elif "wait" in sig and sig["wait"]:
                    addr = sig["wait"].get("ecaddress")
                    if addr:
                        waiting.append(addr)

            total = len(signed) + len(waiting)
            progress = f"{len(signed)}/{total}" if total > 0 else "0/0"

            # Check if complete (all waiting addresses are empty)
            is_complete = len(waiting) == 0 and total > 0

            status = {
                "tx_unid": tx_unid,
                "signed": signed,
                "waiting": waiting,
                "progress": progress,
                "signed_count": len(signed),
                "waiting_count": len(waiting),
                "total_required": total,
                "is_complete": is_complete,
            }

            logger.debug("Signature status for %s: %s", tx_unid, progress)
            return status

        except Exception as e:
            logger.error("Failed to get signature status for %s: %s", tx_unid, e)
            raise

    async def get_signed_transactions_history(
        self,
        user_address: Optional[str] = None,
        limit: int = 50
    ) -> list[dict]:
        """
        Get history of transactions signed by user.

        Args:
            user_address: EC address filter. If None, uses client's signer.
            limit: Maximum number of transactions to return

        Returns:
            List of signed transactions (last 50 by default)
        """
        if not user_address:
            user_address = self._client._signer.address

        try:
            # Get from Safina API
            signed_txs = await self._client.get_signed_transactions()

            logger.info(
                "Found %d signed transactions for address %s",
                len(signed_txs), user_address
            )

            return [tx.model_dump() for tx in signed_txs[:limit]]

        except Exception as e:
            logger.error("Failed to fetch signed transactions: %s", e)
            raise

    async def get_transaction_details(self, tx_unid: str) -> Optional[dict]:
        """
        Get full transaction details including signature status.

        Args:
            tx_unid: Transaction unique ID

        Returns:
            Dict with transaction info and signature status
        """
        try:
            # Get all transactions and find the one we need
            all_txs = await self._client.get_transactions()
            tx = next((t for t in all_txs if t.unid == tx_unid), None)

            if not tx:
                logger.warning("Transaction %s not found", tx_unid)
                return None

            # Get signature status
            sig_status = await self.get_signature_status(tx_unid)

            # Combine transaction data with signature status
            result = tx.model_dump()
            result["signature_status"] = sig_status

            return result

        except Exception as e:
            logger.error("Failed to get transaction details for %s: %s", tx_unid, e)
            raise

    async def check_new_pending_signatures(self) -> list[PendingSignature]:
        """
        Background task: Check for new pending signatures and notify.

        This should be called periodically (e.g., every 5 minutes).
        Compares current pending signatures with last check,
        sends notifications for new ones.

        Returns:
            List of newly detected pending signatures
        """
        try:
            # Get current pending signatures
            current_pending = await self.get_pending_signatures()

            # Get last checked tx_unids from DB
            last_check = await self._db.fetch(
                "SELECT tx_unid FROM pending_signatures_checked ORDER BY checked_at DESC LIMIT 100"
            )
            last_unids = {row["tx_unid"] for row in last_check}

            # Find new pending signatures
            new_pending = [
                p for p in current_pending
                if p.unid not in last_unids
            ]

            if new_pending:
                logger.info("Found %d new pending signatures", len(new_pending))

                # Record new ones
                now = datetime.now(timezone.utc)
                event_manager = get_event_manager()
                
                for pending in new_pending:
                    await self._db.execute(
                        """INSERT OR IGNORE INTO pending_signatures_checked
                           (tx_unid, checked_at)
                           VALUES ($1, $2)""",
                        (pending.unid, now)
                    )
                    
                    # Emit signature pending event
                    await event_manager.emit(EventType.SIGNATURE_PENDING, {
                        "tx_unid": pending.unid,
                        "ec_address": pending.ecaddress,
                        "value": pending.value,
                        "to_addr": pending.to_addr,
                        "token": pending.token,
                        "required_signatures": pending.min_sign,
                        "current_signatures": len(pending.signed) if pending.signed else 0
                    })

                # Send notifications
                await self._notify_new_pending_signatures(new_pending)

            return new_pending

        except Exception as e:
            logger.error("Failed to check new pending signatures: %s", e)
            return []

    # --- Notification helpers ---

    async def _notify_new_pending_signatures(self, pending: list[PendingSignature]):
        """Send notification for new pending signatures."""
        if not self._telegram or not pending:
            return

        try:
            for p in pending:
                # Use structured notification method from TelegramNotifier
                await self._telegram.notify_pending_signature(
                    tx_unid=p.unid,
                    token=p.token,
                    value=p.tx_value,
                    to_addr=p.to_addr,
                    current_signatures=getattr(p, 'current_signatures', 0),
                    required_signatures=getattr(p, 'required_signatures', 0),
                )
                logger.info("Sent Telegram notification for new pending tx %s", p.unid)

        except Exception as e:
            logger.error("Failed to send Telegram notification: %s", e)

    async def _notify_signature_added(self, tx_unid: str, status: dict):
        """Send notification when signature is added."""
        if not self._telegram:
            return

        try:
            # If signature is complete, use structured notification
            if status.get("is_complete"):
                # Get transaction details for full notification
                try:
                    tx_details = await self.get_transaction_details(tx_unid)
                    await self._telegram.notify_signature_complete(
                        tx_unid=tx_unid,
                        token=tx_details.get("token", "Unknown"),
                        value=tx_details.get("value", "0"),
                        to_addr=tx_details.get("to_address", "Unknown"),
                        signatures_count=status.get("signed_count", 0),
                    )
                except Exception as e:
                    logger.warning("Could not get tx details for complete notification: %s", e)
                    # Fallback to basic message
                    progress = status.get("progress", "unknown")
                    message = f"✅ Signature Complete\n\nTX ID: {tx_unid}\nProgress: {progress}\n\n🎉 Transaction ready for broadcast!"
                    await self._telegram.send_message(message)
            else:
                # For intermediate signatures, use basic message
                progress = status.get("progress", "unknown")
                waiting_count = status.get("waiting_count", 0)
                message = (
                    f"✅ Signature Added\n\n"
                    f"TX ID: {tx_unid}\n"
                    f"Progress: {progress}\n"
                    f"Waiting for {waiting_count} more signature(s)"
                )
                await self._telegram.send_message(message)

        except Exception as e:
            logger.error("Failed to send signature notification: %s", e)

    async def _notify_transaction_complete(self, tx_unid: str, status: dict):
        """Send notification when transaction has all signatures."""
        if not self._telegram:
            return

        try:
            message = (
                f"🎉 Transaction complete!\n\n"
                f"TX ID: {tx_unid}\n"
                f"All signatures collected: {status.get('progress', 'unknown')}\n"
                f"Transaction will be broadcast to blockchain."
            )
            await self._telegram.send_message(message)

        except Exception as e:
            logger.error("Failed to send completion notification: %s", e)

    async def _notify_transaction_rejected(
        self,
        tx_unid: str,
        user_address: str,
        reason: str
    ):
        """Send notification when transaction is rejected."""
        if not self._telegram:
            return

        try:
            message = (
                f"❌ Transaction rejected\n\n"
                f"TX ID: {tx_unid}\n"
                f"Rejected by: {user_address[:10]}...\n"
            )
            if reason:
                message += f"Reason: {reason}"

            await self._telegram.send_message(message)

        except Exception as e:
            logger.error("Failed to send rejection notification: %s", e)

    async def get_statistics(self) -> dict:
        """
        Get signature statistics for monitoring.

        Returns:
            Dict with signature counts and rates
        """
        stats = {}

        # Count signatures in last 24 hours
        signed_24h = await self._db.fetchrow(
            """SELECT COUNT(*) as cnt FROM signature_history
               WHERE action = 'signed'
               AND created_at > NOW() - INTERVAL '1 day'"""
        )
        stats["signed_last_24h"] = signed_24h["cnt"] if signed_24h else 0

        # Count rejections in last 24 hours
        rejected_24h = await self._db.fetchrow(
            """SELECT COUNT(*) as cnt FROM signature_history
               WHERE action = 'rejected'
               AND created_at > NOW() - INTERVAL '1 day'"""
        )
        stats["rejected_last_24h"] = rejected_24h["cnt"] if rejected_24h else 0

        # Total signatures all time
        total_signed = await self._db.fetchrow(
            "SELECT COUNT(*) as cnt FROM signature_history WHERE action = 'signed'"
        )
        stats["total_signed"] = total_signed["cnt"] if total_signed else 0

        # Total rejections all time
        total_rejected = await self._db.fetchrow(
            "SELECT COUNT(*) as cnt FROM signature_history WHERE action = 'rejected'"
        )
        stats["total_rejected"] = total_rejected["cnt"] if total_rejected else 0

        return stats
