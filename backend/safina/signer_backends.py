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
    """AWS KMS asymmetric SECP256K1 key — stub.

    Setup checklist when wiring real KMS:

    1. **Create the KMS key.** `aws kms create-key --key-spec
       ECC_SECG_P256K1 --key-usage SIGN_VERIFY`. Note the KeyId.
    2. **Grant the backend role.** Attach a policy allowing
       `kms:Sign` and `kms:GetPublicKey` on the KeyId. The IAM role
       itself MUST have nothing else — never share the role with
       other workloads.
    3. **Bootstrap address.** On startup, call
       `kms.get_public_key(KeyId)`, decode the DER SubjectPublicKeyInfo,
       extract the raw 64-byte public key, run keccak256 on it, take
       the last 20 bytes → checksum address.
    4. **Sign.** `kms.sign(KeyId, Message=msg_hash,
       MessageType='DIGEST', SigningAlgorithm='ECDSA_SHA_256')`. KMS
       returns DER-encoded `(r, s)` — decode with
       `cryptography.hazmat.primitives.asymmetric.utils.decode_dss_signature`.
    5. **Recover v.** ECDSA recovery id is NOT returned by KMS. Try
       both `v=27` and `v=28`, build a `Signature(vrs=(v-27, r, s))`,
       call `recover_public_key_from_msg_hash(msg_hash)`, compare
       against the bootstrap address. Use whichever matches.
    6. **Low-s normalisation.** KMS may return high-s (>= n/2). Most
       Ethereum tooling rejects this — normalise to canonical low-s
       per BIP-62 before recovery.

    Reference: https://docs.aws.amazon.com/kms/latest/developerguide/asymmetric-key-specs.html
    """

    def __init__(self, key_id: str, region: str = "eu-central-1"):
        raise NotImplementedError(
            "KMSSignerBackend is a stub — see signer_backends.py docstring "
            "for the wiring checklist. KeyId %r region %r." % (key_id, region)
        )

    @property
    def address(self) -> str:  # pragma: no cover — stub
        raise NotImplementedError

    def sign_msg_hash(self, msg_hash: bytes) -> Signature:  # pragma: no cover — stub
        raise NotImplementedError


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
