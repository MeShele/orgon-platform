"""On-chain confirmation lookup for OUTBOUND transactions, by tx_hash.

`transaction.broadcasted` fires when Safina returns a tx_hash (money left
toward the chain). `transaction.confirmed` must mean the tx is actually
included in a block — that's the DFNS-parity signal asystem-core uses to
mark an order completed. Safina doesn't give us that, so we poll the same
public explorers the deposit watcher already uses.

Pure lookup. Never raises — a network blip returns `found=False` and the
confirmation sweep simply retries next tick. ORGON-chain (5800/5810) has
no public explorer yet, so it's treated as confirmed immediately (the
broadcast is the best signal we have); documented in WEBHOOKS.md.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional

import httpx

# Reuse the deposit watcher's explorer endpoints / chain ids.
_ETH_CHAINID = {3000: "1", 3040: "11155111"}
_TRON_BASE = {5000: "https://api.trongrid.io", 5010: "https://nile.trongrid.io"}
_BTC_BASE = {1000: "https://blockstream.info/api"}
_ORGON_CHAINS = {5800, 5810}
# ORGON is a Tron fork; its testnet gate exposes the same node API and a
# real gettransactioninfobyid (verified: returns blockNumber + receipt for
# mined txs). So testnet (5810) gets REAL on-chain confirmation. Mainnet
# (5800) has no verified history endpoint yet, so it keeps the
# broadcast-is-terminal fallback below until one is wired.
_ORGON_RPC = {5810: "https://quasargate.orgon.space"}
_ETHERSCAN_V2 = "https://api.etherscan.io/v2/api"


@dataclass
class ConfirmResult:
    found: bool  # did we get a definitive answer this tick?
    confirmed: bool  # included in a block (and successful)?
    block_number: Optional[int]


_UNKNOWN = ConfirmResult(found=False, confirmed=False, block_number=None)


def supports_confirmation(network: Optional[int]) -> bool:
    """True if we have any way to confirm this network's txs (incl. the
    ORGON-chain immediate-confirm fallback)."""
    if network is None:
        return False
    return (
        network in _ORGON_CHAINS
        or network in _ETH_CHAINID
        or network in _TRON_BASE
        or network in _BTC_BASE
    )


async def get_onchain_confirmation(
    client: httpx.AsyncClient, network: int, tx_hash: str
) -> ConfirmResult:
    """Resolve whether `tx_hash` is confirmed on `network`. Best-effort."""
    try:
        if network in _ORGON_RPC:
            # Real on-chain lookup via the ORGON node (Tron-fork API).
            return await _orgon(client, network, tx_hash)
        if network in _ORGON_CHAINS:
            # Mainnet (5800): no verified history endpoint yet — broadcast
            # is our terminal signal (unchanged behavior).
            return ConfirmResult(found=True, confirmed=True, block_number=None)
        if network in _ETH_CHAINID:
            return await _eth(client, network, tx_hash)
        if network in _TRON_BASE:
            return await _tron(client, network, tx_hash)
        if network in _BTC_BASE:
            return await _btc(client, tx_hash)
    except Exception:
        return _UNKNOWN
    return _UNKNOWN


async def _eth(client, network, tx_hash) -> ConfirmResult:
    params = {
        "chainid": _ETH_CHAINID[network],
        "module": "proxy",
        "action": "eth_getTransactionReceipt",
        "txhash": tx_hash,
    }
    key = os.environ.get("ETHERSCAN_API_KEY", "")
    if key:
        params["apikey"] = key
    r = await client.get(_ETHERSCAN_V2, params=params)
    r.raise_for_status()
    res = (r.json() or {}).get("result")
    # `result` is the receipt dict when mined, `null` when not yet mined,
    # or a string/absent on an API error ("Missing/Invalid API Key",
    # rate-limit, etc.). Anything that isn't a dict → no definitive
    # answer; retry next tick (don't crash on `.get`).
    if not isinstance(res, dict):
        return _UNKNOWN
    bn = res.get("blockNumber")
    if bn is None:
        return _UNKNOWN
    block_number = int(bn, 16) if isinstance(bn, str) else int(bn)
    status = res.get("status")
    # "0x1" success, "0x0" reverted. Reverted = mined-but-failed; we only
    # call it confirmed on success (None status = pre-Byzantium, treat ok).
    ok = status in ("0x1", "1", 1, None)
    return ConfirmResult(found=True, confirmed=bool(ok), block_number=block_number)


async def _tron(client, network, tx_hash) -> ConfirmResult:
    base = _TRON_BASE[network]
    # Solidity node only returns a tx once it's in a solidified (confirmed)
    # block — exactly the "confirmed" semantics we want.
    r = await client.post(
        f"{base}/walletsolidity/gettransactioninfobyid", json={"value": tx_hash}
    )
    r.raise_for_status()
    data = r.json() or {}
    bn = data.get("blockNumber")
    if not bn:  # {} → not yet confirmed
        return _UNKNOWN
    # Native TRX transfers have no receipt.result; token txs do. Presence
    # in the solidity node means confirmed; SUCCESS (or absent) means ok.
    result = (data.get("receipt") or {}).get("result")
    ok = result in (None, "SUCCESS")
    return ConfirmResult(found=True, confirmed=bool(ok), block_number=int(bn))


async def _orgon(client, network, tx_hash) -> ConfirmResult:
    base = _ORGON_RPC[network]
    # Full node (no walletsolidity on the gate); gettransactioninfobyid
    # returns {} until the tx is in a block, then blockNumber + receipt.
    r = await client.post(
        f"{base}/wallet/gettransactioninfobyid", json={"value": tx_hash}
    )
    r.raise_for_status()
    data = r.json() or {}
    bn = data.get("blockNumber")
    if not bn:  # {} → not yet mined; sweep retries next tick
        return _UNKNOWN
    # Native transfers carry no receipt.result; presence in a block + a
    # SUCCESS (or absent) result means confirmed.
    result = (data.get("receipt") or {}).get("result")
    ok = result in (None, "SUCCESS")
    return ConfirmResult(found=True, confirmed=bool(ok), block_number=int(bn))


async def _btc(client, tx_hash) -> ConfirmResult:
    r = await client.get(f"{_BTC_BASE[1000]}/tx/{tx_hash}")
    if r.status_code == 404:
        return _UNKNOWN
    r.raise_for_status()
    status = (r.json() or {}).get("status") or {}
    if status.get("confirmed"):
        return ConfirmResult(
            found=True, confirmed=True, block_number=status.get("block_height")
        )
    return _UNKNOWN
