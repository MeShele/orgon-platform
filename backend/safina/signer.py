"""
EC SECP256k1 Signing for Safina Pay API.

Implements the signing protocol compatible with Web3.js eth.accounts.sign():
- Hashes: keccak256("\\x19Ethereum Signed Message:\\n" + len(msg) + msg)
- Signs the hash with SECP256k1
- Returns 4 headers: x-app-ec-from, x-app-ec-sign-r/s/v
- v is adjusted to 27/28 (0x1b/0x1c) per Ethereum convention

GET requests: sign "{}"
POST requests: sign compact JSON (no whitespace)

The signing operation itself is delegated to a `SignerBackend` (see
`signer_backends.py`) so the EC private key can live outside the
process — env, AWS KMS, or HashiCorp Vault — without rewriting any of
the call sites that use SafinaSigner.
"""

import json
import logging
from typing import Optional, Union

from eth_keys import keys
from eth_hash.auto import keccak

from .signer_backends import EnvSignerBackend, SignerBackend

logger = logging.getLogger("orgon.safina.signer")


class SafinaSigner:
    """EC SECP256k1 signer for Safina Pay API requests.

    Two construction modes:

    * `SafinaSigner("0xabcdef…")` — legacy convenience; wraps the hex
      private key in an `EnvSignerBackend`. Equivalent to passing the
      backend explicitly.
    * `SafinaSigner(backend=build_signer_backend())` — production path.
      `build_signer_backend()` reads `ORGON_SIGNER_BACKEND` env and
      returns the configured backend (env / kms / vault).

    All signing flows through `backend.sign_msg_hash(...)`, so a KMS or
    Vault swap requires no edit to this file.
    """

    def __init__(
        self,
        private_key_hex: Optional[str] = None,
        *,
        backend: Optional[SignerBackend] = None,
    ):
        if backend is not None and private_key_hex is not None:
            raise ValueError("Provide either private_key_hex or backend, not both")
        if backend is not None:
            self._backend: SignerBackend = backend
        elif private_key_hex:
            self._backend = EnvSignerBackend(private_key_hex)
        else:
            raise ValueError(
                "SafinaSigner requires private_key_hex or backend; got neither"
            )
        self._address = self._backend.address
        logger.info("SafinaSigner initialised for address %s (backend=%s)",
                    self._address, type(self._backend).__name__)

    @property
    def address(self) -> str:
        return self._address

    def _eth_sign(self, message: bytes):
        """
        Sign using Web3.js-compatible Ethereum personal sign.

        Computes: keccak256("\\x19Ethereum Signed Message:\\n" + str(len(msg)) + msg)
        Then signs the resulting hash via the configured backend.
        """
        prefix = b"\x19Ethereum Signed Message:\n" + str(len(message)).encode()
        msg_hash = keccak(prefix + message)
        return self._backend.sign_msg_hash(msg_hash)

    def sign_message(self, message: bytes) -> dict:
        """
        Sign a message and return Safina API headers.

        Returns:
            Dict with x-app-ec-from, x-app-ec-sign-r, x-app-ec-sign-s, x-app-ec-sign-v
        """
        signature = self._eth_sign(message)
        return {
            "x-app-ec-from": self._address,
            "x-app-ec-sign-r": hex(signature.r),
            "x-app-ec-sign-s": hex(signature.s),
            "x-app-ec-sign-v": hex(signature.v + 27),
        }

    def sign_get(self) -> dict:
        """Sign a GET request (signs '{}')."""
        return self.sign_message(b"{}")

    def sign_post(self, data: Optional[dict] = None) -> dict:
        """
        Sign a POST request body as compact JSON (no whitespace).
        """
        if not data:
            msg = b"{}"
        else:
            msg = json.dumps(data, separators=(",", ":"), ensure_ascii=False).encode()
        return self.sign_message(msg)

    def verify_signature(self, message: bytes) -> bool:
        """Verify own signature for testing."""
        signature = self._eth_sign(message)
        recovered = signature.recover_public_key_from_msg_hash(
            keccak(b"\x19Ethereum Signed Message:\n" + str(len(message)).encode() + message)
        )
        return recovered.to_checksum_address() == self._address

    def sign_tx_canonical_hex(
        self,
        *,
        tx_unid: str,
        network: int,
        value: str,
        to_address: str,
        variant: Optional[str] = None,
    ) -> str:
        """Build the `ec_sign` value Safina is presumed to want in the body
        of `POST /tx_sign/{tx_unid}`.

        The 6 candidate canonical formats live in
        `signature_verifier._CANONICAL_VARIANTS`. This method:

          1. Resolves the variant (arg → `SAFINA_CANONICAL_VARIANT` env →
             error).
          2. Computes the 32-byte digest the variant prescribes.
          3. Signs the digest via the configured backend (env / KMS /
             vault — same path as request-auth headers).
          4. Returns the 65-byte hex signature
             `0x<r:32><s:32><v:1>` ready to drop into a JSON body.

        Speculative scaffolding (Wave-22-aligned). Until Safina confirms
        which variant + body field name match, the caller should leave
        `SAFINA_CANONICAL_VARIANT` unset — then `SafinaPayClient.sign_transaction`
        falls back to its legacy empty-body behaviour and this method is
        never invoked.
        """
        # Local import keeps the verifier optional at module load (some
        # unit tests instantiate SafinaSigner without the verifier path).
        from .signature_verifier import _CANONICAL_VARIANTS, _digest_for_variant
        import os

        name = variant or os.getenv("SAFINA_CANONICAL_VARIANT", "").strip()
        if not name:
            raise RuntimeError(
                "sign_tx_canonical_hex requires SAFINA_CANONICAL_VARIANT "
                "to be set (or `variant=` explicitly). See "
                "backend/safina/signature_verifier.py."
            )
        spec = _CANONICAL_VARIANTS.get(name)
        if spec is None:
            raise ValueError(
                f"unknown canonical variant {name!r}; "
                f"available: {sorted(_CANONICAL_VARIANTS)}"
            )
        digest = _digest_for_variant(spec, {
            "tx_unid": tx_unid,
            "network": network,
            "value": str(value),
            "to_address": to_address,
        })
        sig = self._backend.sign_msg_hash(digest)
        # Safina-side recovery expects `v ∈ {27, 28}` (Ethereum personal-sign
        # convention) per the same convention SafinaSigner uses for the
        # request-auth headers (`x-app-ec-sign-v`).
        v = sig.v + 27 if sig.v in (0, 1) else sig.v
        return (
            "0x"
            + sig.r.to_bytes(32, "big").hex()
            + sig.s.to_bytes(32, "big").hex()
            + v.to_bytes(1, "big").hex()
        )
