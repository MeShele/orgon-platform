"""Payload-pinning tests for the two extracted webhook emit helpers
(TD-12).

What used to be ~30-line inline blocks inside `sync_transactions` and
`sync_wallets` is now in two static helpers:

* `TransactionService._emit_tx_lifecycle_events`
* `WalletService._emit_wallet_activated_if_address_appeared`

These tests pin both halves of each helper: the **gate** (does it fire
or not for each input state) and the **payload** (exact keys + values
match the WEBHOOKS.md contract). A future edit that breaks either —
e.g. changes the `prev_row.tx_hash` emptiness check or drops a payload
field asystem-core consumes — will fail here without needing a
full-stack Safina-fake to reproduce.

We don't touch the surrounding UPSERT logic; that's the responsibility
of the caller and stays untested at this layer (a different feature
of the polling loop entirely).
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from backend.services.transaction_service import TransactionService
from backend.services.wallet_service import WalletService

# A realistic 64-hex on-chain hash. The emit helper now validates the
# hash format (post-058), so fixtures must use a real-shaped hash — a
# short "0xfeedcafe" stub is correctly rejected as not-a-broadcast.
REAL_HASH = "0x" + "ab" * 32
# Verbatim string Safina writes into `tx` when it abandons a signed tx.
CANCEL_STR = "Transaction canceled, 1 day limit."


# ────────────────────────────────────────────────────────────────────
# Common helpers — small Safina-model duck-types
# ────────────────────────────────────────────────────────────────────


class _SafinaTx:
    """Minimal stand-in for the Pydantic `Transaction` model used in
    sync_transactions. The helper only touches a handful of attributes
    so we don't pull in the real model + its many required fields."""

    def __init__(
        self,
        *,
        unid: str = "tx-unid-1",
        tx: str | None = None,
        token: str = "5010:::TRX###wallet-1",
        to_addr: str = "TX-recipient",
        value: float | str = "1.5",
    ):
        self.unid = unid
        self.tx = tx
        self.token = token
        self.to_addr = to_addr
        self.value = value


class _SafinaWallet:
    """Duck-typed Safina wallet — sync_wallets reads .name/.network/.myUNID."""

    def __init__(self, *, name: str = "w1", network: int = 5010, myUNID: str = "u1"):
        self.name = name
        self.network = network
        self.myUNID = myUNID


# ────────────────────────────────────────────────────────────────────
# TransactionService._emit_tx_lifecycle_events
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tx_lifecycle_fires_only_broadcasted_on_null_to_hex_transition() -> None:
    """The canonical happy path: prev.tx_hash empty, tx.tx now present,
    org_id present → ONLY `transaction.broadcasted` fires. `confirmed` is
    no longer co-emitted here — it now comes from the confirmation sweep
    on real on-chain inclusion (else it was a premature duplicate that
    closed orders before the chain confirmed)."""
    prev_row = {
        "id": "row-1",
        "tx_hash": "",
        "organization_id": "11111111-2222-3333-4444-555555555555",
    }
    tx = _SafinaTx(unid="tx-1", tx=REAL_HASH, to_addr="TXdest", value="2")

    captured: list[dict] = []

    async def fake_publish(pool, *, merchant_id, event_type, payload, request_id=None):
        captured.append({
            "merchant_id": merchant_id,
            "event_type": event_type,
            "payload": payload,
        })
        return "delivery-id"

    pool = object()
    with patch("backend.services.webhook_publisher.publish_event", fake_publish):
        await TransactionService._emit_tx_lifecycle_events(
            pool, prev_row, tx, "wallet-A",
        )

    assert len(captured) == 1, "only broadcasted should fire (not confirmed)"
    c = captured[0]
    assert c["event_type"] == "transaction.broadcasted"
    p = c["payload"]
    assert p["tx_id"] == "row-1"
    assert p["tx_unid"] == "tx-1"
    assert p["tx_hash"] == REAL_HASH
    assert p["wallet_name"] == "wallet-A"
    assert p["to_address"] == "TXdest"
    assert p["amount"] == "2"
    assert p["token"] == "5010:::TRX###wallet-1"


