"""
ASAGENT Bridge Integration

Connects ORGON wallet dashboard to ASAGENT autonomous agent gateway.
Enables ASAGENT to execute ORGON skills via API.
"""

import logging
from typing import Optional, Any
import httpx
from datetime import datetime, timezone

logger = logging.getLogger("orgon.integrations.asagent")


class ASAGENTBridge:
    """
    Bridge between ORGON and ASAGENT Gateway.

    Features:
    - Register ORGON skills with ASAGENT
    - Handle skill execution requests
    - Provide wallet, transaction, and signature data to ASAGENT
    """

    def __init__(
        self,
        gateway_url: str = "http://localhost:8000",
        timeout: int = 30,
    ):
        """
        Initialize ASAGENT Bridge.

        Args:
            gateway_url: ASAGENT Gateway base URL
            timeout: Request timeout in seconds
        """
        self.gateway_url = gateway_url.rstrip("/")
        self.timeout = timeout
        self._skills_registered = False

    async def register_orgon_skills(self) -> dict:
        """
        Register ORGON skills with ASAGENT Gateway.

        Returns:
            Registration result
        """
        skills = [
            {
                "name": "orgon_wallet_balance",
                "description": "Get balance for a specific wallet from ORGON",
                "category": "finance",
                "parameters": {
                    "wallet_name": {
                        "type": "string",
                        "description": "Name of the wallet",
                        "required": True,
                    }
                },
                "returns": {
                    "type": "object",
                    "description": "Wallet balance with tokens",
                },
            },
            {
                "name": "orgon_list_wallets",
                "description": "List all wallets managed by ORGON",
                "category": "finance",
                "parameters": {},
                "returns": {
                    "type": "array",
                    "description": "List of wallets with basic info",
                },
            },
            {
                "name": "orgon_pending_signatures",
                "description": "Get pending multi-signature transactions from ORGON",
                "category": "finance",
                "parameters": {},
                "returns": {
                    "type": "array",
                    "description": "List of pending signature requests",
                },
            },
            {
                "name": "orgon_send_transaction",
                "description": "Create and send a transaction via ORGON",
                "category": "finance",
                "parameters": {
                    "token": {
                        "type": "string",
                        "description": "Token identifier (network:::TOKEN###wallet)",
                        "required": True,
                    },
                    "to_address": {
                        "type": "string",
                        "description": "Destination address",
                        "required": True,
                    },
                    "value": {
                        "type": "string",
                        "description": "Amount to send",
                        "required": True,
                    },
                    "info": {
                        "type": "string",
                        "description": "Transaction description (optional)",
                        "required": False,
                    },
                },
                "returns": {
                    "type": "object",
                    "description": "Transaction result with tx_unid",
                },
            },
            {
                "name": "orgon_recent_transactions",
                "description": "Get recent transactions from ORGON",
                "category": "finance",
                "parameters": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of transactions to return (default: 20)",
                        "required": False,
                    }
                },
                "returns": {
                    "type": "array",
                    "description": "List of recent transactions",
                },
            },
            {
                "name": "orgon_dashboard_stats",
                "description": "Get ORGON dashboard statistics",
                "category": "finance",
                "parameters": {},
                "returns": {
                    "type": "object",
                    "description": "Dashboard stats (wallets, transactions, signatures, etc.)",
                },
            },
        ]

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.gateway_url}/api/skills/register",
                    json={
                        "source": "orgon",
                        "skills": skills,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                response.raise_for_status()
                result = response.json()
                self._skills_registered = True
                logger.info(f"Registered {len(skills)} ORGON skills with ASAGENT")
                return result

        except httpx.HTTPError as e:
            logger.error(f"Failed to register ORGON skills: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error registering skills: {e}")
            raise

    async def handle_skill_call(
        self,
        skill_name: str,
        params: dict,
        context: Optional[dict] = None,
    ) -> dict:
        """
        Handle skill execution request from ASAGENT.

        This is called by ASAGENT when it wants to execute an ORGON skill.
        The actual implementation delegates to ORGON services.

        Args:
            skill_name: Name of the skill to execute
            params: Skill parameters
            context: Execution context (user, session, etc.)

        Returns:
            Skill execution result

        Raises:
            ValueError: If skill is not found
            RuntimeError: If skill execution fails
        """
        logger.info(f"ASAGENT requested skill: {skill_name} with params: {params}")

        # Import services here to avoid circular imports
        from backend.main import (
            get_wallet_service,
            get_transaction_service,
            get_signature_service,
            get_dashboard_service,
        )

        try:
            # Route to appropriate service method
            if skill_name == "orgon_wallet_balance":
                wallet_name = params.get("wallet_name")
                if not wallet_name:
                    raise ValueError("wallet_name parameter is required")

                service = get_wallet_service()
                balance = await service.get_wallet_balance(wallet_name)
                return {
                    "success": True,
                    "data": balance,
                    "skill": skill_name,
                }

            elif skill_name == "orgon_list_wallets":
                service = get_wallet_service()
                wallets = await service.list_wallets()
                return {
                    "success": True,
                    "data": wallets,
                    "skill": skill_name,
                }

            elif skill_name == "orgon_pending_signatures":
                service = get_signature_service()
                pending = await service.get_pending_signatures()
                # Convert to dict for JSON serialization
                pending_data = [
                    {
                        "tx_unid": p.unid,
                        "token": p.token,
                        "value": p.tx_value,
                        "to_addr": p.to_addr,
                        "timestamp": p.timestamp,
                    }
                    for p in pending
                ]
                return {
                    "success": True,
                    "data": pending_data,
                    "skill": skill_name,
                }

            elif skill_name == "orgon_send_transaction":
                token = params.get("token")
                to_address = params.get("to_address")
                value = params.get("value")
                info = params.get("info", "")

                if not all([token, to_address, value]):
                    raise ValueError("token, to_address, and value are required")

                service = get_transaction_service()
                result = await service.send_transaction(
                    token=token,
                    to_address=to_address,
                    value=value,
                    info=info,
                )
                return {
                    "success": True,
                    "data": result,
                    "skill": skill_name,
                }

            elif skill_name == "orgon_recent_transactions":
                limit = params.get("limit", 20)
                service = get_transaction_service()
                transactions = await service.list_transactions(limit=limit)
                return {
                    "success": True,
                    "data": transactions,
                    "skill": skill_name,
                }

            elif skill_name == "orgon_dashboard_stats":
                service = get_dashboard_service()
                stats = await service.get_stats()
                return {
                    "success": True,
                    "data": stats,
                    "skill": skill_name,
                }

            else:
                raise ValueError(f"Unknown skill: {skill_name}")

        except ValueError as e:
            logger.error(f"Invalid skill call: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": "validation_error",
                "skill": skill_name,
            }
        except Exception as e:
            logger.error(f"Skill execution failed: {e}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "error_type": "execution_error",
                "skill": skill_name,
            }

    async def ping(self) -> bool:
        """
        Check if ASAGENT Gateway is reachable.

        Returns:
            True if gateway is reachable, False otherwise
        """
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.gateway_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"ASAGENT Gateway ping failed: {e}")
            return False

    @property
    def is_ready(self) -> bool:
        """Check if bridge is ready (skills registered)."""
        return self._skills_registered
