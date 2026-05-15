"""Tron deposit source: native TRX + TRC20 token transfers via TronGrid."""

from __future__ import annotations

from decimal import Decimal
from typing import Optional

import httpx

from . import DepositEvent, register

NETWORKS = [5000, 5010]

_BASE = {
    5000: "https://api.trongrid.io",
    5010: "https://nile.trongrid.io",
}

# Canonical symbols for known TRC20 contracts. Unknown contracts come
# through with asset=<contract addr>; merchant maps in their system.
TRC20_KNOWN: dict[int, dict[str, str]] = {
    5010: {
        "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf": "USDT",
        "TLBaRhANQoJFTqre9Nf1mjuwNWjCJeYqUL": "USDT",
        "TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj": "USDT",
    },
    5000: {
        "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t": "USDT",
        "TEkxiTehnzSmSe2XqrBj4w32RUN966rdz8": "USDC",
    },
}


async def scan_native(client: httpx.AsyncClient, wallet, since) -> list[DepositEvent]:
    base = _BASE[wallet["network"]]
    url = f"{base}/v1/accounts/{wallet['addr']}/transactions"
    params = {
        "only_to": "true",
        "only_confirmed": "true",
        "min_timestamp": str(int(since.timestamp() * 1000)),
        "limit": "50",
    }
    r = await client.get(url, params=params)
    r.raise_for_status()
    txs = (r.json() or {}).get("data") or []
    out: list[DepositEvent] = []
    for tx in txs:
        tx_id = tx.get("txID") or tx.get("transaction_id")
        if not tx_id:
            continue
        if (tx.get("ret") or [{}])[0].get("contractRet") != "SUCCESS":
            continue
        contracts = (tx.get("raw_data") or {}).get("contract") or []
        if not contracts or contracts[0].get("type") != "TransferContract":
            continue
        v = (contracts[0].get("parameter") or {}).get("value") or {}
        amount_sun = int(v.get("amount") or 0)
        if amount_sun <= 0:
            continue
        out.append(DepositEvent(
            tx_hash=tx_id,
            log_index=0,
            from_address=v.get("owner_address_base58") or v.get("owner_address") or "",
            asset="TRX",
            amount=Decimal(amount_sun) / Decimal(1_000_000),
            block_number=int(tx.get("blockNumber") or 0) or None,
            block_ts_ms=int(tx.get("block_timestamp") or 0),
        ))
    return out


async def scan_tokens(client: httpx.AsyncClient, wallet, since) -> list[DepositEvent]:
    base = _BASE[wallet["network"]]
    url = f"{base}/v1/accounts/{wallet['addr']}/transactions/trc20"
    params = {
        "only_to": "true",
        "only_confirmed": "true",
        "min_timestamp": str(int(since.timestamp() * 1000)),
        "limit": "50",
    }
    r = await client.get(url, params=params)
    r.raise_for_status()
    txs = (r.json() or {}).get("data") or []
    out: list[DepositEvent] = []
    known = TRC20_KNOWN.get(wallet["network"], {})
    for tx in txs:
        tx_id = tx.get("transaction_id")
        if not tx_id:
            continue
        ti = tx.get("token_info") or {}
        contract = ti.get("address") or ""
        decimals = int(ti.get("decimals") or 6)
        symbol = known.get(contract) or ti.get("symbol") or contract
        try:
            amount = Decimal(tx.get("value") or "0") / (Decimal(10) ** decimals)
        except Exception:
            continue
        if amount <= 0:
            continue
        out.append(DepositEvent(
            tx_hash=tx_id,
            log_index=int(tx.get("event_index") or 0),
            from_address=tx.get("from") or "",
            asset=symbol,
            amount=amount,
            block_number=None,
            block_ts_ms=int(tx.get("block_timestamp") or 0),
        ))
    return out


register(__import__(__name__, fromlist=["NETWORKS"]))
