"""
Telegram Notifier Integration

Sends notifications via Telegram Bot API for:
- Pending signatures (multi-sig transactions)
- Completed signatures (threshold reached)
- Transaction alerts
"""

import logging
from typing import Optional
import aiohttp
import asyncio
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """
    Send notifications via Telegram Bot API.

    Features:
    - Async HTTP client with retry logic
    - Markdown formatting support
    - Error handling for API failures
    - Rate limiting respect
    """

    def __init__(
        self,
        bot_token: str,
        default_chat_id: Optional[str] = None,
        max_retries: int = 3,
        timeout: int = 10,
    ):
        """
        Initialize Telegram notifier.

        Args:
            bot_token: Telegram bot token from @BotFather
            default_chat_id: Default chat/channel ID to send messages to
            max_retries: Maximum number of retry attempts for failed requests
            timeout: Request timeout in seconds
        """
        self.bot_token = bot_token
        self.default_chat_id = default_chat_id
        self.base_url = f"https://api.telegram.org/bot{bot_token}"
        self.max_retries = max_retries
        self.timeout = aiohttp.ClientTimeout(total=timeout)

    async def send_message(
        self,
        message: str,
        chat_id: Optional[str] = None,
        parse_mode: str = "Markdown",
        disable_notification: bool = False,
    ) -> dict:
        """
        Send a message to Telegram.

        Args:
            message: Message text to send
            chat_id: Target chat ID (uses default if not provided)
            parse_mode: Message formatting mode (Markdown, HTML, or None)
            disable_notification: Send silently without notification

        Returns:
            API response dict with message details

        Raises:
            ValueError: If no chat_id provided and no default set
            aiohttp.ClientError: If API request fails after retries
        """
        target_chat_id = chat_id or self.default_chat_id
        if not target_chat_id:
            raise ValueError("No chat_id provided and no default_chat_id set")

        url = f"{self.base_url}/sendMessage"
        payload = {
            "chat_id": target_chat_id,
            "text": message,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification,
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                async with aiohttp.ClientSession(timeout=self.timeout) as session:
                    async with session.post(url, json=payload) as response:
                        response.raise_for_status()
                        result = await response.json()

                        if not result.get("ok"):
                            error_msg = result.get("description", "Unknown error")
                            logger.error(
                                f"Telegram API error: {error_msg}",
                                extra={"response": result},
                            )
                            raise aiohttp.ClientError(f"Telegram API error: {error_msg}")

                        logger.info(
                            f"Telegram message sent successfully to chat {target_chat_id}"
                        )
                        return result

            except aiohttp.ClientError as e:
                logger.warning(
                    f"Attempt {attempt}/{self.max_retries} failed: {e}",
                    extra={"chat_id": target_chat_id},
                )
                if attempt == self.max_retries:
                    logger.error(
                        f"Failed to send Telegram message after {self.max_retries} attempts",
                        extra={"error": str(e)},
                    )
                    raise
                # Exponential backoff: 1s, 2s, 4s
                await asyncio.sleep(2 ** (attempt - 1))

            except Exception as e:
                logger.error(
                    f"Unexpected error sending Telegram message: {e}",
                    extra={"error": str(e), "type": type(e).__name__},
                )
                raise

    async def notify_pending_signature(
        self,
        tx_unid: str,
        token: str,
        value: str,
        to_addr: str,
        current_signatures: int = 0,
        required_signatures: int = 0,
        wallet_name: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> dict:
        """
        Send notification about a new pending signature request.

        Args:
            tx_unid: Transaction unique ID
            token: Token identifier (network:::TOKEN###wallet)
            value: Transaction amount
            to_addr: Destination address
            current_signatures: Number of signatures collected
            required_signatures: Total signatures needed
            wallet_name: Wallet name (extracted from token if not provided)
            chat_id: Target chat ID (optional)

        Returns:
            API response dict
        """
        # Extract wallet name from token if not provided
        if not wallet_name and "###" in token:
            wallet_name = token.split("###")[1]

        # Parse token for display
        token_parts = token.split(":::")
        if len(token_parts) >= 2:
            token_symbol = token_parts[1].split("###")[0]
        else:
            token_symbol = "Unknown"

        # Truncate address for readability
        short_addr = f"{to_addr[:8]}...{to_addr[-6:]}" if len(to_addr) > 20 else to_addr

        # Build message
        message = f"🔔 *New Signature Required*\n\n"
        message += f"*Transaction ID:* `{tx_unid}`\n"
        message += f"*Amount:* {value} {token_symbol}\n"
        message += f"*To:* `{short_addr}`\n"

        if wallet_name:
            message += f"*Wallet:* {wallet_name}\n"

        if required_signatures > 0:
            message += f"*Progress:* {current_signatures}/{required_signatures} signed\n"

        message += f"\n_Please review and sign this transaction._"

        return await self.send_message(message, chat_id=chat_id)

    async def notify_signature_complete(
        self,
        tx_unid: str,
        token: str,
        value: str,
        to_addr: str,
        signatures_count: int,
        chat_id: Optional[str] = None,
    ) -> dict:
        """
        Send notification when signature threshold is reached.

        Args:
            tx_unid: Transaction unique ID
            token: Token identifier
            value: Transaction amount
            to_addr: Destination address
            signatures_count: Total signatures collected
            chat_id: Target chat ID (optional)

        Returns:
            API response dict
        """
        # Parse token for display
        token_parts = token.split(":::")
        if len(token_parts) >= 2:
            token_symbol = token_parts[1].split("###")[0]
        else:
            token_symbol = "Unknown"

        # Truncate address
        short_addr = f"{to_addr[:8]}...{to_addr[-6:]}" if len(to_addr) > 20 else to_addr

        message = f"✅ *Signature Complete*\n\n"
        message += f"*Transaction ID:* `{tx_unid}`\n"
        message += f"*Amount:* {value} {token_symbol}\n"
        message += f"*To:* `{short_addr}`\n"
        message += f"*Signatures:* {signatures_count}\n"
        message += f"\n_Transaction ready for broadcast._"

        return await self.send_message(message, chat_id=chat_id)

    async def notify_transaction_alert(
        self,
        alert_type: str,
        title: str,
        description: str,
        severity: str = "info",
        chat_id: Optional[str] = None,
    ) -> dict:
        """
        Send a generic transaction alert.

        Args:
            alert_type: Type of alert (e.g., "failed", "high_value", "unusual")
            title: Alert title
            description: Alert description
            severity: Alert severity (info, warning, error)
            chat_id: Target chat ID (optional)

        Returns:
            API response dict
        """
        # Map severity to emoji
        emoji_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅",
        }
        emoji = emoji_map.get(severity.lower(), "📢")

        message = f"{emoji} *{title}*\n\n"
        message += f"{description}\n"
        message += f"\n_Type: {alert_type} | Severity: {severity}_"

        return await self.send_message(
            message,
            chat_id=chat_id,
            disable_notification=(severity == "info"),
        )

    async def test_connection(self) -> bool:
        """
        Test connection to Telegram API.

        Returns:
            True if connection successful, False otherwise
        """
        url = f"{self.base_url}/getMe"
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.get(url) as response:
                    response.raise_for_status()
                    result = await response.json()
                    if result.get("ok"):
                        bot_info = result.get("result", {})
                        logger.info(
                            f"Telegram connection successful: @{bot_info.get('username')}"
                        )
                        return True
                    return False
        except Exception as e:
            logger.error(f"Telegram connection test failed: {e}")
            return False
