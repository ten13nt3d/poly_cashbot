"""
Simple integration tests that don't require complex database setup.

These tests verify that services can work together without full E2E setup.
Run these with: pytest tests/integration/test_simple_integration.py
"""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.polymarket import PolymarketClient
from src.services.price_feed import PriceFeedService


@pytest.mark.integration
class TestPolymarketClientBasic:
    """Basic integration tests for Polymarket client."""

    @pytest.mark.asyncio
    async def test_paper_trading_mode_works(self):
        """Test paper trading client can be created and used."""
        client = PolymarketClient(paper_trading=True)

        order = {
            "market_id": "test_market",
            "side": "BUY",
            "size": 100,
            "price": 0.55,
        }

        result = await client.submit_order(order)

        assert result["status"] == "simulated"
        assert "paper_" in result["id"]

    @pytest.mark.asyncio
    async def test_circuit_breaker_exists(self):
        """Test circuit breaker is initialized."""
        client = PolymarketClient(
            paper_trading=True,
            failure_threshold=3,
            circuit_timeout=60,
        )

        assert hasattr(client, "_circuit_breaker")
        assert client._circuit_breaker.failure_threshold == 3
        assert client._circuit_breaker.timeout == 60


@pytest.mark.integration
class TestPriceFeedBasic:
    """Basic integration tests for price feed."""

    @pytest.mark.asyncio
    async def test_price_feed_with_mock_redis(self):
        """Test price feed works with mocked Redis."""
        mock_redis = AsyncMock()
        mock_redis.get.return_value = "2.45"

        with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
            service = PriceFeedService()

            price = await service.get_price("XRP")

            assert price == Decimal("2.45")
            await service.close()

    @pytest.mark.asyncio
    async def test_price_feed_graceful_degradation(self):
        """Test price feed works without Redis."""
        with patch("src.services.price_feed.Redis.from_url", side_effect=ConnectionError("No Redis")):
            service = PriceFeedService()

            assert service.redis is None
            await service.close()


@pytest.mark.integration
class TestServiceInteroperability:
    """Test that services can work together."""

    @pytest.mark.asyncio
    async def test_polymarket_and_price_feed_coexist(self):
        """Test multiple services can be created together."""
        # Create polymarket client
        poly_client = PolymarketClient(paper_trading=True)

        # Create price feed
        mock_redis = AsyncMock()
        with patch("src.services.price_feed.Redis.from_url", return_value=mock_redis):
            price_feed = PriceFeedService()

            # Both should work
            mock_redis.get.return_value = "2.45"
            price = await price_feed.get_price("XRP")
            assert price == Decimal("2.45")

            order = {"market_id": "test", "side": "BUY", "size": 100, "price": 0.55}
            result = await poly_client.submit_order(order)
            assert result["status"] == "simulated"

            await price_feed.close()
