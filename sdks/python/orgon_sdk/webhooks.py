"""Webhook signature verification.

Server signs each payload with the merchant's webhook_secret:

    msg = f"{ts_ms}\\n".encode() + raw_body
    sig = hex(HMAC-SHA256(secret, msg))

`verify_webhook` returns True only when the signature matches AND the
timestamp is within `tolerance_ms` of `now` (defaults to 5 minutes,
same as the server tolerance).
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Union


def verify_webhook(
    *,
    secret: str,
    timestamp: Union[str, int],
    signature: str,
    raw_body: Union[bytes, str],
    tolerance_ms: int = 5 * 60 * 1000,
) -> bool:
    try:
        ts_ms = int(timestamp)
    except (TypeError, ValueError):
        return False

    now_ms = int(time.time() * 1000)
    if abs(now_ms - ts_ms) > tolerance_ms:
        return False

    body_bytes = raw_body.encode("utf-8") if isinstance(raw_body, str) else raw_body
    msg = f"{ts_ms}\n".encode() + body_bytes
    expected = hmac.new(secret.encode(), msg, hashlib.sha256).hexdigest()
    if not signature:
        return False
    return hmac.compare_digest(expected, signature)