@pytest.mark.asyncio
async def test_tx_lifecycle_skips_when_prev_row_none() -> None:
    """If we don't have a prior row for this unid we never originated
    the tx (race in the polling loop) — don't emit, the next sync
    cycle will see it."""
    fake = AsyncMock()
    pool = object()
    with patch("backend.services.webhook_publisher.publish_event", fake):
        await TransactionService._emit_tx_lifecycle_events(
            pool, None, _SafinaTx(tx="0xabc"), "w",
        )
    fake.assert_not_called()


@pytest.mark.asyncio
async def test_tx_lifecycle_skips_when_prev_already_had_hash() -> None:
    """Re-sync of an already-broadcasted tx: prev.tx_hash already set.
    Re-firing the webhook would be a duplicate event for asystem-core
    — replay-guard would catch it, but emitting twice still burns
    delivery quota for nothing."""
    prev_row = {
        "id": "row-1",
        "tx_hash": "0xpreviously-set",
        "organization_id": "11111111-2222-3333-4444-555555555555",
    }
    fake = AsyncMock()
    pool = object()
    with patch("backend.services.webhook_publisher.publish_event", fake):
        await TransactionService._emit_tx_lifecycle_events(
            pool, prev_row, _SafinaTx(tx=REAL_HASH), "w",
        )
    fake.assert_not_called()


@pytest.mark.asyncio
async def test_tx_lifecycle_skips_when_tx_is_cancellation_string() -> None:
    """REGRESSION (the 2026-05-27 false-confirmation bug): Safina puts
    "Transaction canceled, 1 day limit." into `tx` on abandonment. That
    is truthy but NOT a hash — we must NOT fire broadcasted/confirmed.
    Pre-058 this fired and told asystem-core a canceled payout was
    confirmed."""
    prev_row = {
        "id": "row-1",
        "tx_hash": "",
        "organization_id": "11111111-2222-3333-4444-555555555555",
    }
    fake = AsyncMock()
    pool = object()
    with patch("backend.services.webhook_publisher.publish_event", fake):
        await TransactionService._emit_tx_lifecycle_events(
            pool, prev_row, _SafinaTx(tx=CANCEL_STR), "w",
        )
    fake.assert_not_called()


@pytest.mark.asyncio
async def test_tx_lifecycle_skips_when_tx_still_unsigned() -> None:
    """Sync tick where Safina hasn't broadcast yet — tx.tx still empty.
    We don't have a hash to deliver, so don't fire."""
    prev_row = {
        "id": "row-1",
        "tx_hash": "",
        "organization_id": "11111111-2222-3333-4444-555555555555",
    }
    fake = AsyncMock()
    pool = object()
    with patch("backend.services.webhook_publisher.publish_event", fake):
        await TransactionService._emit_tx_lifecycle_events(
            pool, prev_row, _SafinaTx(tx=None), "w",
        )
    fake.assert_not_called()


@pytest.mark.asyncio
async def test_tx_lifecycle_skips_when_no_organization_id() -> None:
    """A tx without tenancy is legacy/orphan — don't emit, we have
    nowhere to deliver."""
    prev_row = {"id": "row-1", "tx_hash": "", "organization_id": None}
    fake = AsyncMock()
    pool = object()
    with patch("backend.services.webhook_publisher.publish_event", fake):
        await TransactionService._emit_tx_lifecycle_events(
            pool, prev_row, _SafinaTx(tx="0xabc"), "w",
        )
    fake.assert_not_called()


