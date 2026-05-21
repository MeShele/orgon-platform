"""Scaffold tests for the Wave-22-aligned `ec_sign` body submission.

Covers:

* `SafinaSigner.sign_tx_canonical_hex` produces a 65-byte hex signature
  that recovers back to the signer's address through the same canonical
  variant — proving the round-trip is mathematically sound regardless
  of which variant Safina ends up choosing.
* `SafinaPayClient.sign_transaction` is **backwards-compatible**: with
  `SAFINA_CANONICAL_VARIANT` unset, no body is sent (legacy behaviour).
* With the variant set + `tx_payload` provided, the client submits
  `{"ec_sign": "0x..."}`.
* Scaffold failure (unknown variant, missing field) silently falls
  back to legacy empty body — never breaks an existing sign flow.

These tests are intentionally hermetic: no real Safina, no real HTTP.
A fake httpx-style transport captures the outgoing body so we can
assert exactly what gets posted.
"""

from __future__ import annotations

import json
from typing import Any, Optional

import httpx
import pytest

from backend.safina.client import SafinaPayClient
from backend.safina.signature_verifier import (
    _CANONICAL_VARIANTS,
    _digest_for_variant,
    recover_signer_address,
)
from backend.safina.signer import SafinaSigner

# Well-known dev key (same one used in test_signer_backends.py).
TEST_KEY = "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
EXPECTED_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"


# Sample tx data used across the round-trip tests. Values chosen so the
# canonical builders don't raise — v5 in particular needs hex unid +
# 0x-prefixed 20-byte address.
SAMPLE_TX = {
    "tx_unid": "deadbeef" * 8,  # 64-char hex, mimics Safina's unid format
    "network": 5010,
    "value": "1000000",  # base-units, big-int as str
    "to_address": "0x" + "11" * 20,
}


# ────────────────────────────────────────────────────────────────────
# Pure-primitive round-trip — proves sign+recover works for every variant
# ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("variant_name", list(_CANONICAL_VARIANTS.keys()))
def test_sign_tx_canonical_round_trips_through_recover(variant_name: str) -> None:
    signer = SafinaSigner(TEST_KEY)
    sig_hex = signer.sign_tx_canonical_hex(
        tx_unid=SAMPLE_TX["tx_unid"],
        network=SAMPLE_TX["network"],
        value=SAMPLE_TX["value"],
        to_address=SAMPLE_TX["to_address"],
        variant=variant_name,
    )

    # The digest the variant says we should have hashed:
    variant = _CANONICAL_VARIANTS[variant_name]
    digest = _digest_for_variant(variant, SAMPLE_TX)

    recovered = recover_signer_address(digest, sig_hex)
    assert recovered.lower() == EXPECTED_ADDRESS.lower(), (
        f"variant {variant_name} round-trip failed: signed bytes don't recover"
    )


def test_sign_tx_canonical_requires_variant(monkeypatch: pytest.MonkeyPatch) -> None:
    """No env, no explicit variant → RuntimeError, never a silent default."""
    monkeypatch.delenv("SAFINA_CANONICAL_VARIANT", raising=False)
    signer = SafinaSigner(TEST_KEY)
    with pytest.raises(RuntimeError, match="SAFINA_CANONICAL_VARIANT"):
        signer.sign_tx_canonical_hex(
            tx_unid="x", network=0, value="0", to_address="0x" + "00" * 20,
        )


def test_sign_tx_canonical_rejects_unknown_variant() -> None:
    signer = SafinaSigner(TEST_KEY)
    with pytest.raises(ValueError, match="unknown canonical variant"):
        signer.sign_tx_canonical_hex(
            tx_unid="x", network=0, value="0", to_address="0x" + "00" * 20,
            variant="v999_nonexistent",
        )


# ────────────────────────────────────────────────────────────────────
# Client-level: legacy default, scaffold-on path, and graceful fallback
# ────────────────────────────────────────────────────────────────────


class _CapturingTransport(httpx.AsyncBaseTransport):
    """Capture POST body for assertion; respond 200 with empty JSON."""

    def __init__(self) -> None:
        self.last_body: Optional[str] = None
        self.last_url: Optional[str] = None

    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        self.last_url = str(request.url)
        self.last_body = request.content.decode("utf-8") if request.content else ""
        return httpx.Response(200, json={})


async def _client_with_capturing_transport() -> tuple[SafinaPayClient, _CapturingTransport]:
    signer = SafinaSigner(TEST_KEY)
    client = SafinaPayClient(signer, base_url="https://safina.test/ece")
    transport = _CapturingTransport()
    # Swap in a captured httpx client. SafinaPayClient lazily creates
    # one on first `_request` call; we pre-seed it.
    client._client = httpx.AsyncClient(transport=transport, headers={
        "accept": "application/json",
        "content-type": "application/json",
    })
    return client, transport


@pytest.mark.asyncio
async def test_sign_transaction_legacy_empty_body_when_no_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No env flag + no tx_payload = empty body, current production behaviour."""
    monkeypatch.delenv("SAFINA_CANONICAL_VARIANT", raising=False)
    client, transport = await _client_with_capturing_transport()
    try:
        await client.sign_transaction("tx-unid-1")
    finally:
        await client.close()
    # Legacy body — `_request` passes `data=None` → JSON-encoded `{}`.
    assert transport.last_body == "{}"
    assert transport.last_url is not None and transport.last_url.endswith("/tx_sign/tx-unid-1")


@pytest.mark.asyncio
async def test_sign_transaction_legacy_empty_body_when_env_unset_even_with_payload(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Caller passes tx_payload but env flag is OFF — still empty body."""
    monkeypatch.delenv("SAFINA_CANONICAL_VARIANT", raising=False)
    client, transport = await _client_with_capturing_transport()
    try:
        await client.sign_transaction("tx-unid-2", tx_payload=SAMPLE_TX)
    finally:
        await client.close()
    assert transport.last_body == "{}"


@pytest.mark.asyncio
async def test_sign_transaction_scaffold_submits_ec_sign(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Env set + tx_payload provided → body has `ec_sign` over canonical."""
    variant = "v1_pipe_unid_to_value"
    monkeypatch.setenv("SAFINA_CANONICAL_VARIANT", variant)
    client, transport = await _client_with_capturing_transport()
    try:
        await client.sign_transaction(SAMPLE_TX["tx_unid"], tx_payload=SAMPLE_TX)
    finally:
        await client.close()
    body = json.loads(transport.last_body or "{}")
    assert "ec_sign" in body
    sig_hex = body["ec_sign"]
    assert sig_hex.startswith("0x") and len(sig_hex) == 132  # 0x + 130 hex

    # Round-trip: the submitted ec_sign must recover back to our address
    # under the configured variant. Proves the scaffold and the verifier
    # are speaking the same canonical language.
    digest = _digest_for_variant(_CANONICAL_VARIANTS[variant], SAMPLE_TX)
    recovered = recover_signer_address(digest, sig_hex)
    assert recovered.lower() == EXPECTED_ADDRESS.lower()


@pytest.mark.asyncio
async def test_sign_transaction_falls_back_to_empty_body_on_scaffold_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Misconfigured variant ⇒ legacy behaviour preserved, never raises."""
    monkeypatch.setenv("SAFINA_CANONICAL_VARIANT", "v999_does_not_exist")
    client, transport = await _client_with_capturing_transport()
    try:
        # tx_payload provided but variant unknown — scaffold helper
        # raises, client catches, falls back to empty body.
        await client.sign_transaction("tx-unid-3", tx_payload=SAMPLE_TX)
    finally:
        await client.close()
    assert transport.last_body == "{}"
