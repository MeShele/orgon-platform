"""TEMPORARY debug endpoint — live Safina send test from inside the firewall.

Added 2026-05-28 to verify Tron/ETH outbound broadcast from funded wallets
using the owning org's EC, since the prod DB/host is unreachable externally
(firewall: only 443 open). REMOVE after use.

Gated by the ORGON_DEBUG_TOKEN env var — returns 404 unless it is set AND
the `token` query param matches. No secret in source/git.
"""
from __future__ import annotations

import os
import re

from fastapi import APIRouter, HTTPException, Query, Request
from eth_keys import keys

from backend.dependencies import get_db_pool

router = APIRouter(prefix="/api/debug", tags=["debug"])

_TARGET = "0x517e701b42cca24d6a8b50be4b4c1552cc37f642"  # operator EC owning the funded test wallets


def _addr(k: str):
    h = (k or "").strip()
    h = h[2:] if h.startswith("0x") else h
    try:
        return keys.PrivateKey(bytes.fromhex(h)).public_key.to_checksum_address().lower()
    except Exception:
        return None


@router.get("/safina_sendtest")
async def safina_sendtest(request: Request, token: str = Query(...)):
    expected = os.getenv("ORGON_DEBUG_TOKEN")
    if not expected or token != expected:
        raise HTTPException(status_code=404, detail="Not Found")

    pool = get_db_pool(request)
    out: dict = {}

    # 1. Mainnet / false-confirm audit (post-fix sanity).
    async with pool.acquire() as c:
        rows = await c.fetch(
            "SELECT network, status, count(*) n, "
            "count(*) FILTER (WHERE tx_hash IS NOT NULL AND tx_hash !~ '^(0x)?[0-9a-fA-F]{64}$') garbage "
            "FROM transactions GROUP BY network, status ORDER BY network NULLS FIRST, status"
        )
        out["audit"] = [dict(r) for r in rows]
        out["mainnet_tx"] = await c.fetchval(
            "SELECT count(*) FROM transactions WHERE network IN (5000,3000,1000,5800)"
        )
        out["garbage_total"] = await c.fetchval(
            "SELECT count(*) FROM transactions WHERE tx_hash IS NOT NULL "
            "AND tx_hash !~ '^(0x)?[0-9a-fA-F]{64}$'"
        )
        orgs = await c.fetch(
            "SELECT name, safina_ec_private_key FROM organizations WHERE safina_ec_private_key IS NOT NULL"
        )

    # 2. Locate the org whose EC owns the funded test wallets.
    key = None
    for o in orgs:
        if _addr(o["safina_ec_private_key"]) == _TARGET:
            key = o["safina_ec_private_key"]
            out["org"] = o["name"]
    if not key:
        out["error"] = "org with EC 0x517E70 not found"
        return out

    # 3. Drive Safina directly (create + sign) for Tron and ETH.
    from backend.safina.signer import SafinaSigner
    from backend.safina.client import SafinaPayClient

    base = os.getenv("SAFINA_BASE_URL") or "https://my.safina.pro/ece"
    cl = SafinaPayClient(signer=SafinaSigner(private_key_hex=key), base_url=base)
    sends = [
        ("tron", "5010:::TRX###082A21BD89175CC745258DF600432623",
         "TArXF6ycPBo7VmksXPDX57K9gizUuR8ErS", "1"),
        ("eth", "3040:::ETH###98BB910BC778C9FB45258DFB003132C1",
         "0xae685D7D8Cf4F654212cf5E3d7f8115784ddB1D9", "0.01"),
    ]
    try:
        for label, tok, to, val in sends:
            try:
                u = await cl.send_transaction(token=tok, to_address=to, value=val, info="broadcast-test")
                signed: object = True
                try:
                    await cl.sign_transaction(tx_unid=u)
                except Exception as se:  # noqa: BLE001
                    signed = "sign_error: " + str(se)
                out[label] = {"unid": u, "signed": signed}
            except Exception as e:  # noqa: BLE001
                out[label] = {"error": str(e)}
    finally:
        await cl.close()
    return out