@pytest.mark.asyncio
async def test_tx_lifecycle_swallows_publisher_exception() -> None:
    """Webhook queue blip must never break the surrounding sync loop —
    publish failure is logged at WARNING, helper returns normally."""
    prev_row = {
        "id": "row-1",
        "tx_hash": "",
        "organization_id": "11111111-2222-3333-4444-555555555555",
    }

    async def boom(pool, **kwargs):
        raise RuntimeError("webhook queue exploded")

    pool = object()
    # Should NOT raise — the test passes if no exception propagates.
    with patch("backend.services.webhook_publisher.publish_event", boom):
        await TransactionService._emit_tx_lifecycle_events(
            pool, prev_row, _SafinaTx(tx="0xabc"), "w",
        )


# ────────────────────────────────────────────────────────────────────
# TransactionService._emit_tx_failed_event
# ────────────────────────────────────────────────────────────────────

# Verbatim Safina error string captured live on prod 2026-06-03.
OOF_STR = "global: Returned error: EVM error: OutOfFunds"


@pytest.mark.asyncio
async def test_tx_failed_fires_on_transition_into_failed() -> None:
    """Canonical case: prev status was `signed` (in-flight), Safina now
    returned an error string → `transaction.failed` fires once with the
    reason carried verbatim."""
    prev_row = {
        "id": "row-9",
        "tx_hash": "",
        "status": "signed",
        "organization_id": "11111111-2222-3333-4444-555555555555",
    }
    tx = _SafinaTx(unid="tx-9", tx=OOF_STR, to_addr="0xdest", value="5")

    captured: list[dict] = []

    async def fake_publish(pool, *, merchant_id, event_type, payload, request_id=None):
        captured.append({"merchant_id": merchant_id, "event_type": event_type, "payload": payload})

    pool = object()
    with patch("backend.services.webhook_publisher.publish_event", fake_publish):
        await TransactionService._emit_tx_failed_event(
            pool, prev_row, tx, "wallet-A", OOF_STR,
        )

    assert len(captured) == 1
    c = captured[0]
    assert c["event_type"] == "transaction.failed"
    assert c["merchant_id"] == "11111111-2222-3333-4444-555555555555"
    assert c["payload"] == {
        "tx_id": "row-9",
        "tx_unid": "tx-9",
        "tx_hash": None,
        "wallet_name": "wallet-A",
        "to_address": "0xdest",
        "amount": "5",
        "token": "5010:::TRX###wallet-1",
        "reason": OOF_STR,
    }


@pytest.mark.asyncio
async def test_tx_failed_skips_when_prev_row_none() -> None:
    """No prior row — orphan tx (created directly on Safina, no tenancy).
    Nowhere to deliver, don't emit."""
    fake = AsyncMock()
    pool = object()
    with patch("backend.services.webhook_publisher.publish_event", fake):
        await TransactionService._emit_tx_failed_event(
            pool, None, _SafinaTx(tx=OOF_STR), "w", OOF_STR,
        )
    fake.assert_not_called()


@pytest.mark.asyncio
async def test_tx_failed_skips_when_already_terminal() -> None:
    """At-most-once: a row already in a terminal/emitted state
    (`failed`/`canceled`/`confirmed`) must not re-fire on the next sync
    tick."""
    pool = object()
    for prev_status in ("failed", "canceled", "confirmed"):
        prev_row = {
            "id": "row-9",
            "tx_hash": "",
            "status": prev_status,
            "organization_id": "11111111-2222-3333-4444-555555555555",
        }
        fake = AsyncMock()
        with patch("backend.services.webhook_publisher.publish_event", fake):
            await TransactionService._emit_tx_failed_event(
                pool, prev_row, _SafinaTx(tx=OOF_STR), "w", OOF_STR,
            )
        fake.assert_not_called()


@pytest.mark.asyncio
async def test_tx_failed_skips_when_no_organization_id() -> None:
    """A failed tx without tenancy can't be delivered anywhere."""
    prev_row = {"id": "row-9", "tx_hash": "", "status": "signed", "organization_id": None}
    fake = AsyncMock()
    pool = object()
    with patch("backend.services.webhook_publisher.publish_event", fake):
        await TransactionService._emit_tx_failed_event(
            pool, prev_row, _SafinaTx(tx=OOF_STR), "w", OOF_STR,
        )
    fake.assert_not_called()


