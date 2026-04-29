"""Unit tests for NetworkService."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from backend.services.network_service import NetworkService, CACHE_TTL_SECONDS
from backend.safina.models import Network, TokenInfo
from backend.safina.errors import SafinaNetworkError


@pytest.fixture
def mock_client():
    """Mock SafinaPayClient."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_db():
    """Mock Database."""
    db = AsyncMock()
    db.fetchrow = AsyncMock(return_value=None)
    db.fetch = AsyncMock(return_value=[])
    db.execute = AsyncMock()
    return db


@pytest.fixture
def service(mock_client, mock_db):
    """NetworkService instance with mocked dependencies."""
    return NetworkService(mock_client, mock_db)


@pytest.fixture
def sample_networks():
    """Sample network data."""
    return [
        Network(
            network_id=1000,
            network_name="Bitcoin (BTC)",
            link="https://bitcoin.org",
            address_explorer="https://blockchain.com/btc/address/",
            tx_explorer="https://blockchain.com/btc/tx/",
            block_explorer="https://blockchain.com/btc/block/",
            info=None,
            status=1,
        ),
        Network(
            network_id=5010,
            network_name="Tron Nile TestNet (TRX)",
            link="https://tron.network",
            address_explorer="https://nile.tronscan.org/#/address/",
            tx_explorer="https://nile.tronscan.org/#/transaction/",
            block_explorer="https://nile.tronscan.org/#/block/",
            info=None,
            status=1,
        ),
    ]


@pytest.fixture
def sample_tokens_info():
    """Sample tokens info data."""
    return [
        TokenInfo(token="1000:::BTC", c="0.01", cMin="0.001", cMax="100"),
        TokenInfo(token="5010:::TRX", c="0.01", cMin="0.001", cMax="100"),
        TokenInfo(token="5010:::USDT", c="0.01", cMin="0.001", cMax="100"),
    ]


class TestGetNetworks:
    """Tests for get_networks method."""

    @pytest.mark.asyncio
    async def test_cache_miss_fetches_from_api(self, service, mock_client, mock_db, sample_networks):
        """When cache is empty, should fetch from API and cache."""
        # Arrange
        mock_client.get_networks = AsyncMock(return_value=sample_networks)
        mock_db.fetchrow.return_value = None  # No cache

        # Act
        result = await service.get_networks(status=1)

        # Assert
        assert result == sample_networks
        mock_client.get_networks.assert_called_once_with(1)
        # Should cache the results
        assert mock_db.execute.call_count >= 2  # DELETE + INSERTs

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_data(self, service, mock_client, mock_db, sample_networks):
        """When cache is fresh, should return cached data without API call."""
        # Arrange
        now = datetime.now(timezone.utc)
        mock_db.fetchrow.return_value = {
            "value": now.isoformat(),
            "updated_at": now.isoformat()
        }
        mock_db.fetch.return_value = [
            {
                "network_id": 1000,
                "network_name": "Bitcoin (BTC)",
                "link": "https://bitcoin.org",
                "address_explorer": "https://blockchain.com/btc/address/",
                "tx_explorer": "https://blockchain.com/btc/tx/",
                "block_explorer": "https://blockchain.com/btc/block/",
                "info": None,
                "status": 1,
            }
        ]

        # Act
        result = await service.get_networks(status=1)

        # Assert
        assert len(result) == 1
        assert result[0].network_id == 1000
        mock_client.get_networks.assert_not_called()  # Should not call API

    @pytest.mark.asyncio
    async def test_expired_cache_refetches_from_api(self, service, mock_client, mock_db, sample_networks):
        """When cache is expired, should refetch from API."""
        # Arrange
        expired_time = datetime.now(timezone.utc) - timedelta(seconds=CACHE_TTL_SECONDS + 100)
        mock_db.fetchrow.return_value = {
            "value": expired_time.isoformat(),
            "updated_at": expired_time.isoformat()
        }
        mock_client.get_networks = AsyncMock(return_value=sample_networks)

        # Act
        result = await service.get_networks(status=1)

        # Assert
        assert result == sample_networks
        mock_client.get_networks.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_force_refresh_bypasses_cache(self, service, mock_client, mock_db, sample_networks):
        """When force_refresh=True, should always fetch from API."""
        # Arrange
        now = datetime.now(timezone.utc)
        mock_db.fetchrow.return_value = {
            "value": now.isoformat(),
            "updated_at": now.isoformat()
        }
        mock_client.get_networks = AsyncMock(return_value=sample_networks)

        # Act
        result = await service.get_networks(status=1, force_refresh=True)

        # Assert
        assert result == sample_networks
        mock_client.get_networks.assert_called_once_with(1)

    @pytest.mark.asyncio
    async def test_api_failure_falls_back_to_stale_cache(self, service, mock_client, mock_db):
        """When API fails and stale cache exists, should return stale cache."""
        # Arrange
        expired_time = datetime.now(timezone.utc) - timedelta(seconds=CACHE_TTL_SECONDS + 100)
        mock_db.fetchrow.return_value = {
            "value": expired_time.isoformat(),
            "updated_at": expired_time.isoformat()
        }
        mock_db.fetch.return_value = [
            {
                "network_id": 1000,
                "network_name": "Bitcoin (BTC)",
                "link": None,
                "address_explorer": None,
                "tx_explorer": None,
                "block_explorer": None,
                "info": None,
                "status": 1,
            }
        ]
        mock_client.get_networks = AsyncMock(side_effect=SafinaNetworkError("API down"))

        # Act
        result = await service.get_networks(status=1)

        # Assert
        assert len(result) == 1
        assert result[0].network_id == 1000

    @pytest.mark.asyncio
    async def test_api_failure_no_cache_raises_error(self, service, mock_client, mock_db):
        """When API fails and no cache exists, should raise error."""
        # Arrange
        mock_db.fetchrow.return_value = None
        mock_db.fetch.return_value = []
        mock_client.get_networks = AsyncMock(side_effect=SafinaNetworkError("API down"))

        # Act & Assert
        with pytest.raises(SafinaNetworkError):
            await service.get_networks(status=1)


