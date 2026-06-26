"""Per-chain deposit sources.

Each module exposes:
  * NETWORKS — list of network_ids this module owns.
  * async scan_native(client, wallet, since) → list[DepositEvent]
  * async scan_tokens(client, wallet, since) → list[DepositEvent]   (may be empty)

`wallet` is a dict with at least { id, merchant_id, end_user_id, addr, network }.
`since` is a `datetime` (UTC) — the cursor for this stream.

DepositEvent fields:
  tx_hash      str
  log_index    int (0 for native)
  from_address str
  asset        str   (canonical symbol, e.g. "TRX"/"USDT"/"BTC"/"ETH")
  amount       Decimal
  block_number Optional[int]
  block_ts_ms  int (0 if explorer didn't return it)
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Optional


@dataclass
class DepositEvent:
    tx_hash: str
    log_index: int
    from_address: str
    asset: str
    amount: Decimal
    block_number: Optional[int]
    block_ts_ms: int


# Registry built on first import. Each chain module appends itself.
_REGISTRY: dict[int, "object"] = {}


def register(module) -> None:
    for net in getattr(module, "NETWORKS", ()):
        _REGISTRY[net] = module


def get_source(network: int):
    return _REGISTRY.get(network)


def all_supported_networks() -> list[int]:
    return sorted(_REGISTRY.keys())


# Eager-import the chain modules so their `register(__name__)` runs.
from . import tron as _tron  # noqa: E402,F401
from . import bitcoin as _btc  # noqa: E402,F401
from . import ethereum as _eth  # noqa: E402,F401
from . import orgon as _orgon  # noqa: E402,F401
