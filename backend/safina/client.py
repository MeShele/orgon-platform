"""
Async Safina Pay API Client.

Handles all communication with https://my.safina.pro/ece/ API
with EC signature authentication, retry logic, and type-safe responses.
"""

import asyncio
import json
import logging
from typing import Optional

import httpx

from .signer import SafinaSigner
from .models import (
    Network, Wallet, WalletDetail, Token, TokenInfo,
    UserToken, Transaction, SignedTransaction, PendingSignature,
)
from .errors import SafinaError, SafinaAuthError, SafinaNetworkError

logger = logging.getLogger("orgon.safina.client")


class SafinaPayClient:
    """Async client for Safina Pay ECE API."""

    def __init__(
        self,
        signer: SafinaSigner,
        base_url: str = "https://my.safina.pro/ece",
        timeout: int = 30,
        max_retries: int = 3,
        retry_backoff: float = 1.5,
    ):
        self._signer = signer
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._retry_backoff = retry_backoff
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self._timeout,
                headers={
                    "accept": "application/json",
                    "content-type": "application/json",
                },
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(
        self,
        method: str,
        path: str,
        data: Optional[dict] = None,
    ) -> any:
        """Make a signed request with retry logic."""
        url = f"{self._base_url}/{path.lstrip('/')}"
        last_error = None

        for attempt in range(self._max_retries):
            try:
                if method.upper() == "GET":
                    headers = self._signer.sign_get()
                else:
                    headers = self._signer.sign_post(data)

                client = await self._get_client()

                if method.upper() == "GET":
                    response = await client.get(url, headers=headers)
                else:
                    body = json.dumps(data, separators=(",", ":"), ensure_ascii=False) if data else "{}"
                    response = await client.post(url, headers=headers, content=body)

                response.raise_for_status()
                result = response.json()

                # Check for Safina error response
                if isinstance(result, dict) and "ERROR" in result:
                    error_msg = result["ERROR"]
                    error_line = result.get("LINE")
                    if "подпис" in error_msg.lower() or "sign" in error_msg.lower():
                        raise SafinaAuthError(error_msg, error_line)
                    raise SafinaError(error_msg, error_line)

                return result

            except (httpx.ConnectError, httpx.TimeoutException) as e:
                last_error = SafinaNetworkError(str(e))
                if attempt < self._max_retries - 1:
                    wait = self._retry_backoff ** attempt
                    logger.warning(
                        "Safina request failed (attempt %d/%d), retrying in %.1fs: %s",
                        attempt + 1, self._max_retries, wait, e,
                    )
                    await asyncio.sleep(wait)
            except (SafinaAuthError, SafinaError):
                raise
            except httpx.HTTPStatusError as e:
                raise SafinaError(f"HTTP {e.response.status_code}: {e.response.text}")
            except Exception as e:
                raise SafinaError(f"Unexpected error: {e}")

        raise last_error or SafinaNetworkError("Max retries exceeded")

    # --- Network methods ---

    async def get_networks(self, status: int = 1) -> list[Network]:
        """Get network directory. status=1 for active, 0 for disabled."""
        data = await self._request("GET", f"netlist/{status}")
        return [Network(**n) for n in data]

    # --- Wallet methods ---

    async def get_wallets(self) -> list[Wallet]:
        """Get all user wallets."""
        data = await self._request("GET", "wallets")
        return [Wallet(**w) for w in data]

    async def get_wallet(self, name: str) -> Optional[WalletDetail]:
        """Get wallet details by name. Returns None if wallet not found."""
        data = await self._request("GET", f"wallet/{name}")
        if not data or not isinstance(data, dict) or "wallet_name" not in data:
            return None
        return WalletDetail(**data)

    async def get_wallet_by_unid(self, unid: str) -> WalletDetail:
        """Get wallet details by creation UNID."""
        data = await self._request("GET", f"walletbyunid/{unid}")
        return WalletDetail(**data)

    async def create_wallet(
        self,
        network: str,
        info: str = "",
        slist: Optional[dict] = None,
    ) -> str:
        """
        Create a new wallet. Returns myUNID.

        Without slist: creates standard single-sig wallet.
        With slist: creates multi-sig wallet.
        """
        body = {"network": network, "info": info}
        if slist:
            body["slist"] = slist
        data = await self._request("POST", "newWallet", body)
        return data["myUNID"]

    # --- Token methods ---

    async def get_tokens(self) -> list[Token]:
        """Get all user tokens across all wallets."""
        data = await self._request("GET", "tokens")
        return [Token(**t) for t in data]

    async def get_wallet_tokens(self, wallet_name: str) -> list[Token]:
        """Get tokens for a specific wallet."""
        data = await self._request("GET", f"wallet_tokens/{wallet_name}")
        return [Token(**t) for t in data]

    async def get_tokens_info(self) -> list[TokenInfo]:
        """Get token directory with commission info."""
        data = await self._request("GET", "tokensinfo")
        return [TokenInfo(**t) for t in data]

    async def get_user_tokens(self) -> list[UserToken]:
        """Get user tokens with aggregated balances."""
        data = await self._request("GET", "user_tokens/")
        return [UserToken(**t) for t in data]

    # --- Transaction methods ---

    async def get_transactions(self) -> list[Transaction]:
        """Get all user transactions."""
        data = await self._request("GET", "tx")
        return [Transaction(**t) for t in data]

    async def get_token_transactions(self, token: str) -> list[Transaction]:
        """Get transactions for a specific token."""
        data = await self._request("GET", f"tx/{token}")
        return [Transaction(**t) for t in data]

    async def send_transaction(
        self,
        token: str,
        to_address: str,
        value: str,
        info: str = "",
        json_info: Optional[dict] = None,
    ) -> str:
        """
        Send a transaction. Returns tx_unid.

        Args:
            token: "network:::TOKEN###wallet_name" format
            to_address: Destination address
            value: Amount (use comma as decimal separator for Safina)
            info: Description
            json_info: Additional JSON metadata
        """
        # Convert decimal point to comma for Safina
        safina_value = value.replace(".", ",")

        body = {
            "token": token,
            "info": info,
            "value": safina_value,
            "toAddress": to_address,
        }
        if json_info:
            body["json_info"] = json_info
        data = await self._request("POST", "tx", body)
        return data["tx_unid"]

    async def sign_transaction(self, tx_unid: str) -> dict:
        """Sign (approve) a transaction."""
        return await self._request("POST", f"tx_sign/{tx_unid}")

    async def reject_transaction(self, tx_unid: str, reason: str = "") -> dict:
        """Reject a transaction."""
        body = {}
        if reason:
            body["ec_reject"] = reason
        return await self._request("POST", f"tx_reject/{tx_unid}", body)

    # --- Signature status methods ---

    async def get_tx_signatures_waiting(self, tx_unid: str) -> list[dict]:
        """Get expected signatures for a transaction."""
        return await self._request("GET", f"tx_sign_wait/{tx_unid}")

    async def get_tx_signatures_signed(self, tx_unid: str) -> list[dict]:
        """Get received signatures for a transaction."""
        return await self._request("GET", f"tx_sign_signed/{tx_unid}")

    async def get_tx_signatures_all(self, tx_unid: str) -> list[dict]:
        """Get both signed and waiting signatures."""
        return await self._request("GET", f"tx_sign/{tx_unid}")

    async def get_pending_signatures(self) -> list[PendingSignature]:
        """Get transactions awaiting user signature."""
        data = await self._request("GET", "tx_by_ec")
        return [PendingSignature(**t) for t in data]

    async def get_signed_transactions(self) -> list[SignedTransaction]:
        """Get last 50 transactions signed by user."""
        data = await self._request("GET", "tx_sign_signed/")
        return [SignedTransaction(**t) for t in data]

    # --- Health check ---

    async def check_health(self) -> bool:
        """Check if Safina API is reachable."""
        try:
            await self.get_networks(1)
            return True
        except Exception:
            return False
