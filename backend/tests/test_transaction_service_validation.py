"""Unit tests for TransactionService validation helpers."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from backend.services.transaction_service import TransactionService, TransactionValidationError
from backend.safina.models import Token, SendTransactionRequest


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
    """TransactionService instance with mocked dependencies."""
    return TransactionService(mock_client, mock_db)


class TestFormatToken:
    """Tests for format_token helper."""

    def test_formats_token_correctly(self, service):
        """Should format token in Safina format."""
        result = service.format_token("5010", "TRX", "WALLET123")
        assert result == "5010:::TRX###WALLET123"

    def test_handles_different_networks(self, service):
        """Should work with different network IDs."""
        assert service.format_token("1000", "BTC", "WALLET1") == "1000:::BTC###WALLET1"
        assert service.format_token("3000", "ETH", "WALLET2") == "3000:::ETH###WALLET2"

    def test_handles_long_wallet_names(self, service):
        """Should handle long wallet names."""
        long_name = "A" * 100
        result = service.format_token("5010", "USDT", long_name)
        assert result == f"5010:::USDT###{long_name}"


class TestDecimalConversion:
    """Tests for decimal conversion helpers."""

    def test_convert_to_safina_format(self, service):
        """Should convert period to comma."""
        assert service.convert_decimal_to_safina("10.5") == "10,5"
        assert service.convert_decimal_to_safina("100.25") == "100,25"
        assert service.convert_decimal_to_safina("0.001") == "0,001"

    def test_convert_from_safina_format(self, service):
        """Should convert comma to period."""
        assert service.convert_decimal_from_safina("10,5") == "10.5"
        assert service.convert_decimal_from_safina("100,25") == "100.25"
        assert service.convert_decimal_from_safina("0,001") == "0.001"

    def test_handles_no_decimal(self, service):
        """Should handle values without decimals."""
        assert service.convert_decimal_to_safina("100") == "100"
        assert service.convert_decimal_from_safina("100") == "100"

    def test_handles_multiple_decimals(self, service):
        """Should handle multiple decimal separators (edge case)."""
        # This is technically invalid, but the function should still work
        assert service.convert_decimal_to_safina("1.000.5") == "1,000,5"


class TestValidateTransaction:
    """Tests for validate_transaction method."""

    @pytest.mark.asyncio
    async def test_valid_transaction(self, service, mock_client):
        """Should validate correct transaction."""
        # Arrange
        token = "5010:::TRX###WALLET1"
        to_address = "TRx6xXChS5sXz3mpvLSNfKuL6w3PBdMZzL"
        value = "10.5"

        mock_client.get_wallet_tokens = AsyncMock(return_value=[
            Token(
                id="1",
                wallet_id="254",
                network="5010",
                token="TRX",
                value="100,0",
                decimals="6",
                value_hex="0x5F5E100"
            )
        ])

        # Act
        result = await service.validate_transaction(
            token, to_address, value, check_balance=True
        )

        # Assert
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["balance"] == Decimal("100.0")

    @pytest.mark.asyncio
    async def test_invalid_token_format(self, service, mock_client):
        """Should detect invalid token format."""
        # Arrange
        token = "INVALID_TOKEN"
        to_address = "TRx6xXChS5sXz3mpvLSNfKuL6w3PBdMZzL"
        value = "10.5"

        # Act
        result = await service.validate_transaction(
            token, to_address, value, check_balance=False
        )

        # Assert
        assert result["valid"] is False
        assert any("token format" in err.lower() for err in result["errors"])

    @pytest.mark.asyncio
    async def test_missing_address(self, service, mock_client):
        """Should detect missing address."""
        # Arrange
        token = "5010:::TRX###WALLET1"
        to_address = ""
        value = "10.5"

        # Act
        result = await service.validate_transaction(
            token, to_address, value, check_balance=False
        )

        # Assert
        assert result["valid"] is False
        assert any("address is required" in err.lower() for err in result["errors"])

    @pytest.mark.asyncio
    async def test_address_too_short(self, service, mock_client):
        """Should detect address too short."""
        # Arrange
        token = "5010:::TRX###WALLET1"
        to_address = "ABC"
        value = "10.5"

        # Act
        result = await service.validate_transaction(
            token, to_address, value, check_balance=False
        )

        # Assert
        assert result["valid"] is False
        assert any("too short" in err.lower() for err in result["errors"])

    @pytest.mark.asyncio
    async def test_invalid_amount(self, service, mock_client):
        """Should detect invalid amount."""
        # Arrange
        token = "5010:::TRX###WALLET1"
        to_address = "TRx6xXChS5sXz3mpvLSNfKuL6w3PBdMZzL"
        value = "invalid"

        # Act
        result = await service.validate_transaction(
            token, to_address, value, check_balance=False
        )

        # Assert
        assert result["valid"] is False
        assert any("invalid amount" in err.lower() for err in result["errors"])

    @pytest.mark.asyncio
    async def test_zero_amount(self, service, mock_client):
        """Should detect zero amount."""
        # Arrange
        token = "5010:::TRX###WALLET1"
        to_address = "TRx6xXChS5sXz3mpvLSNfKuL6w3PBdMZzL"
        value = "0"

        # Act
        result = await service.validate_transaction(
            token, to_address, value, check_balance=False
        )

        # Assert
        assert result["valid"] is False
        assert any("greater than zero" in err.lower() for err in result["errors"])

    @pytest.mark.asyncio
    async def test_insufficient_balance(self, service, mock_client):
        """Should detect insufficient balance."""
        # Arrange
        token = "5010:::TRX###WALLET1"
        to_address = "TRx6xXChS5sXz3mpvLSNfKuL6w3PBdMZzL"
        value = "200.0"  # More than balance

        mock_client.get_wallet_tokens = AsyncMock(return_value=[
            Token(
                id="1",
                wallet_id="254",
                network="5010",
                token="TRX",
                value="100,0",  # Balance: 100
                decimals="6",
                value_hex="0x5F5E100"
            )
        ])

        # Act
        result = await service.validate_transaction(
            token, to_address, value, check_balance=True
        )

        # Assert
        assert result["valid"] is False
        assert any("insufficient balance" in err.lower() for err in result["errors"])

    @pytest.mark.asyncio
    async def test_skips_balance_check_when_disabled(self, service, mock_client):
        """Should not check balance when check_balance=False."""
        # Arrange
        token = "5010:::TRX###WALLET1"
        to_address = "TRx6xXChS5sXz3mpvLSNfKuL6w3PBdMZzL"
        value = "200.0"

        # Act
        result = await service.validate_transaction(
            token, to_address, value, check_balance=False
        )

        # Assert
        assert result["valid"] is True
        mock_client.get_wallet_tokens.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_balance_check_failure(self, service, mock_client):
        """Should add warning if balance check fails."""
        # Arrange
        token = "5010:::TRX###WALLET1"
        to_address = "TRx6xXChS5sXz3mpvLSNfKuL6w3PBdMZzL"
        value = "10.5"

        mock_client.get_wallet_tokens = AsyncMock(side_effect=Exception("API error"))

        # Act
        result = await service.validate_transaction(
            token, to_address, value, check_balance=True
        )

        # Assert
        assert result["valid"] is True  # Still valid, just warning
        assert len(result["warnings"]) > 0


class TestSendTransactionWithValidation:
    """Tests for send_transaction with validation."""

    @pytest.mark.asyncio
    async def test_sends_valid_transaction(self, service, mock_client, mock_db):
        """Should send transaction when validation passes."""
        # Arrange
        request = SendTransactionRequest(
            token="5010:::TRX###WALLET1",
            to_address="TRx6xXChS5sXz3mpvLSNfKuL6w3PBdMZzL",
            value="10.5",
            info="Test payment"
        )

        mock_client.get_wallet_tokens = AsyncMock(return_value=[
            Token(
                id="1",
                wallet_id="254",
                network="5010",
                token="TRX",
                value="100,0",
                decimals="6",
                value_hex="0x5F5E100"
            )
        ])
        mock_client.send_transaction = AsyncMock(return_value="TX_UNID_123")

        # Act
        tx_unid = await service.send_transaction(request, validate=True)

        # Assert
        assert tx_unid == "TX_UNID_123"
        # Should convert decimal separator
        mock_client.send_transaction.assert_called_once()
        call_args = mock_client.send_transaction.call_args
        assert call_args[1]["value"] == "10,5"  # Comma, not period

    @pytest.mark.asyncio
    async def test_raises_error_on_validation_failure(self, service, mock_client, mock_db):
        """Should raise TransactionValidationError when validation fails."""
        # Arrange
        request = SendTransactionRequest(
            token="INVALID",
            to_address="TRx6xXChS5sXz3mpvLSNfKuL6w3PBdMZzL",
            value="10.5",
            info="Test"
        )

        # Act & Assert
        with pytest.raises(TransactionValidationError):
            await service.send_transaction(request, validate=True)

    @pytest.mark.asyncio
    async def test_skips_validation_when_disabled(self, service, mock_client, mock_db):
        """Should skip validation when validate=False."""
        # Arrange
        request = SendTransactionRequest(
            token="5010:::TRX###WALLET1",
            to_address="TRx6xXChS5sXz3mpvLSNfKuL6w3PBdMZzL",
            value="10.5",
            info="Test"
        )
        mock_client.send_transaction = AsyncMock(return_value="TX_UNID_123")

        # Act
        tx_unid = await service.send_transaction(request, validate=False)

        # Assert
        assert tx_unid == "TX_UNID_123"
        mock_client.get_wallet_tokens.assert_not_called()  # No balance check

    @pytest.mark.asyncio
    async def test_converts_decimal_separator(self, service, mock_client, mock_db):
        """Should always convert decimal separator regardless of validation."""
        # Arrange
        request = SendTransactionRequest(
            token="5010:::TRX###WALLET1",
            to_address="TRx6xXChS5sXz3mpvLSNfKuL6w3PBdMZzL",
            value="123.456",
            info="Test"
        )
        mock_client.send_transaction = AsyncMock(return_value="TX_UNID_123")

        # Act
        await service.send_transaction(request, validate=False)

        # Assert
        call_args = mock_client.send_transaction.call_args
        assert call_args[1]["value"] == "123,456"  # Comma separator


class TestListTransactionsFiltering:
    """Tests for list_transactions filtering."""

    @pytest.mark.asyncio
    async def test_lists_without_filters(self, service, mock_db):
        """Should list all transactions when no filters applied."""
        # Arrange
        mock_db.fetch = AsyncMock(return_value=[
            {"unid": "TX1", "wallet_name": "WALLET1", "status": "confirmed"},
            {"unid": "TX2", "wallet_name": "WALLET2", "status": "pending"},
        ])

        # Act
        result = await service.list_transactions(limit=10, offset=0, filters=None)

        # Assert
        assert len(result) == 2
        # Check query was called correctly
        assert mock_db.fetch.called

    @pytest.mark.asyncio
    async def test_filters_by_wallet_name(self, service, mock_db):
        """Should filter transactions by wallet name."""
        # Arrange
        mock_db.fetch = AsyncMock(return_value=[
            {"unid": "TX1", "wallet_name": "WALLET1", "status": "confirmed"},
        ])

        # Act
        result = await service.list_transactions(
            limit=10,
            offset=0,
            filters={"wallet_name": "WALLET1"}
        )

        # Assert
        assert len(result) == 1
        assert result[0]["wallet_name"] == "WALLET1"
        # Verify query contains wallet filter
        call_args = mock_db.fetch.call_args
        query = call_args[0][0]
        assert "wallet_name = $" in query

    @pytest.mark.asyncio
    async def test_filters_by_status(self, service, mock_db):
        """Should filter transactions by status."""
        # Arrange
        mock_db.fetch = AsyncMock(return_value=[
            {"unid": "TX2", "status": "pending"},
        ])

        # Act
        result = await service.list_transactions(
            limit=10,
            offset=0,
            filters={"status": "pending"}
        )

        # Assert
        assert len(result) == 1
        assert result[0]["status"] == "pending"
        call_args = mock_db.fetch.call_args
        query = call_args[0][0]
        assert "status = $" in query

    @pytest.mark.asyncio
    async def test_filters_by_network(self, service, mock_db):
        """Should filter transactions by network ID."""
        # Arrange
        mock_db.fetch = AsyncMock(return_value=[
            {"unid": "TX1", "network": "5010"},
        ])

        # Act
        result = await service.list_transactions(
            limit=10,
            offset=0,
            filters={"network": "5010"}
        )

        # Assert
        assert len(result) == 1
        call_args = mock_db.fetch.call_args
        query = call_args[0][0]
        assert "network = $" in query

    @pytest.mark.asyncio
    async def test_filters_by_date_range(self, service, mock_db):
        """Should filter transactions by date range."""
        # Arrange
        mock_db.fetch = AsyncMock(return_value=[
            {"unid": "TX1", "created_at": "2026-02-05T12:00:00Z"},
        ])

        # Act
        result = await service.list_transactions(
            limit=10,
            offset=0,
            filters={
                "from_date": "2026-02-05T00:00:00Z",
                "to_date": "2026-02-05T23:59:59Z"
            }
        )

        # Assert
        assert len(result) == 1
        call_args = mock_db.fetch.call_args
        query = call_args[0][0]
        assert "created_at >= $" in query
        assert "created_at <= $" in query

    @pytest.mark.asyncio
    async def test_combines_multiple_filters(self, service, mock_db):
        """Should combine multiple filters."""
        # Arrange
        mock_db.fetch = AsyncMock(return_value=[
            {"unid": "TX1", "wallet_name": "WALLET1", "status": "confirmed", "network": "5010"},
        ])

        # Act
        result = await service.list_transactions(
            limit=10,
            offset=0,
            filters={
                "wallet_name": "WALLET1",
                "status": "confirmed",
                "network": "5010"
            }
        )

        # Assert
        assert len(result) == 1
        call_args = mock_db.fetch.call_args
        query = call_args[0][0]
        assert "wallet_name = $" in query
        assert "status = $" in query
        assert "network = $" in query

    @pytest.mark.asyncio
    async def test_respects_limit_and_offset(self, service, mock_db):
        """Should respect limit and offset parameters."""
        # Arrange
        mock_db.fetch = AsyncMock(return_value=[
            {"unid": "TX3"},
            {"unid": "TX4"},
        ])

        # Act
        result = await service.list_transactions(
            limit=2,
            offset=2,
            filters=None
        )

        # Assert
        call_args = mock_db.fetch.call_args
        query = call_args[0][0]
        params = call_args[0][1]
        assert "LIMIT $" in query and "OFFSET $" in query
        assert params[-2:] == (2, 2)  # Last two params
