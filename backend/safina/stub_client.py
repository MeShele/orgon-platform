"""SafinaPayClient stub — used in environments without a real Safina endpoint.

Wired in when `SAFINA_EC_PRIVATE_KEY` is unset or `SAFINA_STUB=1`. The stub
implements the same async interface as `SafinaPayClient` and returns
deterministic, demo-friendly data so the dashboard renders cleanly and
multi-sig flows can be walked through end-to-end without a live integration.

The stub is **state-aware** for the multi-sig flow: when a stubbed transaction
is `sign_transaction`'d, the in-memory ledger advances toward the configured
`min_sign` threshold. This is enough for a sales demo. It is **not** a
substitute for a real Safina integration in production — never enable it
behind the `prod` Coolify app.
"""

from __future__ import annotations

import logging
import time
import uuid
from typing import Optional

from .models import (
    Network,
    Wallet,
    WalletDetail,
    Token,
    TokenInfo,
    UserToken,
    Transaction,
    SignedTransaction,
    PendingSignature,
)

logger = logging.getLogger("orgon.safina.stub")


class _Signer:
    """Mimics SafinaPayClient._signer for code that reads `client._signer.address`."""

    def __init__(self, address: str):
        self.address = address


class SafinaStubClient:
    """Drop-in replacement for SafinaPayClient with canned responses."""

    # Canned demo data — mirrors a small Tron-mainnet treasury setup.
    _NETWORKS = [
        {"network_id": 5000, "network_name": "Tron",          "status": 1, "info": "Tron mainnet"},
        {"network_id": 5010, "network_name": "Tron Nile",     "status": 1, "info": "Tron testnet"},
        {"network_id": 6000, "network_name": "BNB Chain",     "status": 1, "info": "BNB Smart Chain mainnet"},
        {"network_id": 7000, "network_name": "Ethereum",      "status": 0, "info": "Coming soon"},
    ]

    _WALLETS = [
        {
            "wallet_id": "WALLET-TREASURY-COLD",
            "network": 5000,
            "wallet_type": 1,
            "name": "Treasury · Cold",
            "info": "Cold storage, 5-of-7 multisig",
            "addr": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
            "addr_info": "5-of-7",
            "myUNID": "WALLET-TREASURY-COLD",
            "tokenShortNames": "TRX,USDT",
        },
        {
            "wallet_id": "WALLET-OPERATING",
            "network": 5000,
            "wallet_type": 1,
            "name": "Operating · Pool",
            "info": "Operating pool, 3-of-5",
            "addr": "TXYZab12cdEFGh34iJKLmn56oPQR78stUV",
            "addr_info": "3-of-5",
            "myUNID": "WALLET-OPERATING",
            "tokenShortNames": "TRX,USDT,USDC",
        },
    ]

    def __init__(self, ec_address: str = "0xDEMO0000000000000000000000000000DEADBEEF") -> None:
        self._signer = _Signer(ec_address)
        # In-memory tx ledger so sign/reject calls have somewhere to advance.
        self._txs: dict[str, dict] = {}
        logger.warning(
            "SafinaStubClient active — endpoints will return canned demo data, "
            "no real blockchain interaction.",
        )

    # --- Networks ---

    async def get_networks(self, status: int = 1) -> list[Network]:
        return [Network(**n) for n in self._NETWORKS if status == 0 or n["status"] == status]

    # --- Wallets ---

    async def get_wallets(self) -> list[Wallet]:
        return [Wallet(**w) for w in self._WALLETS]

    async def get_wallet(self, name: str) -> Optional[WalletDetail]:
        match = next((w for w in self._WALLETS if w["name"] == name or w["myUNID"] == name), None)
        if not match:
            return None
        return WalletDetail(
            wallet_name=match["name"],
            info=match.get("info"),
            network=match["network"],
            wallet_type=match.get("wallet_type"),
            unid=match.get("myUNID"),
            slist={"min_sign": 3, "signers": []},
            addrs=match.get("addr"),
        )

    async def get_wallet_by_unid(self, unid: str) -> WalletDetail:
        wd = await self.get_wallet(unid)
        if wd is None:
            raise ValueError(f"stub: wallet {unid} not found")
        return wd

    async def create_wallet(
        self,
        network: str,
        info: str = "",
        slist: Optional[dict] = None,
    ) -> str:
        unid = f"WALLET-DEMO-{uuid.uuid4().hex[:8].upper()}"
        self._WALLETS.append({
            "wallet_id": unid,
            "network": int(network) if str(network).isdigit() else network,
            "wallet_type": 1,
            "name": unid,
            "info": info or "Demo wallet (stub)",
            "addr": "TDEMOaddr" + uuid.uuid4().hex[:24].upper(),
            "addr_info": "demo",
            "myUNID": unid,
            "tokenShortNames": "TRX,USDT",
        })
        logger.info("stub: created wallet %s on network %s", unid, network)
        return unid

    # --- Tokens ---

    async def get_tokens(self) -> list[Token]:
        return [
            Token(id=1, wallet_id="WALLET-TREASURY-COLD", network=5000, token="TRX", value="42500.00", decimals=6),
            Token(id=2, wallet_id="WALLET-TREASURY-COLD", network=5000, token="USDT", value="128540.00", decimals=6),
            Token(id=3, wallet_id="WALLET-OPERATING",     network=5000, token="TRX", value="3200.00",  decimals=6),
            Token(id=4, wallet_id="WALLET-OPERATING",     network=5000, token="USDT", value="9800.00",  decimals=6),
        ]

    async def get_wallet_tokens(self, wallet_name: str) -> list[Token]:
        all_tokens = await self.get_tokens()
        return [t for t in all_tokens if t.wallet_id == wallet_name]

    async def get_tokens_info(self) -> list[TokenInfo]:
        return [
            TokenInfo(token="5000:::TRX",  c="0.001",  cMin="1",  cMax="100"),
            TokenInfo(token="5000:::USDT", c="0.0008", cMin="1",  cMax="200"),
            TokenInfo(token="6000:::USDT", c="0.0008", cMin="1",  cMax="200"),
        ]

    async def get_user_tokens(self) -> list[UserToken]:
        return [
            UserToken(network_name="Tron", token="TRX",  value=45700.0),
            UserToken(network_name="Tron", token="USDT", value=138340.0),
        ]

    # --- Transactions ---

    async def get_transactions(self) -> list[Transaction]:
        return [Transaction(**t) for t in self._txs.values()] if self._txs else []

    async def get_token_transactions(self, token: str) -> list[Transaction]:
        return [Transaction(**t) for t in self._txs.values() if t.get("token") == token]

    async def send_transaction(
        self,
        token: str,
        to_address: str,
        value: str,
        info: str = "",
        json_info: Optional[dict] = None,
    ) -> str:
        unid = f"TX-DEMO-{uuid.uuid4().hex[:10].upper()}"
        self._txs[unid] = {
            "id": unid,
            "unid": unid,
            "tx": None,  # not yet broadcast
            "token": token,
            "token_name": token.split(":::")[-1].split("###")[0] if ":::" in token else token,
            "to_addr": to_address,
            "value": value.replace(".", ","),
            "info": info,
            "init_ts": int(time.time()),
            "min_sign": 3,
            "wait": ["0xSIG1", "0xSIG2", "0xSIG3"],
            "signed": [],
        }
        logger.info("stub: created tx %s → %s value=%s", unid, to_address, value)
        return unid

    async def sign_transaction(self, tx_unid: str) -> dict:
        tx = self._txs.get(tx_unid)
        if not tx:
            return {"ok": True, "stub": True, "message": "tx not in stub ledger — accepted as no-op"}
        if tx["wait"]:
            tx["signed"].append(tx["wait"].pop(0))
        if not tx["wait"]:
            tx["tx"] = "0xDEMO" + uuid.uuid4().hex[:60]  # canned hash
        return {"ok": True, "progress": f"{len(tx['signed'])}/{len(tx['signed']) + len(tx['wait'])}"}

    async def reject_transaction(self, tx_unid: str, reason: str = "") -> dict:
        tx = self._txs.get(tx_unid)
        if tx:
            tx["wait"] = []
            tx["signed"] = []
            tx["info"] = (tx.get("info") or "") + f" [rejected: {reason}]"
        return {"ok": True, "rejected": True}

    # --- Signature status ---

    async def get_tx_signatures_waiting(self, tx_unid: str) -> list[dict]:
        tx = self._txs.get(tx_unid, {"wait": []})
        return [{"wait": {"ecaddress": addr}} for addr in tx.get("wait", [])]

    async def get_tx_signatures_signed(self, tx_unid: str) -> list[dict]:
        tx = self._txs.get(tx_unid, {"signed": []})
        return [{"signed": {"ecaddress": addr}} for addr in tx.get("signed", [])]

    async def get_tx_signatures_all(self, tx_unid: str) -> list[dict]:
        signed = await self.get_tx_signatures_signed(tx_unid)
        wait = await self.get_tx_signatures_waiting(tx_unid)
        return signed + wait

    async def get_pending_signatures(self) -> list[PendingSignature]:
        out = []
        for tx in self._txs.values():
            if tx["wait"]:
                out.append(PendingSignature(
                    token=tx.get("token") or "",
                    to_addr=tx.get("to_addr") or "",
                    tx_value=str(tx.get("value", "0")),
                    init_ts=tx["init_ts"],
                    unid=tx["unid"],
                ))
        return out

    async def get_signed_transactions(self) -> list[SignedTransaction]:
        out = []
        for tx in self._txs.values():
            if tx["signed"] and not tx["wait"]:
                out.append(SignedTransaction(
                    to_addr=tx.get("to_addr") or "",
                    tx_value=str(tx.get("value", "0")),
                    tx=tx.get("tx"),
                    init_ts=tx["init_ts"],
                    info=tx.get("info"),
                    token=tx.get("token"),
                ))
        return out

    # --- Health ---

    async def check_health(self) -> bool:
        return True

    async def close(self) -> None:
        return None