@pytest.mark.asyncio
async def test_tx_failed_swallows_publisher_exception() -> None:
    """Webhook blip must not break the sync loop — the status transition
    already landed in the UPSERT; this helper just logs + returns."""
    prev_row = {
        "id": "row-9",
        "tx_hash": "",
        "status": "signed",
        "organization_id": "11111111-2222-3333-4444-555555555555",
    }

    async def boom(pool, **kwargs):
        raise RuntimeError("webhook queue exploded")

    pool = object()
    with patch("backend.services.webhook_publisher.publish_event", boom):
        await TransactionService._emit_tx_failed_event(
            pool, prev_row, _SafinaTx(tx=OOF_STR), "w", OOF_STR,
        )


@pytest.mark.asyncio
async def test_tx_failed_defaults_reason_when_none() -> None:
    """If we somehow reach the emit with no captured reason, the payload
    still carries a non-null sentinel so consumers can branch."""
    prev_row = {
        "id": "row-9",
        "tx_hash": "",
        "status": "signed",
        "organization_id": "11111111-2222-3333-4444-555555555555",
    }
    captured: list[dict] = []

    async def fake_publish(pool, *, merchant_id, event_type, payload, request_id=None):
        captured.append(payload)

    pool = object()
    with patch("backend.services.webhook_publisher.publish_event", fake_publish):
        await TransactionService._emit_tx_failed_event(
            pool, prev_row, _SafinaTx(tx=OOF_STR), "w", None,
        )
    assert captured and captured[0]["reason"] == "broadcast_rejected"


# ────────────────────────────────────────────────────────────────────
# WalletService._emit_wallet_activated_if_address_appeared
# ────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_wallet_activated_fires_on_empty_to_address_transition() -> None:
    """Canonical case: existing.addr was '' before this sync tick,
    Safina has now returned a real address, merchant_id is known."""
    existing = {
        "id": "wallet-uuid-1",
        "end_user_id": "user-uuid-1",
        "addr": "",
        "organization_id": "22222222-3333-4444-5555-666666666666",
    }

    captured: list[dict] = []

    async def fake_publish(pool, *, merchant_id, event_type, payload, request_id=None):
        captured.append({
            "merchant_id": merchant_id,
            "event_type": event_type,
            "payload": payload,
        })

    pool = object()
    with patch("backend.services.webhook_publisher.publish_event", fake_publish):
        await WalletService._emit_wallet_activated_if_address_appeared(
            pool, existing, _SafinaWallet(network=5010, myUNID="my-unid-1"),
            "TXnewaddr",
        )

    assert len(captured) == 1
    c = captured[0]
    assert c["event_type"] == "wallet.activated"
    assert c["merchant_id"] == "22222222-3333-4444-5555-666666666666"
    assert c["payload"] == {
        "wallet_id": "wallet-uuid-1",
        "end_user_id": "user-uuid-1",
        "network": 5010,
        "address": "TXnewaddr",
        "my_unid": "my-unid-1",
    }


@pytest.mark.asyncio
async def test_wallet_activated_treats_whitespace_addr_as_empty() -> None:
    """A row with `addr = '   '` should be considered "not yet
    activated" — the strip() guard in the helper protects against
    cosmetic whitespace tripping the gate."""
    existing = {
        "id": "wallet-1",
        "end_user_id": "u",
        "addr": "   ",   # whitespace-only — semantically empty
        "organization_id": "org-1",
    }
    captured = []

    async def fake_publish(pool, **kwargs):
        captured.append(kwargs)

    pool = object()
    with patch("backend.services.webhook_publisher.publish_event", fake_publish):
        await WalletService._emit_wallet_activated_if_address_appeared(
            pool, existing, _SafinaWallet(), "TXreal",
        )
    assert len(captured) == 1


