"""On-chain deposit watcher.

V1: Tron (Nile testnet 5010 + mainnet 5000) via TronGrid.
Later sprints: BTC via Esplora, ETH via Alchemy.

Per tick:
  1. Pick wallets in supported networks that have an on-chain addr.
  2. For each, ask the explorer for inbound transfers since the
     `last_seen_ts` cursor. First poll on a wallet defaults to "last
     hour" so we don't accidentally backfill its entire history.
  3. INSERT new rows into `deposits` (ON CONFLICT DO NOTHING).
  4. Update cursor.

Idempotent at the DB level via UNIQUE (network, tx_hash, log_index).
The watcher is best-effort and never raises: a single wallet's
explorer error is logged on the cursor row and skipped.

Confirmation threshold:
  Tron — 19 SR confirmations / ~57s (one round). We treat any tx
  visible in /v1/accounts/.../transactions as confirmed by the API
  layer; TronGrid only returns committed transactions. Reorgs on
  Tron are exceedingly rare (Solidified after ~19 SRs sign).
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

import httpx

logger = logging.getLogger("orgon.deposit_watcher")

# Supported networks → explorer base URL.
NETWORK_EXPLORERS: dict[int, str] = {
    5010: "https://nile.trongrid.io",
    5000: "https://api.trongrid.io",
}

# Per-wallet history horizon on first poll. Anything older than this
# we treat as "not our problem yet" — merchants will get a backfill
# tool in a later sprint.
INITIAL_BACKFILL_HOURS = 1

# How many requests we can make to TronGrid per tick (free tier
# allows about 100k/day shared across the deployment — keep room for
# other usages).
MAX_REQUESTS_PER_TICK = 100

# Per-request timeout. TronGrid is usually fast; cap it so a slow
# response doesn't starve the rest of the tick.
HTTP_TIMEOUT_S = 8.0


async def run_tick(pool) -> dict:
    """Single sweep. Returns a counter dict for observability."""
    stats = {
        "wallets_scanned": 0,
        "deposits_found": 0,
        "explorer_errors": 0,
        "skipped_unsupported_network": 0,
    }

    # Pull active wallets that live on a supported network. Hidden /
    # treasury / user — doesn't matter at this layer; the merchant
    # decides what to do with the deposit. We do skip wallets with no
    # addr (not yet activated by Safina).
    async with pool.acquire() as conn:
        wallets = await conn.fetch(
            """
            SELECT w.id::text, w.organization_id::text AS merchant_id,
                   w.end_user_id::text AS end_user_id, w.network, w.addr,
                   c.last_seen_ts
              FROM wallets w
              LEFT JOIN deposit_watch_cursors c ON c.wallet_id = w.id
             WHERE COALESCE(w.is_hidden, false) = false
               AND w.addr IS NOT NULL
               AND TRIM(w.addr) <> ''
             ORDER BY COALESCE(c.last_polled_at, 'epoch') ASC
             LIMIT $1
            """,
            MAX_REQUESTS_PER_TICK,
        )

    if not wallets:
        return stats

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_S) as client:
        for w in wallets:
            if w["network"] not in NETWORK_EXPLORERS:
                stats["skipped_unsupported_network"] += 1
                continue
            stats["wallets_scanned"] += 1
            try:
                count = await _scan_tron_wallet(
                    client=client,
                    pool=pool,
                    wallet_id=w["id"],
                    merchant_id=w["merchant_id"],
                    end_user_id=w["end_user_id"],
                    network=w["network"],
                    addr=w["addr"],
                    since=w["last_seen_ts"],
                )
                stats["deposits_found"] += count
            except Exception as e:
                stats["explorer_errors"] += 1
                await _record_error(pool, w["id"], str(e)[:300])
                logger.warning("deposit scan failed wallet=%s err=%s", w["id"], e)

    return stats


async def _scan_tron_wallet(
    *,
    client: httpx.AsyncClient,
    pool,
    wallet_id: str,
    merchant_id: str,
    end_user_id: Optional[str],
    network: int,
    addr: str,
    since: Optional[datetime],
) -> int:
    """Pull inbound TRX (native) transfers since `since`.

    TRC20 transfers (USDT etc.) come from a different endpoint and
    will be wired in a follow-up — keeping this V1 narrow.
    """
    base = NETWORK_EXPLORERS[network]
    # Default backfill window for first scan.
    if since is None:
        since = datetime.now(timezone.utc) - timedelta(hours=INITIAL_BACKFILL_HOURS)
    min_ts_ms = int(since.timestamp() * 1000)

    url = f"{base}/v1/accounts/{addr}/transactions"
    params = {
        "only_to": "true",
        "only_confirmed": "true",
        "min_timestamp": str(min_ts_ms),
        "limit": "50",
    }
    r = await client.get(url, params=params)
    r.raise_for_status()
    data = r.json()
    transactions = data.get("data") or []

    if not transactions:
        await _touch_cursor(pool, wallet_id=wallet_id, last_seen_ts=None)
        return 0

    inserted = 0
    newest_ts_ms = 0
    for tx in transactions:
        tx_id = tx.get("txID") or tx.get("transaction_id")
        if not tx_id:
            continue
        ret = (tx.get("ret") or [{}])[0].get("contractRet")
        if ret != "SUCCESS":
            continue
        block_ts_ms = int(tx.get("block_timestamp") or 0)
        if block_ts_ms > newest_ts_ms:
            newest_ts_ms = block_ts_ms
        block_number = int(tx.get("blockNumber") or 0) or None

        # Native TRX transfer: contract[0].type == "TransferContract"
        contracts = (tx.get("raw_data") or {}).get("contract") or []
        if not contracts:
            continue
        c0 = contracts[0]
        if c0.get("type") != "TransferContract":
            continue
        v = (c0.get("parameter") or {}).get("value") or {}
        # Only count txs whose destination matches our wallet address.
        # TronGrid's only_to=true filter is usually accurate, but
        # double-check after b58/hex conversion would require its own
        # encoder; trust the filter for V1.
        amount_sun = int(v.get("amount") or 0)
        if amount_sun <= 0:
            continue
        amount_trx = Decimal(amount_sun) / Decimal(1_000_000)
        from_addr = v.get("owner_address_base58") or v.get("owner_address") or ""

        async with pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO deposits
                    (merchant_id, wallet_id, end_user_id, network, tx_hash,
                     log_index, from_address, to_address, asset, amount,
                     confirmations, block_number, block_timestamp, status)
                VALUES ($1, $2, $3, $4, $5, 0, $6, $7, 'TRX', $8, 19, $9, $10, 'confirmed')
                ON CONFLICT (network, tx_hash, log_index) DO NOTHING
                RETURNING id
                """,
                UUID(merchant_id),
                UUID(wallet_id),
                UUID(end_user_id) if end_user_id else None,
                network,
                tx_id,
                from_addr,
                addr,
                amount_trx,
                block_number,
                datetime.fromtimestamp(block_ts_ms / 1000, tz=timezone.utc) if block_ts_ms else None,
            )
            if row is not None:
                inserted += 1
                logger.info(
                    "deposit recorded merchant=%s wallet=%s amount=%s TRX tx=%s",
                    merchant_id, wallet_id, amount_trx, tx_id,
                )
                # Fire the webhook event right away; failure here
                # is non-fatal, the deposit row is the source of
                # truth and a manual replay tool can re-publish.
                try:
                    from backend.services.webhook_publisher import (
                        publish_event,
                        EV_WALLET_DEPOSIT,
                    )
                    await publish_event(
                        pool,
                        merchant_id=merchant_id,
                        event_type=EV_WALLET_DEPOSIT,
                        payload={
                            "deposit_id": str(row["id"]),
                            "wallet_id": wallet_id,
                            "end_user_id": end_user_id,
                            "network": network,
                            "tx_hash": tx_id,
                            "from_address": from_addr,
                            "to_address": addr,
                            "asset": "TRX",
                            "amount": str(amount_trx),
                            "block_number": block_number,
                        },
                    )
                except Exception as pub_err:
                    logger.warning(
                        "deposit webhook publish failed (deposit kept) tx=%s err=%s",
                        tx_id, pub_err,
                    )

    if newest_ts_ms:
        cursor_ts = datetime.fromtimestamp(newest_ts_ms / 1000, tz=timezone.utc)
        await _touch_cursor(pool, wallet_id=wallet_id, last_seen_ts=cursor_ts)
    else:
        await _touch_cursor(pool, wallet_id=wallet_id, last_seen_ts=None)

    return inserted


async def _touch_cursor(pool, *, wallet_id: str, last_seen_ts: Optional[datetime]) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO deposit_watch_cursors (wallet_id, last_seen_ts, last_polled_at, error_streak, last_error)
            VALUES ($1, $2, now(), 0, NULL)
            ON CONFLICT (wallet_id) DO UPDATE SET
                last_seen_ts   = COALESCE(EXCLUDED.last_seen_ts, deposit_watch_cursors.last_seen_ts),
                last_polled_at = EXCLUDED.last_polled_at,
                error_streak   = 0,
                last_error     = NULL
            """,
            UUID(wallet_id),
            last_seen_ts,
        )


async def _record_error(pool, wallet_id: str, msg: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO deposit_watch_cursors (wallet_id, last_polled_at, error_streak, last_error)
            VALUES ($1, now(), 1, $2)
            ON CONFLICT (wallet_id) DO UPDATE SET
                last_polled_at = EXCLUDED.last_polled_at,
                error_streak   = deposit_watch_cursors.error_streak + 1,
                last_error     = EXCLUDED.last_error
            """,
            UUID(wallet_id),
            msg,
        )