class TestGetTokensInfo:
    """Tests for get_tokens_info method."""

    @pytest.mark.asyncio
    async def test_cache_miss_fetches_from_api(self, service, mock_client, mock_db, sample_tokens_info):
        """When cache is empty, should fetch from API and cache."""
        # Arrange
        mock_client.get_tokens_info = AsyncMock(return_value=sample_tokens_info)
        mock_db.fetchrow.return_value = None

        # Act
        result = await service.get_tokens_info()

        # Assert
        assert result == sample_tokens_info
        mock_client.get_tokens_info.assert_called_once()
        assert mock_db.execute.call_count >= 2  # DELETE + INSERTs

    @pytest.mark.asyncio
    async def test_cache_hit_returns_cached_data(self, service, mock_client, mock_db):
        """When cache is fresh, should return cached data without API call."""
        # Arrange
        now = datetime.now(timezone.utc)
        mock_db.fetchrow.return_value = {
            "value": now.isoformat(),
            "updated_at": now.isoformat()
        }
        mock_db.fetch.return_value = [
            {
                "token": "5010:::TRX",
                "commission": "0.01",
                "commission_min": "0.001",
                "commission_max": "100",
            }
        ]

        # Act
        result = await service.get_tokens_info()

        # Assert
        assert len(result) == 1
        assert result[0].token == "5010:::TRX"
        mock_client.get_tokens_info.assert_not_called()

    @pytest.mark.asyncio
    async def test_api_failure_falls_back_to_stale_cache(self, service, mock_client, mock_db):
        """When API fails and stale cache exists, should return stale cache."""
        # Arrange
        expired_time = datetime.now(timezone.utc) - timedelta(seconds=CACHE_TTL_SECONDS + 100)
        mock_db.fetchrow.return_value = {
            "value": expired_time.isoformat(),
            "updated_at": expired_time.isoformat()
        }
        mock_db.fetch.return_value = [
            {
                "token": "5010:::TRX",
                "commission": "0.01",
                "commission_min": "0.001",
                "commission_max": "100",
            }
        ]
        mock_client.get_tokens_info = AsyncMock(side_effect=SafinaNetworkError("API down"))

        # Act
        result = await service.get_tokens_info()

        # Assert
        assert len(result) == 1


