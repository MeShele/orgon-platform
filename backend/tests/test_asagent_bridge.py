"""
Unit tests for ASAGENT Bridge integration.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from backend.integrations.asagent_bridge import ASAGENTBridge


class TestASAGENTBridgeInit:
    """Test ASAGENTBridge initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        bridge = ASAGENTBridge()
        assert bridge.gateway_url == "http://localhost:8000"
        assert bridge.timeout == 30
        assert bridge.is_ready is False

    def test_init_with_custom_url(self):
        """Test initialization with custom gateway URL."""
        bridge = ASAGENTBridge(gateway_url="http://example.com:9000")
        assert bridge.gateway_url == "http://example.com:9000"

    def test_strips_trailing_slash(self):
        """Test that trailing slash is removed from URL."""
        bridge = ASAGENTBridge(gateway_url="http://example.com/")
        assert bridge.gateway_url == "http://example.com"


class TestRegisterSkills:
    """Test skill registration."""

    @pytest.mark.asyncio
    async def test_registers_skills_successfully(self):
        """Test successful skill registration."""
        bridge = ASAGENTBridge()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "success": True,
            "registered": 6
        }
        mock_response.raise_for_status = MagicMock()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await bridge.register_orgon_skills()

            assert result["success"] is True
            assert bridge.is_ready is True
            mock_client.post.assert_called_once()

            # Verify POST body structure
            call_args = mock_client.post.call_args
            assert "skills" in call_args[1]["json"]
            skills = call_args[1]["json"]["skills"]
            assert len(skills) == 6

    @pytest.mark.asyncio
    async def test_handles_registration_failure(self):
        """Test handling of registration API failure."""
        bridge = ASAGENTBridge()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=Exception("Connection failed"))
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(Exception):
                await bridge.register_orgon_skills()

            assert bridge.is_ready is False


