#!/usr/bin/env python3
"""Auto-discover the Safina canonical-payload variant for a tenant.

Wave 22 / Story 2.7. The pilot runbook is:

  1. Operator captures a known-good Safina-signed transaction (one
     `tx_unid`, `network`, `value`, `to_address`, `signature_hex`,
     `expected_signer`) — typically by tail-ing the `tx.signed[]`
     entries surfaced through `/api/transactions/sync`.
  2. Pipes that JSON into this script.
  3. The script probes every variant in
     `backend.safina.signature_verifier._CANONICAL_VARIANTS` against
     the sample, prints a per-variant ✓/✗ table, and exits 0 if any
     variant matched.
  4. Operator sets `SAFINA_CANONICAL_VARIANT` to the matched name in
     Coolify and (after a 24h shadow-mode soak) flips
     `ORGON_SAFINA_VERIFY_MODE=enforce`.

Usage:
    python backend/scripts/safina_discover_canonical.py --sample sample.json
    python backend/scripts/safina_discover_canonical.py < sample.json
    python backend/scripts/safina_discover_canonical.py --self-test

`sample.json` schema:
    {
      "tx_unid": "abc123...",
      "network": 1,
      "value": "1000000000000000000",
      "to_address": "0xRecipient...",
      "signature_hex": "0x<r:32><s:32><v:1>",
      "expected_signer": "0xSafinaSigner..."
    }

Exit codes:
    0 — at least one variant matched (variant name printed last)
    1 — no variant matched
    2 — bad input (file missing, JSON malformed, required field missing)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Make the script runnable from project root without `pip install -e .`.
_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from backend.safina import signature_verifier as sv  # noqa: E402


REQUIRED_KEYS = (
    "tx_unid", "network", "value", "to_address",
    "signature_hex", "expected_signer",
)


def _load_sample(args: argparse.Namespace) -> dict[str, Any]:
    if args.sample:
        path = Path(args.sample)
        if not path.exists():
            print(f"error: sample file not found: {path}", file=sys.stderr)
            sys.exit(2)
        raw = path.read_text(encoding="utf-8")
    else:
        if sys.stdin.isatty():
            print("error: no --sample and no stdin input", file=sys.stderr)
            sys.exit(2)
        raw = sys.stdin.read()
    try:
        sample = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"error: bad JSON: {exc}", file=sys.stderr)
        sys.exit(2)
    missing = [k for k in REQUIRED_KEYS if k not in sample]
    if missing:
        print(f"error: sample missing keys: {missing}", file=sys.stderr)
        sys.exit(2)
    return sample


def _run_self_test() -> int:
    """Sign a sample with v1 on our side, then probe — should match v1."""
    from eth_keys import keys as eth_keys

    pk = eth_keys.PrivateKey(bytes.fromhex("33" * 32))
    addr = pk.public_key.to_checksum_address()
    tx_data = {
        "tx_unid": "self_test_unid",
        "network": 1,
        "value": "12345",
        "to_address": "0x" + "cd" * 20,
    }
    spec = sv.list_canonical_variants()["v1_pipe_unid_to_value"]
    digest = sv._digest_for_variant(spec, tx_data)
    raw = pk.sign_msg_hash(digest).to_bytes()
    sig_hex = "0x" + raw[:64].hex() + bytes([raw[64] + 27]).hex()
    print("running self-test (synthetic v1 sample)...")
    return _probe({**tx_data, "signature_hex": sig_hex, "expected_signer": addr})


def _probe(sample: dict[str, Any]) -> int:
    results = sv.try_all_variants(
        tx_unid=str(sample["tx_unid"]),
        network=int(sample["network"]),
        value=str(sample["value"]),
        to_address=str(sample["to_address"]),
        signature_hex=str(sample["signature_hex"]),
        expected_signer=str(sample["expected_signer"]),
    )
    matched = [name for name, ok in results.items() if ok]
    width = max(len(n) for n in results) + 2
    print()
    for name, ok in results.items():
        mark = "✓ MATCH" if ok else "✗"
        print(f"  [{name.ljust(width)}] {mark}")
    print()
    if not matched:
        print("→ no variant matched.")
        print("  Add a new candidate to _CANONICAL_VARIANTS or check the sample"
              " (signature_hex format, network, address checksumming).")
        return 1
    if len(matched) > 1:
        print(f"→ multiple variants matched: {matched}")
        print("  This is suspicious — pick the one that round-trips on a second"
              " independent sample.")
        return 0
    name = matched[0]
    print(f"→ Confirmed variant: {name}")
    print(f"  Set in Coolify:  SAFINA_CANONICAL_VARIANT={name}")
    print(f"  Then enable:     ORGON_SAFINA_VERIFY_MODE=shadow"
          " (or =enforce after 24h soak)")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    parser.add_argument("--sample", help="path to sample JSON; defaults to stdin")
    parser.add_argument(
        "--self-test", action="store_true",
        help="probe with a synthetic v1-signed sample and exit",
    )
    args = parser.parse_args()
    if args.self_test:
        return _run_self_test()
    sample = _load_sample(args)
    return _probe(sample)


if __name__ == "__main__":
    sys.exit(main())
