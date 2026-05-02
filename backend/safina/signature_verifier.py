"""Local verification of Safina-returned EC signatures.

When Safina returns a signed transaction, the response includes a list
of signers (`ecaddress` + `ecsign` per signer). Without local
verification, a compromised Safina backend could feed us forged
co-signers on a multi-sig and we'd accept them as valid.

This module gives us the primitive to verify those signatures locally:
recover the EC public key from `ecsign`, derive the address, compare
against the claimed `ecaddress`.

**Canonical payload uncertainty.** ECDSA recovery requires knowing the
exact bytes that were hashed. The precise format Safina uses (field
order, separator, encoding) is part of their internal protocol and is
not yet confirmed in writing. Story 2.7 (Wave 22) therefore:

  1. Registers 6 candidate canonical variants (`_CANONICAL_VARIANTS`)
     each implementing a plausible `(tx_data) -> bytes` mapping.
  2. Lets the operator pick one via `SAFINA_CANONICAL_VARIANT` env.
  3. Provides `try_all_variants` for offline auto-discovery (the CLI
     `backend/scripts/safina_discover_canonical.py` uses this).
  4. Supports three runtime modes via `ORGON_SAFINA_VERIFY_MODE`:
       - `off`     — no verification (default; backwards-compatible).
       - `shadow`  — verify, log + AML-alert on mismatch, do not block tx.
       - `enforce` — additionally mark tx as `rejected_signer_mismatch`.

Once a variant is confirmed against live Safina data via the discovery
CLI, set `SAFINA_CANONICAL_VARIANT` and `ORGON_SAFINA_VERIFY_MODE=shadow`,
monitor 24h, then flip to `enforce`.

Public API:

* `recover_signer_address(message_hash, signature_hex)` — pure primitive.
* `verify_signer(message_hash, signature_hex, expected_address)` —
  recovery + comparison.
* `eth_personal_sign_hash(message)` — Ethereum personal-sign prefix hash.
* `canonical_payload(*, variant=None, **tx_data)` — variant-dispatched
  bytes builder. Raises `NotImplementedError` if no variant configured
  (matches the pre-Wave-22 behaviour for callers that don't opt in).
* `try_all_variants(...)` — for discovery; returns `{variant_name: matched_bool}`.
* `get_verify_mode()` — parses env, returns `"off" | "shadow" | "enforce"`.
* `is_verification_enabled()` — backwards-compat wrapper.
* `verify_safina_tx_signer(...)` — high-level: returns `True | False | None`.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Callable, Dict, Literal, Optional

from eth_hash.auto import keccak
from eth_keys.datatypes import PublicKey, Signature

logger = logging.getLogger("orgon.safina.signature_verifier")


VerifyMode = Literal["off", "shadow", "enforce"]


# ────────────────────────────────────────────────────────────────────
# Pure primitives
# ────────────────────────────────────────────────────────────────────


def _parse_signature_hex(signature_hex: str) -> Signature:
    """Parse a hex-encoded `r||s||v` signature into eth_keys Signature.

    Accepts 65-byte compact: `0x<r:32><s:32><v:1>`. `v` is normalised
    to {0, 1} (subtracts 27 if it's in the {27, 28} ETH-personal-sign
    convention).
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
    """Recover the checksum address that produced this signature."""
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
    """Recover the signer and compare against the expected address."""
    try:
        recovered = recover_signer_address(message_hash, signature_hex)
    except Exception as exc:
        logger.warning("Failed to recover signer: %s", exc)
        return False
    return recovered.lower() == expected_address.lower()


def eth_personal_sign_hash(message: bytes) -> bytes:
    """Compute keccak256 of the Ethereum personal-sign prefix + message."""
    prefix = b"\x19Ethereum Signed Message:\n" + str(len(message)).encode()
    return keccak(prefix + message)


# ────────────────────────────────────────────────────────────────────
# Canonical variant registry
# ────────────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class CanonicalVariant:
    """One candidate way Safina might canonicalize a transaction.

    `build` takes a `tx_data` dict with keys `tx_unid` (str/hex),
    `network` (int), `value` (str — decimal big-int), `to_address`
    (0x-prefixed hex). Returns the raw bytes that Safina is presumed
    to feed into `keccak256` (or, for v6_keccak_pre_hashed, the bytes
    AFTER keccak — caller skips the personal-sign prefix in that case).
    """

    name: str
    description: str
    build: Callable[[Dict[str, Any]], bytes]
    """If True, the bytes returned are the final 32-byte digest and
    must NOT be passed through `eth_personal_sign_hash`. Default False."""
    pre_hashed: bool = False


