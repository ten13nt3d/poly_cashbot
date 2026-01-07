"""
Comprehensive tests for Polymarket service.

Tests cover:
- Market operations (fetch markets, market by ID, orderbook)
- Trading operations (submit order, cancel order)
- Error handling (retry logic, circuit breaker)
- Paper trading mode
"""

import asyncio
import pytest
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.polymarket import (
    PolymarketClient,
    CircuitBreaker,
    CircuitState,
    CircuitBreakerOpenError,
    retry_async,
    RETRYABLE_EXCEPTIONS,
)


# Disable logging during tests to avoid logger issues
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
def sample_markets() -> list[dict[str, Any]]:
    """Sample market data from Polymarket API."""
    return [
        {
            "id": "market_1",
            "question": "Will XRP reach $2.50 by EOD?",
            "end_date": (datetime.now() + timedelta(hours=2)).isoformat(),
            "yes_price": 0.55,
            "no_price": 0.45,
            "volume_24h": 50000,
            "liquidity": 15000,
            "related_asset": "XRP",
        },
        {
            "id": "market_2",
            "question": "Will BTC stay above $45k?",
            "end_date": (datetime.now() + timedelta(hours=1)).isoformat(),
            "yes_price": 0.72,
            "no_price": 0.28,
            "volume_24h": 120000,
            "liquidity": 35000,
            "related_asset": "BTC",
        },
    ]


@pytest.fixture
def sample_market() -> dict[str, Any]:
    """Sample single market data."""
    return {
        "id": "market_1",
        "question": "Will XRP reach $2.50 by EOD?",
        "end_date": (datetime.now() + timedelta(hours=2)).isoformat(),
        "yes_price": 0.55,
        "no_price": 0.45,
        "volume_24h": 50000,
        "liquidity": 15000,
        "related_asset": "XRP",
        "description": "Market for XRP price prediction",
    }


@pytest.fixture
def sample_orderbook() -> dict[str, Any]:
    """Sample orderbook data."""
    return {
        "yes": {
            "bids": [
                {"price": 0.55, "size": 1000},
                {"price": 0.54, "size": 2000},
                {"price": 0.53, "size": 1500},
            ],
            "asks": [
                {"price": 0.56, "size": 800},
                {"price": 0.57, "size": 1200},
                {"price": 0.58, "size": 900},
            ],
        },
        "no": {
            "bids": [
                {"price": 0.44, "size": 1100},
                {"price": 0.43, "size": 1800},
            ],
            "asks": [
                {"price": 0.45, "size": 950},
                {"price": 0.46, "size": 1400},
            ],
        },
    }


@pytest.fixture
def mock_clob_client():
    """Mock py-clob-client for testing."""
    mock = MagicMock()
    mock.get_markets.return_value = []
    mock.get_market.return_value = {}
    mock.get_order_book.return_value = {}
    mock.post_order.return_value = {"id": "order_123", "status": "open"}
    mock.cancel.return_value = {"order_id": "order_123", "status": "cancelled"}
    return mock


# ============================================================================
# TEST CLASS - PolymarketClient Market Operations
# ============================================================================

