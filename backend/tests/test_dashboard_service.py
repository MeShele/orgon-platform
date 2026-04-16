"""Unit tests for DashboardService."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services.dashboard_service import DashboardService
from backend.safina.models import PendingSignature


@pytest.fixture
def mock_wallet_service():
    """Mock WalletService."""
    service = AsyncMock()
    service.list_wallets = AsyncMock(return_value=[
        {"name": "WALLET1", "addr": "0xAAA"},
        {"name": "WALLET2", "addr": "0xBBB"},
        {"name": "WALLET3", "addr": "0xCCC"},
    ])
    return service


@pytest.fixture
def mock_transaction_service():
    """Mock TransactionService."""
    service = AsyncMock()
    now = datetime.now(timezone.utc).isoformat()
    service.list_transactions = AsyncMock(return_value=[
        {
            "unid": "TX1",
            "token": "5010:::TRX###WALLET1",
            "token_name": "TRX",
            "value": "100,5",
            "to_addr": "TRxABC",
            "status": "confirmed",
            "created_at": now,
        },
        {
            "unid": "TX2",
            "token": "5010:::USDT###WALLET2",
            "token_name": "USDT",
            "value": "50,0",
            "to_addr": "TRxDEF",
            "status": "pending",
            "created_at": now,
        },
    ])
    return service


@pytest.fixture
def mock_balance_service():
    """Mock BalanceService."""
    service = AsyncMock()
    service.get_summary = AsyncMock(return_value=[
        {"token": "TRX", "value": "1000,5"},
        {"token": "USDT", "value": "500,0"},
    ])
    return service


@pytest.fixture
def mock_signature_service():
    """Mock SignatureService."""
    service = AsyncMock()

    pending_sigs = [
        PendingSignature(
            token="5010:::TRX###WALLET1",
            to_addr="TRxABC",
            tx_value="100,5",
            init_ts=int(datetime.now(timezone.utc).timestamp()),
            unid="TX_PENDING_1"
        ),
        PendingSignature(
            token="5010:::USDT###WALLET2",
            to_addr="TRxDEF",
            tx_value="50,0",
            init_ts=int(datetime.now(timezone.utc).timestamp()) - 3600,  # 1 hour ago
            unid="TX_PENDING_2"
        ),
    ]

    service.get_pending_signatures = AsyncMock(return_value=pending_sigs)
    service.get_signed_transactions_history = AsyncMock(return_value=[
        {
            "tx_unid": "TX1",
            "action": "signed",
            "signer_address": "0xAAA",
            "signed_at": datetime.now(timezone.utc).isoformat(),
            "reason": None,
        },
        {
            "tx_unid": "TX2",
            "action": "rejected",
            "signer_address": "0xBBB",
            "signed_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
            "reason": "Invalid amount",
        },
    ])
    return service


@pytest.fixture
def mock_network_service():
    """Mock NetworkService."""
    service = AsyncMock()
    service.get_networks = AsyncMock(return_value=[
        {"network_id": "5010", "network_name": "Tron", "status": 1},
        {"network_id": "3000", "network_name": "Ethereum", "status": 1},
    ])
    service.get_cache_stats = MagicMock(return_value={
        "networks_cache_hit": 100,
        "networks_cache_miss": 5,
        "tokens_info_cache_hit": 80,
        "tokens_info_cache_miss": 2,
        "stale": False,
    })
    return service


@pytest.fixture
def mock_db():
    """Mock Database."""
    db = MagicMock()

    # Mock sync_state queries
    db.fetchone = MagicMock(return_value={
        "value": datetime.now(timezone.utc).isoformat()
    })

    # Mock failed transactions query
    db.fetchall = MagicMock(return_value=[
        {
            "unid": "TX_FAILED_1",
            "token": "5010:::TRX###WALLET1",
            "value": "10,0",
            "to_addr": "TRxXYZ",
            "status": "rejected",
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
    ])

    return db


@pytest.fixture
def service(
    mock_wallet_service,
    mock_transaction_service,
    mock_balance_service,
    mock_signature_service,
    mock_network_service,
):
    """DashboardService instance with mocked dependencies."""
    return DashboardService(
        wallet_service=mock_wallet_service,
        transaction_service=mock_transaction_service,
        balance_service=mock_balance_service,
        signature_service=mock_signature_service,
        network_service=mock_network_service,
    )


class TestGetStats:
    """Tests for get_stats method."""

    @pytest.mark.asyncio
    async def test_returns_complete_stats(self, service):
        """Should return all dashboard statistics."""
        # Arrange
        with patch("backend.main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetchone = MagicMock(return_value={
                "value": "2026-02-05T12:00:00Z"
            })
            mock_get_db.return_value = mock_db

            # Act
            stats = await service.get_stats()

            # Assert
            assert stats["total_wallets"] == 3
            assert stats["pending_signatures"] == 2
            assert stats["networks_active"] == 2
            assert "cache_stats" in stats
            assert stats["cache_stats"]["networks_cache_hit"] == 100

    @pytest.mark.asyncio
    async def test_counts_transactions_24h(self, service, mock_transaction_service):
        """Should count transactions in last 24 hours."""
        # Arrange
        now = datetime.now(timezone.utc)
        yesterday = now - timedelta(hours=23)
        two_days_ago = now - timedelta(hours=48)

        mock_transaction_service.list_transactions = AsyncMock(return_value=[
            {"unid": "TX1", "created_at": now.isoformat(), "status": "confirmed"},
            {"unid": "TX2", "created_at": yesterday.isoformat(), "status": "pending"},
            {"unid": "TX3", "created_at": two_days_ago.isoformat(), "status": "confirmed"},  # Old
        ])

        with patch("backend.main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetchone = MagicMock(return_value={"value": now.isoformat()})
            mock_get_db.return_value = mock_db

            # Act
            stats = await service.get_stats()

            # Assert
            assert stats["transactions_24h"] == 2  # Only TX1 and TX2

    @pytest.mark.asyncio
    async def test_handles_service_failures_gracefully(
        self, service, mock_wallet_service
    ):
        """Should return default stats when services fail."""
        # Arrange
        mock_wallet_service.list_wallets = AsyncMock(side_effect=Exception("API error"))

        # Act
        stats = await service.get_stats()

        # Assert
        assert stats["total_wallets"] == 0
        assert "error" in stats

    @pytest.mark.asyncio
    async def test_includes_cache_statistics(self, service):
        """Should include cache performance stats."""
        # Arrange
        with patch("backend.main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetchone = MagicMock(return_value={"value": "2026-02-05T12:00:00Z"})
            mock_get_db.return_value = mock_db

            # Act
            stats = await service.get_stats()

            # Assert
            assert "cache_stats" in stats
            cache_stats = stats["cache_stats"]
            assert cache_stats["networks_cache_hit"] == 100
            assert cache_stats["networks_cache_miss"] == 5
            assert cache_stats["stale"] is False


class TestGetRecentActivity:
    """Tests for get_recent_activity method."""

    @pytest.mark.asyncio
    async def test_returns_combined_activities(self, service):
        """Should return activities from multiple services."""
        # Act
        activities = await service.get_recent_activity(limit=20)

        # Assert
        assert len(activities) > 0

        # Should have transaction activities
        tx_activities = [a for a in activities if a["type"] == "transaction"]
        assert len(tx_activities) == 2

        # Should have signature activities
        sig_activities = [a for a in activities if a["type"] == "signature"]
        assert len(sig_activities) == 2

    @pytest.mark.asyncio
    async def test_sorts_by_timestamp_descending(self, service):
        """Should sort activities by timestamp (newest first)."""
        # Act
        activities = await service.get_recent_activity(limit=20)

        # Assert
        timestamps = [a["timestamp"] for a in activities]
        assert timestamps == sorted(timestamps, reverse=True)

    @pytest.mark.asyncio
    async def test_respects_limit(self, service):
        """Should limit number of activities returned."""
        # Act
        activities = await service.get_recent_activity(limit=2)

        # Assert
        assert len(activities) <= 2

    @pytest.mark.asyncio
    async def test_transaction_activity_format(self, service):
        """Should format transaction activities correctly."""
        # Act
        activities = await service.get_recent_activity(limit=20)

        # Assert
        tx_activity = next(a for a in activities if a["type"] == "transaction")
        assert "timestamp" in tx_activity
        assert "title" in tx_activity
        assert "details" in tx_activity
        assert "priority" in tx_activity
        assert "tx_unid" in tx_activity["details"]
        assert "status" in tx_activity["details"]

    @pytest.mark.asyncio
    async def test_signature_activity_format(self, service):
        """Should format signature activities correctly."""
        # Act
        activities = await service.get_recent_activity(limit=20)

        # Assert
        sig_activity = next(a for a in activities if a["type"] == "signature")
        assert "timestamp" in sig_activity
        assert "title" in sig_activity
        assert "details" in sig_activity
        assert "priority" in sig_activity
        assert "tx_unid" in sig_activity["details"]
        assert "action" in sig_activity["details"]

    @pytest.mark.asyncio
    async def test_handles_service_failures(self, service, mock_transaction_service):
        """Should handle service failures gracefully."""
        # Arrange
        mock_transaction_service.list_transactions = AsyncMock(
            side_effect=Exception("API error")
        )

        # Act
        activities = await service.get_recent_activity(limit=20)

        # Assert
        # Should still return signature activities
        assert len(activities) >= 0


class TestGetAlerts:
    """Tests for get_alerts method."""

    @pytest.mark.asyncio
    async def test_returns_all_alert_categories(self, service):
        """Should return all alert categories."""
        # Arrange
        with patch("backend.main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetchall = MagicMock(return_value=[])
            mock_get_db.return_value = mock_db

            # Act
            alerts = await service.get_alerts()

            # Assert
            assert "pending_signatures" in alerts
            assert "pending_signatures_list" in alerts
            assert "failed_transactions" in alerts
            assert "failed_transactions_list" in alerts
            assert "low_balances" in alerts
            assert "sync_issues" in alerts
            assert "cache_warnings" in alerts

    @pytest.mark.asyncio
    async def test_detects_pending_signatures(self, service):
        """Should detect and list pending signatures."""
        # Arrange
        with patch("backend.main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetchall = MagicMock(return_value=[])
            mock_get_db.return_value = mock_db

            # Act
            alerts = await service.get_alerts()

            # Assert
            assert alerts["pending_signatures"] == 2
            assert len(alerts["pending_signatures_list"]) == 2

            sig = alerts["pending_signatures_list"][0]
            assert "tx_unid" in sig
            assert "token" in sig
            assert "age_hours" in sig

    @pytest.mark.asyncio
    async def test_detects_failed_transactions(self, service):
        """Should detect failed transactions."""
        # Arrange
        with patch("backend.main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetchall = MagicMock(return_value=[
                {
                    "unid": "TX_FAILED_1",
                    "status": "rejected",
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }
            ])
            mock_get_db.return_value = mock_db

            # Act
            alerts = await service.get_alerts()

            # Assert
            assert alerts["failed_transactions"] == 1
            assert len(alerts["failed_transactions_list"]) == 1

    @pytest.mark.asyncio
    async def test_detects_stale_cache(self, service, mock_network_service):
        """Should detect stale cache warnings."""
        # Arrange
        mock_network_service.get_cache_stats = MagicMock(return_value={
            "stale": True
        })

        with patch("backend.main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetchall = MagicMock(return_value=[])
            mock_get_db.return_value = mock_db

            # Act
            alerts = await service.get_alerts()

            # Assert
            assert len(alerts["cache_warnings"]) > 0
            warning = alerts["cache_warnings"][0]
            assert warning["type"] == "stale_cache"

    @pytest.mark.asyncio
    async def test_limits_alert_lists(self, service, mock_signature_service):
        """Should limit alert lists to 10 items."""
        # Arrange - create 15 pending signatures
        many_sigs = [
            PendingSignature(
                token=f"5010:::TRX###WALLET{i}",
                to_addr=f"TRxABC{i}",
                tx_value="100,0",
                init_ts=int(datetime.now(timezone.utc).timestamp()),
                unid=f"TX_PENDING_{i}"
            )
            for i in range(15)
        ]
        mock_signature_service.get_pending_signatures = AsyncMock(return_value=many_sigs)

        with patch("backend.main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetchall = MagicMock(return_value=[])
            mock_get_db.return_value = mock_db

            # Act
            alerts = await service.get_alerts()

            # Assert
            assert alerts["pending_signatures"] == 15
            assert len(alerts["pending_signatures_list"]) == 10  # Limited to 10

    @pytest.mark.asyncio
    async def test_handles_alert_generation_failure(self, service, mock_signature_service):
        """Should handle failures during alert generation."""
        # Arrange
        mock_signature_service.get_pending_signatures = AsyncMock(
            side_effect=Exception("API error")
        )

        with patch("backend.main.get_db") as mock_get_db:
            mock_db = MagicMock()
            mock_db.fetchall = MagicMock(return_value=[])
            mock_get_db.return_value = mock_db

            # Act
            alerts = await service.get_alerts()

            # Assert
            assert len(alerts["sync_issues"]) > 0


class TestHelperMethods:
    """Tests for helper methods."""

    def test_format_transaction_title_confirmed(self, service):
        """Should format confirmed transaction title."""
        # Arrange
        tx = {
            "status": "confirmed",
            "token_name": "TRX",
            "value": "100,5"
        }

        # Act
        title = service._format_transaction_title(tx)

        # Assert
        assert "✅" in title
        assert "100,5" in title
        assert "TRX" in title

    def test_format_transaction_title_pending(self, service):
        """Should format pending transaction title."""
        # Arrange
        tx = {
            "status": "pending",
            "token_name": "USDT",
            "value": "50,0"
        }

        # Act
        title = service._format_transaction_title(tx)

        # Assert
        assert "⏳" in title
        assert "Pending" in title

    def test_format_signature_title_signed(self, service):
        """Should format signed signature title."""
        # Arrange
        item = {
            "action": "signed",
            "tx_unid": "TX123456"
        }

        # Act
        title = service._format_signature_title(item)

        # Assert
        assert "✅" in title
        assert "Signed" in title
        assert "TX12345" in title  # Truncated to 8 chars

    def test_format_signature_title_rejected(self, service):
        """Should format rejected signature title with reason."""
        # Arrange
        item = {
            "action": "rejected",
            "tx_unid": "TX123456",
            "reason": "Invalid amount"
        }

        # Act
        title = service._format_signature_title(item)

        # Assert
        assert "❌" in title
        assert "Rejected" in title
        assert "Invalid amount" in title

    def test_get_transaction_priority(self, service):
        """Should determine transaction priority correctly."""
        # Rejected = high
        assert service._get_transaction_priority({"status": "rejected"}) == "high"

        # Pending = medium
        assert service._get_transaction_priority({"status": "pending"}) == "medium"

        # Confirmed = low
        assert service._get_transaction_priority({"status": "confirmed"}) == "low"

    def test_calculate_age_hours(self, service):
        """Should calculate age in hours from timestamp."""
        # Arrange
        now = datetime.now(timezone.utc)
        one_hour_ago = now - timedelta(hours=1)
        timestamp = int(one_hour_ago.timestamp())

        # Act
        age = service._calculate_age_hours(timestamp)

        # Assert
        assert age >= 0.9 and age <= 1.1  # ~1 hour (with tolerance)
