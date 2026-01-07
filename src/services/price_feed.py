"""Price feed service with Redis caching and multiple API fallbacks."""

import asyncio
from datetime import datetime
from decimal import Decimal
from typing import Optional

import httpx
from redis.asyncio import Redis

from ..config import settings
from .logging_config import get_logger

logger = get_logger(__name__)

# Asset ID mappings for APIs
COINGECKO_ASSET_MAP = {
    "XRP": "ripple",
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
}

COINCAP_ASSET_MAP = {
    "XRP": "ripple",
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
}


class PriceFeedService:
    """
    Cryptocurrency price feed service with Redis caching.

    Features:
    - Primary: CoinGecko API (free tier)
    - Fallback: CoinCap API
    - Redis caching with 5-minute TTL
    - Graceful degradation if cache unavailable

    Example:
        service = PriceFeedService()
        price = await service.get_price("XRP")
        print(f"XRP price: ${price}")
    """

    def __init__(self):
        """Initialize price feed service with Redis and HTTP clients."""
        # Redis client for caching
        try:
            self.redis = Redis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
            )
            logger.info(f"Redis client initialized - URL: {settings.redis_url}")
        except Exception as e:
            logger.warning(
                f"Redis init failed: {str(e)} - Will operate without cache"
            )
            self.redis = None

        # HTTP client for API calls
        self.http_client = httpx.AsyncClient(timeout=10.0)

        logger.info("price_feed_service_initialized")

    def _get_cache_key(self, asset: str) -> str:
        """
        Generate cache key with 5-minute bucketing.

        Args:
            asset: Asset symbol (XRP, BTC, ETH)

        Returns:
            Cache key string

        Example:
            price:XRP:2026-01-06T10:05:00
        """
        now = datetime.now()
        # Round down to 5-minute intervals
        minute = (now.minute // 5) * 5
        bucket = now.replace(minute=minute, second=0, microsecond=0)
        return f"price:{asset}:{bucket.isoformat()}"

    async def _get_from_cache(self, asset: str) -> Optional[Decimal]:
        """
        Try to get price from Redis cache.

        Args:
            asset: Asset symbol

        Returns:
            Cached price or None if not found/unavailable
        """
        if self.redis is None:
            return None

        try:
            key = self._get_cache_key(asset)
            cached = await self.redis.get(key)

            if cached:
                logger.info(f"Cache hit - Asset: {asset}, Key: {key}")
                return Decimal(cached)

        except Exception as e:
            logger.warning(f"Cache read failed for {asset}: {str(e)}")

        return None

    async def _set_cache(self, asset: str, price: Decimal) -> None:
        """
        Store price in Redis cache with 5-minute TTL.

        Args:
            asset: Asset symbol
            price: Price to cache
        """
        if self.redis is None:
            return

        try:
            key = self._get_cache_key(asset)
            await self.redis.setex(key, 300, str(price))  # 300s = 5min TTL

            logger.info(f"Cache set - Asset: {asset}, Price: {price}, TTL: 300s")

        except Exception as e:
            logger.warning(f"Cache write failed for {asset}: {str(e)}")

    async def _fetch_from_coingecko(self, asset: str) -> Decimal:
        """
        Fetch price from CoinGecko API.

        Args:
            asset: Asset symbol (XRP, BTC, ETH)

        Returns:
            Current price in USD

        Raises:
            httpx.HTTPError: If API request fails
            KeyError: If asset not found in response
        """
        coin_id = COINGECKO_ASSET_MAP.get(asset)
        if not coin_id:
            raise ValueError(f"Unsupported asset: {asset}")

        url = "https://api.coingecko.com/api/v3/simple/price"
        params = {"ids": coin_id, "vs_currencies": "usd"}

        logger.info(f"Fetching from CoinGecko - Asset: {asset}, Coin ID: {coin_id}")

        response = await self.http_client.get(url, params=params)
        response.raise_for_status()

        data = response.json()
        price = Decimal(str(data[coin_id]["usd"]))

        logger.info(f"CoinGecko success - Asset: {asset}, Price: ${price}")

        return price

    async def _fetch_from_coincap(self, asset: str) -> Decimal:
        """
        Fetch price from CoinCap API (fallback).

        Args:
            asset: Asset symbol (XRP, BTC, ETH)

        Returns:
            Current price in USD

        Raises:
            httpx.HTTPError: If API request fails
            KeyError: If asset not found in response
        """
        asset_id = COINCAP_ASSET_MAP.get(asset)
        if not asset_id:
            raise ValueError(f"Unsupported asset: {asset}")

        url = f"https://api.coincap.io/v2/assets/{asset_id}"

        logger.info(f"Fetching from CoinCap - Asset: {asset}, Asset ID: {asset_id}")

        response = await self.http_client.get(url)
        response.raise_for_status()

        data = response.json()
        price = Decimal(data["data"]["priceUsd"])

        logger.info(f"CoinCap success - Asset: {asset}, Price: ${price}")

        return price

    async def get_price(self, asset: str) -> Decimal:
        """
        Get current price for an asset with caching and fallback.

        Flow:
        1. Check Redis cache
        2. Try CoinGecko API
        3. Fallback to CoinCap API
        4. Cache result

        Args:
            asset: Asset symbol (XRP, BTC, ETH)

        Returns:
            Current price in USD

        Raises:
            ValueError: If asset not supported
            Exception: If all API sources fail

        Example:
            price = await service.get_price("XRP")
            print(f"${price}")
        """
        # Check cache first
        cached_price = await self._get_from_cache(asset)
        if cached_price is not None:
            return cached_price

        # Try CoinGecko first
        try:
            price = await self._fetch_from_coingecko(asset)
            await self._set_cache(asset, price)
            return price

        except Exception as e:
            logger.warning(
                f"CoinGecko failed for {asset}: {type(e).__name__}: {str(e)} - Falling back to CoinCap"
            )

            # Fallback to CoinCap
            try:
                price = await self._fetch_from_coincap(asset)
                await self._set_cache(asset, price)
                return price

            except Exception as fallback_error:
                logger.error(
                    f"All price sources failed for {asset} - CoinGecko: {str(e)}, CoinCap: {str(fallback_error)}"
                )
                raise

    async def get_multi_asset_prices(
        self, assets: list[str]
    ) -> dict[str, dict[str, Decimal]]:
        """
        Fetch prices for multiple assets concurrently.

        Args:
            assets: Asset symbols (e.g., ["BTC", "ETH", "SOL"])

        Returns:
            Mapping of asset symbol to price payload.
        """
        results: dict[str, dict[str, Decimal]] = {}
        tasks: dict[str, asyncio.Task[Decimal]] = {}

        for asset in assets:
            symbol = asset.upper()
            tasks[symbol] = asyncio.create_task(self.get_price(symbol))

        for symbol, task in tasks.items():
            try:
                price = await task
                results[symbol] = {"price": price, "volume": Decimal("0")}
            except Exception as e:
                logger.warning(
                    f"Failed to fetch price for {symbol}: {type(e).__name__}: {str(e)}"
                )

        return results

    async def get_historical_prices(
        self, asset: str, hours: int = 24
    ) -> list[dict[str, any]]:
        """
        Get historical prices for an asset (placeholder for future implementation).

        Args:
            asset: Asset symbol (XRP, BTC, ETH)
            hours: Number of hours of historical data

        Returns:
            List of price points with timestamps

        Note:
            This is a placeholder. Full implementation requires historical
            data endpoints from CoinGecko or CoinCap.
        """
        logger.warning(
            f"Historical prices not implemented - Asset: {asset}, Hours: {hours}"
        )
        raise NotImplementedError(
            "Historical price fetching not yet implemented. "
            "Will be added in future updates."
        )

    async def close(self) -> None:
        """Close HTTP client and Redis connections."""
        await self.http_client.aclose()

        if self.redis:
            await self.redis.close()

        logger.info("price_feed_service_closed")