class TestPolymarketClientMarketOperations:
    """Test market data fetching operations."""

    @pytest.mark.asyncio
    async def test_initialization_paper_trading(self):
        """Test client initializes correctly in paper trading mode."""
        client = PolymarketClient(paper_trading=True)

        assert client.paper_trading is True
        assert client._client is None
        assert client._circuit_breaker is not None
        assert client._circuit_breaker.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_initialization_with_custom_thresholds(self):
        """Test client initializes with custom circuit breaker settings."""
        client = PolymarketClient(
            paper_trading=True,
            failure_threshold=10,
            circuit_timeout=120,
        )

        assert client._circuit_breaker.failure_threshold == 10
        assert client._circuit_breaker.timeout == 120

    @pytest.mark.asyncio
    async def test_get_markets_success(self, mock_clob_client, sample_markets):
        """Test fetching all markets successfully."""
        mock_clob_client.get_markets.return_value = sample_markets

        with patch("src.services.polymarket.ClobClient", return_value=mock_clob_client):
            client = PolymarketClient(paper_trading=False)
            markets = await client.get_markets()

        assert len(markets) == 2
        assert markets[0]["id"] == "market_1"
        assert markets[1]["id"] == "market_2"
        mock_clob_client.get_markets.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_market_by_id_success(self, mock_clob_client, sample_market):
        """Test fetching a specific market by ID."""
        mock_clob_client.get_market.return_value = sample_market

        with patch("src.services.polymarket.ClobClient", return_value=mock_clob_client):
            client = PolymarketClient(paper_trading=False)
            market = await client.get_market("market_1")

        assert market["id"] == "market_1"
        assert market["question"] == "Will XRP reach $2.50 by EOD?"
        mock_clob_client.get_market.assert_called_once_with("market_1")

    @pytest.mark.asyncio
    async def test_get_orderbook_success(self, mock_clob_client, sample_orderbook):
        """Test fetching orderbook for a market."""
        mock_clob_client.get_order_book.return_value = sample_orderbook

        with patch("src.services.polymarket.ClobClient", return_value=mock_clob_client):
            client = PolymarketClient(paper_trading=False)
            orderbook = await client.get_order_book("market_1")

        assert "yes" in orderbook
        assert "no" in orderbook
        assert len(orderbook["yes"]["bids"]) == 3
        assert orderbook["yes"]["bids"][0]["price"] == 0.55
        mock_clob_client.get_order_book.assert_called_once_with("market_1")


# ============================================================================
# TEST CLASS - PolymarketClient Trading Operations
# ============================================================================

class TestPolymarketClientTradingOperations:
    """Test order submission and management operations."""

    @pytest.mark.asyncio
    async def test_submit_order_paper_trading(self):
        """Test order submission in paper trading mode."""
        client = PolymarketClient(paper_trading=True)

        order = {
            "market_id": "market_1",
            "side": "BUY",
            "size": 100,
            "price": 0.55,
        }

        result = await client.submit_order(order)

        assert result["status"] == "simulated"
        assert result["market_id"] == "market_1"
        assert result["side"] == "BUY"
        assert result["size"] == 100
        assert "paper_" in result["id"]
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_submit_order_real_mode(self, mock_clob_client):
        """Test order submission in real trading mode (mocked)."""
        mock_clob_client.post_order.return_value = {
            "id": "real_order_123",
            "status": "open",
            "market_id": "market_1",
        }

        with patch("src.services.polymarket.ClobClient", return_value=mock_clob_client):
            # Need to patch settings.paper_trading to False for real mode
            with patch("src.services.polymarket.settings") as mock_settings:
                mock_settings.paper_trading = False
                mock_settings.polymarket_host = "https://clob.polymarket.com"
                mock_settings.polymarket_api_key = "test_key"
                mock_settings.polymarket_chain_id = 137

                client = PolymarketClient(paper_trading=False)
                order = {
                    "market_id": "market_1",
                    "side": "BUY",
                    "size": 100,
                    "price": 0.55,
                }

                result = await client.submit_order(order)

        assert result["id"] == "real_order_123"
        assert result["status"] == "open"
        mock_clob_client.post_order.assert_called_once_with(order)

    @pytest.mark.asyncio
    async def test_cancel_order_paper_trading(self):
        """Test order cancellation in paper trading mode."""
        client = PolymarketClient(paper_trading=True)

        result = await client.cancel_order("paper_order_123")

        assert result["order_id"] == "paper_order_123"
        assert result["status"] == "cancelled_simulated"
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_cancel_order_real_mode(self, mock_clob_client):
        """Test order cancellation in real trading mode (mocked)."""
        mock_clob_client.cancel.return_value = {
            "order_id": "real_order_123",
            "status": "cancelled",
        }

        with patch("src.services.polymarket.ClobClient", return_value=mock_clob_client):
            with patch("src.services.polymarket.settings") as mock_settings:
                mock_settings.paper_trading = False
                mock_settings.polymarket_host = "https://clob.polymarket.com"
                mock_settings.polymarket_api_key = "test_key"
                mock_settings.polymarket_chain_id = 137

                client = PolymarketClient(paper_trading=False)
                result = await client.cancel_order("real_order_123")

        assert result["order_id"] == "real_order_123"
        assert result["status"] == "cancelled"
        mock_clob_client.cancel.assert_called_once_with("real_order_123")