class TestHandleSkillCall:
    """Test skill execution handling."""

    @pytest.mark.asyncio
    async def test_wallet_balance_skill(self):
        """Test orgon_wallet_balance skill execution."""
        bridge = ASAGENTBridge()

        mock_service = AsyncMock()
        mock_service.get_wallet_balance = AsyncMock(
            return_value={"wallet": "WALLET1", "balance": "100 TRX"}
        )

        with patch("backend.main.get_wallet_service", return_value=mock_service):
            result = await bridge.handle_skill_call(
                skill_name="orgon_wallet_balance",
                params={"wallet_name": "WALLET1"}
            )

            assert result["success"] is True
            assert result["skill"] == "orgon_wallet_balance"
            assert "data" in result
            mock_service.get_wallet_balance.assert_called_once_with("WALLET1")

    @pytest.mark.asyncio
    async def test_list_wallets_skill(self):
        """Test orgon_list_wallets skill execution."""
        bridge = ASAGENTBridge()

        mock_service = AsyncMock()
        mock_service.list_wallets = AsyncMock(
            return_value=[{"name": "WALLET1"}, {"name": "WALLET2"}]
        )

        with patch("backend.main.get_wallet_service", return_value=mock_service):
            result = await bridge.handle_skill_call(
                skill_name="orgon_list_wallets",
                params={}
            )

            assert result["success"] is True
            assert len(result["data"]) == 2

    @pytest.mark.asyncio
    async def test_pending_signatures_skill(self):
        """Test orgon_pending_signatures skill execution."""
        bridge = ASAGENTBridge()

        # Create mock pending signature objects
        mock_pending = MagicMock()
        mock_pending.unid = "TX123"
        mock_pending.token = "5010:::TRX###WALLET1"
        mock_pending.tx_value = "100"
        mock_pending.to_addr = "TAbCdEfG"
        mock_pending.timestamp = "2024-01-01T00:00:00Z"

        mock_service = AsyncMock()
        mock_service.get_pending_signatures = AsyncMock(
            return_value=[mock_pending]
        )

        with patch("backend.main.get_signature_service", return_value=mock_service):
            result = await bridge.handle_skill_call(
                skill_name="orgon_pending_signatures",
                params={}
            )

            assert result["success"] is True
            assert len(result["data"]) == 1
            assert result["data"][0]["tx_unid"] == "TX123"

    @pytest.mark.asyncio
    async def test_send_transaction_skill(self):
        """Test orgon_send_transaction skill execution."""
        bridge = ASAGENTBridge()

        mock_service = AsyncMock()
        mock_service.send_transaction = AsyncMock(
            return_value={"tx_unid": "NEW_TX_123", "status": "pending"}
        )

        with patch("backend.main.get_transaction_service", return_value=mock_service):
            result = await bridge.handle_skill_call(
                skill_name="orgon_send_transaction",
                params={
                    "token": "5010:::TRX###WALLET1",
                    "to_address": "TDestAddr",
                    "value": "50",
                    "info": "Payment"
                }
            )

            assert result["success"] is True
            assert result["data"]["tx_unid"] == "NEW_TX_123"

    @pytest.mark.asyncio
    async def test_recent_transactions_skill(self):
        """Test orgon_recent_transactions skill execution."""
        bridge = ASAGENTBridge()

        mock_service = AsyncMock()
        mock_service.list_transactions = AsyncMock(
            return_value=[
                {"tx_id": "TX1", "amount": "100"},
                {"tx_id": "TX2", "amount": "50"}
            ]
        )

        with patch("backend.main.get_transaction_service", return_value=mock_service):
            result = await bridge.handle_skill_call(
                skill_name="orgon_recent_transactions",
                params={"limit": 20}
            )

            assert result["success"] is True
            assert len(result["data"]) == 2

    @pytest.mark.asyncio
    async def test_dashboard_stats_skill(self):
        """Test orgon_dashboard_stats skill execution."""
        bridge = ASAGENTBridge()

        mock_service = AsyncMock()
        mock_service.get_stats = AsyncMock(
            return_value={
                "total_wallets": 5,
                "transactions_24h": 10,
                "pending_signatures": 2
            }
        )

        with patch("backend.main.get_dashboard_service", return_value=mock_service):
            result = await bridge.handle_skill_call(
                skill_name="orgon_dashboard_stats",
                params={}
            )

            assert result["success"] is True
            assert result["data"]["total_wallets"] == 5

    @pytest.mark.asyncio
    async def test_unknown_skill_returns_error(self):
        """Test handling of unknown skill name."""
        bridge = ASAGENTBridge()

        result = await bridge.handle_skill_call(
            skill_name="unknown_skill",
            params={}
        )

        assert result["success"] is False
        assert result["error_type"] == "validation_error"
        assert "Unknown skill" in result["error"]

    @pytest.mark.asyncio
    async def test_missing_required_params(self):
        """Test handling of missing required parameters."""
        bridge = ASAGENTBridge()

        mock_service = AsyncMock()
        with patch("backend.main.get_wallet_service", return_value=mock_service):
            result = await bridge.handle_skill_call(
                skill_name="orgon_wallet_balance",
                params={}  # Missing wallet_name
            )

            assert result["success"] is False
            assert result["error_type"] == "validation_error"
            assert "wallet_name" in result["error"]

    @pytest.mark.asyncio
    async def test_execution_error_handling(self):
        """Test handling of execution errors."""
        bridge = ASAGENTBridge()

        mock_service = AsyncMock()
        mock_service.list_wallets = AsyncMock(
            side_effect=RuntimeError("Database error")
        )

        with patch("backend.main.get_wallet_service", return_value=mock_service):
            result = await bridge.handle_skill_call(
                skill_name="orgon_list_wallets",
                params={}
            )

            assert result["success"] is False
            assert result["error_type"] == "execution_error"


class TestPing:
    """Test gateway ping."""

    @pytest.mark.asyncio
    async def test_ping_success(self):
        """Test successful gateway ping."""
        bridge = ASAGENTBridge()

        mock_response = MagicMock()
        mock_response.status_code = 200

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await bridge.ping()
            assert result is True

    @pytest.mark.asyncio
    async def test_ping_failure(self):
        """Test failed gateway ping."""
        bridge = ASAGENTBridge()

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await bridge.ping()
            assert result is False
