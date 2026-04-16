"""
Unit tests for TelegramNotifier integration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.integrations.telegram_notifier import TelegramNotifier


class TestTelegramNotifierInit:
    """Test TelegramNotifier initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        notifier = TelegramNotifier(bot_token="test_token")
        assert notifier.bot_token == "test_token"
        assert notifier.default_chat_id is None
        assert notifier.max_retries == 3
        assert notifier.base_url == "https://api.telegram.org/bottest_token"

    def test_init_with_all_params(self):
        """Test initialization with all parameters."""
        notifier = TelegramNotifier(
            bot_token="test_token",
            default_chat_id="123456",
            max_retries=5,
            timeout=20,
        )
        assert notifier.bot_token == "test_token"
        assert notifier.default_chat_id == "123456"
        assert notifier.max_retries == 5


class TestSendMessage:
    """Test send_message method."""

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Test successful message sending."""
        notifier = TelegramNotifier(
            bot_token="test_token", default_chat_id="123456"
        )

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(
            return_value={"ok": True, "result": {"message_id": 1}}
        )
        mock_response.raise_for_status = MagicMock()

        # Create proper async context manager mock
        mock_post_cm = MagicMock()
        mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_cm.__aexit__ = AsyncMock(return_value=None)

        # Create session mock
        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_post_cm)

        # Create session class mock
        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session_cm):
            result = await notifier.send_message("Test message")

            assert result["ok"] is True
            assert "result" in result
            mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_no_chat_id(self):
        """Test sending message without chat_id raises ValueError."""
        notifier = TelegramNotifier(bot_token="test_token")

        with pytest.raises(ValueError, match="No chat_id provided"):
            await notifier.send_message("Test message")

    @pytest.mark.asyncio
    async def test_send_message_with_explicit_chat_id(self):
        """Test sending message with explicit chat_id overrides default."""
        notifier = TelegramNotifier(
            bot_token="test_token", default_chat_id="123456"
        )

        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.json = AsyncMock(return_value={"ok": True})
        mock_response.raise_for_status = MagicMock()

        mock_post_cm = MagicMock()
        mock_post_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_post_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=mock_post_cm)

        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session_cm):
            await notifier.send_message("Test", chat_id="999")

            # Verify the explicit chat_id was used
            call_args = mock_session.post.call_args
            assert call_args[1]["json"]["chat_id"] == "999"

    @pytest.mark.asyncio
    async def test_send_message_api_error(self):
        """Test handling of Telegram API error."""
        notifier = TelegramNotifier(
            bot_token="test_token", default_chat_id="123456", max_retries=2
        )

        mock_response = MagicMock()
        mock_response.json = AsyncMock(
            return_value={"ok": False, "description": "Bad Request"}
        )
        mock_response.raise_for_status = MagicMock()

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = mock_session_class.return_value.__aenter__.return_value
            mock_session.post.return_value.__aenter__.return_value = mock_response

            with pytest.raises(Exception):
                await notifier.send_message("Test")

    @pytest.mark.asyncio
    async def test_send_message_retry_logic(self):
        """Test retry logic on failure."""
        notifier = TelegramNotifier(
            bot_token="test_token", default_chat_id="123456", max_retries=3
        )

        # Import aiohttp to use real exception
        import aiohttp

        # Create success response for third attempt
        mock_response_success = MagicMock()
        mock_response_success.json = AsyncMock(return_value={"ok": True})
        mock_response_success.raise_for_status = MagicMock()

        # Create context managers
        mock_post_fail_1 = MagicMock()
        mock_post_fail_1.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Network error"))
        mock_post_fail_1.__aexit__ = AsyncMock(return_value=None)

        mock_post_fail_2 = MagicMock()
        mock_post_fail_2.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("Network error"))
        mock_post_fail_2.__aexit__ = AsyncMock(return_value=None)

        mock_post_success = MagicMock()
        mock_post_success.__aenter__ = AsyncMock(return_value=mock_response_success)
        mock_post_success.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.post.side_effect = [mock_post_fail_1, mock_post_fail_2, mock_post_success]

        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session_cm):
            with patch("asyncio.sleep", new_callable=AsyncMock):
                result = await notifier.send_message("Test")
                assert result["ok"] is True
                # Should have been called 3 times (2 failures + 1 success)
                assert mock_session.post.call_count == 3


class TestNotifyPendingSignature:
    """Test notify_pending_signature method."""

    @pytest.mark.asyncio
    async def test_notify_pending_signature(self):
        """Test pending signature notification."""
        notifier = TelegramNotifier(
            bot_token="test_token", default_chat_id="123456"
        )

        # Mock send_message
        notifier.send_message = AsyncMock(return_value={"ok": True})

        result = await notifier.notify_pending_signature(
            tx_unid="TX123",
            token="5010:::TRX###wallet1",
            value="100",
            to_addr="TAbCdEfGhIjKlMnOpQrStUvWxYz1234567",
            current_signatures=1,
            required_signatures=3,
        )

        assert result["ok"] is True
        notifier.send_message.assert_called_once()

        # Check message content
        call_args = notifier.send_message.call_args
        message = call_args[0][0]
        assert "New Signature Required" in message
        assert "TX123" in message
        assert "100 TRX" in message
        assert "1/3 signed" in message

    @pytest.mark.asyncio
    async def test_notify_pending_signature_extracts_wallet_name(self):
        """Test wallet name extraction from token."""
        notifier = TelegramNotifier(
            bot_token="test_token", default_chat_id="123456"
        )
        notifier.send_message = AsyncMock(return_value={"ok": True})

        await notifier.notify_pending_signature(
            tx_unid="TX123",
            token="5010:::TRX###my_wallet",
            value="50",
            to_addr="TAbCdEfG",
        )

        call_args = notifier.send_message.call_args
        message = call_args[0][0]
        assert "my_wallet" in message


class TestNotifySignatureComplete:
    """Test notify_signature_complete method."""

    @pytest.mark.asyncio
    async def test_notify_signature_complete(self):
        """Test signature complete notification."""
        notifier = TelegramNotifier(
            bot_token="test_token", default_chat_id="123456"
        )
        notifier.send_message = AsyncMock(return_value={"ok": True})

        result = await notifier.notify_signature_complete(
            tx_unid="TX456",
            token="5010:::TRX###wallet1",
            value="200",
            to_addr="TAbCdEfGhIjKlMnOpQrStUvWxYz1234567",
            signatures_count=3,
        )

        assert result["ok"] is True
        notifier.send_message.assert_called_once()

        call_args = notifier.send_message.call_args
        message = call_args[0][0]
        assert "Signature Complete" in message
        assert "TX456" in message
        assert "200 TRX" in message
        assert "3" in message


class TestNotifyTransactionAlert:
    """Test notify_transaction_alert method."""

    @pytest.mark.asyncio
    async def test_notify_transaction_alert_info(self):
        """Test info-level alert notification."""
        notifier = TelegramNotifier(
            bot_token="test_token", default_chat_id="123456"
        )
        notifier.send_message = AsyncMock(return_value={"ok": True})

        result = await notifier.notify_transaction_alert(
            alert_type="status_update",
            title="System Status",
            description="All systems operational",
            severity="info",
        )

        assert result["ok"] is True

        # Check that silent notification is enabled for info
        call_args = notifier.send_message.call_args
        assert call_args[1]["disable_notification"] is True

    @pytest.mark.asyncio
    async def test_notify_transaction_alert_error(self):
        """Test error-level alert notification."""
        notifier = TelegramNotifier(
            bot_token="test_token", default_chat_id="123456"
        )
        notifier.send_message = AsyncMock(return_value={"ok": True})

        await notifier.notify_transaction_alert(
            alert_type="failed_tx",
            title="Transaction Failed",
            description="Failed to broadcast transaction",
            severity="error",
        )

        call_args = notifier.send_message.call_args
        message = call_args[0][0]
        assert "❌" in message
        assert "Transaction Failed" in message


class TestConnectionTest:
    """Test test_connection method."""

    @pytest.mark.asyncio
    async def test_connection_success(self):
        """Test successful connection test."""
        notifier = TelegramNotifier(bot_token="test_token")

        mock_response = MagicMock()
        mock_response.json = AsyncMock(
            return_value={"ok": True, "result": {"username": "test_bot"}}
        )
        mock_response.raise_for_status = MagicMock()

        mock_get_cm = MagicMock()
        mock_get_cm.__aenter__ = AsyncMock(return_value=mock_response)
        mock_get_cm.__aexit__ = AsyncMock(return_value=None)

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=mock_get_cm)

        mock_session_cm = MagicMock()
        mock_session_cm.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_cm.__aexit__ = AsyncMock(return_value=None)

        with patch("aiohttp.ClientSession", return_value=mock_session_cm):
            result = await notifier.test_connection()
            assert result is True

    @pytest.mark.asyncio
    async def test_connection_failure(self):
        """Test failed connection test."""
        notifier = TelegramNotifier(bot_token="test_token")

        with patch("aiohttp.ClientSession") as mock_session_class:
            mock_session = mock_session_class.return_value.__aenter__.return_value
            mock_session.get.side_effect = Exception("Connection failed")

            result = await notifier.test_connection()
            assert result is False
