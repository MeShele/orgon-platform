"""Dashboard aggregation service.

Aggregates data from multiple services to provide unified dashboard views.
"""

import logging
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from typing import Optional

logger = logging.getLogger("orgon.services.dashboard")


class DashboardService:
    """
    Dashboard service for aggregating cross-service data.

    Responsibilities:
    - Aggregate statistics from all services
    - Generate recent activity feed
    - Detect and report alerts
    - Provide unified dashboard views
    """

    def __init__(
        self,
        wallet_service,
        transaction_service,
        balance_service,
        signature_service,
        network_service,
        db=None,
    ):
        """
        Initialize DashboardService.

        Args:
            wallet_service: WalletService instance
            transaction_service: TransactionService instance
            balance_service: BalanceService instance
            signature_service: SignatureService instance
            db: AsyncDatabase instance (optional, for direct queries)
            network_service: NetworkService instance
        """
        self._wallet_service = wallet_service
        self._transaction_service = transaction_service
        self._balance_service = balance_service
        self._signature_service = signature_service
        self._network_service = network_service
        self._db = db

    async def get_stats(self) -> dict:
        """
        Get aggregated dashboard statistics.

        Returns:
            Dict with:
            - total_wallets: Number of wallets
            - total_balance_usd: Estimated total balance in USD (placeholder)
            - transactions_24h: Transaction count in last 24 hours
            - pending_signatures: Number of pending signatures
            - networks_active: Number of active networks
            - cache_stats: Cache performance statistics
            - last_sync: Last synchronization timestamp
        """
        # Get wallet count
        total_wallets = 0
        try:
            wallets = await self._wallet_service.list_wallets()
            total_wallets = len(wallets)
        except Exception as e:
            logger.warning("Failed to get wallet count: %s", e)

        # Get balance summary
        total_balance_usd = "0.00"  # TODO: Add USD conversion in future
        try:
            balance_summary = await self._balance_service.get_summary()
        except Exception as e:
            logger.warning("Failed to get balance summary: %s", e)

        # Get transactions in last 24 hours
        transactions_24h = 0
        try:
            transactions_24h = await self._get_transactions_count_24h()
        except Exception as e:
            logger.warning("Failed to get 24h transactions: %s", e)

        # Get pending signatures count
        pending_signatures = 0
        try:
            pending_sigs = await self._signature_service.get_pending_signatures()
            pending_signatures = len(pending_sigs)
        except Exception as e:
            logger.warning("Failed to get pending signatures: %s", e)

        # Get active networks count
        networks_active = 0
        try:
            networks = await self._network_service.get_networks(status=1)
            networks_active = len(networks)
        except Exception as e:
            logger.warning("Failed to get active networks: %s", e)

        # Get cache statistics
        cache_stats = {}
        try:
            cache_stats = await self._network_service.get_cache_stats()
        except Exception as e:
            logger.warning("Failed to get cache stats: %s", e)

        # Get last sync timestamp
        last_sync = None
        try:
            last_sync = await self._get_last_sync_timestamp()
        except Exception as e:
            logger.warning("Failed to get last sync timestamp: %s", e)

        return {
            "total_wallets": total_wallets,
            "total_balance_usd": total_balance_usd,
            "transactions_24h": transactions_24h,
            "pending_signatures": pending_signatures,
            "networks_active": networks_active,
            "cache_stats": cache_stats,
            "last_sync": last_sync,
        }

    async def get_recent_activity(self, limit: int = 20) -> list[dict]:
        """
        Get recent activity feed from all services.

        Combines and sorts activities from:
        - Recent transactions
        - Signature events
        - Wallet changes

        Args:
            limit: Maximum number of activities to return

        Returns:
            List of activity dicts sorted by timestamp DESC:
            [
                {
                    "type": "transaction|signature|wallet",
                    "timestamp": "ISO datetime",
                    "title": "Brief description",
                    "details": {...},
                    "priority": "low|medium|high"
                }
            ]
        """
        activities = []

        try:
            # Get recent transactions
            tx_activities = await self._get_transaction_activities(limit)
            activities.extend(tx_activities)

            # Get recent signature events
            sig_activities = await self._get_signature_activities(limit)
            activities.extend(sig_activities)

            # Get wallet events (placeholder - no wallet change tracking yet)
            # wallet_activities = await self._get_wallet_activities(limit)
            # activities.extend(wallet_activities)

        except Exception as e:
            logger.error("Failed to get recent activity: %s", e)

        # Sort by timestamp descending
        activities.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        # Return limited results
        return activities[:limit]

    async def get_alerts(self) -> dict:
        """
        Get system alerts and warnings.

        Returns:
            Dict with alert categories:
            {
                "pending_signatures": 3,          # Count
                "pending_signatures_list": [...], # Details
                "failed_transactions": 0,         # Count
                "low_balances": [],               # Wallets with low balance
                "sync_issues": [],                # Sync problems
                "cache_warnings": []              # Cache issues
            }
        """
        alerts = {
            "pending_signatures": 0,
            "pending_signatures_list": [],
            "failed_transactions": 0,
            "failed_transactions_list": [],
            "low_balances": [],
            "sync_issues": [],
            "cache_warnings": [],
        }

        try:
            # Check pending signatures
            pending_sigs = await self._signature_service.get_pending_signatures()
            alerts["pending_signatures"] = len(pending_sigs)
            alerts["pending_signatures_list"] = [
                {
                    "tx_unid": sig.unid,
                    "token": sig.token,
                    "value": sig.tx_value,
                    "to_address": sig.to_addr,
                    "age_hours": self._calculate_age_hours(sig.init_ts),
                }
                for sig in pending_sigs[:10]  # Limit to 10
            ]

            # Check for failed/rejected transactions
            failed_txs = await self._get_failed_transactions()
            alerts["failed_transactions"] = len(failed_txs)
            alerts["failed_transactions_list"] = failed_txs[:10]

            # Check cache health
            cache_stats = await self._network_service.get_cache_stats()
            if cache_stats.get("stale", False):
                alerts["cache_warnings"].append(
                    {
                        "type": "stale_cache",
                        "message": "Network cache is stale, using fallback data",
                        "cache": "networks",
                    }
                )

            # TODO: Add low balance detection
            # TODO: Add sync issue detection

        except Exception as e:
            logger.error("Failed to get alerts: %s", e)
            alerts["sync_issues"].append(
                {"type": "alert_generation_failed", "message": str(e)}
            )

        return alerts

    # --- Helper Methods ---

    async def _get_transactions_count_24h(self) -> int:
        """Get transaction count in last 24 hours."""
        try:
            # Calculate timestamp 24 hours ago
            now = datetime.now(timezone.utc)
            yesterday = now - timedelta(hours=24)
            yesterday_iso = yesterday.isoformat()

            # Get transactions from last 24h
            all_txs = await self._transaction_service.list_transactions(limit=1000)

            # Count those within 24h
            count = 0
            for tx in all_txs:
                tx_time = tx.get("created_at") or tx.get("updated_at")
                if tx_time:
                    # Handle both datetime objects and strings
                    if isinstance(tx_time, str):
                        tx_time = datetime.fromisoformat(tx_time)
                    if tx_time >= yesterday:
                        count += 1

            return count

        except Exception as e:
            logger.warning("Failed to count 24h transactions: %s", e)
            return 0

    async def _get_last_sync_timestamp(self) -> Optional[str]:
        """Get the most recent sync timestamp."""
        try:
            # Check multiple sync timestamps and return the most recent
            if not self._db:
                return None
            
            sync_keys = [
                "balances_synced",
                "transactions_synced",
                "wallets_synced",
                "networks_cache_refreshed",
            ]

            timestamps = []
            for key in sync_keys:
                result = await self._db.fetchrow(
                    "SELECT value FROM sync_state WHERE key = $1", (key,)
                )
                if result and result.get("value"):
                    timestamps.append(result["value"])

            if timestamps:
                # Return the most recent
                timestamps.sort(reverse=True)
                return timestamps[0]

            return None

        except Exception as e:
            logger.warning("Failed to get last sync timestamp: %s", e)
            return None

    async def _get_transaction_activities(self, limit: int) -> list[dict]:
        """Get recent transaction activities."""
        activities = []

        try:
            txs = await self._transaction_service.list_transactions(limit=limit)

            for tx in txs:
                activity = {
                    "type": "transaction",
                    "timestamp": tx.get("created_at") or tx.get("updated_at") or "",
                    "title": self._format_transaction_title(tx),
                    "details": {
                        "tx_unid": tx.get("unid"),
                        "token": tx.get("token_name") or tx.get("token", "").split(":::")[1].split("###")[0] if ":::" in tx.get("token", "") else "",
                        "value": tx.get("value"),
                        "to_address": tx.get("to_addr"),
                        "status": tx.get("status", "unknown"),
                    },
                    "priority": self._get_transaction_priority(tx),
                }
                activities.append(activity)

        except Exception as e:
            logger.warning("Failed to get transaction activities: %s", e)

        return activities

    async def _get_signature_activities(self, limit: int) -> list[dict]:
        """Get recent signature activities."""
        activities = []

        try:
            # Get signature history
            history = await self._signature_service.get_signed_transactions_history(
                user_address=None, limit=limit
            )

            for item in history:
                activity = {
                    "type": "signature",
                    "timestamp": item.get("signed_at", ""),
                    "title": self._format_signature_title(item),
                    "details": {
                        "tx_unid": item.get("tx_unid"),
                        "action": item.get("action"),
                        "signer": item.get("signer_address"),
                        "reason": item.get("reason"),
                    },
                    "priority": "medium" if item.get("action") == "rejected" else "low",
                }
                activities.append(activity)

        except Exception as e:
            logger.warning("Failed to get signature activities: %s", e)

        return activities

    async def _get_failed_transactions(self) -> list[dict]:
        """Get recently failed/rejected transactions."""
        try:
            if not self._db:
                return []

            # Query for rejected transactions in last 7 days
            seven_days_ago = (
                datetime.now(timezone.utc) - timedelta(days=7)
            ).isoformat()

            failed = await self._db.fetch(
                """SELECT unid, token, value, to_addr, status, updated_at
                   FROM transactions
                   WHERE status = 'rejected' AND updated_at >= $1
                   ORDER BY updated_at DESC
                   LIMIT 20""",
                (seven_days_ago,),
            )

            return [dict(tx) for tx in failed]

        except Exception as e:
            logger.warning("Failed to get failed transactions: %s", e)
            return []

    def _format_transaction_title(self, tx: dict) -> str:
        """Format transaction as human-readable title."""
        status = tx.get("status", "unknown")
        token_name = tx.get("token_name") or "Token"
        value = tx.get("value", "$1")

        if status == "confirmed":
            return f"✅ Sent {value} {token_name}"
        elif status == "pending":
            return f"⏳ Pending: {value} {token_name}"
        elif status == "signed":
            return f"✍️ Signed: {value} {token_name}"
        else:
            return f"❓ {status}: {value} {token_name}"

    def _format_signature_title(self, item: dict) -> str:
        """Format signature event as human-readable title."""
        action = item.get("action", "unknown")
        tx_unid = item.get("tx_unid", "unknown")[:8]

        if action == "signed":
            return f"✅ Signed transaction {tx_unid}"
        elif action == "rejected":
            reason = item.get("reason", "")
            if reason:
                return f"❌ Rejected {tx_unid}: {reason}"
            return f"❌ Rejected transaction {tx_unid}"
        else:
            return f"Signature event: {tx_unid}"

    def _get_transaction_priority(self, tx: dict) -> str:
        """Determine priority level for transaction."""
        status = tx.get("status", "unknown")

        if status == "rejected":
            return "high"
        elif status == "pending":
            return "medium"
        else:
            return "low"

    def _calculate_age_hours(self, timestamp: int) -> float:
        """Calculate age in hours from Unix timestamp."""
        try:
            tx_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)
            now = datetime.now(timezone.utc)
            delta = now - tx_time
            return round(delta.total_seconds() / 3600, 1)
        except Exception:
            return 0.0
