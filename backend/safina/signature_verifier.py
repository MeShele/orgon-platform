"""Local verification of Safina-returned EC signatures.

When Safina returns a signed transaction, the response includes a list
of signers (`ecaddress` + `ecsign` per signer). Today we **trust**
that data — if Safina is compromised or buggy, we'd accept attacker-
forged signers as valid co-signers on a multi-sig.

This module gives us the primitive to verify those signatures locally:
recover the EC public key from `ecsign`, derive the address, compare
against the claimed `ecaddress`.

**Important caveat — canonical payload format.** ECDSA recovery
requires knowing the exact bytes that were hashed. Multi-sig
participants in Safina sign a canonical representation of the
transaction, but the precise format (field order, separator, encoding)
is part of Safina's protocol and must be confirmed against their
documentation before turning verification on in production.

This file therefore exposes:

* `recover_signer_address(message_hash, signature_hex)` — pure
  primitive. Given a 32-byte digest and `r||s||v` hex, returns the
  recovered checksum address. No assumptions about the message format.
* `verify_signer(message_hash, signature_hex, expected_address)` —
  recover and compare. Returns True/False.

The wire-up point in `transaction_service.sync_transactions` is left
explicitly OFF until the canonical payload format is confirmed.
Setting `ORGON_VERIFY_SAFINA_SIGS=1` will activate verification once
`canonical_payload(tx)` (below) is implemented correctly. Until then
the function raises `NotImplementedError` with a clear message.
"""

from __future__ import annotations

import logging
import os
from typing import Optional

from eth_hash.auto import keccak
from eth_keys.datatypes import PublicKey, Signature

logger = logging.getLogger("orgon.safina.signature_verifier")


# ────────────────────────────────────────────────────────────────────
# Pure primitives
# ────────────────────────────────────────────────────────────────────


def _parse_signature_hex(signature_hex: str) -> Signature:
    """Parse a hex-encoded `r||s||v` signature into eth_keys Signature.

    Accepts either:
      * 65-byte compact: `0x<r:32><s:32><v:1>`
      * 64-byte (no v): rejected — we cannot recover without v.

    `v` is normalised to {0, 1} for the eth_keys constructor (subtracts
    27 if it's in the {27, 28} ETH-personal-sign convention).
    """
    sig = signature_hex.removeprefix("0x")
    if len(sig) != 130:
        raise ValueError(
            f"signature must be 65 bytes (130 hex chars); got {len(sig)} chars"
        )
    r = int(sig[:64], 16)
    s = int(sig[64:128], 16)
    v = int(sig[128:130], 16)
    if v in (27, 28):
        v -= 27
    if v not in (0, 1):
        raise ValueError(f"signature v must be 0/1 or 27/28; got {v}")
    return Signature(vrs=(v, r, s))


def recover_signer_address(message_hash: bytes, signature_hex: str) -> str:
    """Recover the checksum address that produced this signature.

    `message_hash` is the 32-byte keccak256 digest of whatever payload
    was signed. `signature_hex` is `0x<r:32><s:32><v:1>`.
    """
    if len(message_hash) != 32:
        raise ValueError(f"message_hash must be 32 bytes; got {len(message_hash)}")
    sig = _parse_signature_hex(signature_hex)
    pubkey: PublicKey = sig.recover_public_key_from_msg_hash(message_hash)
    return pubkey.to_checksum_address()


def verify_signer(
    message_hash: bytes,
    signature_hex: str,
    expected_address: str,
) -> bool:
    """Recover the signer and compare against the expected address.

    Case-insensitive on the address comparison (we always derive a
    fresh checksum on the recovered side).
    """
    try:
        recovered = recover_signer_address(message_hash, signature_hex)
    except (ValueError, Exception) as exc:
        logger.warning("Failed to recover signer: %s", exc)
        return False
    return recovered.lower() == expected_address.lower()


# ────────────────────────────────────────────────────────────────────
# Ethereum personal-sign helper
# ────────────────────────────────────────────────────────────────────


def eth_personal_sign_hash(message: bytes) -> bytes:
    """Compute keccak256 of the Ethereum personal-sign prefix + message.

    This matches what Web3.js `eth.accounts.sign` and our own
    `SafinaSigner._eth_sign` produce — useful when the multi-sig
    participants sign via MetaMask / a hardware wallet exposing the
    same `personal_sign` interface.
    """
    prefix = b"\x19Ethereum Signed Message:\n" + str(len(message)).encode()
    return keccak(prefix + message)


# ────────────────────────────────────────────────────────────────────
# Wire-up gate — NOT YET ACTIVE
# ────────────────────────────────────────────────────────────────────


def canonical_payload(*, tx_unid: str, network: int, value: str,
                      to_address: str) -> bytes:
    """Build the canonical message that Safina multi-sig participants sign.

    **NOT YET CONFIRMED against Safina's documentation.** Two strong
    candidates from the wiki + their JS reference impl:

    * Pipe-joined: `f"{tx_unid}|{network}|{value}|{to_address}"`
    * Compact JSON: `{"unid":"...","network":...,"value":"...","to":"..."}`

    Until one is confirmed end-to-end (sign on Safina side, recover
    locally, addresses match), this function raises so verification
    cannot be turned on by accident.

    To turn this on:
      1. Replace this body with the confirmed format
      2. Set `ORGON_VERIFY_SAFINA_SIGS=1` in production env
      3. Test against a known signed transaction from staging Safina
      4. Watch logs for `signer mismatch` warnings before relying on it
    """
    raise NotImplementedError(
        "canonical_payload() not implemented — Safina canonical sign-payload "
        "format must be confirmed against their documentation before "
        "verification can be activated. See module docstring."
    )


def is_verification_enabled() -> bool:
    """Whether transaction sync should run local signer verification.

    Two conditions: the env flag is set AND `canonical_payload` has
    been wired up (we probe by trying with dummy args).
    """
    if os.getenv("ORGON_VERIFY_SAFINA_SIGS", "").lower() not in {"1", "true", "yes"}:
        return False
    try:
        canonical_payload(tx_unid="x", network=0, value="0", to_address="0x0")
    except NotImplementedError:
        logger.warning(
            "ORGON_VERIFY_SAFINA_SIGS=1 but canonical_payload() is not wired — "
            "verification stays off. See backend/safina/signature_verifier.py."
        )
        return False
    except Exception:
        # Any other exception means the function exists and just rejected the
        # dummy args — that's fine, the wire-up is real.
        return True
    return True


def verify_safina_tx_signer(
    *,
    tx_unid: str,
    network: int,
    value: str,
    to_address: str,
    signature_hex: str,
    expected_signer: str,
) -> Optional[bool]:
    """High-level: verify ONE Safina-returned signer against the canonical tx.

    Returns:
      * `True` — signer matches.
      * `False` — recovered address differs (possible forgery / Safina bug).
      * `None` — verification disabled (canonical_payload not wired or
        env flag off). Caller should treat this as "skip", not "fail".
    """
    if not is_verification_enabled():
        return None
    msg = canonical_payload(
        tx_unid=tx_unid, network=network, value=value, to_address=to_address,
    )
    return verify_signer(eth_personal_sign_hash(msg), signature_hex, expected_signer)
