"""Bitcoin deposit source via Blockstream Esplora (public, no API key)."""

from __future__ import annotations

from decimal import Decimal

import httpx

from . import DepositEvent, register

NETWORKS = [1000]   # mainnet; Safina doesn't expose BTC testnet right now

_BASE = {1000: "https://blockstream.info/api"}


async def scan_native(client: httpx.AsyncClient, wallet, since) -> list[DepositEvent]:
    base = _BASE[wallet["network"]]
    url = f"{base}/address/{wallet['addr']}/txs"
    r = await client.get(url)
    r.raise_for_status()
    txs = r.json() or []

    out: list[DepositEvent] = []
    since_s = int(since.timestamp())
    for tx in txs:
        status = tx.get("status") or {}
        if not status.get("confirmed"):
            continue
        block_ts = int(status.get("block_time") or 0)
        if block_ts < since_s:
            continue
        block_n = status.get("block_height")
        tx_hash = tx.get("txid") or ""

        # Bitcoin doesn't have an explicit "to" — sum every vout
        # targeting our addr. Multiple matching vouts in one tx are
        # rare but we still aggregate.
        total_sats = 0
        from_addr = ""
        # Best-effort source address: first input's prevout scriptpubkey.
        vin = tx.get("vin") or []
        if vin:
            prev = (vin[0].get("prevout") or {}).get("scriptpubkey_address")
            if prev:
                from_addr = prev
        for vout in tx.get("vout") or []:
            if vout.get("scriptpubkey_address") == wallet["addr"]:
                total_sats += int(vout.get("value") or 0)
        if total_sats <= 0:
            continue
        out.append(DepositEvent(
            tx_hash=tx_hash,
            log_index=0,
            from_address=from_addr,
            asset="BTC",
            amount=Decimal(total_sats) / Decimal(100_000_000),
            block_number=block_n,
            block_ts_ms=block_ts * 1000,
        ))
    return out


async def scan_tokens(client: httpx.AsyncClient, wallet, since) -> list[DepositEvent]:
    # Bitcoin has no fungible-token layer Safina supports natively
    # (BRC-20 lives off the side; no Esplora endpoint for it).
    # Return empty so the dispatcher still advances the cursor.
    return []


register(__import__(__name__, fromlist=["NETWORKS"]))