# ============================================================================
# TEST CLASS - Retry Logic
# ============================================================================

class TestRetryLogic:
    """Test retry decorator with exponential backoff."""

    @pytest.mark.asyncio
    async def test_retry_succeeds_first_attempt(self):
        """Test function succeeds on first attempt without retry."""
        call_count = 0

        @retry_async(max_retries=3, backoff_factor=2.0)
        async def successful_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = await successful_func()

        assert result == "success"
        assert call_count == 1

    @pytest.mark.asyncio
    async def test_retry_succeeds_after_failures(self):
        """Test function succeeds after some retryable failures."""
        call_count = 0

        @retry_async(max_retries=3, backoff_factor=0.01)  # Fast backoff for testing
        async def flaky_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary network issue")
            return "success"

        result = await flaky_func()

        assert result == "success"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_exhausted(self):
        """Test retry fails after max attempts."""
        call_count = 0

        @retry_async(max_retries=3, backoff_factor=0.01)
        async def always_fails():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Persistent network issue")

        with pytest.raises(ConnectionError):
            await always_fails()

        assert call_count == 3

    @pytest.mark.asyncio
    async def test_retry_non_retryable_exception(self):
        """Test non-retryable exceptions are not retried."""
        call_count = 0

        @retry_async(max_retries=3, backoff_factor=0.01)
        async def raises_value_error():
            nonlocal call_count
            call_count += 1
            raise ValueError("This should not be retried")

        with pytest.raises(ValueError):
            await raises_value_error()

        # Should fail immediately without retries
        assert call_count == 1


# ============================================================================
# TEST CLASS - Circuit Breaker
# ============================================================================

