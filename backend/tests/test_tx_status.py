"""Unit tests for backend.safina.tx_status — the single source of truth
that distinguishes a real on-chain hash from a Safina status string.

Pins the false-confirmation fix (2026-05-27): Safina writes
"Transaction canceled, 1 day limit." into the `tx` field on abandonment,
and that must never be treated as a broadcast hash.
"""

import pytest

from backend.safina.tx_status import (
    is_broadcast_hash,
    clean_tx_hash,
    looks_canceled,
    looks_failed,
    classify_safina_tx_status,
)

REAL_TRON = "f9e97928c346af4087ab61d827ea2bebdd741cee38e9f2670cf961a446b9ee73"  # 64 hex, no 0x
REAL_ETH = "0x" + "ab" * 32                                                     # 0x + 64 hex
CANCEL = "Transaction canceled, 1 day limit."
# Verbatim error string Safina returns in `tx` on a rejected broadcast,
# captured live on prod 2026-06-03 (5 ETH overdraft from a 0.36 wallet).
OOF = "global: Returned error: EVM error: OutOfFunds"


@pytest.mark.parametrize("val", [REAL_TRON, REAL_ETH, REAL_TRON.upper(), "  " + REAL_ETH + " "])
def test_real_hashes_accepted(val):
    assert is_broadcast_hash(val) is True
    assert clean_tx_hash(val) == val.strip()


@pytest.mark.parametrize("val", [
    None, "", "   ",
    CANCEL,
    "0xfeedcafe",                       # too short
    "0x" + "ab" * 31,                   # 62 hex — one byte short
    "0x" + "ab" * 33,                   # too long
    "Transaction failed",
    "pending",
    "0x" + "zz" * 32,                   # non-hex chars
])
def test_non_hashes_rejected(val):
    assert is_broadcast_hash(val) is False
    assert clean_tx_hash(val) is None


@pytest.mark.parametrize("val,expected", [
    (CANCEL, True),
    ("Transaction canceled, 1 day limit.", True),
    ("daily LIMIT reached", True),
    ("tx failed: insufficient funds", True),
    (REAL_ETH, False),
    (None, False),
    ("", False),
    ("pending broadcast", False),
])
def test_looks_canceled(val, expected):
    assert looks_canceled(val) is expected


@pytest.mark.parametrize("val,expected", [
    (OOF, True),                          # the live OutOfFunds string
    ("global: Returned error: nonce too low", True),
    ("insufficient funds for gas", True),
    (REAL_ETH, False),                    # a real hash is a broadcast, not a failure
    (REAL_TRON, False),
    (None, False),                        # null = in-flight, not failed
    ("", False),
    ("   ", False),
    (CANCEL, False),                      # cancellation is `canceled`, not `failed`
    ("daily LIMIT reached", False),
])
def test_looks_failed(val, expected):
    assert looks_failed(val) is expected


@pytest.mark.parametrize("tx_field,signed,expected", [
    (REAL_ETH, True, "confirmed"),
    (REAL_TRON, False, "confirmed"),      # a hash wins regardless of `signed`
    (CANCEL, True, "canceled"),
    (OOF, True, "failed"),                # error string → failed, not stuck signed
    (OOF, False, "failed"),
    (None, True, "signed"),               # signed, no tx yet
    (None, False, "pending"),
    ("", False, "pending"),
])
def test_classify_safina_tx_status(tx_field, signed, expected):
    assert classify_safina_tx_status(tx_field, signed=signed) == expected
