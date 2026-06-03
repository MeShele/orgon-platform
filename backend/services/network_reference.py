"""Authoritative public network reference for the `/v1/*` surface.

B2B integrators (asystem-core's `orgon-*` edge functions in particular)
need a canonical mapping from their own network slugs (e.g.
``"eth-sepolia"``) to the numeric chain_id ORGON's `/v1` endpoints expect
on input (``"3040"``), plus native-asset metadata and the sandbox/testnet
flag. DFNS exposes well-known chain slugs; ORGON's chain_ids — especially
the bespoke ORGON-chain ``5800``/``5810`` — are not guessable, so we
publish them here instead of forcing integrators to hardcode a fragile
map (which previously meant manually editing
``NETWORK_SLUG_TO_CHAIN_ID`` on the consumer side).

Source of truth for chain_id values: prod ``networks_cache`` (verified
2026-05-20). Slugs follow asystem-core's existing convention
(``tron-nile`` / ``eth-sepolia`` / ``orgon-testnet``) extended to the
mainnets. `native_decimals` is ``None`` where genuinely unknown
(ORGON-chain) rather than guessed — integrators read per-asset decimals
from ``GET /v1/wallets/{id}/assets`` anyway.
"""

from __future__ import annotations

import json
from typing import Optional

from backend.services.merchant_wallet_service import TESTNET_NETWORKS

# chain_id -> (slug, native_symbol, native_decimals | None)
NETWORK_REFERENCE: dict[int, tuple[str, str, Optional[int]]] = {
    1000: ("bitcoin", "BTC", 8),
    3000: ("ethereum", "ETH", 18),
    3040: ("eth-sepolia", "ETH", 18),
    5000: ("tron", "TRX", 6),
    5010: ("tron-nile", "TRX", 6),
    5800: ("orgon", "ORGON", None),
    5810: ("orgon-testnet", "ORGON", None),
}


def _coerce_tokens(raw) -> list:
    """`networks_cache.tokens` is jsonb — asyncpg may hand it back as a
    JSON string or an already-decoded list depending on codec setup.
    Normalise to a list; never raise on malformed data."""
    if isinstance(raw, str):
        try:
            raw = json.loads(raw)
        except Exception:
            return []
    return raw if isinstance(raw, list) else []


def project_network(row: dict) -> dict:
    """Shape one `networks_cache` row into the public reference entry."""
    cid = int(row["network_id"])
    slug, sym, dec = NETWORK_REFERENCE.get(cid, (None, None, None))
    return {
        "chain_id": str(cid),  # string form — exactly what /v1 expects on input
        "chain_id_int": cid,
        "slug": slug,  # null for networks not yet canonicalised
        "name": row.get("network_name"),
        "native_symbol": sym,
        "native_decimals": dec,
        "testnet": cid in TESTNET_NETWORKS,
        # sandbox API keys are restricted to testnet networks on the backend
        "sandbox_allowed": cid in TESTNET_NETWORKS,
        "status": row.get("status"),
        "explorers": {
            "address": row.get("address_explorer") or None,
            "tx": row.get("tx_explorer") or None,
            "block": row.get("block_explorer") or None,
        },
        # best-effort token directory; authoritative per-wallet balances
        # (with verified contracts) come from GET /v1/wallets/{id}/assets
        "tokens": _coerce_tokens(row.get("tokens")),
    }


async def list_public_networks(pool) -> dict:
    """Public, merchant-agnostic network reference. No HMAC required."""
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            "SELECT network_id, network_name, short_name, status, tokens, "
            "address_explorer, tx_explorer, block_explorer "
            "FROM networks_cache ORDER BY network_id"
        )
    return {"networks": [project_network(dict(r)) for r in rows]}
