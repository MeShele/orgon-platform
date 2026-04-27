# TODO: Add ON CONFLICT clauses to INSERT statements
"""Transaction business logic."""

import logging
import re
from decimal import Decimal
from typing import Optional
from datetime import datetime, timezone

from backend.safina.client import SafinaPayClient
from backend.safina.models import SendTransactionRequest
from backend.database.db_postgres import AsyncDatabase
from backend.events.manager import get_event_manager, EventType

logger = logging.getLogger("orgon.services.transaction")


class TransactionValidationError(Exception):
    """Transaction validation failed."""
    pass


class TransactionService:
    def __init__(self, client: SafinaPayClient, db: AsyncDatabase):
        self._client = client
        self._db = db

    async def list_transactions(
        self,
        limit: int = 50,
        offset: int = 0,
        wallet_name: Optional[str] = None,
        status: Optional[str] = None,
        network: Optional[int] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        filters: Optional[dict] = None,
        org_ids: list = None
    ) -> list[dict]:
        """
        Get transactions with optional filtering.

        Args:
            limit: Maximum number of transactions to return
            offset: Number of transactions to skip
            wallet_name: Optional filter by wallet name
            status: Optional filter by status (pending/signed/confirmed/rejected)
            network: Optional filter by network ID
            from_date: Optional filter by creation date (ISO timestamp, inclusive)
            to_date: Optional filter by creation date (ISO timestamp, inclusive)
            filters: Alternative: Optional filters dict (for backward compatibility)

        Returns:
            List of transaction dicts
        """
        # Merge kwargs into filters dict
        if filters is None:
            filters = {}
        if wallet_name:
            filters["wallet_name"] = wallet_name
        if status:
            filters["status"] = status
        if network:
            filters["network"] = network
        if from_date:
            filters["from_date"] = from_date
        if to_date:
            filters["to_date"] = to_date
        
        # Build query with filters
        query = "SELECT * FROM transactions WHERE 1=1"
        params = []
        param_idx = 1

        if "wallet_name" in filters and filters["wallet_name"]:
            query += f" AND wallet_name = ${param_idx}"
            params.append(filters["wallet_name"])
            param_idx += 1

        if "status" in filters and filters["status"]:
            query += f" AND status = ${param_idx}"
            params.append(filters["status"])
            param_idx += 1

        if "network" in filters and filters["network"]:
            query += f" AND network = ${param_idx}"
            params.append(filters["network"])
            param_idx += 1

        if "from_date" in filters and filters["from_date"]:
            query += f" AND created_at >= ${param_idx}"
            params.append(filters["from_date"])
            param_idx += 1

        if "to_date" in filters and filters["to_date"]:
            query += f" AND created_at <= ${param_idx}"
            params.append(filters["to_date"])
            param_idx += 1

        # Organization isolation filter
        if org_ids is not None:
            if not org_ids:
                return []  # User has no orgs
            placeholders = ", ".join(f"${param_idx + i}" for i in range(len(org_ids)))
            query += f" AND organization_id IN ({placeholders})"
            params.extend(org_ids)
            param_idx += len(org_ids)

        query += f" ORDER BY created_at DESC LIMIT ${param_idx} OFFSET ${param_idx + 1}"
        params.extend([limit, offset])

        txs = await self._db.fetch(query, tuple(params))

        # Auto-sync if empty and no filters applied (only if client available)
        if not txs and not filters and self._client is not None:
            await self.sync_transactions()
            txs = await self._db.fetch(query, tuple(params))

        return txs
    
    async def count_transactions(
        self,
        wallet_name: Optional[str] = None,
        status: Optional[str] = None,
        network: Optional[int] = None,
        org_ids: Optional[list] = None,
    ) -> int:
        """Count transactions, scoped to org_ids when provided.

        `org_ids=None` means "no scoping" (super_admin / internal). An empty
        list means the caller has no organizations and the count is 0.
        """
        if org_ids is not None and not org_ids:
            return 0

        query = "SELECT COUNT(*) FROM transactions WHERE 1=1"
        params: list = []
        param_idx = 1

        if wallet_name:
            query += f" AND wallet_name = ${param_idx}"
            params.append(wallet_name)
            param_idx += 1

        if status:
            query += f" AND status = ${param_idx}"
            params.append(status)
            param_idx += 1

        if network:
            query += f" AND network = ${param_idx}"
            params.append(network)
            param_idx += 1

        if org_ids is not None:
            placeholders = ", ".join(f"${param_idx + i}" for i in range(len(org_ids)))
            query += f" AND organization_id IN ({placeholders})"
            params.extend(org_ids)
            param_idx += len(org_ids)

        result = await self._db.fetchrow(query, tuple(params))
        return result["count"] if result else 0

    async def get_transaction(
        self,
        unid: str,
        org_ids: Optional[list] = None,
    ) -> dict | None:
        """Get transaction details with signatures, scoped to org_ids when provided.

        Returns None when the row exists but is outside the caller's tenancy —
        do not leak existence to wrong tenants.
        """
        tx = await self._db.fetchrow("SELECT * FROM transactions WHERE unid = $1", params=(unid,))
        if not tx:
            return None
        if org_ids is not None:
            if not org_ids or tx.get("organization_id") not in org_ids:
                return None
        sigs = await self._db.fetch("SELECT * FROM tx_signatures WHERE tx_unid = $1", params=(unid,))
        tx["signatures"] = sigs
        return tx

    # --- Validation and formatting helpers ---

    def format_token(
        self,
        network_id: str,
        token_symbol: str,
        wallet_name: str
    ) -> str:
        """
        Format token string for Safina API.

        Args:
            network_id: Network ID (e.g., "5010")
            token_symbol: Token symbol (e.g., "TRX")
            wallet_name: Wallet name/UNID

        Returns:
            Formatted token: "network:::TOKEN###wallet_name"

        Example:
            >>> format_token("5010", "TRX", "WALLET123")
            "5010:::TRX###WALLET123"
        """
        return f"{network_id}:::{token_symbol}###{wallet_name}"

    def convert_decimal_to_safina(self, value: str) -> str:
        """
        Convert decimal value to Safina format (comma separator).

        Args:
            value: Decimal value with period (e.g., "10.5")

        Returns:
            Value with comma separator (e.g., "10,5")

        Example:
            >>> convert_decimal_to_safina("10.5")
            "10,5"
        """
        return value.replace(".", ",")

    def convert_decimal_from_safina(self, value: str) -> str:
        """
        Convert Safina decimal format (comma) to standard (period).

        Args:
            value: Safina value with comma (e.g., "10,5")

        Returns:
            Value with period separator (e.g., "10.5")
        """
        return value.replace(",", ".")

    async def validate_transaction(
        self,
        token: str,
        to_address: str,
        value: str,
        check_balance: bool = True
    ) -> dict:
        """
        Validate transaction before sending.

        Args:
            token: Full token format "network:::TOKEN###wallet_name"
            to_address: Destination address
            value: Amount (with period decimal separator)
            check_balance: Whether to check balance sufficiency

        Returns:
            Dict with validation results:
                - valid: bool
                - errors: list[str]
                - warnings: list[str]
                - balance: Decimal (if check_balance=True)

        Raises:
            TransactionValidationError: If validation fails
        """
        errors = []
        warnings = []
        balance = None

        # Validate token format
        if ":::" not in token or "###" not in token:
            errors.append(
                "Invalid token format. Expected: 'network:::TOKEN###wallet_name'"
            )
        else:
            # Parse token
            try:
                network_token, wallet_name = token.split("###")
                network_id, token_symbol = network_token.split(":::")
            except ValueError:
                errors.append("Failed to parse token format")

        # Validate address format
        if not to_address:
            errors.append("Destination address is required")
        else:
            # Basic address validation (can be enhanced per network)
            if len(to_address) < 10:
                errors.append("Destination address too short")

        # Validate value
        try:
            value_decimal = Decimal(value.replace(",", "."))
            if value_decimal <= 0:
                errors.append("Amount must be greater than zero")
        except Exception as e:
            errors.append(f"Invalid amount format: {e}")

        # Check balance if requested (skip if no client)
        if check_balance and not errors and self._client is not None:
            try:
                # Extract wallet_name from token
                wallet_name = token.split("###")[1]

                # Get wallet tokens
                tokens = await self._client.get_wallet_tokens(wallet_name)

                # Find matching token
                token_symbol_only = token.split(":::")[1].split("###")[0]
                matching_token = next(
                    (t for t in tokens if t.token == token_symbol_only),
                    None
                )

                if matching_token:
                    balance = matching_token.value_decimal
                    value_decimal = Decimal(value.replace(",", "."))

                    if value_decimal > balance:
                        errors.append(
                            f"Insufficient balance. "
                            f"Required: {value_decimal}, Available: {balance}"
                        )
                else:
                    warnings.append("Could not verify balance - token not found")

            except Exception as e:
                warnings.append(f"Balance check failed: {e}")

        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "balance": balance,
        }

    async def send_transaction(
        self,
        request: SendTransactionRequest,
        validate: bool = True
    ) -> str:
        """
        Send a new transaction via Safina API.

        Args:
            request: Transaction request data
            validate: Whether to validate before sending (default True)

        Returns:
            Transaction UNID

        Raises:
            TransactionValidationError: If validation fails
        """
        # Validate if requested
        if validate:
            validation = await self.validate_transaction(
                token=request.token,
                to_address=request.to_address,
                value=request.value,
                check_balance=True
            )

            if not validation["valid"]:
                error_msg = "; ".join(validation["errors"])
                logger.error("Transaction validation failed: %s", error_msg)
                raise TransactionValidationError(error_msg)

            if validation["warnings"]:
                logger.warning(
                    "Transaction warnings: %s",
                    "; ".join(validation["warnings"])
                )

        if self._client is None:
            raise RuntimeError("Safina client is not configured")

        # Convert decimal separator for Safina
        safina_value = self.convert_decimal_to_safina(request.value)

        # Send to Safina API
        tx_unid = await self._client.send_transaction(
            token=request.token,
            to_address=request.to_address,
            value=safina_value,  # Use converted value
            info=request.info,
            json_info=request.json_info,
        )

        # Extract wallet_name and network from token string
        wallet_name = None
        network = None
        if "###" in request.token:
            parts = request.token.split("###")
            wallet_name = parts[1] if len(parts) > 1 else None
            network_token = parts[0]
            network = network_token.split(":::")[0] if ":::" in network_token else None

        # Cache locally
        now = datetime.now(timezone.utc)
        await self._db.execute(
            """INSERT OR IGNORE INTO transactions
               (token, to_addr, value, unid, status, info, wallet_name, network, created_at, updated_at)
               VALUES ($1, $2, $3, $4, 'pending', $5, $6, $7, $8, $9)""",
            (request.token, request.to_address, safina_value, tx_unid,
             request.info, wallet_name, network, now, now),
        )

        logger.info(
            "Transaction sent: unid=%s, to=%s, value=%s (validated=%s)",
            tx_unid, request.to_address, safina_value, validate
        )
        
        # Emit real-time event
        event_manager = get_event_manager()
        await event_manager.emit(EventType.TRANSACTION_CREATED, {
            "unid": tx_unid,
            "token": request.token,
            "to_address": request.to_address,
            "value": safina_value,
            "wallet_name": wallet_name,
            "network": network,
            "status": "pending"
        })
        
        return tx_unid

    async def sign_transaction(self, tx_unid: str) -> dict:
        """Sign (approve) a transaction."""
        if self._client is None:
            raise RuntimeError("Safina client is not configured")
        result = await self._client.sign_transaction(tx_unid)

        await self._db.execute(
            "UPDATE transactions SET status = 'signed', updated_at = $1 WHERE unid = $2",
            (datetime.now(timezone.utc), tx_unid),
        )

        logger.info("Transaction signed: %s", tx_unid)
        
        # Emit signature approved event
        event_manager = get_event_manager()
        await event_manager.emit(EventType.SIGNATURE_APPROVED, {
            "tx_unid": tx_unid,
            "status": "signed"
        })
        
        return result

    async def reject_transaction(self, tx_unid: str, reason: str = "") -> dict:
        """Reject a transaction."""
        if self._client is None:
            raise RuntimeError("Safina client is not configured")
        result = await self._client.reject_transaction(tx_unid, reason)

        await self._db.execute(
            "UPDATE transactions SET status = 'rejected', updated_at = $1 WHERE unid = $2",
            (datetime.now(timezone.utc), tx_unid),
        )

        logger.info("Transaction rejected: %s, reason: %s", tx_unid, reason)
        
        # Emit signature rejected event
        event_manager = get_event_manager()
        await event_manager.emit(EventType.SIGNATURE_REJECTED, {
            "tx_unid": tx_unid,
            "reason": reason,
            "status": "rejected"
        })
        
        return result

    async def get_pending_signatures(self) -> list[dict]:
        """Get transactions awaiting user's signature."""
        pending = await self._client.get_pending_signatures()
        return [p.model_dump() for p in pending]

    async def get_tx_signatures(self, tx_unid: str) -> list[dict]:
        """Get all signatures (signed + waiting) for a transaction."""
        return await self._client.get_tx_signatures_all(tx_unid)

    async def sync_transactions(self):
        """Sync transactions from Safina API to local DB."""
        txs = await self._client.get_transactions()
        now = datetime.now(timezone.utc)

        for tx in txs:
            # Determine status
            status = "pending"
            if tx.tx:
                status = "confirmed"
            elif tx.signed:
                status = "signed"

            # Extract wallet name from token
            wallet_name = None
            if tx.token and "###" in tx.token:
                wallet_name = tx.token.split("###")[1]

            await self._db.execute(
                """INSERT INTO transactions
                   (safina_id, tx_hash, token, token_name, to_addr, value, value_hex,
                    unid, init_ts, min_sign, status, wallet_name, synced_at, updated_at)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14)
               ON CONFLICT (unid) DO UPDATE SET
                   safina_id = EXCLUDED.safina_id, tx_hash = EXCLUDED.tx_hash, token = EXCLUDED.token, token_name = EXCLUDED.token_name, to_addr = EXCLUDED.to_addr, value = EXCLUDED.value, value_hex = EXCLUDED.value_hex, init_ts = EXCLUDED.init_ts, min_sign = EXCLUDED.min_sign, status = EXCLUDED.status, info = EXCLUDED.info, wallet_name = EXCLUDED.wallet_name, network = EXCLUDED.network, synced_at = EXCLUDED.synced_at, updated_at = EXCLUDED.updated_at""",
                (tx.id, tx.tx, tx.token, tx.token_name, tx.to_addr,
                 str(tx.value), tx.value_hex, tx.unid, 
                 int(tx.init_ts) if tx.init_ts else None,  # init_ts это integer (Unix timestamp)
                 int(tx.min_sign) if tx.min_sign else 0,
                 status, wallet_name, now, now),
            )

            # Sync signatures
            if tx.wait:
                for sig in tx.wait:
                    if sig.get("ecaddress"):
                        await self._db.execute(
                            """INSERT INTO tx_signatures (tx_unid, ec_address, sig_type)
                               VALUES ($1, $2, 'wait')
                               ON CONFLICT (tx_unid, ec_address) DO NOTHING""",
                            (tx.unid, sig["ecaddress"]),
                        )
            if tx.signed:
                for sig in tx.signed:
                    if sig.get("ecaddress"):
                        await self._db.execute(
                            """INSERT INTO tx_signatures (tx_unid, ec_address, sig_type, ec_sign)
                               VALUES ($1, $2, 'signed', $3)
                               ON CONFLICT (tx_unid, ec_address) DO UPDATE SET
                               sig_type = EXCLUDED.sig_type, ec_sign = EXCLUDED.ec_sign""",
                            (tx.unid, sig["ecaddress"], sig.get("ecsign")),
                        )

        await self._db.execute(
            """INSERT INTO sync_state (key, value, updated_at) VALUES ($1, $2, $3)
               ON CONFLICT (key) DO UPDATE SET
               value = EXCLUDED.value, updated_at = EXCLUDED.updated_at""",
            ("transactions_synced", now.isoformat(), now),
        )
        logger.info("Synced %d transactions from Safina", len(txs))
