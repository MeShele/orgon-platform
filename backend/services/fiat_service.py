"""Fiat Service — On-ramp, Off-ramp, Payment Gateways."""
import asyncpg
import httpx
import time
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime
from decimal import Decimal

# In-memory cache for CoinGecko rates: {(crypto, fiat): (rate, timestamp)}
_rate_cache: Dict[tuple, tuple] = {}
_RATE_CACHE_TTL = 60  # seconds

# CoinGecko ID mapping
_COINGECKO_IDS = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "TRX": "tron",
}

class FiatService:
    def __init__(self, pool: asyncpg.Pool):
        self.pool = pool
    
    # ==================== Fiat Transactions ====================
    
    async def create_onramp_transaction(self, org_id: UUID, user_id: UUID,
                                         fiat_amount: Decimal, fiat_currency: str,
                                         crypto_currency: str, payment_method: str) -> Dict:
        """Create on-ramp transaction (buy crypto with fiat)."""
        # Get exchange rate
        rate = await self.get_exchange_rate(crypto_currency, fiat_currency)
        crypto_amount = fiat_amount / Decimal(str(rate))
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO fiat_transactions (
                    organization_id, user_id, transaction_type,
                    fiat_amount, fiat_currency, crypto_amount, crypto_currency,
                    exchange_rate, payment_method, status
                ) VALUES ($1, $2, 'onramp', $3, $4, $5, $6, $7, $8, 'pending')
                RETURNING *
            """, org_id, user_id, fiat_amount, fiat_currency,
                crypto_amount, crypto_currency, rate, payment_method)
            return dict(row)
    
    async def create_offramp_transaction(self, org_id: UUID, user_id: UUID,
                                          crypto_amount: Decimal, crypto_currency: str,
                                          fiat_currency: str, bank_account_id: UUID) -> Dict:
        """Create off-ramp transaction (sell crypto for fiat)."""
        rate = await self.get_exchange_rate(crypto_currency, fiat_currency)
        fiat_amount = crypto_amount * Decimal(str(rate))
        
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO fiat_transactions (
                    organization_id, user_id, transaction_type,
                    fiat_amount, fiat_currency, crypto_amount, crypto_currency,
                    exchange_rate, bank_account_id, status
                ) VALUES ($1, $2, 'offramp', $3, $4, $5, $6, $7, $8, 'pending')
                RETURNING *
            """, org_id, user_id, fiat_amount, fiat_currency,
                crypto_amount, crypto_currency, rate, bank_account_id)
            return dict(row)
    
    async def get_fiat_transactions(self, org_id: UUID, user_id: Optional[UUID] = None,
                                     limit: int = 50) -> List[Dict]:
        """Get fiat transactions."""
        async with self.pool.acquire() as conn:
            if user_id:
                rows = await conn.fetch("""
                    SELECT * FROM fiat_transactions
                    WHERE organization_id = $1 AND user_id = $2
                    ORDER BY created_at DESC LIMIT $3
                """, org_id, user_id, limit)
            else:
                rows = await conn.fetch("""
                    SELECT * FROM fiat_transactions WHERE organization_id = $1
                    ORDER BY created_at DESC LIMIT $2
                """, org_id, limit)
            return [dict(r) for r in rows]
    
    async def update_transaction_status(self, txn_id: UUID, status: str,
                                         gateway_txn_id: Optional[str] = None) -> Dict:
        """Update fiat transaction status."""
        async with self.pool.acquire() as conn:
            now = datetime.utcnow()
            row = await conn.fetchrow("""
                UPDATE fiat_transactions
                SET status = $1,
                    gateway_transaction_id = COALESCE($2, gateway_transaction_id),
                    processed_at = CASE WHEN $1 = 'processing' THEN $3 ELSE processed_at END,
                    completed_at = CASE WHEN $1 = 'completed' THEN $3 ELSE completed_at END
                WHERE id = $4
                RETURNING *
            """, status, gateway_txn_id, now, txn_id)
            return dict(row) if row else None
    
    # ==================== Bank Accounts ====================
    
    async def add_bank_account(self, org_id: UUID, user_id: UUID,
                                account_holder_name: str, account_number_last4: str,
                                bank_country: str, currency: str = 'USD') -> Dict:
        """Add bank account for withdrawals."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow("""
                INSERT INTO bank_accounts (
                    organization_id, user_id, account_holder_name,
                    account_number_last4, bank_country, currency
                ) VALUES ($1, $2, $3, $4, $5, $6)
                RETURNING *
            """, org_id, user_id, account_holder_name,
                account_number_last4, bank_country, currency)
            return dict(row)
    
    async def get_bank_accounts(self, org_id: UUID, user_id: UUID) -> List[Dict]:
        """Get user bank accounts."""
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM bank_accounts
                WHERE organization_id = $1 AND user_id = $2 AND is_active = TRUE
                ORDER BY created_at DESC
            """, org_id, user_id)
            return [dict(r) for r in rows]
    
    # ==================== Exchange Rates ====================
    
    async def _fetch_coingecko_rates(self) -> Dict[str, float]:
        """Fetch USD rates from CoinGecko free API. Returns {crypto_symbol: usd_rate}."""
        ids = ",".join(_COINGECKO_IDS.values())
        url = f"https://api.coingecko.com/api/v3/simple/price?ids={ids}&vs_currencies=usd"
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
        rates = {}
        for symbol, cg_id in _COINGECKO_IDS.items():
            if cg_id in data and "usd" in data[cg_id]:
                rates[symbol] = float(data[cg_id]["usd"])
        return rates

    async def get_exchange_rate(self, crypto: str, fiat: str) -> float:
        """Get cached exchange rate or fetch new one."""
        # Hardcoded fallback rates
        fallback_rates = {
            ('BTC', 'USD'): 98000.0,
            ('ETH', 'USD'): 3500.0,
            ('USDT', 'USD'): 1.0,
            ('TRX', 'USD'): 0.25,
            ('BTC', 'EUR'): 92000.0,
            ('ETH', 'EUR'): 3300.0,
            ('USDT', 'EUR'): 0.94,
            ('BTC', 'KGS'): 8500000.0,
            ('USDT', 'KGS'): 87.0,
        }

        # Check in-memory cache first (60s TTL)
        cache_key = (crypto, fiat)
        cached = _rate_cache.get(cache_key)
        if cached and (time.time() - cached[1]) < _RATE_CACHE_TTL:
            return cached[0]

        # Try DB cache (last 5 minutes)
        try:
            async with self.pool.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT rate FROM crypto_exchange_rates
                    WHERE crypto_currency = $1 AND fiat_currency = $2
                    AND fetched_at > NOW() - INTERVAL '5 minutes'
                    ORDER BY fetched_at DESC LIMIT 1
                """, crypto, fiat)
                if row:
                    rate = float(row['rate'])
                    _rate_cache[cache_key] = (rate, time.time())
                    return rate
        except Exception:
            pass  # DB read failure — fall through

        # Fetch live rates from CoinGecko (USD pairs)
        rate = None
        if fiat.upper() == "USD" and crypto.upper() in _COINGECKO_IDS:
            try:
                live_rates = await self._fetch_coingecko_rates()
                if crypto.upper() in live_rates:
                    rate = live_rates[crypto.upper()]
            except Exception:
                pass  # API failure — fall through to fallback
        # Stablecoins always 1:1
        if rate is None and crypto.upper() == "USDT" and fiat.upper() == "USD":
            rate = 1.0

        # Fallback to hardcoded rates
        if rate is None:
            rate = fallback_rates.get((crypto, fiat), 1.0)

        # Update in-memory cache
        _rate_cache[cache_key] = (rate, time.time())

        # Try to persist to DB (non-critical)
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO crypto_exchange_rates (crypto_currency, fiat_currency, rate)
                    VALUES ($1, $2, $3)
                """, crypto, fiat, rate)
        except Exception:
            pass

        return rate
