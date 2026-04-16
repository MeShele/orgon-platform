"""
EC SECP256k1 Signing for Safina Pay API.

Implements the signing protocol compatible with Web3.js eth.accounts.sign():
- Hashes: keccak256("\\x19Ethereum Signed Message:\\n" + len(msg) + msg)
- Signs the hash with SECP256k1
- Returns 4 headers: x-app-ec-from, x-app-ec-sign-r/s/v
- v is adjusted to 27/28 (0x1b/0x1c) per Ethereum convention

GET requests: sign "{}"
POST requests: sign compact JSON (no whitespace)
"""

import json
import logging
from typing import Optional

from eth_keys import keys
from eth_hash.auto import keccak

logger = logging.getLogger("orgon.safina.signer")


class SafinaSigner:
    """EC SECP256k1 signer for Safina Pay API requests."""

    def __init__(self, private_key_hex: str):
        key_bytes = bytes.fromhex(private_key_hex.removeprefix("0x"))
        self._private_key = keys.PrivateKey(key_bytes)
        self._address = self._private_key.public_key.to_checksum_address()
        logger.info("SafinaSigner initialized for address %s", self._address)

    @property
    def address(self) -> str:
        return self._address

    def _eth_sign(self, message: bytes):
        """
        Sign using Web3.js-compatible Ethereum personal sign.

        Computes: keccak256("\\x19Ethereum Signed Message:\\n" + str(len(msg)) + msg)
        Then signs the resulting hash.
        """
        prefix = b"\x19Ethereum Signed Message:\n" + str(len(message)).encode()
        msg_hash = keccak(prefix + message)
        return self._private_key.sign_msg_hash(msg_hash)

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
