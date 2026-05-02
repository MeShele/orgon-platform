"""Pluggable signer backends for SafinaSigner.

The signing key for Safina Pay must, in production, live outside the
application process. This module defines a small `SignerBackend`
protocol and three implementations:

* `EnvSignerBackend`  — key in env var. Process holds it in memory.
                        Acceptable for dev / preview / single-org pilots.
                        **Unacceptable for institutional custody** —
                        the key is in /proc memory and any RCE / crash
                        dump leaks it.
* `KMSSignerBackend`  — AWS KMS asymmetric key (ECC_SECG_P256K1).
                        Stub. The host process never sees the key — KMS
                        does the signing and returns DER ECDSA. We
                        recover v locally by trying both candidates.
* `VaultSignerBackend` — HashiCorp Vault Transit engine (ecdsa-p256k1).
                        Stub. Same shape as KMS.

The selector `build_signer_backend()` reads `ORGON_SIGNER_BACKEND`
(default `env`) and constructs the appropriate backend.

Future-proofing: every backend exposes the same `(address, sign_msg_hash)`
interface, so SafinaSigner is decoupled from where the key actually lives.
"""

from __future__ import annotations

import logging
import os
from typing import Protocol

from eth_keys import keys
from eth_keys.datatypes import Signature

logger = logging.getLogger("orgon.safina.signer_backends")


# ────────────────────────────────────────────────────────────────────
# Constants & helpers used by KMS / Vault backends
# ────────────────────────────────────────────────────────────────────

# secp256k1 curve order. ECDSA signatures with `s > n/2` are non-canonical
# under BIP-62. Most Ethereum tooling rejects high-s. AWS KMS may emit
# either form, so we always normalise to low-s before doing v-recovery.
_SECP256K1_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
_SECP256K1_HALF_N = _SECP256K1_N // 2


def _normalize_low_s(s: int) -> int:
    """Return canonical low-s (BIP-62). If s > n/2, flip to n - s."""
    return _SECP256K1_N - s if s > _SECP256K1_HALF_N else s


def _der_to_raw_pubkey(der_bytes: bytes) -> bytes:
    """Decode DER SubjectPublicKeyInfo → 64-byte raw uncompressed (x || y).

    AWS KMS returns the public key in `SubjectPublicKeyInfo` DER form
    (RFC 5480). We need the uncompressed coordinates as a flat 64-byte
    buffer because `eth_keys.PublicKey(...)` and keccak-based address
    derivation expect that layout.

    Raises:
        ValueError: not an EC public key, or curve != secp256k1.
    """
    # Lazy import — `cryptography` is already installed transitively via
    # python-jose[cryptography]; only pay the import cost on backends
    # that actually need DER work.
    from cryptography.hazmat.primitives.asymmetric.ec import (
        EllipticCurvePublicKey,
        SECP256K1,
    )
    from cryptography.hazmat.primitives.serialization import load_der_public_key

    pub = load_der_public_key(der_bytes)
    if not isinstance(pub, EllipticCurvePublicKey):
        raise ValueError(
            f"Expected EC public key, got {type(pub).__name__}"
        )
    if not isinstance(pub.curve, SECP256K1):
        raise ValueError(
            f"Expected SECP256K1 curve, got {pub.curve.name!r}; "
            "KMS key spec must be ECC_SECG_P256K1"
        )
    nums = pub.public_numbers()
    return nums.x.to_bytes(32, "big") + nums.y.to_bytes(32, "big")


# ────────────────────────────────────────────────────────────────────
# Protocol
# ────────────────────────────────────────────────────────────────────


class SignerBackend(Protocol):
    """Minimal interface a signing backend must expose.

    `sign_msg_hash` returns an `eth_keys.datatypes.Signature` so that
    SafinaSigner can call `.recover_public_key_from_msg_hash` on it for
    self-verification. KMS / Vault stubs build the Signature from raw
    (r, s, v) in their respective implementations.
    """

    @property
    def address(self) -> str:
        ...

    def sign_msg_hash(self, msg_hash: bytes) -> Signature:
        ...


# ────────────────────────────────────────────────────────────────────
# Env backend (current production path)
# ────────────────────────────────────────────────────────────────────


class EnvSignerBackend:
    """Holds the EC private key in process memory.

    `private_key_hex` may be provided with or without a leading `0x`.
    """

    def __init__(self, private_key_hex: str):
        if not private_key_hex:
            raise ValueError("EnvSignerBackend requires a non-empty private key")
        key_bytes = bytes.fromhex(private_key_hex.removeprefix("0x"))
        self._key = keys.PrivateKey(key_bytes)
        self._address = self._key.public_key.to_checksum_address()

    @property
    def address(self) -> str:
        return self._address

    def sign_msg_hash(self, msg_hash: bytes) -> Signature:
        return self._key.sign_msg_hash(msg_hash)


# ────────────────────────────────────────────────────────────────────
# KMS backend stub
# ────────────────────────────────────────────────────────────────────


