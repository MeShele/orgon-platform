"""Multi-chain deposit watcher.

Dispatcher: per tick picks a batch of wallets, looks up the per-chain
source module (see services/deposit_sources/*), calls scan_native +
scan_tokens with the right cursor, persists new deposits, and fires
webhook events.

Each chain module is fully self-contained — adding a new network is
"drop a new file under deposit_sources/ and call register(module)".
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

import httpx

from backend.services.deposit_sources import (
    DepositEvent,
    all_supported_networks,
    get_source,
)

logger = logging.getLogger("orgon.deposit_watcher")

INITIAL_BACKFILL_HOURS = 1
MAX_WALLETS_PER_TICK = 50
HTTP_TIMEOUT_S = 12.0


async def run_tick(pool) -> dict:
    stats = {
        "wallets_scanned": 0,
        "deposits_native": 0,
        "deposits_tokens": 0,
        "explorer_errors": 0,
        "skipped_unsupported_network": 0,
    }
    supported = set(all_supported_networks())

    async with pool.acquire() as conn:
        wallets = await conn.fetch(
            """
            SELECT w.id::text, w.organization_id::text AS merchant_id,
                   w.end_user_id::text AS end_user_id, w.network, w.addr,
                   c.last_seen_ts_native, c.last_seen_ts_tokens
              FROM wallets w
              LEFT JOIN deposit_watch_cursors c ON c.wallet_id = w.id
             WHERE COALESCE(w.is_hidden, false) = false
               AND w.addr IS NOT NULL
               AND TRIM(w.addr) <> ''
             ORDER BY COALESCE(c.last_polled_at, 'epoch') ASC
             LIMIT $1
            """,
            MAX_WALLETS_PER_TICK,
        )

    if not wallets:
        return stats

    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT_S) as client:
        for w_row in wallets:
            if w_row["network"] not in supported:
                stats["skipped_unsupported_network"] += 1
                continue
            stats["wallets_scanned"] += 1
            source = get_source(w_row["network"])
            assert source is not None  # narrowed by supported check
            w = dict(w_row)
            ok_any = False

            for stream, fn_name, cursor_col in (
                ("native", "scan_native", "last_seen_ts_native"),
                ("tokens", "scan_tokens", "last_seen_ts_tokens"),
            ):
                since = w[cursor_col] or _default_since()
                try:
                    events = await getattr(source, fn_name)(client, w, since)
                except Exception as e:
                    stats["explorer_errors"] += 1
                    logger.warning(
                        "%s scan failed network=%s wallet=%s err=%s",
                        stream, w["network"], w["id"], e,
                    )
                    await _record_error(pool, w["id"], f"{stream}: {str(e)[:200]}")
                    continue

                newest_ts_ms = 0
                inserted = 0
                for ev in events:
                    if ev.block_ts_ms > newest_ts_ms:
                        newest_ts_ms = ev.block_ts_ms
                    if await _persist_deposit(pool, w=w, ev=ev):
                        inserted += 1
                stats[f"deposits_{stream}"] += inserted
                ok_any = True

                new_ts = (
                    datetime.fromtimestamp(newest_ts_ms / 1000, tz=timezone.utc)
                    if newest_ts_ms else None
                )
                await _touch_cursor(pool, wallet_id=w["id"], col=cursor_col, new_ts=new_ts)

            if ok_any:
                await _clear_error(pool, w["id"])
    return stats


async def _persist_deposit(pool, *, w, ev: DepositEvent) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO deposits
                (merchant_id, wallet_id, end_user_id, network, tx_hash,
                 log_index, from_address, to_address, asset, amount,
                 confirmations, block_number, block_timestamp, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 0, $11, $12, 'confirmed')
            ON CONFLICT (network, tx_hash, log_index) DO NOTHING
            RETURNING id
            """,
            UUID(w["merchant_id"]),
            UUID(w["id"]),
            UUID(w["end_user_id"]) if w["end_user_id"] else None,
            w["network"],
            ev.tx_hash,
            ev.log_index,
            ev.from_address,
            w["addr"],
            ev.asset,
            ev.amount,
            ev.block_number,
            datetime.fromtimestamp(ev.block_ts_ms / 1000, tz=timezone.utc) if ev.block_ts_ms else None,
        )
    if row is None:
        return False
    logger.info(
        "deposit recorded merchant=%s wallet=%s network=%s asset=%s amount=%s tx=%s",
        w["merchant_id"], w["id"], w["network"], ev.asset, ev.amount, ev.tx_hash,
    )
    try:
        from backend.services.webhook_publisher import (
            publish_event,
            EV_WALLET_DEPOSIT,
        )
        await publish_event(
            pool,
            merchant_id=w["merchant_id"],
            event_type=EV_WALLET_DEPOSIT,
            payload={
                "deposit_id": str(row["id"]),
                "wallet_id": w["id"],
                "end_user_id": w["end_user_id"],
                "network": w["network"],
                "tx_hash": ev.tx_hash,
                "log_index": ev.log_index,
                "from_address": ev.from_address,
                "to_address": w["addr"],
                "asset": ev.asset,
                "amount": str(ev.amount),
                "block_number": ev.block_number,
            },
        )
    except Exception as e:
        logger.warning("webhook publish failed tx=%s err=%s", ev.tx_hash, e)
    return True


def _default_since() -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=INITIAL_BACKFILL_HOURS)


async def _touch_cursor(pool, *, wallet_id: str, col: str, new_ts: Optional[datetime]) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            f"""
            INSERT INTO deposit_watch_cursors
                (wallet_id, {col}, last_polled_at, error_streak, last_error)
            VALUES ($1, $2, now(), 0, NULL)
            ON CONFLICT (wallet_id) DO UPDATE SET
                {col}          = COALESCE(EXCLUDED.{col}, deposit_watch_cursors.{col}),
                last_polled_at = EXCLUDED.last_polled_at
            """,
            UUID(wallet_id),
            new_ts,
        )


async def _clear_error(pool, wallet_id: str) -> None:
    async with pool.acquire() as conn:
        await conn.execute(
            "UPDATE deposit_watch_cursors SET error_streak = 0, last_error = NULL WHERE wallet_id = $1",
            UUID(wallet_id),
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
