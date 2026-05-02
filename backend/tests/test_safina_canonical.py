"""Unit tests for the Safina canonical-payload variant registry
and the runtime verification dispatch (Wave 22, Story 2.7).

Round-trip coverage: for each variant, we sign a known payload with
an `eth_keys.PrivateKey` (the same primitive `SafinaSigner` uses on
our side), then verify that `try_all_variants` recovers the correct
signer. This proves the recovery chain is wired correctly even if
the live Safina format is none of these candidates yet.
"""

from __future__ import annotations

import os

import pytest
from eth_keys.datatypes import PrivateKey
from eth_keys import keys as eth_keys

from backend.safina import signature_verifier as sv


# ────────────────────────────────────────────────────────────────────
# Fixtures
# ────────────────────────────────────────────────────────────────────


@pytest.fixture
def env_isolated(monkeypatch):
    """Wipe the two env vars verifier reads so tests don't leak state."""
    for k in ("SAFINA_CANONICAL_VARIANT", "ORGON_SAFINA_VERIFY_MODE",
              "ORGON_VERIFY_SAFINA_SIGS"):
        monkeypatch.delenv(k, raising=False)
    yield monkeypatch


@pytest.fixture
def tx():
    """A canonical sample tx the variants build against."""
    return {
        "tx_unid": "abc123def456",
        "network": 1,
        "value": "1000000000000000000",
        "to_address": "0x" + "ab" * 20,
    }


@pytest.fixture
def keypair():
    """Deterministic test key — never used outside tests."""
    pk_bytes = bytes.fromhex("11" * 32)
    pk = eth_keys.PrivateKey(pk_bytes)
    return pk, pk.public_key.to_checksum_address()


def _sign_for_variant(variant: sv.CanonicalVariant, tx: dict, pk: PrivateKey) -> str:
    """Replicate the digest-then-sign flow we expect Safina to follow."""
    digest = sv._digest_for_variant(variant, tx)
    sig = pk.sign_msg_hash(digest)
    # eth_keys Signature.to_bytes() returns r||s||v (v ∈ {0,1}); we
    # bump v to {27,28} to match the convention `_parse_signature_hex`
    # accepts in production.
    raw = sig.to_bytes()
    v = raw[64]
    return "0x" + raw[:64].hex() + bytes([v + 27]).hex()


# ────────────────────────────────────────────────────────────────────
# Variant round-trips (one per variant)
# ────────────────────────────────────────────────────────────────────


@pytest.mark.parametrize("variant_name", list(sv.list_canonical_variants().keys()))
def test_variant_round_trip(variant_name, tx, keypair):
    """For each registered variant: sign on our side using the variant,
    then `try_all_variants` should mark THAT variant as the match."""
    pk, addr = keypair
    spec = sv.list_canonical_variants()[variant_name]
    sig_hex = _sign_for_variant(spec, tx, pk)

    results = sv.try_all_variants(
        tx_unid=tx["tx_unid"], network=tx["network"], value=tx["value"],
        to_address=tx["to_address"],
        signature_hex=sig_hex, expected_signer=addr,
    )
    assert results[variant_name] is True, (
        f"{variant_name} should match its own signing digest. "
        f"Full result map: {results}"
    )


def test_try_all_variants_reports_all_keys(tx, keypair):
    pk, addr = keypair
    sig = _sign_for_variant(sv.list_canonical_variants()["v1_pipe_unid_to_value"], tx, pk)
    results = sv.try_all_variants(
        tx_unid=tx["tx_unid"], network=tx["network"], value=tx["value"],
        to_address=tx["to_address"],
        signature_hex=sig, expected_signer=addr,
    )
    assert set(results.keys()) == set(sv.list_canonical_variants().keys())
    # Exactly one match — different variants produce different digests.
    matches = [k for k, v in results.items() if v]
    assert matches == ["v1_pipe_unid_to_value"]


# ────────────────────────────────────────────────────────────────────
# canonical_payload() dispatch
# ────────────────────────────────────────────────────────────────────


def test_canonical_payload_unset_raises(env_isolated, tx):
    """Pre-Wave-22 callers without env get the original NotImplementedError."""
    with pytest.raises(NotImplementedError):
        sv.canonical_payload(**tx)


def test_canonical_payload_explicit_variant_works(env_isolated, tx):
    out = sv.canonical_payload(**tx, variant="v1_pipe_unid_to_value")
    assert isinstance(out, bytes)
    assert b"abc123def456" in out


def test_canonical_payload_unknown_variant_raises_value_error(env_isolated, tx):
    with pytest.raises(ValueError, match="unknown canonical variant"):
        sv.canonical_payload(**tx, variant="v99_nonsense")


def test_canonical_payload_env_variant_is_used(env_isolated, tx):
    env_isolated.setenv("SAFINA_CANONICAL_VARIANT", "v2_pipe_unid_value_to_network")
    out = sv.canonical_payload(**tx)
    # v2 puts value before to_address.
    assert out.startswith(b"abc123def456|1000000000000000000|")