class KMSSignerBackend:
    """AWS KMS asymmetric SECP256K1 signer.

    The private key is generated and held by AWS KMS (HSM-backed). It
    NEVER leaves KMS — even our process can't read it. We send a 32-byte
    digest, KMS signs, returns DER-encoded `(r, s)`. We recover `v`
    locally by trying both candidates against a public key fetched once
    at boot.

    For institutional custody this is the minimum acceptable signer
    posture: RCE / container escape / crash dump in ORGON cannot leak
    the key, only signing access (which is itself revocable via IAM).

    Configuration (env vars read by `build_signer_backend`):

        ORGON_SIGNER_BACKEND=kms
        AWS_KMS_KEY_ID=<key-id | arn | alias/name>
        AWS_REGION=eu-central-1                   (or wherever the key lives)
        AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY  (standard boto3 chain)

    AWS-side setup:

        1. Create the key:
             aws kms create-key \\
                 --key-spec ECC_SECG_P256K1 \\
                 --key-usage SIGN_VERIFY \\
                 --description "ORGON Safina signer"
        2. Attach an IAM policy granting ONLY this principal these
           actions on this exact key ARN:  kms:Sign, kms:GetPublicKey.
        3. (recommended) Set up KMS key alias, e.g.
             aws kms create-alias --alias-name alias/orgon-safina --target-key-id <key-id>
        4. (recommended) Enable CloudTrail logging for the key.

    Boot semantics — fail fast:

        `__init__` performs `kms.get_public_key(KeyId)` synchronously
        and derives the Ethereum-style checksum address. Any error
        (network, IAM denied, wrong key spec, malformed DER) propagates
        out — caller (`build_signer_backend`) does NOT swallow them.
        Result: ORGON refuses to start with a broken signer.

    Sign semantics:

        Returns `eth_keys.datatypes.Signature` with v ∈ {0, 1} and
        canonical low-s, identical in shape to what `EnvSignerBackend`
        returns. `SafinaSigner` adds 27 to v at the header layer.
    """

    def __init__(self, key_id: str, region: str = "eu-central-1") -> None:
        if not key_id:
            raise ValueError("KMSSignerBackend requires a non-empty key_id")

        # Lazy boto3 import: only required when this backend is selected,
        # so env-only deployments don't pay the import time / memory.
        import boto3
        from botocore.config import Config

        self._key_id = key_id
        self._region = region
        self._kms = boto3.client(
            "kms",
            region_name=region,
            config=Config(
                retries={"max_attempts": 3, "mode": "adaptive"},
                connect_timeout=5,
                read_timeout=10,
            ),
        )

        # Bootstrap: fetch public key once. This call validates KMS
        # reachability, IAM permissions, and key spec all at once.
        # Any error short-circuits process startup (fail-fast per ADR-3).
        resp = self._kms.get_public_key(KeyId=key_id)
        der = resp["PublicKey"]
        self._public_key_bytes = _der_to_raw_pubkey(der)
        self._address = keys.PublicKey(self._public_key_bytes).to_checksum_address()

        logger.info(
            "KMSSignerBackend initialised: address=%s key_id=%s region=%s",
            self._address, self._key_id, self._region,
        )

    @property
    def address(self) -> str:
        return self._address

    def sign_msg_hash(self, msg_hash: bytes) -> Signature:
        """Sign a 32-byte digest via AWS KMS.

        Args:
            msg_hash: 32-byte keccak digest (already prefixed with the
                Ethereum personal-sign magic by SafinaSigner).

        Returns:
            `Signature` with v ∈ {0, 1} and canonical low-s.

        Raises:
            ValueError: msg_hash is not exactly 32 bytes.
            botocore.exceptions.ClientError: any KMS-side error, surfaced
                as-is. Caller (SafinaClient) decides retry policy.
            RuntimeError: v-recovery failed — neither v=0 nor v=1 matched
                the bootstrap public key. This is a critical bug
                signalling DER-parse mismatch or wrong key spec.
        """
        if len(msg_hash) != 32:
            raise ValueError(
                f"msg_hash must be 32 bytes, got {len(msg_hash)}"
            )

        # KMS signs the digest as-is when MessageType=DIGEST. The
        # SigningAlgorithm name says ECDSA_SHA_256 but with DIGEST mode
        # the SHA-256 is NOT applied again — KMS treats the input as the
        # 32-byte digest directly. (Critical: any other MessageType would
        # double-hash with SHA-256 instead of using our keccak digest.)
        resp = self._kms.sign(
            KeyId=self._key_id,
            Message=msg_hash,
            MessageType="DIGEST",
            SigningAlgorithm="ECDSA_SHA_256",
        )

        # DER-decoded r, s (ints).
        from cryptography.hazmat.primitives.asymmetric.utils import (
            decode_dss_signature,
        )

        r, s = decode_dss_signature(resp["Signature"])
        s = _normalize_low_s(s)

        # v-recovery: KMS does not return the recovery id. Try both
        # candidates and pick the one whose recovered public key
        # matches our cached bootstrap pubkey (ADR-6).
        for v in (0, 1):
            sig = Signature(vrs=(v, r, s))
            try:
                recovered = sig.recover_public_key_from_msg_hash(msg_hash).to_bytes()
            except Exception:  # pragma: no cover — defensive
                continue
            if recovered == self._public_key_bytes:
                return sig

        # Both v=0 and v=1 failed. This is unreachable under correct
        # operation — surfacing as RuntimeError makes the diagnostic
        # explicit instead of silently returning a bad signature.
        raise RuntimeError(
            f"KMS v-recovery failed for key_id={self._key_id!r}: "
            "neither v=0 nor v=1 produced the bootstrap public key. "
            "Likely DER-parse mismatch or wrong KMS key spec "
            "(must be ECC_SECG_P256K1)."
        )


