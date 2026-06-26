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


def looks_failed(tx_field: object) -> bool:
    """True if `tx` holds a Safina terminal ERROR string — the broadcast
    was rejected (e.g. ``"global: Returned error: EVM error: OutOfFunds"``).

    Distinct from `looks_canceled` (the ~24h "1 day limit" abandonment).
    Verified against Safina prod after the 2026-06-03 ETH-Sepolia fix:
    `tx` is null while a signed tx is in-flight, then flips to EITHER a
    64-hex on-chain hash (success) OR a human-readable error string
    (rejection). So any non-empty value that is neither a hash nor a
    cancellation marker is a terminal failure — surfacing it as `failed`
    (instead of leaving the tx stuck in `signed`) is the whole point.
    """
    if not tx_field:
        return False
    if not str(tx_field).strip():
        return False
    return not is_broadcast_hash(tx_field) and not looks_canceled(tx_field)


# Raw Safina / chain error strings are developer-facing noise
# ("Error for sendtx", "ContractValidateException ... no OwnerAccount",
# "EVM error: OutOfFunds"). Surfacing them to a non-technical operator or
# end user is pure confusion. Map the known cause-patterns to a plain
# message; keep the raw string elsewhere for support/debugging.
#
# Order matters: specific patterns before generic ones. Each entry is
# (substrings_any, human_message). Matching is case-insensitive.
_FAILURE_PATTERNS: list[tuple[tuple[str, ...], str]] = [
    # Network-resource shortage before the generic "not enough" so a
    # "bandwidth is not enough" doesn't get the funds message.
    (("bandwidth", "energy", "freenet", "resource insufficient"),
     "Недостаточно ресурсов сети (energy/bandwidth) для оплаты комиссии. "
     "Пополните кошелёк нативной монетой сети."),
    (("outoffunds", "insufficient", "not enough", "balance",
      "недостаточно"),
     "Недостаточно средств на кошельке для суммы и комиссии сети. "
     "Пополните кошелёк и повторите."),
    (("owneraccount", "account not exist", "account does not exist",
      "not activated", "inactive account", "create_account"),
     "Кошелёк ещё не активирован в сети — на него нужно сначала получить "
     "любой входящий перевод. Повторите после пополнения."),
    (("1 day limit", "day limit", "expired", "истёк", "timeout",
      "timed out", "no_broadcast"),
     "Истёк срок подтверждения транзакции. Создайте новую."),
    (("cancel", "отмен"),
     "Транзакция отменена. Создайте новую."),
    (("slist", "signature", "sign mismatch", "подпис"),
     "Не совпали данные подписи кошелька. Обратитесь в поддержку."),
    (("validate", "contractvalidate", "invalid", "bad address",
      "wrong address", "неверн"),
     "Сеть отклонила транзакцию: проверьте адрес получателя и сумму."),
]

_FAILURE_FALLBACK = (
    "Не удалось отправить транзакцию. Попробуйте ещё раз позже или "
    "обратитесь в поддержку."
)


def humanize_failure_reason(raw: object) -> Optional[str]:
    """Translate a raw Safina/chain failure string into a plain message a
    non-technical user can act on. Returns None when there's nothing to
    translate (no failure). The raw string is preserved by callers for
    operator-facing debug — this is the user-facing layer only.
    """
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    low = s.lower()
    for needles, message in _FAILURE_PATTERNS:
        if any(n in low for n in needles):
            return message
    return _FAILURE_FALLBACK


def classify_safina_tx_status(tx_field: object, *, signed: bool) -> str:
    """Map Safina's `tx` field (+ whether a signature is present) to our
    canonical internal status. Single source of truth shared by the
    global and per-tenant sync paths so they can never diverge.

    Precedence (a non-empty `tx` is always terminal — hash or error):

        confirmed  — real on-chain hash present
        canceled   — Safina abandonment string (cancel / limit)
        failed     — any other non-empty error string (broadcast rejected)
        signed     — no `tx` yet but at least one signature collected
        pending    — created, not yet signed
    """
    if is_broadcast_hash(tx_field):
        return "confirmed"
    if looks_canceled(tx_field):
        return "canceled"
    if looks_failed(tx_field):
        return "failed"
    if signed:
        return "signed"
    return "pending"
