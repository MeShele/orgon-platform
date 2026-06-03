"""Unit tests for backend.services.network_reference — the authoritative
chain_id <-> slug map published on GET /v1/networks.

Pins the contract B2B integrators (asystem-core's orgon-* edge functions)
depend on: the numeric chain_id they must send on input, the slug they
map from, the testnet/sandbox flag, and robust tokens handling.
"""

import pytest

from backend.services.network_reference import (
    NETWORK_REFERENCE,
    project_network,
    _coerce_tokens,
)


def _row(network_id, **kw):
    base = {
        "network_id": network_id,
        "network_name": kw.get("network_name", "X"),
        "short_name": kw.get("short_name"),
        "status": kw.get("status", 1),
        "tokens": kw.get("tokens", []),
        "address_explorer": kw.get("address_explorer"),
        "tx_explorer": kw.get("tx_explorer"),
        "block_explorer": kw.get("block_explorer"),
    }
    return base


@pytest.mark.parametrize("cid,slug,sym,dec,testnet", [
    (1000, "bitcoin", "BTC", 8, False),
    (3000, "ethereum", "ETH", 18, False),
    (3040, "eth-sepolia", "ETH", 18, True),
    (5000, "tron", "TRX", 6, False),
    (5010, "tron-nile", "TRX", 6, True),
    (5800, "orgon", "ORGON", None, False),
    (5810, "orgon-testnet", "ORGON", None, True),
])
def test_known_networks_projected(cid, slug, sym, dec, testnet):
    out = project_network(_row(cid, network_name="N"))
    assert out["chain_id"] == str(cid)           # string form — what /v1 expects on input
    assert out["chain_id_int"] == cid
    assert out["slug"] == slug
    assert out["native_symbol"] == sym
    assert out["native_decimals"] == dec
    assert out["testnet"] is testnet
    assert out["sandbox_allowed"] is testnet     # sandbox keys restricted to testnets


def test_unknown_network_has_null_slug_but_still_listed():
    """Forward-compat: a network in networks_cache we haven't canonicalised
    is still returned (chain_id + name) with slug=null, not dropped."""
    out = project_network(_row(9999, network_name="Future Chain"))
    assert out["chain_id"] == "9999"
    assert out["slug"] is None
    assert out["native_symbol"] is None
    assert out["testnet"] is False


def test_explorers_projected():
    out = project_network(_row(3000, address_explorer="https://a", tx_explorer="https://t"))
    assert out["explorers"] == {"address": "https://a", "tx": "https://t", "block": None}


@pytest.mark.parametrize("raw,expected", [
    ([{"symbol": "USDT"}], [{"symbol": "USDT"}]),       # already a list
    ('[{"symbol":"USDT"}]', [{"symbol": "USDT"}]),       # jsonb as string
    ("not json", []),                                    # malformed → empty, no raise
    (None, []),
    ({}, []),                                            # dict (unexpected) → empty
])
def test_coerce_tokens(raw, expected):
    assert _coerce_tokens(raw) == expected


def test_reference_covers_prod_networks():
    """The 7 networks live in prod networks_cache (verified 2026-05-20)
    must all be in the static reference, else /v1/networks would emit a
    null slug for a real network and break the integrator's map."""
    for cid in (1000, 3000, 3040, 5000, 5010, 5800, 5810):
        assert cid in NETWORK_REFERENCE
