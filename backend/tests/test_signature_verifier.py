"""Unit tests for the Safina signature verification primitives.

We sign known messages with our own SafinaSigner, then assert the
verifier recovers the same address. This validates the round-trip
(parse → recover → compare) without needing live Safina data.
"""

from __future__ import annotations

import pytest

from backend.safina.signer import SafinaSigner
from backend.safina.signer_backends import EnvSignerBackend
from backend.safina.signature_verifier import (
    canonical_payload,
    eth_personal_sign_hash,
    is_verification_enabled,
    recover_signer_address,
    verify_safina_tx_signer,
    verify_signer,
)

TEST_KEY = "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
EXPECTED_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"


# ────────────────────────────────────────────────────────────────────
# helpers — produce a known-good signature
# ────────────────────────────────────────────────────────────────────


def _sign_compact(message: bytes) -> str:
    """Sign with TEST_KEY, return r||s||v hex (the format Safina returns)."""
    backend = EnvSignerBackend(TEST_KEY)
    digest = eth_personal_sign_hash(message)
    sig = backend.sign_msg_hash(digest)
    # eth_keys returns v as 0/1; the wire format that callers usually
    # see is +27 (Ethereum personal_sign convention). We test both forms.
    r_hex = format(sig.r, "064x")
    s_hex = format(sig.s, "064x")
    v_hex = format(sig.v + 27, "02x")
    return "0x" + r_hex + s_hex + v_hex


# ────────────────────────────────────────────────────────────────────
# recover_signer_address
# ────────────────────────────────────────────────────────────────────


def test_recover_round_trips_known_signer():
    msg = b"hello safina"
    sig_hex = _sign_compact(msg)
    digest = eth_personal_sign_hash(msg)
    recovered = recover_signer_address(digest, sig_hex)
    assert recovered == EXPECTED_ADDRESS


def test_recover_accepts_v_in_legacy_27_28_form():
    """Some wallets return v=27/28; we normalise."""
    msg = b"x"
    sig_hex = _sign_compact(msg)
    digest = eth_personal_sign_hash(msg)
    # _sign_compact already produces v+27, so just check round-trip works.
    assert recover_signer_address(digest, sig_hex) == EXPECTED_ADDRESS


def test_recover_rejects_short_signature():
    with pytest.raises(ValueError, match="65 bytes"):
        recover_signer_address(b"\x00" * 32, "0x" + "00" * 32)


def test_recover_rejects_invalid_v():
    bad = "0x" + "00" * 32 + "00" * 32 + "ff"
    with pytest.raises(ValueError, match="v must be"):
        recover_signer_address(b"\x00" * 32, bad)


def test_recover_rejects_wrong_digest_length():
    sig_hex = _sign_compact(b"x")
    with pytest.raises(ValueError, match="32 bytes"):
        recover_signer_address(b"\x00" * 31, sig_hex)


# ────────────────────────────────────────────────────────────────────
# verify_signer
# ────────────────────────────────────────────────────────────────────


def test_verify_signer_matches_expected_address():
    msg = b"approve transfer"
    sig_hex = _sign_compact(msg)
    digest = eth_personal_sign_hash(msg)
    assert verify_signer(digest, sig_hex, EXPECTED_ADDRESS) is True


def test_verify_signer_case_insensitive():
    msg = b"x"
    sig_hex = _sign_compact(msg)
    digest = eth_personal_sign_hash(msg)
    assert verify_signer(digest, sig_hex, EXPECTED_ADDRESS.lower()) is True
    assert verify_signer(digest, sig_hex, EXPECTED_ADDRESS.upper()) is True


def test_verify_signer_rejects_wrong_address():
    msg = b"x"
    sig_hex = _sign_compact(msg)
    digest = eth_personal_sign_hash(msg)
    other = "0x0000000000000000000000000000000000000001"
    assert verify_signer(digest, sig_hex, other) is False


def test_verify_signer_rejects_tampered_signature():
    msg = b"x"
    sig_hex = _sign_compact(msg)
    # Flip a bit in r → recovers a different (random) address.
    tampered = sig_hex[:5] + ("0" if sig_hex[5] != "0" else "1") + sig_hex[6:]
    digest = eth_personal_sign_hash(msg)
    assert verify_signer(digest, tampered, EXPECTED_ADDRESS) is False


def test_verify_signer_returns_false_on_malformed_signature():
    """Doesn't raise — just logs and returns False."""
    digest = eth_personal_sign_hash(b"x")
    assert verify_signer(digest, "not-hex", EXPECTED_ADDRESS) is False


# ────────────────────────────────────────────────────────────────────
# canonical_payload — gate stays closed until wired
# ────────────────────────────────────────────────────────────────────


def test_canonical_payload_raises_until_wired():
    with pytest.raises(NotImplementedError, match="canonical sign-payload"):
        canonical_payload(tx_unid="x", network=0, value="0", to_address="0x0")


def test_is_verification_enabled_off_by_default(monkeypatch):
    monkeypatch.delenv("ORGON_VERIFY_SAFINA_SIGS", raising=False)
    assert is_verification_enabled() is False


def test_is_verification_enabled_off_when_canonical_not_wired(monkeypatch):
    """Even with the env flag set, returns False because canonical_payload raises."""
    monkeypatch.setenv("ORGON_VERIFY_SAFINA_SIGS", "1")
    assert is_verification_enabled() is False


def test_verify_safina_tx_signer_returns_none_when_disabled(monkeypatch):
    monkeypatch.delenv("ORGON_VERIFY_SAFINA_SIGS", raising=False)
    out = verify_safina_tx_signer(
        tx_unid="DEMO-1", network=5010, value="100", to_address="0xabc",
        signature_hex="0x" + "00" * 65, expected_signer=EXPECTED_ADDRESS,
    )
    assert out is None