@pytest.mark.asyncio
async def test_wallet_activated_skips_when_prev_addr_already_populated() -> None:
    """Re-sync of an already-activated wallet — addr unchanged. Don't
    fire again."""
    existing = {
        "id": "w1",
        "end_user_id": "u",
        "addr": "TXpreviously-set",
        "organization_id": "org-1",
    }
    fake = AsyncMock()
    pool = object()
    with patch("backend.services.webhook_publisher.publish_event", fake):
        await WalletService._emit_wallet_activated_if_address_appeared(
            pool, existing, _SafinaWallet(), "TXpreviously-set",
        )
    fake.assert_not_called()


@pytest.mark.asyncio
async def test_wallet_activated_skips_when_new_addr_empty() -> None:
    """Safina hasn't filled the address yet — nothing to emit. We'll
    re-check next sync tick."""
    existing = {
        "id": "w1", "end_user_id": None, "addr": "",
        "organization_id": "org-1",
    }
    fake = AsyncMock()
    pool = object()
    with patch("backend.services.webhook_publisher.publish_event", fake):
        await WalletService._emit_wallet_activated_if_address_appeared(
            pool, existing, _SafinaWallet(), "",
        )
    fake.assert_not_called()


@pytest.mark.asyncio
async def test_wallet_activated_uses_fallback_org_when_existing_is_null() -> None:
    """Legacy rows without organization_id get tenancy backfilled at
    sync time — the helper should pick up the fallback when
    `existing.organization_id` is None."""
    existing = {
        "id": "w1", "end_user_id": "u", "addr": "",
        "organization_id": None,
    }

    captured = []

    async def fake_publish(pool, *, merchant_id, **kwargs):
        captured.append({"merchant_id": merchant_id, **kwargs})

    pool = object()
    with patch("backend.services.webhook_publisher.publish_event", fake_publish):
        await WalletService._emit_wallet_activated_if_address_appeared(
            pool, existing, _SafinaWallet(), "TXnew",
            fallback_org_id="org-fallback",
        )
    assert len(captured) == 1
    assert captured[0]["merchant_id"] == "org-fallback"


@pytest.mark.asyncio
async def test_wallet_activated_skips_when_no_merchant_anywhere() -> None:
    """Existing.org_id NULL and no fallback — fire would have nowhere
    to deliver, skip silently."""
    existing = {
        "id": "w1", "end_user_id": None, "addr": "",
        "organization_id": None,
    }
    fake = AsyncMock()
    pool = object()
    with patch("backend.services.webhook_publisher.publish_event", fake):
        await WalletService._emit_wallet_activated_if_address_appeared(
            pool, existing, _SafinaWallet(), "TXnew",
            fallback_org_id=None,
        )
    fake.assert_not_called()


@pytest.mark.asyncio
async def test_wallet_activated_handles_null_end_user_id() -> None:
    """Treasury wallets (corporate hot/fee/cold) have end_user_id=NULL.
    The payload's `end_user_id` field must be JSON null, not the string
    'None' or absent entirely."""
    existing = {
        "id": "w1", "end_user_id": None, "addr": "",
        "organization_id": "org-1",
    }
    captured = []

    async def fake_publish(pool, *, payload, **kwargs):
        captured.append(payload)

    pool = object()
    with patch("backend.services.webhook_publisher.publish_event", fake_publish):
        await WalletService._emit_wallet_activated_if_address_appeared(
            pool, existing, _SafinaWallet(), "TXnew",
        )
    assert len(captured) == 1
    assert captured[0]["end_user_id"] is None


@pytest.mark.asyncio
async def test_wallet_activated_swallows_publisher_exception() -> None:
    """Same as tx lifecycle — webhook queue blip must never break the
    sync polling loop."""
    existing = {
        "id": "w1", "end_user_id": "u", "addr": "",
        "organization_id": "org-1",
    }

    async def boom(pool, **kwargs):
        raise RuntimeError("queue full")

    pool = object()
    with patch("backend.services.webhook_publisher.publish_event", boom):
        await WalletService._emit_wallet_activated_if_address_appeared(
            pool, existing, _SafinaWallet(), "TXnew",
        )