# ────────────────────────────────────────────────────────────────────
# get_verify_mode() — env parsing matrix
# ────────────────────────────────────────────────────────────────────


def test_get_verify_mode_off_default(env_isolated):
    assert sv.get_verify_mode() == "off"


def test_get_verify_mode_explicit_shadow(env_isolated):
    env_isolated.setenv("ORGON_SAFINA_VERIFY_MODE", "shadow")
    assert sv.get_verify_mode() == "shadow"


def test_get_verify_mode_explicit_enforce(env_isolated):
    env_isolated.setenv("ORGON_SAFINA_VERIFY_MODE", "enforce")
    assert sv.get_verify_mode() == "enforce"


def test_get_verify_mode_legacy_one_maps_to_enforce(env_isolated):
    env_isolated.setenv("ORGON_VERIFY_SAFINA_SIGS", "1")
    assert sv.get_verify_mode() == "enforce"


def test_get_verify_mode_invalid_falls_back_to_off(env_isolated):
    env_isolated.setenv("ORGON_SAFINA_VERIFY_MODE", "wat")
    assert sv.get_verify_mode() == "off"


def test_get_verify_mode_explicit_off_overrides_legacy(env_isolated):
    """If new var is `off` it wins, even if the legacy =1 is set."""
    env_isolated.setenv("ORGON_SAFINA_VERIFY_MODE", "off")
    env_isolated.setenv("ORGON_VERIFY_SAFINA_SIGS", "1")
    assert sv.get_verify_mode() == "off"


# ────────────────────────────────────────────────────────────────────
# is_verification_enabled / verify_safina_tx_signer
# ────────────────────────────────────────────────────────────────────


def test_verification_disabled_when_mode_off(env_isolated):
    env_isolated.setenv("SAFINA_CANONICAL_VARIANT", "v1_pipe_unid_to_value")
    assert sv.is_verification_enabled() is False


def test_verification_disabled_when_variant_unset(env_isolated):
    env_isolated.setenv("ORGON_SAFINA_VERIFY_MODE", "shadow")
    assert sv.is_verification_enabled() is False


def test_verification_enabled_when_both_set(env_isolated):
    env_isolated.setenv("ORGON_SAFINA_VERIFY_MODE", "shadow")
    env_isolated.setenv("SAFINA_CANONICAL_VARIANT", "v1_pipe_unid_to_value")
    assert sv.is_verification_enabled() is True


def test_verify_safina_tx_signer_returns_none_when_disabled(env_isolated, tx):
    out = sv.verify_safina_tx_signer(
        signature_hex="0x" + "00" * 65, expected_signer="0x" + "00" * 20, **tx,
    )
    assert out is None


def test_verify_safina_tx_signer_returns_true_on_match(env_isolated, tx, keypair):
    pk, addr = keypair
    env_isolated.setenv("ORGON_SAFINA_VERIFY_MODE", "enforce")
    env_isolated.setenv("SAFINA_CANONICAL_VARIANT", "v1_pipe_unid_to_value")
    spec = sv.list_canonical_variants()["v1_pipe_unid_to_value"]
    sig = _sign_for_variant(spec, tx, pk)
    out = sv.verify_safina_tx_signer(
        signature_hex=sig, expected_signer=addr, **tx,
    )
    assert out is True


def test_verify_safina_tx_signer_returns_false_on_wrong_address(env_isolated, tx, keypair):
    pk, _ = keypair
    env_isolated.setenv("ORGON_SAFINA_VERIFY_MODE", "shadow")
    env_isolated.setenv("SAFINA_CANONICAL_VARIANT", "v1_pipe_unid_to_value")
    spec = sv.list_canonical_variants()["v1_pipe_unid_to_value"]
    sig = _sign_for_variant(spec, tx, pk)
    # Signer is real but expected address is a different one.
    out = sv.verify_safina_tx_signer(
        signature_hex=sig, expected_signer="0x" + "ff" * 20, **tx,
    )
    assert out is False


# ────────────────────────────────────────────────────────────────────
# Pre-hashed variant edge cases
# ────────────────────────────────────────────────────────────────────


def test_v6_pre_hashed_marker_set():
    spec = sv.list_canonical_variants()["v6_keccak_pre_hashed"]
    assert spec.pre_hashed is True


def test_v5_binary_concat_round_trip(tx, keypair):
    """v5 needs a hex-string tx_unid — sanity-check it actually works."""
    pk, addr = keypair
    spec = sv.list_canonical_variants()["v5_concat_no_separator"]
    sig = _sign_for_variant(spec, tx, pk)
    results = sv.try_all_variants(
        tx_unid=tx["tx_unid"], network=tx["network"], value=tx["value"],
        to_address=tx["to_address"],
        signature_hex=sig, expected_signer=addr,
    )
    assert results["v5_concat_no_separator"] is True