class TestHelperMethods:
    """Tests for helper methods."""

    @pytest.mark.asyncio
    async def test_get_network_by_id_found(self, service, mock_client, mock_db, sample_networks):
        """Should find network by ID."""
        # Arrange
        mock_client.get_networks = AsyncMock(return_value=sample_networks)
        mock_db.fetchrow.return_value = None

        # Act
        result = await service.get_network_by_id(5010)

        # Assert
        assert result is not None
        assert result.network_id == 5010
        assert result.network_name == "Tron Nile TestNet (TRX)"

    @pytest.mark.asyncio
    async def test_get_network_by_id_not_found(self, service, mock_client, mock_db, sample_networks):
        """Should return None if network not found."""
        # Arrange
        mock_client.get_networks = AsyncMock(return_value=sample_networks)
        mock_db.fetchrow.return_value = None

        # Act
        result = await service.get_network_by_id(9999)

        # Assert
        assert result is None

    @pytest.mark.asyncio
    async def test_get_token_info_found(self, service, mock_client, mock_db, sample_tokens_info):
        """Should find token info by token."""
        # Arrange
        mock_client.get_tokens_info = AsyncMock(return_value=sample_tokens_info)
        mock_db.fetchrow.return_value = None

        # Act
        result = await service.get_token_info("5010:::USDT")

        # Assert
        assert result is not None
        assert result.token == "5010:::USDT"

    @pytest.mark.asyncio
    async def test_get_token_info_not_found(self, service, mock_client, mock_db, sample_tokens_info):
        """Should return None if token info not found."""
        # Arrange
        mock_client.get_tokens_info = AsyncMock(return_value=sample_tokens_info)
        mock_db.fetchrow.return_value = None

        # Act
        result = await service.get_token_info("9999:::FAKE")

        # Assert
        assert result is None


class TestCacheStats:
    """Tests for cache statistics."""

    @pytest.mark.asyncio
    async def test_get_cache_stats(self, service, mock_db):
        """Should return cache statistics."""
        # Arrange
        now = datetime.now(timezone.utc)
        mock_db.fetchrow.side_effect = [
            {"updated_at": now.isoformat()},  # networks state
            {"cnt": 5},  # networks count
            {"updated_at": now.isoformat()},  # tokens state
            {"cnt": 10},  # tokens count
        ]

        # Act
        stats = await service.get_cache_stats()

        # Assert
        assert "networks_age_seconds" in stats
        assert "networks_fresh" in stats
        assert stats["networks_count"] == 5
        assert "tokens_info_age_seconds" in stats
        assert "tokens_info_fresh" in stats
        assert stats["tokens_info_count"] == 10


class TestBackgroundRefresh:
    """Tests for background cache refresh."""

    @pytest.mark.asyncio
    async def test_refresh_cache_updates_both_caches(self, service, mock_client, mock_db, sample_networks, sample_tokens_info):
        """Background refresh should update both networks and tokens_info."""
        # Arrange
        mock_client.get_networks = AsyncMock(return_value=sample_networks)
        mock_client.get_tokens_info = AsyncMock(return_value=sample_tokens_info)
        mock_db.fetchrow.return_value = None

        # Act
        await service.refresh_cache()

        # Assert
        mock_client.get_networks.assert_called_once_with(1)
        mock_client.get_tokens_info.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_cache_handles_errors_gracefully(self, service, mock_client, mock_db):
        """Background refresh should not raise errors."""
        # Arrange
        mock_client.get_networks = AsyncMock(side_effect=Exception("API error"))
        mock_db.fetchrow.return_value = None

        # Act - should not raise
        await service.refresh_cache()

        # Assert - no exception raised
