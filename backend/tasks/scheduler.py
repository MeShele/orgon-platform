"""APScheduler setup for periodic tasks."""

import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

from backend.config import get_config

logger = logging.getLogger("orgon.scheduler")

_scheduler: AsyncIOScheduler | None = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler()
    return _scheduler


def setup_scheduler(
    sync_service,
    balance_service,
    transaction_service,
    network_service=None,
    signature_service=None,
    scheduled_transaction_service=None,
    webhook_service=None
):
    """Configure scheduled jobs."""
    config = get_config()
    scheduler = get_scheduler()

    balance_interval = config["sync"].get("balance_interval_seconds", 300)
    pending_interval = config["sync"].get("pending_tx_interval_seconds", 60)
    signature_check_interval = config["sync"].get("signature_check_interval_seconds", 300)  # 5 min

    async def sync_balances_job():
        try:
            await sync_service.sync_balances()
            await balance_service.record_balance_snapshot()
        except Exception as e:
            logger.error("Balance sync job failed: %s", e)

    async def check_pending_tx_job():
        try:
            await transaction_service.sync_transactions()
        except Exception as e:
            logger.error("Pending TX check job failed: %s", e)

    async def sync_full_job():
        try:
            await sync_service.sync_all()
        except Exception as e:
            logger.error("Full sync job failed: %s", e)

    scheduler.add_job(
        sync_balances_job,
        IntervalTrigger(seconds=balance_interval),
        id="sync_balances",
        name="Sync token balances",
    )

    scheduler.add_job(
        check_pending_tx_job,
        IntervalTrigger(seconds=pending_interval),
        id="check_pending_tx",
        name="Check pending transactions",
    )

    # Full sync every hour
    scheduler.add_job(
        sync_full_job,
        IntervalTrigger(hours=1),
        id="sync_full",
        name="Full data sync",
    )

    # Network cache refresh every hour
    if network_service:
        async def refresh_network_cache_job():
            try:
                await network_service.refresh_cache()
            except Exception as e:
                logger.error("Network cache refresh job failed: %s", e)

        scheduler.add_job(
            refresh_network_cache_job,
            IntervalTrigger(hours=1),
            id="refresh_network_cache",
            name="Refresh network cache",
        )
        logger.info("Network cache refresh job added (every hour)")

    # Pending signatures check
    if signature_service:
        async def check_pending_signatures_job():
            try:
                new_pending = await signature_service.check_new_pending_signatures()
                if new_pending:
                    logger.info("Found %d new pending signatures", len(new_pending))
            except Exception as e:
                logger.error("Pending signatures check job failed: %s", e)

        scheduler.add_job(
            check_pending_signatures_job,
            IntervalTrigger(seconds=signature_check_interval),
            id="check_pending_signatures",
            name="Check pending signatures",
        )
        logger.info("Pending signatures check job added (every %ds)", signature_check_interval)
    
    # Process scheduled transactions (every minute)
    if scheduled_transaction_service:
        async def process_scheduled_tx_job():
            try:
                results = await scheduled_transaction_service.process_due_transactions()
                if results:
                    logger.info("Processed %d scheduled transactions", len(results))
            except Exception as e:
                logger.error("Scheduled transactions processing job failed: %s", e)
        
        scheduler.add_job(
            process_scheduled_tx_job,
            IntervalTrigger(minutes=1),
            id="process_scheduled_transactions",
            name="Process scheduled transactions",
        )
        logger.info("Scheduled transactions processing job added (every 1 min)")

    # Prune `partner_request_nonces` rows older than the replay window.
    # Without this the table grows unbounded — every B2B request adds a
    # row and the only filter is age. Runs hourly, deletes anything past
    # the window we actually enforce in the middleware (5 min drift +
    # safety margin → keep 1 hour).
    async def prune_partner_nonces_job():
        from backend.main import get_database
        db = get_database()
        if db is None:
            return
        try:
            await db.execute(
                "DELETE FROM partner_request_nonces WHERE seen_at < NOW() - interval '1 hour'"
            )
        except Exception as e:
            logger.error("Partner nonce prune job failed: %s", e)

    scheduler.add_job(
        prune_partner_nonces_job,
        IntervalTrigger(minutes=15),
        id="prune_partner_nonces",
        name="Prune partner replay-protection nonces",
    )
    logger.info("Partner nonce prune job added (every 15 min)")

    # Process pending webhook events (every 30 seconds)
    if webhook_service:
        async def process_webhooks_job():
            try:
                processed = await webhook_service.process_pending_events(batch_size=100)
                if processed > 0:
                    logger.debug("Processed %d webhook events", processed)
            except Exception as e:
                logger.error("Webhook processing job failed: %s", e)
        
        scheduler.add_job(
            process_webhooks_job,
            IntervalTrigger(seconds=30),
            id="process_webhooks",
            name="Process pending webhooks",
        )
        logger.info("Webhook processing job added (every 30s)")
    
    logger.info(
        "Scheduler configured: balances every %ds, pending TX every %ds",
        balance_interval, pending_interval,
    )
    return scheduler
