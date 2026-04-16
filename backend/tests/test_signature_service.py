"""Unit tests for SignatureService."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from backend.services.signature_service import SignatureService
from backend.safina.models import PendingSignature, Transaction
from backend.safina.errors import SafinaError


@pytest.fixture
def mock_client():
    """Mock SafinaPayClient."""
    client = AsyncMock()
    # Mock signer address
    client._signer = MagicMock()
    client._signer.address = "0xA285990a1Ce696d770d578Cf4473d80e0228DF95"
    return client


@pytest.fixture
def mock_db():
    """Mock Database."""
    db = MagicMock()
    db.fetchone = MagicMock(return_value=None)
    db.fetchall = MagicMock(return_value=[])
    db.execute = MagicMock()
    return db


@pytest.fixture
def mock_telegram():
    """Mock Telegram notifier."""
    notifier = AsyncMock()
    notifier.send_message = AsyncMock()
    return notifier


@pytest.fixture
def service(mock_client, mock_db):
    """SignatureService instance without Telegram."""
    return SignatureService(mock_client, mock_db)


@pytest.fixture
def service_with_telegram(mock_client, mock_db, mock_telegram):
    """SignatureService instance with Telegram."""
    return SignatureService(mock_client, mock_db, mock_telegram)


@pytest.fixture
def sample_pending_signatures():
    """Sample pending signature data."""
    return [
        PendingSignature(
            token="5010:::TRX###WALLET1",
            to_addr="TRx6xXChS5sXz3mpvLSNfKuL6w3PBdMZzL",
            tx_value="100,5",
            init_ts=1670786865,
            unid="TX_UNID_1"
        ),
        PendingSignature(
            token="5010:::USDT###WALLET2",
            to_addr="TRx6xXChS5sXz3mpvLSNfKuL6w3PBdMZzL",
            tx_value="50,0",
            init_ts=1670786900,
            unid="TX_UNID_2"
        ),
    ]


class TestGetPendingSignatures:
    """Tests for get_pending_signatures method."""

    @pytest.mark.asyncio
    async def test_returns_pending_signatures(
        self, service, mock_client, sample_pending_signatures
    ):
        """Should return pending signatures from API."""
        # Arrange
        mock_client.get_pending_signatures = AsyncMock(
            return_value=sample_pending_signatures
        )

        # Act
        result = await service.get_pending_signatures()

        # Assert
        assert len(result) == 2
        assert result[0].unid == "TX_UNID_1"
        mock_client.get_pending_signatures.assert_called_once()

    @pytest.mark.asyncio
    async def test_uses_provided_user_address(self, service, mock_client):
        """Should work with custom user address (though API doesn't filter by it)."""
        # Arrange
        mock_client.get_pending_signatures = AsyncMock(return_value=[])
        custom_address = "0xCUSTOM123"

        # Act
        result = await service.get_pending_signatures(user_address=custom_address)

        # Assert
        assert result == []
        mock_client.get_pending_signatures.assert_called_once()

    @pytest.mark.asyncio
    async def test_handles_api_error(self, service, mock_client):
        """Should raise error when API call fails."""
        # Arrange
        mock_client.get_pending_signatures = AsyncMock(
            side_effect=SafinaError("API error")
        )

        # Act & Assert
        with pytest.raises(SafinaError):
            await service.get_pending_signatures()


class TestSignTransaction:
    """Tests for sign_transaction method."""

    @pytest.mark.asyncio
    async def test_signs_transaction_successfully(self, service, mock_client, mock_db):
        """Should sign transaction and record in DB."""
        # Arrange
        tx_unid = "TX_UNID_1"
        mock_client.sign_transaction = AsyncMock(return_value={})
        mock_client.get_tx_signatures_all = AsyncMock(return_value=[
            {"signed": {"ecaddress": "0xAAA"}},
            {"signed": {"ecaddress": "0xBBB"}},
        ])

        # Act
        result = await service.sign_transaction(tx_unid)

        # Assert
        assert result == {}
        mock_client.sign_transaction.assert_called_once_with(tx_unid)
        # Should record in DB
        assert mock_db.execute.called

    @pytest.mark.asyncio
    async def test_uses_custom_user_address(self, service, mock_client, mock_db):
        """Should work with custom user address for logging."""
        # Arrange
        tx_unid = "TX_UNID_1"
        custom_address = "0xCUSTOM123"
        mock_client.sign_transaction = AsyncMock(return_value={})
        mock_client.get_tx_signatures_all = AsyncMock(return_value=[
            {"signed": {"ecaddress": custom_address}}
        ])

        # Act
        await service.sign_transaction(tx_unid, user_address=custom_address)

        # Assert
        mock_client.sign_transaction.assert_called_once_with(tx_unid)

    @pytest.mark.asyncio
    async def test_handles_sign_error(self, service, mock_client, mock_db):
        """Should raise error when signing fails."""
        # Arrange
        tx_unid = "TX_UNID_1"
        mock_client.sign_transaction = AsyncMock(
            side_effect=SafinaError("Sign failed")
        )

        # Act & Assert
        with pytest.raises(SafinaError):
            await service.sign_transaction(tx_unid)


class TestRejectTransaction:
    """Tests for reject_transaction method."""

    @pytest.mark.asyncio
    async def test_rejects_transaction_with_reason(self, service, mock_client, mock_db):
        """Should reject transaction and record reason."""
        # Arrange
        tx_unid = "TX_UNID_1"
        reason = "Invalid amount"
        mock_client.reject_transaction = AsyncMock(return_value={})

        # Act
        result = await service.reject_transaction(tx_unid, reason)

        # Assert
        assert result == {}
        mock_client.reject_transaction.assert_called_once_with(tx_unid, reason)
        assert mock_db.execute.called

    @pytest.mark.asyncio
    async def test_rejects_without_reason(self, service, mock_client, mock_db):
        """Should allow rejecting without reason."""
        # Arrange
        tx_unid = "TX_UNID_1"
        mock_client.reject_transaction = AsyncMock(return_value={})

        # Act
        await service.reject_transaction(tx_unid)

        # Assert
        mock_client.reject_transaction.assert_called_once_with(tx_unid, "")

    @pytest.mark.asyncio
    async def test_handles_reject_error(self, service, mock_client):
        """Should raise error when rejection fails."""
        # Arrange
        tx_unid = "TX_UNID_1"
        mock_client.reject_transaction = AsyncMock(
            side_effect=SafinaError("Reject failed")
        )

        # Act & Assert
        with pytest.raises(SafinaError):
            await service.reject_transaction(tx_unid)


class TestGetSignatureStatus:
    """Tests for get_signature_status method."""

    @pytest.mark.asyncio
    async def test_returns_complete_status(self, service, mock_client):
        """Should return complete status when all signed."""
        # Arrange
        tx_unid = "TX_UNID_1"
        mock_client.get_tx_signatures_all = AsyncMock(return_value=[
            {"signed": {"ecaddress": "0xAAA"}},
            {"signed": {"ecaddress": "0xBBB"}},
            {"signed": {"ecaddress": "0xCCC"}},
        ])

        # Act
        status = await service.get_signature_status(tx_unid)

        # Assert
        assert status["tx_unid"] == tx_unid
        assert status["signed_count"] == 3
        assert status["waiting_count"] == 0
        assert status["progress"] == "3/3"
        assert status["is_complete"] is True

    @pytest.mark.asyncio
    async def test_returns_partial_status(self, service, mock_client):
        """Should return partial status when some waiting."""
        # Arrange
        tx_unid = "TX_UNID_1"
        mock_client.get_tx_signatures_all = AsyncMock(return_value=[
            {"signed": {"ecaddress": "0xAAA"}},
            {"wait": {"ecaddress": "0xBBB"}},
            {"wait": {"ecaddress": "0xCCC"}},
        ])

        # Act
        status = await service.get_signature_status(tx_unid)

        # Assert
        assert status["signed_count"] == 1
        assert status["waiting_count"] == 2
        assert status["progress"] == "1/3"
        assert status["is_complete"] is False

    @pytest.mark.asyncio
    async def test_handles_empty_signatures(self, service, mock_client):
        """Should handle transaction with no signatures."""
        # Arrange
        tx_unid = "TX_UNID_1"
        mock_client.get_tx_signatures_all = AsyncMock(return_value=[])

        # Act
        status = await service.get_signature_status(tx_unid)

        # Assert
        assert status["progress"] == "0/0"
        assert status["is_complete"] is False


class TestGetSignedTransactionsHistory:
    """Tests for get_signed_transactions_history method."""

    @pytest.mark.asyncio
    async def test_returns_signed_transactions(self, service, mock_client):
        """Should return history of signed transactions."""
        # Arrange
        from backend.safina.models import SignedTransaction
        signed_txs = [
            SignedTransaction(
                to_addr="TRx6xX...",
                tx_value="100,5",
                tx="0xABC123",
                init_ts=1670786865,
                info="Payment",
                token="5010:::TRX"
            )
        ]
        mock_client.get_signed_transactions = AsyncMock(return_value=signed_txs)

        # Act
        result = await service.get_signed_transactions_history()

        # Assert
        assert len(result) == 1
        assert result[0]["to_addr"] == "TRx6xX..."


class TestCheckNewPendingSignatures:
    """Tests for background check_new_pending_signatures task."""

    @pytest.mark.asyncio
    async def test_detects_new_pending_signatures(
        self, service_with_telegram, mock_client, mock_db, mock_telegram, sample_pending_signatures
    ):
        """Should detect and notify about new pending signatures."""
        # Arrange
        mock_client.get_pending_signatures = AsyncMock(
            return_value=sample_pending_signatures
        )
        mock_db.fetchall.return_value = []  # No previously checked

        # Act
        new_pending = await service_with_telegram.check_new_pending_signatures()

        # Assert
        assert len(new_pending) == 2
        # Should send Telegram notifications using structured method
        assert mock_telegram.notify_pending_signature.call_count == 2

    @pytest.mark.asyncio
    async def test_ignores_already_checked(
        self, service_with_telegram, mock_client, mock_db, sample_pending_signatures
    ):
        """Should not notify about already checked signatures."""
        # Arrange
        mock_client.get_pending_signatures = AsyncMock(
            return_value=sample_pending_signatures
        )
        # All already checked
        mock_db.fetchall.return_value = [
            {"tx_unid": "TX_UNID_1"},
            {"tx_unid": "TX_UNID_2"},
        ]

        # Act
        new_pending = await service_with_telegram.check_new_pending_signatures()

        # Assert
        assert len(new_pending) == 0


class TestTelegramNotifications:
    """Tests for Telegram notification integration."""

    @pytest.mark.asyncio
    async def test_sends_notification_on_sign(
        self, service_with_telegram, mock_client, mock_db, mock_telegram
    ):
        """Should send Telegram notification when transaction is signed."""
        # Arrange
        tx_unid = "TX_UNID_1"
        mock_client.sign_transaction = AsyncMock(return_value={})
        mock_client.get_tx_signatures_all = AsyncMock(return_value=[
            {"signed": {"ecaddress": "0xAAA"}},
            {"wait": {"ecaddress": "0xBBB"}},
        ])

        # Act
        await service_with_telegram.sign_transaction(tx_unid)

        # Assert
        assert mock_telegram.send_message.called

    @pytest.mark.asyncio
    async def test_sends_notification_on_reject(
        self, service_with_telegram, mock_client, mock_db, mock_telegram
    ):
        """Should send Telegram notification when transaction is rejected."""
        # Arrange
        tx_unid = "TX_UNID_1"
        reason = "Invalid"
        mock_client.reject_transaction = AsyncMock(return_value={})

        # Act
        await service_with_telegram.reject_transaction(tx_unid, reason)

        # Assert
        assert mock_telegram.send_message.called

    @pytest.mark.asyncio
    async def test_no_notification_without_telegram(
        self, service, mock_client, mock_db
    ):
        """Should not crash when Telegram notifier not configured."""
        # Arrange
        tx_unid = "TX_UNID_1"
        mock_client.sign_transaction = AsyncMock(return_value={})
        mock_client.get_tx_signatures_all = AsyncMock(return_value=[
            {"signed": {"ecaddress": "0xAAA"}}
        ])

        # Act - should not raise
        await service.sign_transaction(tx_unid)


class TestGetStatistics:
    """Tests for get_statistics method."""

    def test_returns_statistics(self, service, mock_db):
        """Should return signature statistics."""
        # Arrange
        mock_db.fetchone.side_effect = [
            {"cnt": 10},  # signed_last_24h
            {"cnt": 2},   # rejected_last_24h
            {"cnt": 100}, # total_signed
            {"cnt": 5},   # total_rejected
        ]

        # Act
        stats = service.get_statistics()

        # Assert
        assert stats["signed_last_24h"] == 10
        assert stats["rejected_last_24h"] == 2
        assert stats["total_signed"] == 100
        assert stats["total_rejected"] == 5
