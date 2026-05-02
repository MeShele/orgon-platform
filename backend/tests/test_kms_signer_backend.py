"""Unit tests for `KMSSignerBackend`.

We don't use moto[kms] here even though it would seem the natural fit:
moto 5.2.0's KMS sign emulation has a bug where `MessageType=DIGEST`
still re-hashes the Message through SHA-256, while the real AWS KMS
treats DIGEST as "use the input as the 32-byte digest verbatim". Tests
written against moto would either fail or require warping production
code to match the bug. Instead we wire a tiny in-process fake KMS
client built on `eth_keys.PrivateKey` and `cryptography` — it matches
real AWS KMS behaviour exactly, and we get to assert against a known
keypair (deterministic addresses for stable assertions).

The fake intercepts only the two boto3 KMS APIs we use:
`get_public_key` and `sign`. Everything else is left undefined — if
the production code starts calling other KMS APIs, tests fail loudly.
"""

from __future__ import annotations

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import encode_dss_signature
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    PublicFormat,
)
from eth_keys import keys as eth_keys
from eth_keys.datatypes import Signature

from backend.safina.signer_backends import (
    KMSSignerBackend,
    _SECP256K1_HALF_N,
    _SECP256K1_N,
    _der_to_raw_pubkey,
    _normalize_low_s,
    build_signer_backend,
)


# Test private key reused from test_signer_backends.py for parity.
TEST_KEY_HEX = "ac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
EXPECTED_ADDRESS = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"


# ────────────────────────────────────────────────────────────────────
# Fake KMS client — two-method drop-in for boto3.client("kms")
# ────────────────────────────────────────────────────────────────────


class _FakeKmsClient:
    """In-memory KMS emulator backed by a real `eth_keys.PrivateKey`.

    Behaves like `boto3.client("kms")` for the two methods we touch:
    `get_public_key(KeyId=...)` and `sign(KeyId=..., Message=...,
    MessageType="DIGEST", SigningAlgorithm="ECDSA_SHA_256")`.

    Faithful to AWS KMS:
      - DIGEST mode signs the input as-is; no re-hashing.
      - Returns ECDSA signature in DER form.
      - GetPublicKey returns SubjectPublicKeyInfo DER (RFC 5480),
        which is what `cryptography.serialization.load_der_public_key`
        consumes — same path real KMS responses take through our code.
    """

    def __init__(
        self,
        private_key_hex: str = TEST_KEY_HEX,
        force_high_s: bool = False,
    ):
        self._eth_pk = eth_keys.PrivateKey(bytes.fromhex(private_key_hex))
        # Build matching cryptography EC private key for DER pubkey export
        # and DER signature emission.
        priv_int = int.from_bytes(self._eth_pk.to_bytes(), "big")
        self._crypto_priv = ec.derive_private_key(priv_int, ec.SECP256K1())
        self._force_high_s = force_high_s

    # boto3 KMS API ----------------------------------------------------

    def get_public_key(self, *, KeyId: str) -> dict:
        der = self._crypto_priv.public_key().public_bytes(
            Encoding.DER, PublicFormat.SubjectPublicKeyInfo
        )
        return {"PublicKey": der, "KeyId": KeyId, "KeySpec": "ECC_SECG_P256K1"}

    def sign(
        self,
        *,
        KeyId: str,
        Message: bytes,
        MessageType: str,
        SigningAlgorithm: str,
    ) -> dict:
        # Real AWS KMS contract: with MessageType=DIGEST the input is
        # already a digest — KMS signs it as-is.
        if MessageType != "DIGEST":
            raise NotImplementedError(
                f"FakeKmsClient only implements DIGEST mode, got {MessageType!r}"
            )
        if SigningAlgorithm != "ECDSA_SHA_256":
            raise NotImplementedError(
                f"FakeKmsClient only implements ECDSA_SHA_256, got {SigningAlgorithm!r}"
            )
        if len(Message) != 32:
            raise ValueError(f"DIGEST mode requires 32-byte input, got {len(Message)}")

        # Sign with eth_keys (deterministic RFC 6979) — gives us low-s.
        sig = self._eth_pk.sign_msg_hash(Message)
        r, s = sig.r, sig.s
        if self._force_high_s:
            # Flip s to its high counterpart to exercise our normaliser.
            s = _SECP256K1_N - s
            assert s > _SECP256K1_HALF_N

        der = encode_dss_signature(r, s)
        return {"Signature": der, "KeyId": KeyId, "SigningAlgorithm": SigningAlgorithm}


