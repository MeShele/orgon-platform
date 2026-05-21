"""Live-AWS integration test for `KMSSignerBackend`.

Why this exists separately from `test_kms_signer_backend.py`:

* The unit tests use a hand-built in-process fake KMS (eth_keys +
  cryptography). They cover the ECDSA-recovery logic and the IEEE-
  P1363 vs DER signature conversion — but they assume the AWS API
  behaves a specific way. They cannot catch a divergence between
  what we expect from `kms:Sign` / `kms:GetPublicKey` and what real
  AWS sends back.
* `moto[kms]` would seem to fit, but `MessageType=DIGEST` on moto
  5.x silently re-hashes the input via SHA-256 — real AWS treats
  the input as the 32-byte digest verbatim. A pilot deploy that
  relied on moto-passing tests would fail on first live call.
* This file fills the gap: against a freshly-rotated KMS key in a
  sandbox AWS account, it runs the full round-trip — `sign` a
  random 32-byte digest, recover the address, verify against
  `get_public_key`. Closes TD-3 once green.

**Gating.** Skipped unless `ORGON_KMS_INTEGRATION=1` AND
`AWS_KMS_KEY_ID` is set. This means:
* A developer running `pytest backend/tests/` locally does NOT hit
  AWS (skipped).
* The CI job `.github/workflows/kms-integration.yml` sets the env
  via OIDC + repo vars, and the test runs against the real key.
* No credentials live in the repo; the OIDC role is provisioned by
  `infrastructure/terraform/kms-signer/main.tf`.

If/when the gate flips green, this becomes a CI deliverable for the
SOC-2 audit trail: "yes, our KMS signer works against real AWS, here
is the green CI run from <date>".
"""

from __future__ import annotations

import os

import pytest

from backend.safina.signer_backends import KMSSignerBackend


_INTEGRATION_ENABLED = os.getenv("ORGON_KMS_INTEGRATION", "").strip() == "1"
_KEY_ID = os.getenv("AWS_KMS_KEY_ID", "").strip()
_REGION = os.getenv("AWS_REGION", "eu-central-1").strip()

pytestmark = pytest.mark.skipif(
    not _INTEGRATION_ENABLED or not _KEY_ID,
    reason=(
        "Live KMS integration disabled. Set ORGON_KMS_INTEGRATION=1 "
        "and AWS_KMS_KEY_ID=<alias-or-arn> to enable. CI does this "
        "automatically when the OIDC role is configured."
    ),
)


def test_address_derives_from_kms_public_key():
    """Constructor pulls the public key via `kms:GetPublicKey` and
    derives the Ethereum-style address. A real key always derives a
    valid 0x-prefixed 40-hex address.
    """
    backend = KMSSignerBackend(key_id=_KEY_ID, region=_REGION)
    assert backend.address.startswith("0x")
    assert len(backend.address) == 42, "expected 0x + 40 hex"
    # Address must round-trip under EIP-55 — checksum mixed-case is
    # how `eth_keys` returns it. Any all-lower or all-upper would
    # signal a derivation bug.
    assert backend.address != backend.address.lower(), (
        "address should be EIP-55 checksum (mixed case)"
    )


def test_sign_round_trip_recovers_to_same_address():
    """Sign a fixed 32-byte digest, recover the signer from the
    returned (r, s, v), and confirm it matches the key's address.
    This is the production code path — same `sign_msg_hash` call the
    Safina request signer uses.
    """
    backend = KMSSignerBackend(key_id=_KEY_ID, region=_REGION)

    # Fixed digest so the test is deterministic against the same
    # key. Value chosen arbitrarily — any 32 bytes works.
    digest = b"\x42" * 32

    sig = backend.sign_msg_hash(digest)

    # Signature fields should be valid integers in the secp256k1 range.
    _SECP_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    assert 1 <= sig.r < _SECP_N
    assert 1 <= sig.s < _SECP_N
    assert sig.v in (0, 1), f"v should be 0 or 1 after recovery, got {sig.v}"

    # Recover and compare. eth_keys.Signature has
    # recover_public_key_from_msg_hash; address derivation matches
    # what KMSSignerBackend.__init__ computed for `.address`.
    pubkey = sig.recover_public_key_from_msg_hash(digest)
    recovered = pubkey.to_checksum_address()
    assert recovered.lower() == backend.address.lower(), (
        f"recovered address {recovered} ≠ key address {backend.address}"
    )


def test_low_s_signature_normalization():
    """BIP-62 requires low-s (s ≤ n/2). AWS KMS may emit either
    form; `KMSSignerBackend` should always normalise. Without
    normalisation, downstream Ethereum tooling rejects.
    """
    _SECP_HALF_N = (
        0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
    ) // 2

    backend = KMSSignerBackend(key_id=_KEY_ID, region=_REGION)
    # Try a handful of different digests — at least one will land in
    # the high-s territory before normalisation, exercising the flip.
    for i in range(8):
        digest = (str(i) * 32).encode()[:32].ljust(32, b"\x00")
        sig = backend.sign_msg_hash(digest)
        assert sig.s <= _SECP_HALF_N, (
            f"digest #{i} produced non-canonical s={sig.s} (must be <= n/2). "
            f"KMSSignerBackend low-s normalisation broken?"
        )