# ────────────────────────────────────────────────────────────────────
# Vault backend stub
# ────────────────────────────────────────────────────────────────────


class VaultSignerBackend:
    """HashiCorp Vault Transit engine-backed signer — stub.

    Setup checklist when wiring real Vault:

    1. **Enable Transit.** `vault secrets enable transit`.
    2. **Create the key.** `vault write -f transit/keys/safina-ec
       type=ecdsa-p256k1 derived=false exportable=false
       allow_plaintext_backup=false`. The key never leaves Vault.
    3. **Policy + token.** Create a policy granting
       `transit/sign/safina-ec` and `transit/keys/safina-ec/read`
       (for the public key on bootstrap). Issue a service token
       (preferably AppRole-bound) and pass via `VAULT_TOKEN` env.
    4. **Bootstrap address.** `transit/keys/safina-ec` returns the
       public key in PEM. Parse, extract raw 64-byte public key,
       keccak256, last 20 bytes → checksum address.
    5. **Sign.** `transit/sign/safina-ec` with
       `hash_input=base64(msg_hash)`, `prehashed=true`,
       `signature_algorithm='ecdsa'`. Response is
       `vault:v1:<base64-DER-sig>`. Strip the prefix, base64 decode,
       DER decode → (r, s). Same v-recovery as KMS.

    Reference: https://developer.hashicorp.com/vault/api-docs/secret/transit
    """

    def __init__(
        self,
        vault_addr: str,
        key_name: str = "safina-ec",
        token: str | None = None,
    ):
        raise NotImplementedError(
            "VaultSignerBackend is a stub — see signer_backends.py docstring "
            "for the wiring checklist. addr=%r key=%r." % (vault_addr, key_name)
        )

    @property
    def address(self) -> str:  # pragma: no cover — stub
        raise NotImplementedError

    def sign_msg_hash(self, msg_hash: bytes) -> Signature:  # pragma: no cover — stub
        raise NotImplementedError


# ────────────────────────────────────────────────────────────────────
# Selector
# ────────────────────────────────────────────────────────────────────


def build_signer_backend() -> SignerBackend:
    """Construct the configured signer backend.

    Driven by `ORGON_SIGNER_BACKEND` (default: `env`).

    | value   | required env                                        |
    | ------- | --------------------------------------------------- |
    | `env`   | `SAFINA_EC_PRIVATE_KEY`                             |
    | `kms`   | `AWS_KMS_KEY_ID` (+ standard AWS auth)              |
    | `vault` | `VAULT_ADDR`, `VAULT_KEY_NAME`, optionally `VAULT_TOKEN` |

    Raises `ValueError` for unknown backends or missing config.
    """
    backend = os.getenv("ORGON_SIGNER_BACKEND", "env").lower().strip()

    if backend == "env":
        key = os.getenv("SAFINA_EC_PRIVATE_KEY", "")
        if not key:
            raise ValueError(
                "SAFINA_EC_PRIVATE_KEY is required when ORGON_SIGNER_BACKEND=env "
                "(or unset, since env is the default backend)"
            )
        logger.warning(
            "Signer backend = env; private key in process memory. "
            "Switch to KMS/Vault for institutional production."
        )
        return EnvSignerBackend(key)

    if backend == "kms":
        key_id = os.environ.get("AWS_KMS_KEY_ID")
        if not key_id:
            raise ValueError("AWS_KMS_KEY_ID required for ORGON_SIGNER_BACKEND=kms")
        return KMSSignerBackend(
            key_id=key_id,
            region=os.getenv("AWS_REGION", "eu-central-1"),
        )

    if backend == "vault":
        addr = os.environ.get("VAULT_ADDR")
        if not addr:
            raise ValueError("VAULT_ADDR required for ORGON_SIGNER_BACKEND=vault")
        return VaultSignerBackend(
            vault_addr=addr,
            key_name=os.getenv("VAULT_KEY_NAME", "safina-ec"),
            token=os.getenv("VAULT_TOKEN"),
        )

    raise ValueError(
        f"Unknown ORGON_SIGNER_BACKEND={backend!r}; "
        "expected one of: env, kms, vault"
    )
