"""On-chain deposit watcher.

V1 streams:
  * Tron native (TRX)  — /v1/accounts/{addr}/transactions
  * Tron TRC20 (USDT…) — /v1/accounts/{addr}/transactions/trc20

Each stream has its own cursor in deposit_watch_cursors so the two
don't truncate each other. Later sprints add BTC (Esplora) and ETH
(Alchemy/Etherscan) the same way.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

import httpx

logger = logging.getLogger("orgon.deposit_watcher")

NETWORK_EXPLORERS: dict[int, str] = {
    5010: "https://nile.trongrid.io",
    5000: "https://api.trongrid.io",
}

# TRC20 contract addresses we recognise. Anything not in this map is
# still recorded but with asset=<contract addr> — merchants can map
# the rest in their own systems. Keep the canonical token symbol
# uppercase.
TRC20_KNOWN: dict[int, dict[str, str]] = {
    5010: {  # Nile testnet
        "TXYZopYRdj2D9XRtbG411XZZ3kM5VkAeBf": "USDT",
        "TLBaRhANQoJFTqre9Nf1mjuwNWjCJeYqUL": "USDT",
        "TXLAQ63Xg1NAzckPwKHvzw7CSEmLMEqcdj": "USDT",
    },
    5000: {  # mainnet
        "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t": "USDT",
        "TEkxiTehnzSmSe2XqrBj4w32RUN966rdz8": "USDC",
    },
}

INITIAL_BACKFILL_HOURS = 1
MAX_WALLETS_PER_TICK = 50          # 2 requests per wallet → 100 explorer calls/tick
HTTP_TIMEOUT_S = 8.0


async def run_tick(pool) -> dict:
    stats = {
        "wallets_scanned": 0,
        "deposits_native": 0,
        "deposits_trc20": 0,
        "explorer_errors": 0,
        "skipped_unsupported_network": 0,
    }

    async with pool.acquire() as conn:
        wallets = await conn.fetch(
            """
            SELECT w.id::text, w.organization_id::text AS merchant_id,
                   w.end_user_id::text AS end_user_id, w.network, w.addr,
                   c.last_seen_ts_native, c.last_seen_ts_trc20
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
        for w in wallets:
            if w["network"] not in NETWORK_EXPLORERS:
                stats["skipped_unsupported_network"] += 1
                continue
            stats["wallets_scanned"] += 1
            ok_any = False
            try:
                n = await _scan_tron_native(
                    client=client, pool=pool, w=w,
                )
                stats["deposits_native"] += n
                ok_any = True
            except Exception as e:
                stats["explorer_errors"] += 1
                logger.warning("native scan failed wallet=%s err=%s", w["id"], e)
                await _record_error(pool, w["id"], f"native: {str(e)[:200]}")
            try:
                n = await _scan_tron_trc20(
                    client=client, pool=pool, w=w,
                )
                stats["deposits_trc20"] += n
                ok_any = True
            except Exception as e:
                stats["explorer_errors"] += 1
                logger.warning("trc20 scan failed wallet=%s err=%s", w["id"], e)
                await _record_error(pool, w["id"], f"trc20: {str(e)[:200]}")
            if ok_any:
                # Clear streak after at least one successful stream.
                await _clear_error(pool, w["id"])
    return stats


async def _scan_tron_native(
    *, client: httpx.AsyncClient, pool, w
) -> int:
    base = NETWORK_EXPLORERS[w["network"]]
    since = w["last_seen_ts_native"] or _default_since()
    url = f"{base}/v1/accounts/{w['addr']}/transactions"
    params = {
        "only_to": "true",
        "only_confirmed": "true",
        "min_timestamp": str(int(since.timestamp() * 1000)),
        "limit": "50",
    }
    r = await client.get(url, params=params)
    r.raise_for_status()
    txs = (r.json() or {}).get("data") or []
    if not txs:
        await _touch_cursor(pool, wallet_id=w["id"], stream="native", new_ts=None)
        return 0

    inserted = 0
    newest_ts_ms = 0
    for tx in txs:
        tx_id = tx.get("txID") or tx.get("transaction_id")
        if not tx_id:
            continue
        ret = (tx.get("ret") or [{}])[0].get("contractRet")
        if ret != "SUCCESS":
            continue
        ts_ms = int(tx.get("block_timestamp") or 0)
        if ts_ms > newest_ts_ms:
            newest_ts_ms = ts_ms
        block_n = int(tx.get("blockNumber") or 0) or None
        contracts = (tx.get("raw_data") or {}).get("contract") or []
        if not contracts or contracts[0].get("type") != "TransferContract":
            continue
        v = (contracts[0].get("parameter") or {}).get("value") or {}
        amount_sun = int(v.get("amount") or 0)
        if amount_sun <= 0:
            continue
        amount = Decimal(amount_sun) / Decimal(1_000_000)
        from_addr = v.get("owner_address_base58") or v.get("owner_address") or ""

        if await _insert_deposit(
            pool,
            merchant_id=w["merchant_id"],
            wallet_id=w["id"],
            end_user_id=w["end_user_id"],
            network=w["network"],
            tx_hash=tx_id,
            log_index=0,
            from_addr=from_addr,
            to_addr=w["addr"],
            asset="TRX",
            amount=amount,
            block_number=block_n,
            block_ts_ms=ts_ms,
        ):
            inserted += 1

    await _touch_cursor(
        pool,
        wallet_id=w["id"],
        stream="native",
        new_ts=datetime.fromtimestamp(newest_ts_ms / 1000, tz=timezone.utc) if newest_ts_ms else None,
    )
    return inserted


