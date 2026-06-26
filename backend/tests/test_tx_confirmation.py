"""Unit tests for backend.services.tx_confirmation — per-chain on-chain
confirmation lookup that backs `transaction.confirmed`.

No network: a fake httpx client returns canned explorer payloads so we
pin the parse logic (block_number extraction, success vs revert, not-yet
-mined) and the ORGON-chain immediate-confirm fallback.
"""

import pytest

from backend.services.tx_confirmation import (
    get_onchain_confirmation,
    supports_confirmation,
)


class _Resp:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400 and self.status_code != 404:
            raise RuntimeError(f"http {self.status_code}")


class _FakeClient:
    """Stubs .get / .post; returns whatever the test queued."""

    def __init__(self, get_resp=None, post_resp=None):
        self._get = get_resp
        self._post = post_resp
        self.calls = []

    async def get(self, url, params=None):
        self.calls.append(("GET", url, params))
        return self._get

    async def post(self, url, json=None):
        self.calls.append(("POST", url, json))
        return self._post


def test_supports_confirmation():
    for n in (1000, 3000, 3040, 5000, 5010, 5800, 5810):
        assert supports_confirmation(n) is True
    assert supports_confirmation(9999) is False
    assert supports_confirmation(None) is False


@pytest.mark.asyncio
async def test_orgon_mainnet_confirms_immediately_no_http():
    # 5800 has no verified history endpoint → broadcast is terminal, no HTTP.
    client = _FakeClient()
    res = await get_onchain_confirmation(client, 5800, "0x" + "ab" * 32)
    assert res.found and res.confirmed and res.block_number is None
    assert client.calls == []


@pytest.mark.asyncio
async def test_orgon_testnet_real_confirmation_with_block():
    # 5810 → real gettransactioninfobyid lookup on the Quasar gate.
    client = _FakeClient(post_resp=_Resp({"blockNumber": 1943941, "receipt": {"result": "SUCCESS"}}))
    res = await get_onchain_confirmation(client, 5810, "f1ed1e5a" + "0" * 56)
    assert res.found and res.confirmed and res.block_number == 1943941
    assert client.calls[0][0] == "POST"
    assert "gettransactioninfobyid" in client.calls[0][1]


@pytest.mark.asyncio
async def test_orgon_testnet_native_no_receipt_still_confirmed():
    # Native ORGON transfers have no receipt.result — in-a-block = confirmed.
    client = _FakeClient(post_resp=_Resp({"blockNumber": 100}))
    res = await get_onchain_confirmation(client, 5810, "ab" * 32)
    assert res.found and res.confirmed and res.block_number == 100


@pytest.mark.asyncio
async def test_orgon_testnet_not_yet_mined_unknown():
    # Empty {} → tx not in a block yet → not found, sweep retries (no stuck).
    client = _FakeClient(post_resp=_Resp({}))
    res = await get_onchain_confirmation(client, 5810, "ab" * 32)
    assert not res.found and not res.confirmed


@pytest.mark.asyncio
async def test_eth_receipt_success():
    client = _FakeClient(get_resp=_Resp({"result": {"blockNumber": "0xa1b2", "status": "0x1"}}))
    res = await get_onchain_confirmation(client, 3040, "0x" + "cd" * 32)
    assert res.found and res.confirmed
    assert res.block_number == 0xA1B2


@pytest.mark.asyncio
async def test_eth_receipt_reverted_not_confirmed():
    client = _FakeClient(get_resp=_Resp({"result": {"blockNumber": "0x5", "status": "0x0"}}))
    res = await get_onchain_confirmation(client, 3000, "0x" + "cd" * 32)
    assert res.found is True
    assert res.confirmed is False
    assert res.block_number == 5


@pytest.mark.asyncio
async def test_eth_not_yet_mined():
    client = _FakeClient(get_resp=_Resp({"result": None}))
    res = await get_onchain_confirmation(client, 3040, "0x" + "cd" * 32)
    assert res.found is False and res.confirmed is False


@pytest.mark.asyncio
async def test_tron_confirmed_in_solidity_block():
    client = _FakeClient(post_resp=_Resp({"blockNumber": 12345, "receipt": {"result": "SUCCESS"}}))
    res = await get_onchain_confirmation(client, 5010, "abc123")
    assert res.found and res.confirmed and res.block_number == 12345


@pytest.mark.asyncio
async def test_tron_native_no_receipt_result_still_confirmed():
    # Native TRX transfers carry no receipt.result; presence in the
    # solidity node (blockNumber set) is itself confirmation.
    client = _FakeClient(post_resp=_Resp({"blockNumber": 777}))
    res = await get_onchain_confirmation(client, 5000, "abc123")
    assert res.found and res.confirmed and res.block_number == 777


@pytest.mark.asyncio
async def test_tron_not_yet_confirmed_empty():
    client = _FakeClient(post_resp=_Resp({}))
    res = await get_onchain_confirmation(client, 5010, "abc123")
    assert res.found is False


@pytest.mark.asyncio
async def test_btc_confirmed():
    client = _FakeClient(get_resp=_Resp({"status": {"confirmed": True, "block_height": 880000}}))
    res = await get_onchain_confirmation(client, 1000, "deadbeef")
    assert res.found and res.confirmed and res.block_number == 880000


@pytest.mark.asyncio
async def test_btc_unconfirmed_in_mempool():
    client = _FakeClient(get_resp=_Resp({"status": {"confirmed": False}}))
    res = await get_onchain_confirmation(client, 1000, "deadbeef")
    assert res.found is False


@pytest.mark.asyncio
async def test_btc_404_not_found():
    client = _FakeClient(get_resp=_Resp({}, status_code=404))
    res = await get_onchain_confirmation(client, 1000, "deadbeef")
    assert res.found is False


@pytest.mark.asyncio
async def test_unknown_network_unknown():
    client = _FakeClient()
    res = await get_onchain_confirmation(client, 9999, "0x" + "ab" * 32)
    assert res.found is False
