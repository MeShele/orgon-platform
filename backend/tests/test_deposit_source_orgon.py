"""ORGON deposit source — native-coin detection via the Quasar gate.

Pins the parse of the TronGrid-style /v1/accounts/{addr}/transactions
shape that quasargate returns (ORGON is a Tron fork): only SUCCESS
TransferContract rows with a positive amount become DepositEvents, tagged
asset="ORGON" with Tron's 6-decimal sun base unit.
"""

from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

import pytest

from backend.services.deposit_sources import orgon, get_source, all_supported_networks


SINCE = datetime(2026, 6, 1, tzinfo=timezone.utc)
WALLET = {"id": "w1", "merchant_id": "m1", "end_user_id": "u1",
          "addr": "oZgGn1jJegoqCKqPSkmn6J4dmaG7yCYTQ5", "network": 5810}


class _FakeResp:
    def __init__(self, payload):
        self._payload = payload
    def raise_for_status(self):
        return None
    def json(self):
        return self._payload


class _FakeClient:
    """Minimal httpx.AsyncClient stand-in: returns a canned response and
    records the URL/params it was called with."""
    def __init__(self, payload):
        self._payload = payload
        self.calls: list[tuple[str, dict]] = []
    async def get(self, url, params=None):
        self.calls.append((url, params or {}))
        return _FakeResp(self._payload)


def _transfer_tx(*, txid, amount, success=True, ctype="TransferContract"):
    return {
        "txID": txid,
        "ret": [{"contractRet": "SUCCESS" if success else "REVERT"}],
        "raw_data": {"contract": [{
            "type": ctype,
            "parameter": {"value": {
                "amount": amount,
                "owner_address_base58": "oSenderAddrBase58xxxxxxxxxxxxxxxxx",
            }},
        }]},
        "blockNumber": 1947000,
        "block_timestamp": 1780000000000,
    }


def test_registered_for_5810():
    assert 5810 in all_supported_networks()
    assert get_source(5810) is orgon


@pytest.mark.asyncio
async def test_scan_native_parses_success_transfer():
    payload = {"data": [_transfer_tx(txid="AA11", amount=2_500_000)]}  # 2.5 ORGON
    client = _FakeClient(payload)
    out = await orgon.scan_native(client, WALLET, SINCE)
    assert len(out) == 1
    ev = out[0]
    assert ev.tx_hash == "AA11"
    assert ev.asset == "ORGON"
    assert ev.amount == Decimal("2.5")
    assert ev.log_index == 0
    assert ev.block_number == 1947000
    # hit the testnet gate, address-scoped, only confirmed inbound
    url, params = client.calls[0]
    assert url.startswith("https://quasargate.orgon.space/v1/accounts/")
    assert params["only_to"] == "true" and params["only_confirmed"] == "true"


@pytest.mark.asyncio
async def test_scan_native_skips_failed_nonzero_and_nontransfer():
    payload = {"data": [
        _transfer_tx(txid="OK", amount=1_000_000),
        _transfer_tx(txid="FAILED", amount=1_000_000, success=False),
        _transfer_tx(txid="ZERO", amount=0),
        _transfer_tx(txid="NOTTRANSFER", amount=1_000_000, ctype="TriggerSmartContract"),
        {"txID": None},  # malformed
    ]}
    out = await orgon.scan_native(_FakeClient(payload), WALLET, SINCE)
    assert [e.tx_hash for e in out] == ["OK"]


@pytest.mark.asyncio
async def test_scan_native_empty_data():
    out = await orgon.scan_native(_FakeClient({"data": []}), WALLET, SINCE)
    assert out == []


@pytest.mark.asyncio
async def test_scan_tokens_is_empty_orgon_has_no_tokens():
    out = await orgon.scan_tokens(_FakeClient({"data": []}), WALLET, SINCE)
    assert out == []
