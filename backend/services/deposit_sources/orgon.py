"""ORGON deposit source: native ORGON transfers via the ORGON-chain node.

ORGON is a Tron fork — its node speaks the same HTTP API and even exposes
the TronGrid-style `/v1/accounts/{addr}/transactions` history endpoint
(verified on the Quasar testnet gate). So native-coin detection is the
same shape as Tron's, just a different base URL and asset symbol.

Native-only: ORGON has no token standard live yet (oRC-20 is on their
roadmap), and the node returns 404 for the `/trc20` history endpoint.
`scan_tokens` therefore returns nothing — when ORGON ships tokens, add the
contract map here, mirroring tron.py.

Mainnet (5800) is intentionally NOT registered: the mainnet full node
(tr80) does not expose the account-history index (404), so detection there
needs a different endpoint/keys. Add 5800 once that's available.
"""

from __future__ import annotations

from decimal import Decimal

import httpx

from . import DepositEvent, register

NETWORKS = [5810]

_BASE = {
    5810: "https://quasargate.orgon.space",  # Quasar testnet gate (TronGrid-style)
}

# ORGON inherits Tron's 6-decimal "sun" base unit.
_DECIMALS = Decimal(1_000_000)


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
            asset="ORGON",
            amount=Decimal(amount_sun) / _DECIMALS,
            block_number=int(tx.get("blockNumber") or 0) or None,
            block_ts_ms=int(tx.get("block_timestamp") or 0),
        ))
    return out


async def scan_tokens(client: httpx.AsyncClient, wallet, since) -> list[DepositEvent]:
    # ORGON has no live token standard yet — native-only. Mirror tron.py
    # here (a TRC20_KNOWN-style map + /trc20 history call) once oRC-20 ships.
    return []


register(__import__(__name__, fromlist=["NETWORKS"]))
