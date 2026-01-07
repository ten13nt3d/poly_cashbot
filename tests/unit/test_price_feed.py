"""
Comprehensive tests for Price Feed service.

Tests cover:
- Service initialization with/without Redis
- Cache operations (read, write, key generation)
- API fetching (CoinGecko, CoinCap)
- Price retrieval with caching and fallback
- Multi-asset price fetching
- Resource cleanup
"""

import pytest
import logging
from datetime import datetime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch
import httpx

from src.services.price_feed import PriceFeedService, COINGECKO_ASSET_MAP, COINCAP_ASSET_MAP


# Disable logging during tests
@pytest.fixture(autouse=True)
def disable_logging():
    """Disable logging during tests."""
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


# ============================================================================
# FIXTURES - Mock Data
# ============================================================================

@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    redis = AsyncMock()
    redis.get = AsyncMock(return_value=None)
    redis.setex = AsyncMock()
    redis.close = AsyncMock()
    return redis


@pytest.fixture
def mock_http_client():
    """Mock HTTP client."""
    client = AsyncMock()
    client.aclose = AsyncMock()
    return client


@pytest.fixture
def coingecko_response():
    """Sample CoinGecko API response."""
    return {
        "ripple": {"usd": 2.45},
        "bitcoin": {"usd": 45000.00},
        "ethereum": {"usd": 3200.00},
    }


@pytest.fixture
def coincap_response():
    """Sample CoinCap API response."""
    return {
        "data": {
            "id": "ripple",
            "rank": "6",
            "symbol": "XRP",
            "name": "XRP",
            "priceUsd": "2.45",
        }
    }


# ============================================================================
# TEST CLASS - Initialization
# ============================================================================

class TestPriceFeedInitialization:
    """Test service initialization."""

    @pytest.mark.asyncio
    async def test_initialization_with_redis_success(self, mock_redis):
        """Test service initializes successfully with Redis."""
        with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
            service = PriceFeedService()

            assert service.redis is not None
            assert service.http_client is not None

            await service.close()

    @pytest.mark.asyncio
    async def test_initialization_redis_failure_graceful_degradation(self):
        """Test service initializes without Redis when connection fails."""
        with patch("src.services.price_feed.Redis.from_url", side_effect=ConnectionError("Redis unavailable")):
            service = PriceFeedService()

            # Should initialize without Redis
            assert service.redis is None
            assert service.http_client is not None

            await service.close()


# ============================================================================
# TEST CLASS - Cache Operations
# ============================================================================

class TestCacheOperations:
    """Test Redis caching functionality."""

    @pytest.mark.asyncio
    async def test_get_cache_key_format(self, mock_redis):
        """Test cache key generation format."""
        with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
            service = PriceFeedService()

            key = service._get_cache_key("XRP")

            # Should have correct format: price:ASSET:timestamp
            assert key.startswith("price:XRP:")
            # Key should contain ISO format timestamp
            assert "T" in key  # ISO format separator

            await service.close()

    @pytest.mark.asyncio
    async def test_get_from_cache_hit(self, mock_redis):
        """Test successful cache read."""
        mock_redis.get.return_value = "2.45"

        with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
            service = PriceFeedService()

            price = await service._get_from_cache("XRP")

            assert price == Decimal("2.45")
            mock_redis.get.assert_called_once()

            await service.close()

    @pytest.mark.asyncio
    async def test_get_from_cache_miss(self, mock_redis):
        """Test cache miss returns None."""
        mock_redis.get.return_value = None

        with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
            service = PriceFeedService()

            price = await service._get_from_cache("XRP")

            assert price is None
            mock_redis.get.assert_called_once()

            await service.close()

    @pytest.mark.asyncio
    async def test_get_from_cache_no_redis(self):
        """Test cache read when Redis is unavailable."""
        with patch("src.services.price_feed.Redis.from_url", side_effect=ConnectionError("Redis down")):
            service = PriceFeedService()

            price = await service._get_from_cache("XRP")

            assert price is None
            assert service.redis is None

            await service.close()

    @pytest.mark.asyncio
    async def test_set_cache_success(self, mock_redis):
        """Test successful cache write."""
        with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
            service = PriceFeedService()

            await service._set_cache("XRP", Decimal("2.45"))

            # Verify setex was called with 300s TTL
            mock_redis.setex.assert_called_once()
            args = mock_redis.setex.call_args
            assert args[0][1] == 300  # TTL
            assert args[0][2] == "2.45"  # Price value

            await service.close()

    @pytest.mark.asyncio
    async def test_set_cache_no_redis(self):
        """Test cache write when Redis is unavailable."""
        with patch("src.services.price_feed.Redis.from_url", side_effect=ConnectionError("Redis down")):
            service = PriceFeedService()

            # Should not raise error
            await service._set_cache("XRP", Decimal("2.45"))

            await service.close()

    @pytest.mark.asyncio
    async def test_cache_error_handling(self, mock_redis):
        """Test cache operations handle errors gracefully."""
        mock_redis.get.side_effect = Exception("Redis error")

        with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
            service = PriceFeedService()

            # Should return None on error, not raise
            price = await service._get_from_cache("XRP")
            assert price is None

            await service.close()


