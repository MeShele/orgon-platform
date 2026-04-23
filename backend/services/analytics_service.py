"""Analytics service for dashboard visualizations."""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from backend.database.db_postgres import AsyncDatabase

logger = logging.getLogger("orgon.services.analytics")


class AnalyticsService:
    """
    Analytics and data aggregation for dashboard.
    
    Features:
    - Balance history (time-series)
    - Transaction volume by network
    - Token distribution
    - Signature statistics
    - Daily trends
    """

    def __init__(self, db: AsyncDatabase):
        self._db = db

    async def get_balance_history(self, days: int = 30) -> List[Dict]:
        """
        Get balance history over time.
        
        Args:
            days: Number of days to look back
            
        Returns:
            List of daily balance snapshots
        """
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=days)
        
        # Query transactions grouped by day
        query = """
            WITH daily_activity AS (
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as tx_count,
                    SUM(CASE WHEN value ~ '^[0-9.]+$' THEN CAST(value AS NUMERIC) ELSE 0 END) as total_value
                FROM transactions
                WHERE created_at >= $1 AND created_at <= $2
                GROUP BY DATE(created_at)
                ORDER BY date ASC
            )
            SELECT * FROM daily_activity
        """
        
        rows = await self._db.fetch(query, params=(start_date, end_date))
        
        # Convert to list of dicts
        result = []
        for row in rows:
            result.append({
                "date": row["date"].isoformat(),
                "tx_count": row["tx_count"],
                "total_value": float(row["total_value"]) if row["total_value"] else 0
            })
        
        # Fill missing days with zeros
        date_map = {item["date"]: item for item in result}
        current_date = start_date.date()
        filled_result = []
        
        while current_date <= end_date.date():
            date_str = current_date.isoformat()
            if date_str in date_map:
                filled_result.append(date_map[date_str])
            else:
                filled_result.append({
                    "date": date_str,
                    "tx_count": 0,
                    "total_value": 0
                })
            current_date += timedelta(days=1)
        
        logger.info(f"Generated balance history: {len(filled_result)} days")
        return filled_result

    async def get_transaction_volume(self, network: Optional[int] = None, days: int = 30) -> List[Dict]:
        """
        Get transaction volume grouped by network.
        
        Args:
            network: Optional network ID filter
            
        Returns:
            List of network volumes
        """
        query = """
            SELECT 
                t.network as network_id,
                COALESCE(n.network_name, CAST(t.network AS TEXT)) as network_name,
                COUNT(*) as tx_count,
                SUM(CASE WHEN t.value ~ '^[0-9.]+$' THEN CAST(t.value AS NUMERIC) ELSE 0 END) as total_value
            FROM transactions t
            LEFT JOIN networks_cache n ON t.network = n.network_id
            WHERE t.network IS NOT NULL
        """
        
        params = []
        if network:
            query += " AND t.network = $1"
            params.append(network)
        
        query += " GROUP BY t.network, n.network_name ORDER BY tx_count DESC"
        
        rows = await self._db.fetch(query, params=tuple(params) if params else None)
        
        result = []
        for row in rows:
            result.append({
                "network_id": row["network_id"],
                "network_name": row["network_name"],
                "tx_count": row["tx_count"],
                "total_value": float(row["total_value"]) if row["total_value"] else 0
            })
        
        logger.info(f"Transaction volume: {len(result)} networks")
        return result

    async def get_token_distribution(self) -> List[Dict]:
        """
        Get token distribution (pie chart data).
        
        Returns:
            List of token balances
        """
        query = """
            WITH token_balances AS (
                SELECT 
                    SUBSTRING(token FROM '^[^:]+') as token_symbol,
                    COUNT(*) as tx_count,
                    SUM(CASE WHEN value ~ '^[0-9.]+$' THEN CAST(value AS NUMERIC) ELSE 0 END) as total_value
                FROM transactions
                WHERE token IS NOT NULL
                GROUP BY token_symbol
            )
            SELECT * FROM token_balances
            ORDER BY total_value DESC
            LIMIT 20
        """
        
        rows = await self._db.fetch(query)
        
        result = []
        total_value = 0
        
        for row in rows:
            value = float(row["total_value"]) if row["total_value"] else 0
            total_value += value
            result.append({
                "token": row["token_symbol"],
                "tx_count": row["tx_count"],
                "value": value
            })
        
        # Calculate percentages
        for item in result:
            item["percentage"] = (item["value"] / total_value * 100) if total_value > 0 else 0
        
        logger.info(f"Token distribution: {len(result)} tokens, total value: {total_value}")
        return result

    async def get_signature_stats(self) -> Dict:
        """
        Get signature completion statistics.
        
        Returns:
            Signature stats dictionary
        """
        # Query signature counts
        query_signed = """
            SELECT COUNT(*) as count
            FROM tx_signatures
            WHERE signed_at IS NOT NULL
        """
        
        query_total = """
            SELECT COUNT(*) as count
            FROM tx_signatures
        """
        
        query_pending = """
            SELECT COUNT(DISTINCT tx_unid) as count
            FROM tx_signatures
            WHERE signed_at IS NULL
        """
        
        signed_row = await self._db.fetchrow(query_signed)
        total_row = await self._db.fetchrow(query_total)
        pending_row = await self._db.fetchrow(query_pending)
        
        signed_count = signed_row["count"] if signed_row else 0
        total_count = total_row["count"] if total_row else 0
        pending_count = pending_row["count"] if pending_row else 0
        
        completion_rate = (signed_count / total_count * 100) if total_count > 0 else 0
        
        result = {
            "signed": signed_count,
            "total": total_count,
            "pending": pending_count,
            "completion_rate": round(completion_rate, 2)
        }
        
        logger.info(f"Signature stats: {result}")
        return result

    async def get_daily_trends(
        self,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Get daily transaction trends.
        
        Args:
            from_date: Start date (default: 30 days ago)
            to_date: End date (default: today)
            
        Returns:
            List of daily trends
        """
        if not to_date:
            to_date = datetime.now(timezone.utc)
        if not from_date:
            from_date = to_date - timedelta(days=30)
        
        query = """
            SELECT 
                DATE(created_at) as date,
                COUNT(*) as tx_count,
                COUNT(DISTINCT wallet_name) as active_wallets,
                COUNT(DISTINCT network) as networks_used
            FROM transactions
            WHERE created_at >= $1 AND created_at <= $2
            GROUP BY DATE(created_at)
            ORDER BY date ASC
        """
        
        rows = await self._db.fetch(query, params=(from_date, to_date))
        
        result = []
        for row in rows:
            result.append({
                "date": row["date"].isoformat(),
                "tx_count": row["tx_count"],
                "active_wallets": row["active_wallets"],
                "networks_used": row["networks_used"]
            })
        
        logger.info(f"Daily trends: {len(result)} days")
        return result

    async def get_network_activity(self) -> List[Dict]:
        """
        Get network activity summary.
        
        Returns:
            List of network activities
        """
        query = """
            SELECT 
                t.network as network_id,
                COALESCE(n.network_name, CAST(t.network AS TEXT)) as network_name,
                COUNT(*) as tx_count,
                COUNT(DISTINCT t.wallet_name) as wallet_count,
                MAX(t.created_at) as last_activity
            FROM transactions t
            LEFT JOIN networks_cache n ON t.network = n.network_id
            WHERE t.network IS NOT NULL
            GROUP BY t.network, n.network_name
            ORDER BY tx_count DESC
        """
        
        rows = await self._db.fetch(query)
        
        result = []
        for row in rows:
            result.append({
                "network_id": row["network_id"],
                "network_name": row["network_name"],
                "tx_count": row["tx_count"],
                "wallet_count": row["wallet_count"],
                "last_activity": row["last_activity"].isoformat() if row["last_activity"] else None
            })
        
        logger.info(f"Network activity: {len(result)} networks")
        return result

    async def get_wallet_summary(self) -> Dict:
        """
        Get wallet summary statistics.
        
        Returns:
            Wallet summary dictionary
        """
        query_total = "SELECT COUNT(*) as count FROM wallets"
        query_active = """
            SELECT COUNT(DISTINCT wallet_name) as count
            FROM transactions
            WHERE created_at >= $1
        """
        
        # Active = had transactions in last 7 days
        active_since = datetime.now(timezone.utc) - timedelta(days=7)
        
        total_row = await self._db.fetchrow(query_total)
        active_row = await self._db.fetchrow(query_active, params=(active_since,))
        
        total_wallets = total_row["count"] if total_row else 0
        active_wallets = active_row["count"] if active_row else 0
        
        result = {
            "total": total_wallets,
            "active": active_wallets,
            "inactive": total_wallets - active_wallets
        }
        
        logger.info(f"Wallet summary: {result}")
        return result
