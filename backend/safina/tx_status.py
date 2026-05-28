"""Single source of truth for interpreting Safina's `Transaction.tx` field.

Safina's `tx` carries the on-chain transaction hash ONLY after broadcast;
before that it is null. The trap: when Safina abandons a signed tx (its
~24h "1 day limit"), it overwrites `tx` with a human-readable string such
as ``"Transaction canceled, 1 day limit."`` — not null, not a hash.

The pre-058 code did ``if tx.tx: status = "confirmed"`` and stored the raw
value as `tx_hash`, which (a) flipped canceled txs to `confirmed`, (b) put
the message into `tx_hash`, and (c) fired false
`transaction.broadcasted`/`transaction.confirmed` webhooks to merchants and
asystem-core. Verified 2026-05-27: 26 of 30 demo txs were mislabeled.

Use these helpers everywhere the Safina `tx` field is interpreted, so the
hash-vs-status-string distinction lives in exactly one place.
"""

from __future__ import annotations

import re
from typing import Optional

# BTC / ETH / TRX / ORGON transaction hashes are all 32-byte values =
# 64 hex chars, optionally `0x`-prefixed (ETH). Any other content Safina
# puts in `tx` (cancellation / limit / error strings) fails this and is
# therefore NOT treated as a broadcast.
_HASH_RE = re.compile(r"^(?:0x)?[0-9a-fA-F]{64}$")


def is_broadcast_hash(tx_field: object) -> bool:
    """True only if `tx_field` is a real on-chain transaction hash."""
    if not tx_field:
        return False
    return bool(_HASH_RE.match(str(tx_field).strip()))


def clean_tx_hash(tx_field: object) -> Optional[str]:
    """Return the hash if it is real, else None.

    Use for any `tx_hash` we store or expose — guarantees we never
    persist or surface a Safina status string as if it were a hash.
    """
    if not tx_field:
        return None
    s = str(tx_field).strip()
    return s if is_broadcast_hash(s) else None


def looks_canceled(tx_field: object) -> bool:
    """True if the `tx` field is a Safina cancellation/limit/failure marker.

    These are terminal: Safina gave up on the signed tx (commonly the
    "Transaction canceled, 1 day limit." string).
    """
    if not tx_field:
        return False
    low = str(tx_field).lower()
    return ("cancel" in low) or ("limit" in low) or ("failed" in low)