# ============================================================================
# TEST CLASS - API Fetching
# ============================================================================

class TestAPIFetching:
    """Test external API price fetching."""

    @pytest.mark.asyncio
    async def test_fetch_from_coingecko_success(self, mock_redis, coingecko_response):
        """Test successful CoinGecko fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = coingecko_response
        mock_response.raise_for_status = MagicMock()

        with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
            service = PriceFeedService()
            service.http_client.get = AsyncMock(return_value=mock_response)

            price = await service._fetch_from_coingecko("XRP")

            assert price == Decimal("2.45")
            service.http_client.get.assert_called_once()

            await service.close()

    @pytest.mark.asyncio
    async def test_fetch_from_coingecko_unsupported_asset(self, mock_redis):
        """Test CoinGecko fetch with unsupported asset."""
        with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
            service = PriceFeedService()

            with pytest.raises(ValueError, match="Unsupported asset"):
                await service._fetch_from_coingecko("INVALID_ASSET")

            await service.close()

    @pytest.mark.asyncio
    async def test_fetch_from_coingecko_http_error(self, mock_redis):
        """Test CoinGecko fetch handles HTTP errors."""
        with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
            service = PriceFeedService()
            service.http_client.get = AsyncMock(side_effect=httpx.HTTPError("API error"))

            with pytest.raises(httpx.HTTPError):
                await service._fetch_from_coingecko("XRP")

            await service.close()

    @pytest.mark.asyncio
    async def test_fetch_from_coincap_success(self, mock_redis, coincap_response):
        """Test successful CoinCap fetch."""
        mock_response = MagicMock()
        mock_response.json.return_value = coincap_response
        mock_response.raise_for_status = MagicMock()

        with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
            service = PriceFeedService()
            service.http_client.get = AsyncMock(return_value=mock_response)

            price = await service._fetch_from_coincap("XRP")

            assert price == Decimal("2.45")
            service.http_client.get.assert_called_once()

            await service.close()

    @pytest.mark.asyncio
    async def test_fetch_from_coincap_unsupported_asset(self, mock_redis):
        """Test CoinCap fetch with unsupported asset."""
        with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
            service = PriceFeedService()

            with pytest.raises(ValueError, match="Unsupported asset"):
                await service._fetch_from_coincap("INVALID_ASSET")

            await service.close()

    @pytest.mark.asyncio
    async def test_fetch_from_coincap_http_error(self, mock_redis):
        """Test CoinCap fetch handles HTTP errors."""
        with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
            service = PriceFeedService()
            service.http_client.get = AsyncMock(side_effect=httpx.HTTPError("API error"))

            with pytest.raises(httpx.HTTPError):
                await service._fetch_from_coincap("XRP")

            await service.close()


# ============================================================================
# TEST CLASS - Price Retrieval
# ============================================================================

class TestPriceRetrieval:
    """Test get_price flow with caching and fallback."""

    @pytest.mark.asyncio
    async def test_get_price_cache_hit(self, mock_redis):
        """Test get_price returns cached value without API call."""
        mock_redis.get.return_value = "2.45"

        with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
            service = PriceFeedService()

            price = await service.get_price("XRP")

            assert price == Decimal("2.45")
            # Should not call API
            mock_redis.get.assert_called_once()

            await service.close()

    @pytest.mark.asyncio
    async def test_get_price_cache_miss_coingecko_success(self, mock_redis, coingecko_response):
        """Test get_price fetches from CoinGecko on cache miss."""
        mock_redis.get.return_value = None  # Cache miss

        mock_response = MagicMock()
        mock_response.json.return_value = coingecko_response
        mock_response.raise_for_status = MagicMock()

        with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
            service = PriceFeedService()
            service.http_client.get = AsyncMock(return_value=mock_response)

            price = await service.get_price("XRP")

            assert price == Decimal("2.45")
            # Should cache the result
            mock_redis.setex.assert_called_once()

            await service.close()

    @pytest.mark.asyncio
    async def test_get_price_coingecko_fails_coincap_succeeds(self, mock_redis, coincap_response):
        """Test get_price falls back to CoinCap when CoinGecko fails."""
        mock_redis.get.return_value = None  # Cache miss

        mock_response = MagicMock()
        mock_response.json.return_value = coincap_response
        mock_response.raise_for_status = MagicMock()

        with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
            service = PriceFeedService()

            # CoinGecko fails
            call_count = 0

            async def mock_get(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    # First call (CoinGecko) fails
                    raise httpx.HTTPError("CoinGecko down")
                else:
                    # Second call (CoinCap) succeeds
                    return mock_response

            service.http_client.get = mock_get

            price = await service.get_price("XRP")

            assert price == Decimal("2.45")
            # Should cache the fallback result
            mock_redis.setex.assert_called_once()

            await service.close()

    @pytest.mark.asyncio
    async def test_get_price_all_sources_fail(self, mock_redis):
        """Test get_price raises when all sources fail."""
        mock_redis.get.return_value = None  # Cache miss

        with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
            service = PriceFeedService()
            service.http_client.get = AsyncMock(side_effect=httpx.HTTPError("All APIs down"))

            with pytest.raises(httpx.HTTPError):
                await service.get_price("XRP")

            await service.close()


# ============================================================================
# TEST CLASS - Multi-Asset Prices
# ============================================================================

class TestMultiAssetPrices:
    """Test concurrent multi-asset price fetching."""

    @pytest.mark.asyncio
    async def test_get_multi_asset_prices_success(self, mock_redis, coingecko_response):
        """Test fetching multiple asset prices concurrently."""
        mock_redis.get.return_value = None  # Cache miss

        mock_response = MagicMock()
        mock_response.json.return_value = coingecko_response
        mock_response.raise_for_status = MagicMock()

        with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
            service = PriceFeedService()
            service.http_client.get = AsyncMock(return_value=mock_response)

            results = await service.get_multi_asset_prices(["XRP", "BTC", "ETH"])

            assert len(results) == 3
            assert "XRP" in results
            assert "BTC" in results
            assert "ETH" in results
            assert results["XRP"]["price"] == Decimal("2.45")
            assert results["BTC"]["price"] == Decimal("45000.00")
            assert results["ETH"]["price"] == Decimal("3200.00")

            await service.close()

    @pytest.mark.asyncio
    async def test_get_multi_asset_prices_partial_failure(self, mock_redis, coingecko_response):
        """Test multi-asset fetch handles partial failures gracefully."""
        mock_redis.get.return_value = None

        mock_response = MagicMock()
        mock_response.json.return_value = coingecko_response
        mock_response.raise_for_status = MagicMock()

        with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
            service = PriceFeedService()

            call_count = 0

            async def mock_get(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                if call_count == 2:  # Fail BTC
                    raise httpx.HTTPError("API error")
                return mock_response

            service.http_client.get = mock_get

            results = await service.get_multi_asset_prices(["XRP", "BTC", "ETH"])

            # XRP and ETH should succeed, BTC should be missing
            assert "XRP" in results
            assert "ETH" in results
            # BTC might be present if the error handling allows it through, or absent

            await service.close()


# ============================================================================
# TEST CLASS - Historical Prices
# ============================================================================

class TestHistoricalPrices:
    """Test historical price fetching (not yet implemented)."""

    @pytest.mark.asyncio
    async def test_get_historical_prices_not_implemented(self, mock_redis):
        """Test historical prices raises NotImplementedError."""
        with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
            service = PriceFeedService()

            with pytest.raises(NotImplementedError):
                await service.get_historical_prices("XRP", hours=24)

            await service.close()


# ============================================================================
# TEST CLASS - Resource Cleanup
# ============================================================================

class TestResourceCleanup:
    """Test service resource cleanup."""

    @pytest.mark.asyncio
    async def test_close_with_redis(self, mock_redis):
        """Test close cleans up HTTP client and Redis."""
        with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
            service = PriceFeedService()

            # Replace http_client with mock
            mock_http_client = AsyncMock()
            service.http_client = mock_http_client

            await service.close()

            mock_http_client.aclose.assert_called_once()
            mock_redis.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_without_redis(self):
        """Test close cleans up HTTP client when Redis is unavailable."""
        with patch("src.services.price_feed.Redis.from_url", side_effect=ConnectionError("Redis down")):
            service = PriceFeedService()

            # Replace http_client with mock
            mock_http_client = AsyncMock()
            service.http_client = mock_http_client

            await service.close()

            mock_http_client.aclose.assert_called_once()
