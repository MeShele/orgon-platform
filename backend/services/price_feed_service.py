"""
Price Feed Service - Cryptocurrency price data from CoinGecko
Provides USD conversion for analytics and reporting
"""

import httpx
import asyncio
import logging
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone


logger = logging.getLogger("orgon.services.price_feed")


class PriceFeedService:
    """
    Cryptocurrency price feed from CoinGecko API (free tier).
    
    Features:
    - Real-time price data for major cryptocurrencies
    - In-memory caching (5 min TTL)
    - Batch requests (multi-coin support)
    - Fallback to last known price on API failure
    - Rate limit compliance (10-50 calls/min free tier)
    """
    
    # CoinGecko coin IDs mapping
    COIN_IDS = {
        "TRX": "tron",
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "USDT": "tether",
        "USDC": "usd-coin",
        "BUSD": "binance-usd",
        "DAI": "dai",
        "WBTC": "wrapped-bitcoin",
        "WETH": "weth",
        "BNB": "binancecoin",
    }
    
    # Reverse mapping
    COIN_IDS_REVERSE = {v: k for k, v in COIN_IDS.items()}
    
    def __init__(
        self,
        base_url: str = "https://api.coingecko.com/api/v3",
        cache_ttl_seconds: int = 300,  # 5 minutes
        timeout: float = 10.0
    ):
        """
        Initialize Price Feed Service.
        
        Args:
            base_url: CoinGecko API base URL
            cache_ttl_seconds: Cache TTL in seconds (default: 5 min)
            timeout: HTTP timeout in seconds
        """
        self.base_url = base_url
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)
        self.timeout = timeout
        
        # In-memory cache: {coin_id: {"price": float, "timestamp": datetime}}
        self._cache: Dict[str, Dict] = {}
        
        # HTTP client
        self.http_client = httpx.AsyncClient(timeout=self.timeout)
    
    async def get_price(self, symbol: str, vs_currency: str = "usd") -> Optional[float]:
        """
        Get current price for a single cryptocurrency.
        
        Args:
            symbol: Coin symbol (TRX, BTC, ETH, etc.)
            vs_currency: Target currency (default: usd)
            
        Returns:
            Price in target currency or None if not available
        """
        prices = await self.get_prices([symbol], vs_currency)
        return prices.get(symbol)
    
    async def get_prices(
        self, 
        symbols: List[str], 
        vs_currency: str = "usd"
    ) -> Dict[str, float]:
        """
        Get current prices for multiple cryptocurrencies.
        
        Args:
            symbols: List of coin symbols (TRX, BTC, ETH, etc.)
            vs_currency: Target currency (default: usd)
            
        Returns:
            Dictionary mapping symbols to prices
            Example: {"TRX": 0.065, "BTC": 45000.0}
        """
        # Convert symbols to CoinGecko IDs
        coin_ids = []
        symbol_to_id = {}
        
        for symbol in symbols:
            coin_id = self.COIN_IDS.get(symbol.upper())
            if coin_id:
                coin_ids.append(coin_id)
                symbol_to_id[symbol.upper()] = coin_id
            else:
                logger.warning(f"Unknown coin symbol: {symbol}")
        
        if not coin_ids:
            return {}
        
        # Check cache first
        now = datetime.now(timezone.utc)
        cached_prices = {}
        missing_coin_ids = []
        
        for symbol, coin_id in symbol_to_id.items():
            cached = self._cache.get(coin_id)
            if cached and (now - cached["timestamp"]) < self.cache_ttl:
                cached_prices[symbol] = cached["price"]
                logger.debug(f"Cache hit for {symbol}: ${cached['price']}")
            else:
                missing_coin_ids.append(coin_id)
        
        # Fetch missing prices from API
        if missing_coin_ids:
            try:
                api_prices = await self._fetch_prices_from_api(missing_coin_ids, vs_currency)
                
                # Update cache
                for coin_id, price in api_prices.items():
                    self._cache[coin_id] = {
                        "price": price,
                        "timestamp": now
                    }
                    
                    # Convert back to symbol
                    symbol = self.COIN_IDS_REVERSE.get(coin_id)
                    if symbol:
                        cached_prices[symbol] = price
                
                logger.info(f"Fetched prices for {len(api_prices)} coins from CoinGecko")
                
            except Exception as e:
                logger.error(f"Failed to fetch prices from CoinGecko: {e}")
                
                # Fallback to last known price (even if expired)
                for coin_id in missing_coin_ids:
                    cached = self._cache.get(coin_id)
                    if cached:
                        symbol = self.COIN_IDS_REVERSE.get(coin_id)
                        if symbol and symbol not in cached_prices:
                            cached_prices[symbol] = cached["price"]
                            logger.warning(
                                f"Using stale price for {symbol}: ${cached['price']} "
                                f"(age: {(now - cached['timestamp']).total_seconds()}s)"
                            )
        
        return cached_prices
    
    async def _fetch_prices_from_api(
        self,
        coin_ids: List[str],
        vs_currency: str
    ) -> Dict[str, float]:
        """
        Fetch prices from CoinGecko API.
        
        Args:
            coin_ids: List of CoinGecko coin IDs
            vs_currency: Target currency
            
        Returns:
            Dictionary mapping coin IDs to prices
        """
        # CoinGecko simple price endpoint (supports batch requests)
        url = f"{self.base_url}/simple/price"
        
        params = {
            "ids": ",".join(coin_ids),
            "vs_currencies": vs_currency
        }
        
        response = await self.http_client.get(url, params=params)
        response.raise_for_status()
        
        data = response.json()
        
        # Parse response
        # Example: {"tron": {"usd": 0.065}, "bitcoin": {"usd": 45000.0}}
        prices = {}
        for coin_id in coin_ids:
            if coin_id in data and vs_currency in data[coin_id]:
                prices[coin_id] = float(data[coin_id][vs_currency])
        
        return prices
    
    async def convert_to_usd(self, amount: float, symbol: str) -> Optional[float]:
        """
        Convert amount in cryptocurrency to USD.
        
        Args:
            amount: Amount in cryptocurrency
            symbol: Coin symbol (TRX, BTC, etc.)
            
        Returns:
            USD equivalent or None if price not available
        """
        price = await self.get_price(symbol)
        if price is None:
            return None
        
        return amount * price
    
    def clear_cache(self):
        """Clear price cache."""
        self._cache.clear()
        logger.info("Price cache cleared")
    
    def get_cache_stats(self) -> Dict:
        """Get cache statistics."""
        now = datetime.now(timezone.utc)
        fresh_count = 0
        stale_count = 0
        
        for coin_id, cached in self._cache.items():
            age = now - cached["timestamp"]
            if age < self.cache_ttl:
                fresh_count += 1
            else:
                stale_count += 1
        
        return {
            "total_cached": len(self._cache),
            "fresh": fresh_count,
            "stale": stale_count,
            "ttl_seconds": self.cache_ttl.total_seconds()
        }
    
    async def close(self):
        """Close HTTP client."""
        await self.http_client.aclose()
        logger.info("PriceFeedService HTTP client closed")


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

_price_feed_service: Optional[PriceFeedService] = None


def get_price_feed_service() -> PriceFeedService:
    """Get singleton PriceFeedService instance."""
    global _price_feed_service
    if _price_feed_service is None:
        _price_feed_service = PriceFeedService()
    return _price_feed_service


async def close_price_feed_service():
    """Close singleton PriceFeedService instance."""
    global _price_feed_service
    if _price_feed_service is not None:
        await _price_feed_service.close()
        _price_feed_service = None
