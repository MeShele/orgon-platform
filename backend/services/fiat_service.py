"""Fiat Service — On-ramp, Off-ramp, Payment Gateways."""
import asyncpg
from typing import Optional, List, Dict
from uuid import UUID
from datetime import datetime
from decimal import Decimal

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
    
    async def get_exchange_rate(self, crypto: str, fiat: str) -> float:
        """Get cached exchange rate or fetch new one."""
        # Mock rates (use CoinGecko API in production)
        mock_rates = {
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
        
        try:
            async with self.pool.acquire() as conn:
                # Try cache (last 5 minutes)
                row = await conn.fetchrow("""
                    SELECT rate FROM crypto_exchange_rates
                    WHERE crypto_currency = $1 AND fiat_currency = $2
                    AND fetched_at > NOW() - INTERVAL '5 minutes'
                    ORDER BY fetched_at DESC LIMIT 1
                """, crypto, fiat)
                
                if row:
                    return float(row['rate'])
        except Exception:
            pass  # DB read failure — fall through to mock
        
        rate = mock_rates.get((crypto, fiat), 1.0)
        
        # Try to cache (non-critical)
        try:
            async with self.pool.acquire() as conn:
                await conn.execute("""
                    INSERT INTO crypto_exchange_rates (crypto_currency, fiat_currency, rate)
                    VALUES ($1, $2, $3)
                """, crypto, fiat, rate)
        except Exception:
            pass
        
        return rate
