"""Ethereum deposit source: native ETH + ERC20 via Etherscan.

Etherscan offers a free tier without API key (1 req per 5s), and a
free-with-key tier (5 req/s). We read `ETHERSCAN_API_KEY` from env
and pass it when present.

Mainnet endpoint:        https://api.etherscan.io/api
Sepolia endpoint:        https://api-sepolia.etherscan.io/api
"""

from __future__ import annotations

import os
from decimal import Decimal

import httpx

from . import DepositEvent, register

NETWORKS = [3000, 3040]

_BASE = {
    3000: "https://api.etherscan.io/api",
    3040: "https://api-sepolia.etherscan.io/api",
}

# Canonical token symbol overrides. Anything outside this map keeps
# the symbol Etherscan reports.
ERC20_KNOWN: dict[int, dict[str, str]] = {
    3000: {
        "0xdac17f958d2ee523a2206206994597c13d831ec7": "USDT",
        "0xa0b86991c6218b36c1d19d4a2e9eb0ce3606eb48": "USDC",
    },
    3040: {  # Sepolia testnet — Safina supplies the canonical contract
        # left empty until Safina shares the exact deployments
    },
}


def _api_key() -> str:
    return os.environ.get("ETHERSCAN_API_KEY", "")


async def _etherscan(client: httpx.AsyncClient, network: int, action: str, params: dict):
    full = {
        "module": "account",
        "action": action,
        "sort": "desc",
        "page": "1",
        "offset": "50",
        **params,
    }
    key = _api_key()
    if key:
        full["apikey"] = key
    r = await client.get(_BASE[network], params=full)
    r.raise_for_status()
    data = r.json() or {}
    # Etherscan returns status "0" when "No transactions found" — not
    # actually an error. The `result` field then is a string message.
    if data.get("status") != "1":
        result = data.get("result")
        if isinstance(result, str):
            return []
        return []
    return data.get("result") or []


async def scan_native(client: httpx.AsyncClient, wallet, since) -> list[DepositEvent]:
    rows = await _etherscan(
        client,
        wallet["network"],
        "txlist",
        {"address": wallet["addr"], "startblock": "0", "endblock": "99999999"},
    )
    out: list[DepositEvent] = []
    since_s = int(since.timestamp())
    for tx in rows:
        # Outbound from this address — skip.
        if (tx.get("to") or "").lower() != wallet["addr"].lower():
            continue
        if tx.get("isError") == "1":
            continue
        block_ts = int(tx.get("timeStamp") or 0)
        if block_ts < since_s:
            continue
        value_wei = int(tx.get("value") or 0)
        if value_wei <= 0:
            continue
        out.append(DepositEvent(
            tx_hash=tx.get("hash") or "",
            log_index=0,
            from_address=tx.get("from") or "",
            asset="ETH",
            amount=Decimal(value_wei) / (Decimal(10) ** 18),
            block_number=int(tx.get("blockNumber") or 0) or None,
            block_ts_ms=block_ts * 1000,
        ))
    return out


async def scan_tokens(client: httpx.AsyncClient, wallet, since) -> list[DepositEvent]:
    rows = await _etherscan(
        client,
        wallet["network"],
        "tokentx",
        {"address": wallet["addr"], "startblock": "0", "endblock": "99999999"},
    )
    out: list[DepositEvent] = []
    since_s = int(since.timestamp())
    known = ERC20_KNOWN.get(wallet["network"], {})
    for ev in rows:
        if (ev.get("to") or "").lower() != wallet["addr"].lower():
            continue
        block_ts = int(ev.get("timeStamp") or 0)
        if block_ts < since_s:
            continue
        contract = (ev.get("contractAddress") or "").lower()
        symbol = known.get(contract) or ev.get("tokenSymbol") or contract
        try:
            decimals = int(ev.get("tokenDecimal") or 18)
            amount = Decimal(ev.get("value") or "0") / (Decimal(10) ** decimals)
        except Exception:
            continue
        if amount <= 0:
            continue
        out.append(DepositEvent(
            tx_hash=ev.get("hash") or "",
            # Etherscan doesn't surface logIndex on tokentx; use a
            # synthetic index from `transactionIndex` so two transfers
            # in one tx don't collide on UNIQUE(tx_hash, log_index).
            log_index=int(ev.get("transactionIndex") or 0),
            from_address=ev.get("from") or "",
            asset=symbol,
            amount=amount,
            block_number=int(ev.get("blockNumber") or 0) or None,
            block_ts_ms=block_ts * 1000,
        ))
    return out


register(__import__(__name__, fromlist=["NETWORKS"]))
