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
        # Each sub-step isolated: one failure must not block the others.
        # Global sync (legacy path)
        try:
            await sync_service.sync_balances()
            await balance_service.record_balance_snapshot()
        except Exception as e:
            logger.error("Global balance sync failed: %s", e)
        # Per-tenant sync — critical for multi-tenant: data of wallets
        # created under a tenant EC is invisible to the global EC.
        try:
            from backend.tasks.multi_tenant_sync import sync_balances_all_tenants
            await sync_balances_all_tenants(sync_service._db)
        except Exception as e:
            logger.error("Per-tenant balance sync failed: %s", e)

    async def check_pending_tx_job():
        try:
            await transaction_service.sync_transactions()
        except Exception as e:
            logger.error("Global tx sync failed: %s", e)
        try:
            from backend.tasks.multi_tenant_sync import (
                sync_transactions_all_tenants,
                sync_wallets_all_tenants,
            )
            # Sync wallets in this tick too — refresh addr for any
            # tenant-side wallet Safina just activated.
            await sync_wallets_all_tenants(transaction_service._db)
            await sync_transactions_all_tenants(transaction_service._db)
        except Exception as e:
            logger.error("Per-tenant sync failed: %s", e)

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

    # Prune merchant HMAC replay nonces older than the drift window
    # plus safety. The middleware enforces ±60s; we keep 1h. Without
    # this the table grows by every signed /v1/* request forever.
    async def prune_merchant_nonces_job():
        from backend.main import get_database
        db = get_database()
        if db is None:
            return
        try:
            await db.execute(
                "DELETE FROM merchant_request_nonces WHERE seen_at < NOW() - interval '1 hour'"
            )
        except Exception as e:
            # merchant_request_nonces may not exist yet on a fresh DB
            # before migration 041 applies; demote to debug.
            logger.debug("merchant nonce prune skipped: %s", e)

    scheduler.add_job(
        prune_merchant_nonces_job,
        IntervalTrigger(minutes=15),
        id="prune_merchant_nonces",
        name="Prune merchant HMAC replay nonces",
    )

    # Prune expired idempotency cache rows. TTL is 24h on each row;
    # we sweep hourly. Without this the table monotonically grows.
    async def prune_idempotency_keys_job():
        from backend.main import get_database
        from backend.services.idempotency_service import prune_expired
        db = get_database()
        if db is None or db.pool is None:
            return
        try:
            n = await prune_expired(db.pool)
            if n:
                logger.info("idempotency prune: %d expired rows deleted", n)
        except Exception as e:
            # Table may not exist yet on a fresh DB before migration
            # 047 applies; demote to debug.
            logger.debug("idempotency prune skipped: %s", e)

    scheduler.add_job(
        prune_idempotency_keys_job,
        IntervalTrigger(hours=1),
        id="prune_idempotency_keys",
        name="Prune expired idempotency cache",
    )

    # 90-day retention sweep for webhook_deliveries. NEVER touches
    # in-flight rows (delivered_at IS NULL AND attempts < 6) — only
    # terminal rows beyond the horizon. Daily is enough; partial
    # index from migration 049 keeps the DELETE cheap.
    async def webhook_retention_sweep_job():
        from backend.main import get_database
        db = get_database()
        if db is None or db.pool is None:
            return
        try:
            async with db.pool.acquire() as conn:
                result = await conn.execute(
                    """
                    DELETE FROM webhook_deliveries
                     WHERE created_at < now() - interval '90 days'
                       AND (delivered_at IS NOT NULL OR attempts >= 6)
                    """
                )
            try:
                n = int(result.split()[-1])
            except (ValueError, IndexError):
                n = 0
            if n:
                logger.info("webhook retention sweep: %d terminal rows deleted", n)
        except Exception as e:
            logger.debug("webhook retention sweep skipped: %s", e)

    scheduler.add_job(
        webhook_retention_sweep_job,
        IntervalTrigger(hours=24),
        id="webhook_retention_sweep",
        name="Sweep webhook_deliveries past 90-day retention",
    )

    # Transaction-failure timeout sweep — flips stuck `signed` txs to
    # `failed` and emits `transaction.failed`. Source-of-truth for the
    # `transaction.failed` webhook today; supersedes the deleted
    # Safina-callback path (Wave 30). Threshold is conservative (24h
    # default, env-tunable via `TX_FAILED_TIMEOUT_HOURS`) so genuinely
    # slow Safina broadcasts don't surface as false positives.
    async def transaction_failure_sweep_job():
        from backend.main import get_database
        from backend.services.transaction_failure_sweep import run_tick as tx_fail_run_tick
        db = get_database()
        if db is None or db.pool is None:
            return
        try:
            stats = await tx_fail_run_tick(db.pool)
            if stats.get("candidates_swept"):
                logger.info("tx_failure_sweep: %s", stats)
        except Exception as e:
            logger.error("tx_failure_sweep job failed: %s", e)

    scheduler.add_job(
        transaction_failure_sweep_job,
        IntervalTrigger(hours=1),
        id="transaction_failure_sweep",
        name="Mark stuck-signed transactions as failed",
    )
    logger.info("Transaction-failure timeout sweep added (hourly)")

    # Transaction-uncertain preview signal (Wave 37) — fires once per
    # stuck-signed tx at the ~10-minute mark (env: TX_UNCERTAIN_TIMEOUT_MINUTES).
    # Pairs with the 24h `transaction.failed` sweep: uncertain is a
    # non-terminal "we're checking" preview; failed is the eventual
    # 24h conclusion. Both emit through the same webhook queue;
    # consumers dedupe on `tx_id` and treat later `broadcasted` as
    # superseding any earlier uncertain/failed for the same tx.
    # Interval 5 min so the 10-min threshold has at most ~5 min of
    # additional latency before the warning fires.
    async def transaction_uncertain_sweep_job():
        from backend.main import get_database
        from backend.services.transaction_uncertain_sweep import run_tick as tx_uncertain_run_tick
        db = get_database()
        if db is None or db.pool is None:
            return
        try:
            stats = await tx_uncertain_run_tick(db.pool)
            if stats.get("candidates_swept"):
                logger.info("tx_uncertain_sweep: %s", stats)
        except Exception as e:
            logger.error("tx_uncertain_sweep job failed: %s", e)

    scheduler.add_job(
        transaction_uncertain_sweep_job,
        IntervalTrigger(minutes=5),
        id="transaction_uncertain_sweep",
        name="Emit transaction.uncertain for stuck-signed txs ≥ 10min",
    )
    logger.info("Transaction-uncertain preview sweep added (every 5 min)")

    # Monthly invoice generator. Runs every day at 02:00 UTC and
    # idempotently generates invoices for the PREVIOUS month — so on
    # the 1st of every month all merchants get their invoice within
    # the first 2 hours. If the deploy was down on the 1st, the
    # daily re-run catches up the next day.
    from datetime import date as _date
    async def b2b_monthly_invoice_job():
        from backend.main import get_database
        from backend.services.invoice_service import (
            generate_invoices_for_month, previous_month_period,
        )
        db = get_database()
        if db is None or db.pool is None:
            return
        try:
            period = previous_month_period(_date.today())
            n = await generate_invoices_for_month(db.pool, period_start=period)
            if n:
                logger.info("monthly invoice job: %d invoices created for %s", n, period)
        except Exception as e:
            logger.error("monthly invoice job failed: %s", e)

    from apscheduler.triggers.cron import CronTrigger
    scheduler.add_job(
        b2b_monthly_invoice_job,
        CronTrigger(hour=2, minute=0, timezone="UTC"),
        id="b2b_monthly_invoice",
        name="B2B monthly invoice generator",
    )
    logger.info("Monthly invoice job added (daily 02:00 UTC, catches up previous month)")

    # On-chain deposit watcher (Tron only in V1). Each tick scans a
    # batch of active wallets via TronGrid and writes new inbound
    # transfers into the `deposits` table. Webhook delivery (which
    # this feeds) lands in the next sprint — for now consumers query
    # /v1/wallets/{id}/deposits.
    async def deposit_watch_tick():
        from backend.main import get_database
        from backend.services.deposit_watcher import run_tick as deposit_run_tick
        db = get_database()
        if db is None or db.pool is None:
            return
        try:
            stats = await deposit_run_tick(db.pool)
            if stats.get("deposits_found"):
                logger.info("deposit watcher tick: %s", stats)
        except Exception as e:
            logger.error("deposit watcher tick failed: %s", e)

    scheduler.add_job(
        deposit_watch_tick,
        IntervalTrigger(seconds=60),
        id="deposit_watch_tick",
        name="On-chain deposit watcher (Tron)",
    )
    logger.info("Deposit watcher job added (every 60s, Tron only for V1)")

    # B2B webhook delivery: drains webhook_deliveries queue every 15s
    # with HMAC-signed POST to each merchant's configured URL. Errors
    # are retried with exponential backoff (30s → 2m → 10m → 1h → 6h);
    # six attempts then we mark the row as given up.
    async def b2b_webhook_delivery_tick():
        from backend.main import get_database
        from backend.services.webhook_delivery import run_tick as wh_run_tick
        db = get_database()
        if db is None or db.pool is None:
            return
        try:
            stats = await wh_run_tick(db.pool)
            if any(stats.values()):
                logger.info("b2b webhook tick: %s", stats)
        except Exception as e:
            logger.error("b2b webhook tick failed: %s", e)

    scheduler.add_job(
        b2b_webhook_delivery_tick,
        IntervalTrigger(seconds=15),
        id="b2b_webhook_delivery",
        name="B2B merchant webhook delivery",
    )
    logger.info("B2B webhook delivery job added (every 15s)")

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