@pytest.fixture
def fake_kms(monkeypatch):
    """Replace `boto3.client` so any KMSSignerBackend instantiated under
    this fixture talks to our in-process fake KMS instead.
    """
    fake = _FakeKmsClient()

    def _factory(service_name, **kwargs):
        if service_name != "kms":
            raise RuntimeError(
                f"Tests only mock 'kms' boto3 client, got {service_name!r}"
            )
        return fake

    import boto3

    monkeypatch.setattr(boto3, "client", _factory)
    return fake


@pytest.fixture
def fake_kms_high_s(monkeypatch):
    """Same as `fake_kms` but flips every signature to high-s so the
    low-s normaliser inside KMSSignerBackend is exercised."""
    fake = _FakeKmsClient(force_high_s=True)

    def _factory(service_name, **kwargs):
        return fake

    import boto3

    monkeypatch.setattr(boto3, "client", _factory)
    return fake


# ────────────────────────────────────────────────────────────────────
# DER + low-s helpers
# ────────────────────────────────────────────────────────────────────


def test_der_to_raw_pubkey_roundtrip():
    """Round-trip: known eth address → derive pubkey → DER export →
    decode through our helper → 64-byte raw matches eth_keys raw."""
    pk = eth_keys.PrivateKey(bytes.fromhex(TEST_KEY_HEX))
    expected_raw = pk.public_key.to_bytes()  # 64 bytes (x || y)

    priv_int = int.from_bytes(pk.to_bytes(), "big")
    crypto_priv = ec.derive_private_key(priv_int, ec.SECP256K1())
    der = crypto_priv.public_key().public_bytes(
        Encoding.DER, PublicFormat.SubjectPublicKeyInfo
    )

    raw = _der_to_raw_pubkey(der)
    assert raw == expected_raw
    assert len(raw) == 64


def test_der_to_raw_pubkey_rejects_non_secp256k1():
    """A NIST P-256 key's DER must be rejected — wrong curve."""
    nist_priv = ec.generate_private_key(ec.SECP256R1())
    der = nist_priv.public_key().public_bytes(
        Encoding.DER, PublicFormat.SubjectPublicKeyInfo
    )
    with pytest.raises(ValueError, match="SECP256K1"):
        _der_to_raw_pubkey(der)


def test_der_to_raw_pubkey_rejects_non_ec():
    """An RSA key DER must be rejected — wrong key type."""
    from cryptography.hazmat.primitives.asymmetric import rsa

    rsa_priv = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    der = rsa_priv.public_key().public_bytes(
        Encoding.DER, PublicFormat.SubjectPublicKeyInfo
    )
    with pytest.raises(ValueError, match="EC public key"):
        _der_to_raw_pubkey(der)


def test_normalize_low_s_passthrough_for_low():
    """Already-low s stays as-is."""
    assert _normalize_low_s(1) == 1
    assert _normalize_low_s(_SECP256K1_HALF_N) == _SECP256K1_HALF_N


def test_normalize_low_s_flips_high():
    """High s gets reflected to n - s."""
    high = _SECP256K1_N - 1
    assert _normalize_low_s(high) == 1
    just_above = _SECP256K1_HALF_N + 1
    assert _normalize_low_s(just_above) == _SECP256K1_N - just_above


# ────────────────────────────────────────────────────────────────────
# KMSSignerBackend — init & address derivation
# ────────────────────────────────────────────────────────────────────


def test_init_rejects_empty_key_id():
    with pytest.raises(ValueError, match="non-empty key_id"):
        KMSSignerBackend("")


def test_init_derives_known_address(fake_kms):
    """Bootstrap address must match the well-known address for our test key."""
    b = KMSSignerBackend("alias/orgon-test", region="eu-central-1")
    assert b.address == EXPECTED_ADDRESS


def test_init_caches_public_key_bytes(fake_kms):
    """We rely on cached pubkey for v-recovery."""
    b = KMSSignerBackend("alias/orgon-test", region="eu-central-1")
    expected = eth_keys.PrivateKey(bytes.fromhex(TEST_KEY_HEX)).public_key.to_bytes()
    assert b._public_key_bytes == expected
    assert len(b._public_key_bytes) == 64


# ────────────────────────────────────────────────────────────────────
# KMSSignerBackend — sign_msg_hash semantics
# ────────────────────────────────────────────────────────────────────


def test_sign_msg_hash_round_trip(fake_kms):
    """sign → recover → must equal the bootstrap address."""
    b = KMSSignerBackend("alias/orgon-test")
    msg_hash = b"\x42" * 32
    sig = b.sign_msg_hash(msg_hash)
    assert isinstance(sig, Signature)
    recovered_addr = sig.recover_public_key_from_msg_hash(msg_hash).to_checksum_address()
    assert recovered_addr == b.address


def test_sign_msg_hash_v_in_zero_or_one(fake_kms):
    """SafinaSigner adds 27 to v at the header layer; backend returns 0/1."""
    b = KMSSignerBackend("alias/orgon-test")
    sig = b.sign_msg_hash(b"\x00" * 32)
    assert sig.v in (0, 1)


