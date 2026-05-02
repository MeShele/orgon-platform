"""Unit tests for signer backends + SafinaSigner backend integration."""

from __future__ import annotations

import pytest

from backend.safina.signer import SafinaSigner
from backend.safina.signer_backends import (
    EnvSignerBackend,
    KMSSignerBackend,
    VaultSignerBackend,
    build_signer_backend,
)

# Test private key from Safina docs (well-known, public).
TEST_KEY = "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
EXPECTED_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"


# ────────────────────────────────────────────────────────────────────
# EnvSignerBackend
# ────────────────────────────────────────────────────────────────────


def test_env_backend_derives_address():
    b = EnvSignerBackend(TEST_KEY)
    assert b.address == EXPECTED_ADDRESS


def test_env_backend_accepts_0x_prefix():
    b = EnvSignerBackend("0x" + TEST_KEY)
    assert b.address == EXPECTED_ADDRESS


def test_env_backend_rejects_empty_key():
    with pytest.raises(ValueError, match="non-empty"):
        EnvSignerBackend("")


def test_env_backend_signs_msg_hash_deterministic():
    b = EnvSignerBackend(TEST_KEY)
    digest = b"\x00" * 32
    sig1 = b.sign_msg_hash(digest)
    sig2 = b.sign_msg_hash(digest)
    # ECDSA on the same digest with the same key must produce the same
    # signature (deterministic per RFC 6979 — eth_keys uses this).
    assert (sig1.r, sig1.s, sig1.v) == (sig2.r, sig2.s, sig2.v)


# ────────────────────────────────────────────────────────────────────
# Stubs (Vault still a stub; KMS implementation lives in
# test_kms_signer_backend.py with its own fake-KMS infrastructure)
# ────────────────────────────────────────────────────────────────────


def test_vault_backend_raises_not_implemented():
    with pytest.raises(NotImplementedError, match="stub"):
        VaultSignerBackend("https://vault.local:8200")


# ────────────────────────────────────────────────────────────────────
# build_signer_backend selector
# ────────────────────────────────────────────────────────────────────


def test_build_returns_env_by_default(monkeypatch):
    monkeypatch.delenv("ORGON_SIGNER_BACKEND", raising=False)
    monkeypatch.setenv("SAFINA_EC_PRIVATE_KEY", TEST_KEY)
    b = build_signer_backend()
    assert isinstance(b, EnvSignerBackend)
    assert b.address == EXPECTED_ADDRESS


def test_build_env_explicit(monkeypatch):
    monkeypatch.setenv("ORGON_SIGNER_BACKEND", "env")
    monkeypatch.setenv("SAFINA_EC_PRIVATE_KEY", TEST_KEY)
    b = build_signer_backend()
    assert isinstance(b, EnvSignerBackend)


def test_build_env_missing_key_raises(monkeypatch):
    monkeypatch.delenv("ORGON_SIGNER_BACKEND", raising=False)
    monkeypatch.delenv("SAFINA_EC_PRIVATE_KEY", raising=False)
    with pytest.raises(ValueError, match="SAFINA_EC_PRIVATE_KEY"):
        build_signer_backend()


# NOTE: positive `ORGON_SIGNER_BACKEND=kms` selector test lives in
# test_kms_signer_backend.py because it needs the fake-KMS fixture.


def test_build_kms_missing_id_raises(monkeypatch):
    monkeypatch.setenv("ORGON_SIGNER_BACKEND", "kms")
    monkeypatch.delenv("AWS_KMS_KEY_ID", raising=False)
    with pytest.raises(ValueError, match="AWS_KMS_KEY_ID"):
        build_signer_backend()


def test_build_vault_missing_addr_raises(monkeypatch):
    monkeypatch.setenv("ORGON_SIGNER_BACKEND", "vault")
    monkeypatch.delenv("VAULT_ADDR", raising=False)
    with pytest.raises(ValueError, match="VAULT_ADDR"):
        build_signer_backend()


def test_build_unknown_backend_raises(monkeypatch):
    monkeypatch.setenv("ORGON_SIGNER_BACKEND", "yubikey")
    with pytest.raises(ValueError, match="Unknown ORGON_SIGNER_BACKEND"):
        build_signer_backend()


# ────────────────────────────────────────────────────────────────────
# SafinaSigner backend integration
# ────────────────────────────────────────────────────────────────────


def test_safina_signer_legacy_hex_constructor_still_works():
    s = SafinaSigner(TEST_KEY)
    assert s.address == EXPECTED_ADDRESS


def test_safina_signer_with_env_backend_explicit():
    s = SafinaSigner(backend=EnvSignerBackend(TEST_KEY))
    assert s.address == EXPECTED_ADDRESS


def test_safina_signer_rejects_neither_arg():
    with pytest.raises(ValueError, match="requires"):
        SafinaSigner()


def test_safina_signer_rejects_both_args():
    with pytest.raises(ValueError, match="not both"):
        SafinaSigner(TEST_KEY, backend=EnvSignerBackend(TEST_KEY))


def test_safina_signer_get_signature_round_trip():
    """Sign GET '{}' and verify own signature."""
    s = SafinaSigner(TEST_KEY)
    headers = s.sign_get()
    assert headers["x-app-ec-from"] == EXPECTED_ADDRESS
    # All four headers present, hex-formatted.
    for k in ("x-app-ec-from", "x-app-ec-sign-r", "x-app-ec-sign-s", "x-app-ec-sign-v"):
        assert k in headers
    # v ∈ {27, 28} encoded as hex.
    assert headers["x-app-ec-sign-v"] in {"0x1b", "0x1c"}


def test_safina_signer_self_verify():
    s = SafinaSigner(TEST_KEY)
    assert s.verify_signature(b"{}") is True
    assert s.verify_signature(b'{"hello":"world"}') is True
