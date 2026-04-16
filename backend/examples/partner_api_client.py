"""
ASYSTEM ORGON - Partner API Client Example
Python SDK for B2B Partner API integration
"""

import os

import requests
from typing import Optional, Dict, Any, List
from datetime import datetime


class ORGONPartnerClient:
    """
    Python SDK for ORGON Partner API.
    
    Usage:
        client = ORGONPartnerClient(
            api_key="your_api_key",
            api_secret="your_api_secret",
            base_url="https://orgon.asystem.ai"
        )
        
        # List wallets
        wallets = client.list_wallets(limit=50, offset=0)
        print(f"Found {len(wallets['wallets'])} wallets")
        
        # Get wallet details
        wallet = client.get_wallet("WALLET_NAME")
        print(f"Wallet address: {wallet['address']}")
        
        # Create wallet
        new_wallet = client.create_wallet(
            name="my-new-wallet",
            network_id=5010,  # Tron Nile testnet
            wallet_type=1,     # Multisig
            label="Production Wallet"
        )
        print(f"Created wallet: {new_wallet['name']}")
    """
    
    def __init__(
        self,
        api_key: str,
        api_secret: str,
        base_url: str = "http://localhost:8890",
        timeout: int = 30
    ):
        """
        Initialize Partner API client.
        
        Args:
            api_key: Partner API key (64 chars hex)
            api_secret: Partner API secret (64 chars hex)
            base_url: API base URL (default: http://localhost:8890)
            timeout: Request timeout in seconds (default: 30)
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            "X-API-Key": api_key,
            "X-API-Secret": api_secret,
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    def _request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make authenticated API request.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., "/api/v1/partner/wallets")
            params: Query parameters
            json: Request body (JSON)
            
        Returns:
            Response JSON
            
        Raises:
            requests.HTTPError: On HTTP error status
        """
        url = f"{self.base_url}{endpoint}"
        
        response = self.session.request(
            method=method,
            url=url,
            params=params,
            json=json,
            timeout=self.timeout
        )
        
        # Raise on HTTP error (4xx, 5xx)
        response.raise_for_status()
        
        return response.json()
    
    # ========================================================================
    # WALLET ENDPOINTS
    # ========================================================================
    
    def list_wallets(
        self,
        limit: int = 50,
        offset: int = 0,
        network_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        List all wallets for partner.
        
        Args:
            limit: Results per page (1-100, default 50)
            offset: Offset for pagination (default 0)
            network_id: Optional network filter
            
        Returns:
            {
                "wallets": [...],
                "pagination": {
                    "total": int,
                    "limit": int,
                    "offset": int,
                    "has_more": bool
                }
            }
        """
        params = {"limit": limit, "offset": offset}
        if network_id is not None:
            params["network_id"] = network_id
        
        return self._request("GET", "/api/v1/partner/wallets", params=params)
    
    def get_wallet(self, wallet_name: str) -> Dict[str, Any]:
        """
        Get wallet details by name.
        
        Args:
            wallet_name: Wallet name
            
        Returns:
            {
                "name": str,
                "network_id": int,
                "wallet_type": int,
                "address": str,
                "label": str | null,
                "is_favorite": bool,
                "tokens": [...],
                "created_at": str,
                "synced_at": str | null
            }
        """
        return self._request("GET", f"/api/v1/partner/wallets/{wallet_name}")
    
    def create_wallet(
        self,
        name: str,
        network_id: int,
        wallet_type: int = 1,
        label: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new wallet.
        
        Args:
            name: Unique wallet name (alphanumeric, hyphens, underscores)
            network_id: Network ID (5000=Tron mainnet, 5010=Tron Nile testnet)
            wallet_type: Wallet type (1=multisig, default: 1)
            label: Optional custom label
            
        Returns:
            Wallet details (same as get_wallet)
        """
        data = {
            "name": name,
            "network_id": network_id,
            "wallet_type": wallet_type
        }
        if label is not None:
            data["label"] = label
        
        return self._request("POST", "/api/v1/partner/wallets", json=data)
    
    # ========================================================================
    # TRANSACTION ENDPOINTS
    # ========================================================================
    
    def list_transactions(
        self,
        limit: int = 50,
        offset: int = 0,
        wallet_name: Optional[str] = None,
        status: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        List transactions for partner.
        
        Args:
            limit: Results per page (1-100, default 50)
            offset: Offset for pagination (default 0)
            wallet_name: Optional filter by wallet name
            status: Optional filter by status (pending|confirmed|failed)
            
        Returns:
            {
                "transactions": [...],
                "pagination": {...}
            }
        """
        params = {"limit": limit, "offset": offset}
        if wallet_name is not None:
            params["wallet_name"] = wallet_name
        if status is not None:
            params["status"] = status
        
        return self._request("GET", "/api/v1/partner/transactions", params=params)
    
    def get_transaction(self, unid: str) -> Dict[str, Any]:
        """
        Get transaction details by UNID.
        
        Args:
            unid: Transaction UNID
            
        Returns:
            Transaction details
        """
        return self._request("GET", f"/api/v1/partner/transactions/{unid}")
    
    def create_transaction(
        self,
        wallet_name: str,
        to_address: str,
        amount: str,
        token_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new transaction.
        
        Args:
            wallet_name: Source wallet name
            to_address: Destination address
            amount: Amount to send (string, e.g., "100.50")
            token_id: Optional token ID (null = native currency)
            notes: Optional transaction notes
            
        Returns:
            Transaction details
        """
        data = {
            "wallet_name": wallet_name,
            "to_address": to_address,
            "amount": amount
        }
        if token_id is not None:
            data["token_id"] = token_id
        if notes is not None:
            data["notes"] = notes
        
        return self._request("POST", "/api/v1/partner/transactions", json=data)
    
    # ========================================================================
    # SIGNATURE ENDPOINTS
    # ========================================================================
    
    def list_pending_signatures(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        Get pending signatures requiring approval.
        
        Args:
            limit: Results per page (1-100, default 50)
            offset: Offset for pagination (default 0)
            
        Returns:
            {
                "signatures": [...],
                "pagination": {...}
            }
        """
        params = {"limit": limit, "offset": offset}
        return self._request("GET", "/api/v1/partner/signatures/pending", params=params)
    
    def approve_signature(
        self,
        signature_id: str,
        approved_by: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Approve a pending signature.
        
        Args:
            signature_id: Signature ID
            approved_by: Optional approver identifier
            
        Returns:
            Updated signature details
        """
        data = {"signature_id": signature_id}
        if approved_by is not None:
            data["approved_by"] = approved_by
        
        return self._request("POST", "/api/v1/partner/signatures/approve", json=data)
    
    def reject_signature(
        self,
        signature_id: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Reject a pending signature.
        
        Args:
            signature_id: Signature ID
            reason: Optional rejection reason
            
        Returns:
            Updated signature details
        """
        data = {"signature_id": signature_id}
        if reason is not None:
            data["reason"] = reason
        
        return self._request("POST", "/api/v1/partner/signatures/reject", json=data)
    
    # ========================================================================
    # NETWORK & TOKEN INFO
    # ========================================================================
    
    def list_networks(self) -> Dict[str, Any]:
        """
        Get supported blockchain networks.
        
        Returns:
            {
                "networks": [
                    {
                        "id": int,
                        "name": str,
                        "chain_id": str,
                        "is_testnet": bool
                    },
                    ...
                ]
            }
        """
        return self._request("GET", "/api/v1/partner/networks")
    
    def list_tokens(self) -> Dict[str, Any]:
        """
        Get supported tokens across all networks.
        
        Returns:
            {
                "tokens": [
                    {
                        "id": int,
                        "symbol": str,
                        "name": str,
                        "network_id": int,
                        "decimals": int,
                        "contract_address": str | null
                    },
                    ...
                ]
            }
        """
        return self._request("GET", "/api/v1/partner/tokens-info")
    
    def close(self):
        """Close HTTP session."""
        self.session.close()


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Initialize client with test credentials
    client = ORGONPartnerClient(
        api_key=os.getenv("ORGON_PARTNER_API_KEY", "SET_YOUR_API_KEY"),
        api_secret=os.getenv("ORGON_PARTNER_API_SECRET", "SET_YOUR_API_SECRET"),
        base_url=os.getenv("ORGON_BASE_URL", "http://localhost:8890")
    )
    
    try:
        # List wallets
        print("=" * 80)
        print("LISTING WALLETS")
        print("=" * 80)
        wallets_response = client.list_wallets(limit=10)
        wallets = wallets_response["wallets"]
        print(f"Found {len(wallets)} wallets:")
        for wallet in wallets:
            print(f"  - {wallet['name']} (Network: {wallet['network_id']}, Address: {wallet['address']})")
        
        # Get wallet details (if any wallets exist)
        if wallets:
            print("\n" + "=" * 80)
            print(f"WALLET DETAILS: {wallets[0]['name']}")
            print("=" * 80)
            wallet = client.get_wallet(wallets[0]['name'])
            print(f"Name: {wallet['name']}")
            print(f"Network: {wallet['network_id']}")
            print(f"Address: {wallet['address']}")
            print(f"Label: {wallet.get('label', 'N/A')}")
            print(f"Created: {wallet['created_at']}")
        
        # List pending signatures
        print("\n" + "=" * 80)
        print("PENDING SIGNATURES")
        print("=" * 80)
        sigs_response = client.list_pending_signatures(limit=10)
        sigs = sigs_response["signatures"]
        print(f"Found {len(sigs)} pending signatures")
        
        print("\n✅ Client test complete!")
        
    except requests.HTTPError as e:
        print(f"❌ HTTP Error: {e}")
        print(f"Response: {e.response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        client.close()