def test_sign_msg_hash_canonical_low_s_when_kms_returns_high_s(fake_kms_high_s):
    """Even when KMS hands back a high-s signature, we must emit low-s."""
    b = KMSSignerBackend("alias/orgon-test")
    # Probe several digests so we exercise the normaliser repeatedly.
    for i in range(8):
        sig = b.sign_msg_hash(bytes([i]) * 32)
        assert sig.s <= _SECP256K1_HALF_N
        # And the signature must STILL recover correctly post-normalisation.
        recovered = sig.recover_public_key_from_msg_hash(bytes([i]) * 32).to_checksum_address()
        assert recovered == b.address


def test_sign_msg_hash_validates_length(fake_kms):
    b = KMSSignerBackend("alias/orgon-test")
    with pytest.raises(ValueError, match="32 bytes"):
        b.sign_msg_hash(b"\x00" * 31)
    with pytest.raises(ValueError, match="32 bytes"):
        b.sign_msg_hash(b"\x00" * 33)


def test_v_recovery_failure_path(fake_kms, monkeypatch):
    """If KMS returns a signature for a *different* key from the one we
    bootstrapped with, v-recovery must fail loudly (not silently emit
    a wrong-address signature)."""
    b = KMSSignerBackend("alias/orgon-test")

    # Swap the fake's private key out for a different one so subsequent
    # signs no longer match the cached pubkey.
    other_pk = eth_keys.PrivateKey(b"\x01" * 32)
    fake_kms._eth_pk = other_pk
    other_priv_int = int.from_bytes(other_pk.to_bytes(), "big")
    fake_kms._crypto_priv = ec.derive_private_key(other_priv_int, ec.SECP256K1())

    with pytest.raises(RuntimeError, match="v-recovery failed"):
        b.sign_msg_hash(b"\x77" * 32)


# ────────────────────────────────────────────────────────────────────
# End-to-end with SafinaSigner
# ────────────────────────────────────────────────────────────────────


def test_kms_backend_produces_valid_safina_headers(fake_kms):
    """Through the full SafinaSigner stack: sign GET '{}', verify
    headers + self-verification round-trip."""
    from backend.safina.signer import SafinaSigner

    signer = SafinaSigner(backend=KMSSignerBackend("alias/orgon-test"))
    headers = signer.sign_get()
    assert headers["x-app-ec-from"] == EXPECTED_ADDRESS
    assert headers["x-app-ec-sign-v"] in {"0x1b", "0x1c"}
    for key in ("x-app-ec-sign-r", "x-app-ec-sign-s"):
        assert headers[key].startswith("0x")
    assert signer.verify_signature(b"{}") is True


def test_kms_backend_signature_matches_env_backend(fake_kms):
    """Two backends, same key → SafinaSigner.address must match. Sign
    output isn't bit-identical (KMS path goes through DER + recovery)
    but address recovery and verify_signature must hold for both."""
    from backend.safina.signer import SafinaSigner
    from backend.safina.signer_backends import EnvSignerBackend

    env_signer = SafinaSigner(backend=EnvSignerBackend(TEST_KEY_HEX))
    kms_signer = SafinaSigner(backend=KMSSignerBackend("alias/orgon-test"))
    assert env_signer.address == kms_signer.address == EXPECTED_ADDRESS
    assert env_signer.verify_signature(b"{}") is True
    assert kms_signer.verify_signature(b"{}") is True


# ────────────────────────────────────────────────────────────────────
# build_signer_backend selector with kms backend
# ────────────────────────────────────────────────────────────────────


def test_build_signer_backend_kms_constructs_real_backend(fake_kms, monkeypatch):
    """With ORGON_SIGNER_BACKEND=kms and AWS_KMS_KEY_ID set, the
    selector must return a fully-initialised KMSSignerBackend (not the
    old NotImplementedError stub)."""
    monkeypatch.setenv("ORGON_SIGNER_BACKEND", "kms")
    monkeypatch.setenv("AWS_KMS_KEY_ID", "alias/orgon-test")
    monkeypatch.setenv("AWS_REGION", "eu-central-1")
    backend = build_signer_backend()
    assert isinstance(backend, KMSSignerBackend)
    assert backend.address == EXPECTED_ADDRESS


def test_build_signer_backend_kms_missing_key_id_raises(monkeypatch):
    monkeypatch.setenv("ORGON_SIGNER_BACKEND", "kms")
    monkeypatch.delenv("AWS_KMS_KEY_ID", raising=False)
    with pytest.raises(ValueError, match="AWS_KMS_KEY_ID"):
        build_signer_backend()