async def _scan_tron_trc20(
    *, client: httpx.AsyncClient, pool, w
) -> int:
    base = NETWORK_EXPLORERS[w["network"]]
    since = w["last_seen_ts_trc20"] or _default_since()
    url = f"{base}/v1/accounts/{w['addr']}/transactions/trc20"
    params = {
        "only_to": "true",
        "only_confirmed": "true",
        "min_timestamp": str(int(since.timestamp() * 1000)),
        "limit": "50",
    }
    r = await client.get(url, params=params)
    r.raise_for_status()
    txs = (r.json() or {}).get("data") or []
    if not txs:
        await _touch_cursor(pool, wallet_id=w["id"], stream="trc20", new_ts=None)
        return 0

    inserted = 0
    newest_ts_ms = 0
    for tx in txs:
        tx_id = tx.get("transaction_id")
        if not tx_id:
            continue
        ts_ms = int(tx.get("block_timestamp") or 0)
        if ts_ms > newest_ts_ms:
            newest_ts_ms = ts_ms
        token_info = tx.get("token_info") or {}
        contract = (tx.get("token_info") or {}).get("address") or ""
        decimals = int(token_info.get("decimals") or 6)
        symbol = (
            TRC20_KNOWN.get(w["network"], {}).get(contract)
            or token_info.get("symbol")
            or contract
        )
        raw_value = tx.get("value") or "0"
        try:
            amount = Decimal(raw_value) / (Decimal(10) ** decimals)
        except Exception:
            continue
        if amount <= 0:
            continue
        from_addr = tx.get("from") or ""
        log_index = int(tx.get("event_index") or 0)

        if await _insert_deposit(
            pool,
            merchant_id=w["merchant_id"],
            wallet_id=w["id"],
            end_user_id=w["end_user_id"],
            network=w["network"],
            tx_hash=tx_id,
            log_index=log_index,
            from_addr=from_addr,
            to_addr=w["addr"],
            asset=symbol,
            amount=amount,
            block_number=None,  # TRC20 endpoint doesn't include it directly
            block_ts_ms=ts_ms,
        ):
            inserted += 1

    await _touch_cursor(
        pool,
        wallet_id=w["id"],
        stream="trc20",
        new_ts=datetime.fromtimestamp(newest_ts_ms / 1000, tz=timezone.utc) if newest_ts_ms else None,
    )
    return inserted


async def _insert_deposit(
    pool,
    *,
    merchant_id: str,
    wallet_id: str,
    end_user_id: Optional[str],
    network: int,
    tx_hash: str,
    log_index: int,
    from_addr: str,
    to_addr: str,
    asset: str,
    amount: Decimal,
    block_number: Optional[int],
    block_ts_ms: int,
) -> bool:
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            INSERT INTO deposits
                (merchant_id, wallet_id, end_user_id, network, tx_hash,
                 log_index, from_address, to_address, asset, amount,
                 confirmations, block_number, block_timestamp, status)
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, 19, $11, $12, 'confirmed')
            ON CONFLICT (network, tx_hash, log_index) DO NOTHING
            RETURNING id
            """,
            UUID(merchant_id),
            UUID(wallet_id),
            UUID(end_user_id) if end_user_id else None,
            network,
            tx_hash,
            log_index,
            from_addr,
            to_addr,
            asset,
            amount,
            block_number,
            datetime.fromtimestamp(block_ts_ms / 1000, tz=timezone.utc) if block_ts_ms else None,
        )
    if row is None:
        return False
    logger.info(
        "deposit recorded merchant=%s wallet=%s asset=%s amount=%s tx=%s",
        merchant_id, wallet_id, asset, amount, tx_hash,
    )
    # Fire the webhook event. Non-fatal on failure — deposit row is
    # source of truth, a manual replay tool can re-publish.
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
                "tx_hash": tx_hash,
                "log_index": log_index,
                "from_address": from_addr,
                "to_address": to_addr,
                "asset": asset,
                "amount": str(amount),
                "block_number": block_number,
            },
        )
    except Exception as e:
        logger.warning("webhook publish failed tx=%s err=%s", tx_hash, e)
    return True


def _default_since() -> datetime:
    return datetime.now(timezone.utc) - timedelta(hours=INITIAL_BACKFILL_HOURS)


async def _touch_cursor(
    pool, *, wallet_id: str, stream: str, new_ts: Optional[datetime]
) -> None:
    col = "last_seen_ts_native" if stream == "native" else "last_seen_ts_trc20"
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
            """
            UPDATE deposit_watch_cursors
               SET error_streak = 0, last_error = NULL
             WHERE wallet_id = $1
            """,
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