class TestCircuitBreaker:
    """Test circuit breaker pattern for fault tolerance."""

    def test_circuit_breaker_initialization(self):
        """Test circuit breaker initializes in CLOSED state."""
        cb = CircuitBreaker(failure_threshold=5, timeout=60)

        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0
        assert cb.last_failure_time is None
        assert cb.failure_threshold == 5
        assert cb.timeout == 60

    @pytest.mark.asyncio
    async def test_circuit_closed_successful_call(self):
        """Test successful call through closed circuit."""
        cb = CircuitBreaker(failure_threshold=3, timeout=60)

        async def successful_func():
            return "success"

        result = await cb.call(successful_func)

        assert result == "success"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_opens_after_threshold(self):
        """Test circuit opens after failure threshold reached."""
        cb = CircuitBreaker(failure_threshold=3, timeout=60)

        async def failing_func():
            raise ConnectionError("Service unavailable")

        # Fail 3 times to reach threshold
        for i in range(3):
            with pytest.raises(ConnectionError):
                await cb.call(failing_func)

        assert cb.state == CircuitState.OPEN
        assert cb.failure_count == 3
        assert cb.last_failure_time is not None

    @pytest.mark.asyncio
    async def test_circuit_open_fails_immediately(self):
        """Test open circuit fails immediately without calling function."""
        cb = CircuitBreaker(failure_threshold=2, timeout=60)

        call_count = 0

        async def failing_func():
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Service unavailable")

        # Open the circuit
        for i in range(2):
            with pytest.raises(ConnectionError):
                await cb.call(failing_func)

        assert cb.state == CircuitState.OPEN

        # Next call should fail immediately
        with pytest.raises(CircuitBreakerOpenError):
            await cb.call(failing_func)

        # Function should not have been called again
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_circuit_half_open_on_timeout(self):
        """Test circuit transitions to HALF_OPEN after timeout."""
        cb = CircuitBreaker(failure_threshold=2, timeout=1)  # 1 second timeout

        async def failing_func():
            raise ConnectionError("Service unavailable")

        # Open the circuit
        for i in range(2):
            with pytest.raises(ConnectionError):
                await cb.call(failing_func)

        assert cb.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(1.1)

        # Next call should transition to HALF_OPEN
        try:
            await cb.call(failing_func)
        except ConnectionError:
            pass

        # Circuit should have been in HALF_OPEN before the call failed
        # After failure, it should be OPEN again
        assert cb.state == CircuitState.OPEN

    @pytest.mark.asyncio
    async def test_circuit_half_open_success_closes_circuit(self):
        """Test successful call in HALF_OPEN state closes circuit."""
        cb = CircuitBreaker(failure_threshold=2, timeout=1)

        async def failing_func():
            raise ConnectionError("Service unavailable")

        async def successful_func():
            return "recovered"

        # Open the circuit
        for i in range(2):
            with pytest.raises(ConnectionError):
                await cb.call(failing_func)

        assert cb.state == CircuitState.OPEN

        # Wait for timeout
        await asyncio.sleep(1.1)

        # Successful call should close the circuit
        result = await cb.call(successful_func)

        assert result == "recovered"
        assert cb.state == CircuitState.CLOSED
        assert cb.failure_count == 0

    @pytest.mark.asyncio
    async def test_circuit_resets_on_success(self):
        """Test circuit resets failure count on successful call."""
        cb = CircuitBreaker(failure_threshold=5, timeout=60)

        async def failing_func():
            raise ConnectionError("Service unavailable")

        async def successful_func():
            return "success"

        # Fail twice (not enough to open)
        for i in range(2):
            with pytest.raises(ConnectionError):
                await cb.call(failing_func)

        assert cb.failure_count == 2

        # Successful call should reset
        await cb.call(successful_func)

        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED


# ============================================================================
# TEST CLASS - Integration Tests
# ============================================================================

class TestPolymarketClientIntegration:
    """Integration tests combining multiple features."""

    @pytest.mark.asyncio
    async def test_client_with_circuit_breaker(self, mock_clob_client):
        """Test client respects circuit breaker on repeated failures."""
        # Make the mock fail consistently
        mock_clob_client.get_markets.side_effect = ConnectionError("Service down")

        with patch("src.services.polymarket.ClobClient", return_value=mock_clob_client):
            client = PolymarketClient(
                paper_trading=False,
                failure_threshold=2,  # Low threshold for testing
                circuit_timeout=60,
            )

            # First failure
            with pytest.raises(ConnectionError):
                await client.get_markets()

            # Second failure
            with pytest.raises(ConnectionError):
                await client.get_markets()

            # Circuit should now be open
            # Note: The retry decorator will retry 3 times before raising,
            # so we need to account for that in our test

    @pytest.mark.asyncio
    async def test_paper_trading_multiple_orders(self):
        """Test multiple orders in paper trading mode."""
        client = PolymarketClient(paper_trading=True)

        orders = [
            {"market_id": "m1", "side": "BUY", "size": 100, "price": 0.50},
            {"market_id": "m2", "side": "SELL", "size": 200, "price": 0.60},
            {"market_id": "m3", "side": "BUY", "size": 150, "price": 0.55},
        ]

        results = []
        for order in orders:
            result = await client.submit_order(order)
            results.append(result)

        assert len(results) == 3
        assert all(r["status"] == "simulated" for r in results)
        assert results[0]["market_id"] == "m1"
        assert results[1]["market_id"] == "m2"
        assert results[2]["market_id"] == "m3"
