"""Scheduled transaction service for delayed/recurring payments."""

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional
from croniter import croniter

from backend.safina.client import SafinaPayClient
from backend.safina.models import SendTransactionRequest
from backend.database.db_postgres import AsyncDatabase
from backend.services.transaction_service import TransactionService
from backend.events.manager import get_event_manager, EventType

logger = logging.getLogger("orgon.services.scheduled_tx")


class ScheduledTransactionService:
    """
    Manage scheduled and recurring transactions.
    
    Features:
    - One-time scheduled transactions ("send tomorrow at 10:00")
    - Recurring payments with cron syntax ("send every Monday at 10:00")
    - Status tracking (pending, sent, failed, cancelled)
    - Event emission for monitoring
    """
    
    def __init__(
        self,
        transaction_service: TransactionService,
        db: AsyncDatabase
    ):
        self._tx_service = transaction_service
        self._db = db
    
    async def create_scheduled_transaction(
        self,
        token: str,
        to_address: str,
        value: str,
        scheduled_at: datetime,
        info: Optional[str] = None,
        json_info: Optional[dict] = None,
        recurrence_rule: Optional[str] = None
    ) -> int:
        """
        Create a scheduled transaction.
        
        Args:
            token: Token identifier (e.g., "TRX:::1###wallet-name")
            to_address: Recipient address
            value: Amount to send
            scheduled_at: When to send (datetime object)
            info: Optional description
            json_info: Optional JSON metadata
            recurrence_rule: Optional cron expression (e.g., "0 10 * * MON")
        
        Returns:
            Scheduled transaction ID
        """
        # Validate cron expression if provided
        if recurrence_rule:
            try:
                croniter(recurrence_rule)
            except Exception as e:
                raise ValueError(f"Invalid cron expression: {e}")
        
        now = datetime.now(timezone.utc)
        
        # For recurring, set next_run_at
        next_run_at = None
        if recurrence_rule:
            cron = croniter(recurrence_rule, scheduled_at)
            next_run_at = cron.get_next(datetime)
        
        result = await self._db.execute(
            """INSERT INTO scheduled_transactions
               (token, to_address, value, info, json_info, scheduled_at,
                recurrence_rule, status, created_at, updated_at, next_run_at)
               VALUES ($1, $2, $3, $4, $5, $6, $7, 'pending', $8, $9, $10)""",
            (
                token,
                to_address,
                value,
                info,
                str(json_info) if json_info else None,
                scheduled_at,
                recurrence_rule,
                now,
                now,
                next_run_at if next_run_at else None
            )
        )
        
        # Extract ID from result
        tx_id = result.split()[-1] if "INSERT" in result else None
        
        logger.info(
            "Scheduled transaction created: id=%s, scheduled_at=%s, recurring=%s",
            tx_id, scheduled_at, bool(recurrence_rule)
        )
        
        return int(tx_id) if tx_id else 0
    
    async def get_scheduled_transaction(self, tx_id: int) -> Optional[dict]:
        """Get scheduled transaction by ID."""
        row = await self._db.fetchrow("SELECT * FROM scheduled_transactions WHERE id = $1", params=(tx_id,)
        )
        return dict(row) if row else None
    
    async def list_scheduled_transactions(
        self,
        status: Optional[str] = None,
        limit: int = 50
    ) -> list[dict]:
        """
        List scheduled transactions with optional filtering.
        
        Args:
            status: Filter by status (pending, sent, failed, cancelled)
            limit: Maximum number of results
        
        Returns:
            List of scheduled transactions
        """
        query = "SELECT * FROM scheduled_transactions"
        params = []
        
        if status:
            query += " WHERE status = $1"
            params.append(status)
            query += " ORDER BY scheduled_at DESC LIMIT $2"
        else:
            query += " ORDER BY scheduled_at DESC LIMIT $1"
        
        params.append(limit)
        
        rows = await self._db.fetch(query, params=tuple(params))
        return [dict(row) for row in rows]
    
    async def cancel_scheduled_transaction(self, tx_id: int) -> bool:
        """Cancel a pending scheduled transaction."""
        await self._db.execute(
            """UPDATE scheduled_transactions
               SET status = 'cancelled', updated_at = $1
               WHERE id = $2 AND status = 'pending'""",
            (datetime.now(timezone.utc), tx_id)
        )
        
        logger.info("Scheduled transaction cancelled: id=%s", tx_id)
        return True
    
    async def process_due_transactions(self) -> list[dict]:
        """
        Background task: Process transactions that are due to be sent.
        
        This should be called periodically (e.g., every minute).
        Finds all pending transactions with scheduled_at <= now and sends them.
        
        Returns:
            List of processed transaction results
        """
        now = datetime.now(timezone.utc)
        
        # Find due transactions
        due = await self._db.fetch("""SELECT * FROM scheduled_transactions
               WHERE status = 'pending' AND scheduled_at <= $1
               ORDER BY scheduled_at ASC
               LIMIT 100""", params=(now,)
        )
        
        if not due:
            return []
        
        logger.info("Processing %d due scheduled transactions", len(due))
        results = []
        
        for row in due:
            tx_dict = dict(row)
            result = await self._process_one_transaction(tx_dict)
            results.append(result)
        
        return results
    
    async def _process_one_transaction(self, scheduled_tx: dict) -> dict:
        """Process one scheduled transaction."""
        tx_id = scheduled_tx["id"]
        
        try:
            # Send the transaction
            request = SendTransactionRequest(
                token=scheduled_tx["token"],
                to_address=scheduled_tx["to_address"],
                value=scheduled_tx["value"],
                info=scheduled_tx.get("info"),
                json_info=scheduled_tx.get("json_info")
            )
            
            tx_unid = await self._tx_service.send_transaction(request, validate=True)
            
            now = datetime.now(timezone.utc)
            
            # Update status to sent
            await self._db.execute(
                """UPDATE scheduled_transactions
                   SET status = 'sent', sent_at = $1, tx_unid = $2, updated_at = $3
                   WHERE id = $4""",
                (now, tx_unid, now, tx_id)
            )
            
            # Handle recurring
            if scheduled_tx.get("recurrence_rule"):
                await self._schedule_next_occurrence(scheduled_tx)
            
            # Emit event
            event_manager = get_event_manager()
            await event_manager.emit(EventType.TRANSACTION_SENT, {
                "scheduled_tx_id": tx_id,
                "tx_unid": tx_unid,
                "value": scheduled_tx["value"],
                "to_address": scheduled_tx["to_address"]
            })
            
            logger.info(
                "Scheduled transaction sent: id=%s, tx_unid=%s",
                tx_id, tx_unid
            )
            
            return {"id": tx_id, "status": "sent", "tx_unid": tx_unid}
            
        except Exception as e:
            # Mark as failed
            error_msg = str(e)
            await self._db.execute(
                """UPDATE scheduled_transactions
                   SET status = 'failed', error_message = $1, updated_at = $2
                   WHERE id = $3""",
                (error_msg, datetime.now(timezone.utc), tx_id)
            )
            
            logger.error(
                "Scheduled transaction failed: id=%s, error=%s",
                tx_id, error_msg
            )
            
            # Emit failure event
            event_manager = get_event_manager()
            await event_manager.emit(EventType.TRANSACTION_FAILED, {
                "scheduled_tx_id": tx_id,
                "error": error_msg
            })
            
            return {"id": tx_id, "status": "failed", "error": error_msg}
    
    async def _schedule_next_occurrence(self, scheduled_tx: dict):
        """For recurring transactions, create the next occurrence."""
        recurrence_rule = scheduled_tx["recurrence_rule"]
        if not recurrence_rule:
            return
        
        # Calculate next run time
        base_time = datetime.fromisoformat(scheduled_tx["scheduled_at"])
        cron = croniter(recurrence_rule, base_time)
        next_run = cron.get_next(datetime)
        
        # Create new pending transaction
        await self.create_scheduled_transaction(
            token=scheduled_tx["token"],
            to_address=scheduled_tx["to_address"],
            value=scheduled_tx["value"],
            scheduled_at=next_run,
            info=scheduled_tx.get("info"),
            json_info=scheduled_tx.get("json_info"),
            recurrence_rule=recurrence_rule
        )
        
        logger.info(
            "Scheduled next recurring transaction: next_run=%s",
            next_run
        )
    
    async def get_upcoming_transactions(self, hours: int = 24) -> list[dict]:
        """Get transactions scheduled in the next N hours."""
        now = datetime.now(timezone.utc)
        future = now + timedelta(hours=hours)
        
        rows = await self._db.fetch("""SELECT * FROM scheduled_transactions
               WHERE status = 'pending' AND scheduled_at BETWEEN $1 AND $2
               ORDER BY scheduled_at ASC""", params=(now, future)
        )
        
        return [dict(row) for row in rows]