def _v1_pipe_unid_to_value(d: Dict[str, Any]) -> bytes:
    return f"{d['tx_unid']}|{d['to_address']}|{d['value']}|{d['network']}".encode("utf-8")


def _v2_pipe_unid_value_to_network(d: Dict[str, Any]) -> bytes:
    return f"{d['tx_unid']}|{d['value']}|{d['to_address']}|{d['network']}".encode("utf-8")


def _v3_json_sorted(d: Dict[str, Any]) -> bytes:
    return json.dumps(
        {
            "network": d["network"],
            "to": d["to_address"],
            "unid": d["tx_unid"],
            "value": d["value"],
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _v4_json_to_lower(d: Dict[str, Any]) -> bytes:
    return json.dumps(
        {
            "unid": d["tx_unid"],
            "network": d["network"],
            "value": d["value"],
            "to": str(d["to_address"]).lower(),
        },
        separators=(",", ":"),
    ).encode("utf-8")


def _v5_concat_no_separator(d: Dict[str, Any]) -> bytes:
    """Hex-concat: unid_bytes || to_bytes || value_padded(32be).

    Caller's `tx_unid` may be hex (without 0x) — we tolerate both.
    `to_address` MUST be 0x-prefixed 40-hex.
    """
    unid_str = str(d["tx_unid"])
    if unid_str.startswith("0x"):
        unid_str = unid_str[2:]
    # Pad to even length so bytes.fromhex doesn't fail on odd-length strings.
    if len(unid_str) % 2 == 1:
        unid_str = "0" + unid_str
    unid_bytes = bytes.fromhex(unid_str)
    to_addr = str(d["to_address"])
    if not to_addr.startswith("0x") or len(to_addr) != 42:
        raise ValueError(f"v5 expects 0x-prefixed 20-byte address; got {to_addr}")
    to_bytes = bytes.fromhex(to_addr[2:])
    value_padded = int(d["value"]).to_bytes(32, "big")
    return unid_bytes + to_bytes + value_padded


def _v6_keccak_pre_hashed(d: Dict[str, Any]) -> bytes:
    """V1 string then keccak256 — caller must NOT re-hash."""
    return keccak(_v1_pipe_unid_to_value(d))


_CANONICAL_VARIANTS: Dict[str, CanonicalVariant] = {
    "v1_pipe_unid_to_value": CanonicalVariant(
        name="v1_pipe_unid_to_value",
        description="Pipe-joined unid|to|value|network (string)",
        build=_v1_pipe_unid_to_value,
    ),
    "v2_pipe_unid_value_to_network": CanonicalVariant(
        name="v2_pipe_unid_value_to_network",
        description="Pipe-joined unid|value|to|network",
        build=_v2_pipe_unid_value_to_network,
    ),
    "v3_json_sorted": CanonicalVariant(
        name="v3_json_sorted",
        description="Compact JSON with sorted keys",
        build=_v3_json_sorted,
    ),
    "v4_json_to_lower": CanonicalVariant(
        name="v4_json_to_lower",
        description="JSON with lowercase to_address (no checksum)",
        build=_v4_json_to_lower,
    ),
    "v5_concat_no_separator": CanonicalVariant(
        name="v5_concat_no_separator",
        description="Binary concat: unid_bytes || to_bytes || value(32be)",
        build=_v5_concat_no_separator,
    ),
    "v6_keccak_pre_hashed": CanonicalVariant(
        name="v6_keccak_pre_hashed",
        description="V1 piped string then keccak256 — already-hashed digest",
        build=_v6_keccak_pre_hashed,
        pre_hashed=True,
    ),
}


def list_canonical_variants() -> Dict[str, CanonicalVariant]:
    """Return a copy of the variant registry — discovery + tests."""
    return dict(_CANONICAL_VARIANTS)


# ────────────────────────────────────────────────────────────────────
# Variant dispatch
# ────────────────────────────────────────────────────────────────────


def _selected_variant_name() -> Optional[str]:
    name = os.getenv("SAFINA_CANONICAL_VARIANT", "").strip()
    return name or None


def canonical_payload(
    *,
    tx_unid: str,
    network: int,
    value: str,
    to_address: str,
    variant: Optional[str] = None,
) -> bytes:
    """Build the canonical bytes for the configured variant.

    Args:
        variant: explicit name; if None, reads SAFINA_CANONICAL_VARIANT env.

    Returns:
        For most variants: the bytes to feed into `eth_personal_sign_hash`.
        For pre-hashed variants (v6): the final 32-byte digest. Callers
        wanting `verify_signer` semantics can simply trust that
        `verify_safina_tx_signer` handles the dispatch correctly.

    Raises:
        NotImplementedError: when no variant is configured. Preserves
            pre-Wave-22 behaviour so callers that haven't opted in never
            get false-positive verification results.
        ValueError: when an unknown variant name is supplied.
    """
    name = variant or _selected_variant_name()
    if not name:
        raise NotImplementedError(
            "canonical_payload() not configured — set SAFINA_CANONICAL_VARIANT "
            "in env or pass `variant=` explicitly. See "
            "backend/safina/signature_verifier.py module docstring."
        )
    spec = _CANONICAL_VARIANTS.get(name)
    if spec is None:
        raise ValueError(
            f"unknown canonical variant '{name}'. "
            f"Available: {sorted(_CANONICAL_VARIANTS)}"
        )
    return spec.build({
        "tx_unid": tx_unid,
        "network": network,
        "value": value,
        "to_address": to_address,
    })


def _digest_for_variant(
    variant: CanonicalVariant,
    tx_data: Dict[str, Any],
) -> bytes:
    """Return the 32-byte message digest the signer would have hashed.

    Pre-hashed variants emit the digest directly; others go through
    `eth_personal_sign_hash` (the convention `SafinaSigner` uses on
    our side, see Wave 18 KMS story).
    """
    raw = variant.build(tx_data)
    if variant.pre_hashed:
        if len(raw) != 32:
            raise ValueError(
                f"variant {variant.name} marked pre_hashed but emitted {len(raw)} bytes"
            )
        return raw
    return eth_personal_sign_hash(raw)


# ────────────────────────────────────────────────────────────────────
# Mode + high-level verification
# ────────────────────────────────────────────────────────────────────


def get_verify_mode() -> VerifyMode:
    """Resolve the operator-configured verification mode.

    Reads `ORGON_SAFINA_VERIFY_MODE` first. If unset, falls back to the
    legacy `ORGON_VERIFY_SAFINA_SIGS=1` flag for backwards compat
    (=1 → enforce). Otherwise returns "off".
    """
    mode = os.getenv("ORGON_SAFINA_VERIFY_MODE", "").strip().lower()
    if mode in ("off", "shadow", "enforce"):
        return mode  # type: ignore[return-value]
    legacy = os.getenv("ORGON_VERIFY_SAFINA_SIGS", "").strip().lower()
    if legacy in ("1", "true", "yes"):
        return "enforce"
    return "off"


def is_verification_enabled() -> bool:
    """Backwards-compat: True if mode is shadow or enforce AND a variant is wired."""
    if get_verify_mode() == "off":
        return False
    if _selected_variant_name() is None:
        logger.warning(
            "ORGON_SAFINA_VERIFY_MODE is set but SAFINA_CANONICAL_VARIANT is empty — "
            "verification stays off."
        )
        return False
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
      * `True`  — signer matches.
      * `False` — recovered address differs (forgery / wrong variant / bug).
      * `None`  — verification disabled (off-mode or variant unset).
        Caller treats this as "skip", not "fail".
    """
    if not is_verification_enabled():
        return None
    name = _selected_variant_name()
    if name is None:                 # double-check (race with env-unset)
        return None
    spec = _CANONICAL_VARIANTS.get(name)
    if spec is None:
        logger.warning("Unknown SAFINA_CANONICAL_VARIANT=%r — verification skipped", name)
        return None
    digest = _digest_for_variant(spec, {
        "tx_unid": tx_unid,
        "network": network,
        "value": value,
        "to_address": to_address,
    })
    return verify_signer(digest, signature_hex, expected_signer)


def try_all_variants(
    *,
    tx_unid: str,
    network: int,
    value: str,
    to_address: str,
    signature_hex: str,
    expected_signer: str,
) -> Dict[str, bool]:
    """Probe every registered variant. Returns {variant_name: matched}.

    Used by the discovery CLI and tests. Variants that raise during
    `build` (e.g. bad hex input for v5) are reported as `False` —
    discovery cares about working matches, not crash diagnostics.
    """
    results: Dict[str, bool] = {}
    for name, spec in _CANONICAL_VARIANTS.items():
        try:
            digest = _digest_for_variant(spec, {
                "tx_unid": tx_unid,
                "network": network,
                "value": value,
                "to_address": to_address,
            })
            results[name] = verify_signer(digest, signature_hex, expected_signer)
        except Exception as exc:
            logger.debug("variant %s failed to build: %s", name, exc)
            results[name] = False
    return results
