"""Polymarket API client with async support, retry logic, and circuit breaker."""

import asyncio
from datetime import datetime, timedelta
from enum import Enum
from functools import wraps
from typing import Any, Callable, Optional

import httpx
from py_clob_client.client import ClobClient

from ..config import settings
from .logging_config import get_logger, log_api_call

logger = get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # All calls fail immediately
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitBreakerOpenError(Exception):
    """Raised when circuit breaker is open."""

    pass

# Retryable exceptions
RETRYABLE_EXCEPTIONS = (
    ConnectionError,
    TimeoutError,
    httpx.TimeoutException,
    httpx.ConnectError,
    httpx.NetworkError,
)


def retry_async(max_retries: int = 3, backoff_factor: float = 2.0) -> Callable:
    """
    Decorator to retry async functions with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts (default: 3)
        backoff_factor: Multiplier for exponential backoff (default: 2.0)

    Returns:
        Decorator function

    Example:
        @retry_async(max_retries=3, backoff_factor=2.0)
        async def fetch_data():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except RETRYABLE_EXCEPTIONS as e:
                    last_exception = e

                    if attempt == max_retries - 1:
                        # Last attempt failed, raise the exception
                        logger.error(
                            "retry_exhausted",
                            function=func.__name__,
                            attempt=attempt + 1,
                            max_retries=max_retries,
                            error_type=type(e).__name__,
                            error_message=str(e),
                        )
                        raise

                    # Calculate delay with exponential backoff
                    delay = backoff_factor ** attempt
                    logger.warning(
                        "retry_attempt",
                        function=func.__name__,
                        attempt=attempt + 1,
                        max_retries=max_retries,
                        delay=delay,
                        error_type=type(e).__name__,
                        error_message=str(e),
                    )

                    await asyncio.sleep(delay)

            # This should never be reached, but just in case
            if last_exception:
                raise last_exception

        return wrapper

    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures.

    States:
        CLOSED: Normal operation, all calls proceed
        OPEN: Too many failures, all calls fail immediately
        HALF_OPEN: Testing if service recovered

    Transitions:
        CLOSED -> OPEN: After failure_threshold consecutive failures
        OPEN -> HALF_OPEN: After timeout seconds
        HALF_OPEN -> CLOSED: On successful call
        HALF_OPEN -> OPEN: On failed call
    """

    def __init__(self, failure_threshold: int = 5, timeout: int = 60):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            timeout: Seconds to wait before attempting reset (HALF_OPEN)
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time: Optional[datetime] = None
        self.state = CircuitState.CLOSED

    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset."""
        if self.last_failure_time is None:
            return False

        time_since_failure = datetime.now() - self.last_failure_time
        return time_since_failure >= timedelta(seconds=self.timeout)

    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute function through circuit breaker.

        Args:
            func: Async function to call
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from func

        Raises:
            CircuitBreakerOpenError: If circuit is open
            Exception: Original exception from func
        """
        # Check circuit state
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                logger.info(
                    "circuit_breaker_half_open",
                    failure_count=self.failure_count,
                    timeout=self.timeout,
                )
                self.state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError(
                    f"Circuit breaker is OPEN. Too many failures ({self.failure_count}). "
                    f"Will retry after {self.timeout}s timeout."
                )

        try:
            # Call the function
            result = await func(*args, **kwargs)

            # Success - reset circuit
            self._on_success()
            return result

        except Exception as e:
            # Failure - update circuit
            self._on_failure()
            raise

    def _on_success(self) -> None:
        """Handle successful call."""
        if self.state == CircuitState.HALF_OPEN:
            logger.info("circuit_breaker_closed", message="Service recovered")

        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED

    def _on_failure(self) -> None:
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = datetime.now()

        if self.failure_count >= self.failure_threshold:
            if self.state != CircuitState.OPEN:
                logger.error(
                    "circuit_breaker_opened",
                    failure_count=self.failure_count,
                    threshold=self.failure_threshold,
                )
                self.state = CircuitState.OPEN
        elif self.state == CircuitState.HALF_OPEN:
            # Failed during half-open, go back to open
            logger.warning(
                "circuit_breaker_reopened", message="Service still failing"
            )
            self.state = CircuitState.OPEN


class PolymarketClient:
    """
    Async wrapper around py-clob-client for Polymarket CLOB API.

    Provides async methods for market data fetching and order management with:
    - Async wrappers for synchronous py-clob-client
    - Retry logic with exponential backoff (Phase 2.2)
    - Circuit breaker pattern (Phase 2.3)
    - Paper trading mode support (Phase 2.4)

    Example:
        client = PolymarketClient()
        markets = await client.get_markets()
    """

    def __init__(
        self, paper_trading: bool = True, failure_threshold: int = 5, circuit_timeout: int = 60
    ):
        """
        Initialize Polymarket client with settings from config.

        Args:
            paper_trading: If True, simulate orders without real execution
            failure_threshold: Number of failures before circuit opens
            circuit_timeout: Seconds before attempting circuit reset
        """
        self.paper_trading = paper_trading
        try:
            # In paper trading mode, don't initialize real client
            if not paper_trading:
                self._client = ClobClient(
                    host=settings.polymarket_host,
                    key=settings.polymarket_api_key,
                    chain_id=settings.polymarket_chain_id,
                )
            else:
                self._client = None  # No real client in paper trading mode

            self._circuit_breaker = CircuitBreaker(
                failure_threshold=failure_threshold,
                timeout=circuit_timeout,
            )
            mode = "PAPER TRADING" if paper_trading else "LIVE"
            logger.info(
                f"Polymarket client initialized ({mode}) - "
                f"Circuit threshold: {failure_threshold}"
            )
        except Exception as e:
            logger.error(
                f"Polymarket client initialization failed - Error: {type(e).__name__}: {str(e)}"
            )
            raise

    @retry_async(max_retries=3, backoff_factor=2.0)
    @log_api_call("get_markets")
    async def get_markets(self) -> list[dict[str, Any]]:
        """
        Fetch all markets from Polymarket.

        Returns:
            List of market dictionaries with market data

        Raises:
            Exception: If API call fails after retries

        Example:
            markets = await client.get_markets()
            for market in markets:
                print(market['question'])
        """
        return await asyncio.to_thread(self._client.get_markets)

    @retry_async(max_retries=3, backoff_factor=2.0)
    @log_api_call("get_market")
    async def get_market(self, market_id: str) -> dict[str, Any]:
        """
        Fetch a specific market by ID.

        Args:
            market_id: Polymarket market identifier

        Returns:
            Market dictionary with detailed market data

        Raises:
            Exception: If API call fails or market not found

        Example:
            market = await client.get_market("0x123abc...")
            print(market['question'])
        """
        return await asyncio.to_thread(self._client.get_market, market_id)

    @retry_async(max_retries=3, backoff_factor=2.0)
    @log_api_call("get_order_book")
    async def get_order_book(self, market_id: str) -> dict[str, Any]:
        """
        Fetch orderbook for a specific market.

        Args:
            market_id: Polymarket market identifier

        Returns:
            Orderbook dictionary with bids and asks

        Raises:
            Exception: If API call fails

        Example:
            orderbook = await client.get_order_book("0x123abc...")
            yes_bids = orderbook['yes']['bids']
        """
        return await asyncio.to_thread(self._client.get_order_book, market_id)

    @retry_async(max_retries=3, backoff_factor=2.0)
    @log_api_call("submit_order")
    async def submit_order(self, order: dict[str, Any]) -> dict[str, Any]:
        """
        Submit an order to Polymarket (or simulate in paper trading mode).

        Args:
            order: Order dictionary with size, price, side, etc.

        Returns:
            Order confirmation with order ID and status

        Raises:
            Exception: If order submission fails

        Example:
            order = {
                'market_id': '0x123abc...',
                'side': 'BUY',
                'size': 100,
                'price': 0.55
            }
            result = await client.submit_order(order)
        """
        # Paper trading mode - simulate order without hitting API
        if settings.paper_trading:
            import uuid

            simulated_order = {
                "id": f"paper_{uuid.uuid4().hex[:12]}",
                "status": "simulated",
                "market_id": order.get("market_id"),
                "side": order.get("side"),
                "size": order.get("size"),
                "price": order.get("price"),
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(
                "paper_trading_order_simulated",
                order_id=simulated_order["id"],
                market_id=order.get("market_id"),
                side=order.get("side"),
                size=order.get("size"),
            )

            return simulated_order

        # Real trading mode
        return await asyncio.to_thread(self._client.post_order, order)

    @retry_async(max_retries=3, backoff_factor=2.0)
    @log_api_call("cancel_order")
    async def cancel_order(self, order_id: str) -> dict[str, Any]:
        """
        Cancel an existing order (or simulate in paper trading mode).

        Args:
            order_id: Order identifier to cancel

        Returns:
            Cancellation confirmation

        Raises:
            Exception: If cancellation fails

        Example:
            result = await client.cancel_order("order_123")
        """
        # Paper trading mode - simulate cancellation without hitting API
        if settings.paper_trading:
            simulated_cancellation = {
                "order_id": order_id,
                "status": "cancelled_simulated",
                "timestamp": datetime.now().isoformat(),
            }

            logger.info(
                "paper_trading_cancel_simulated",
                order_id=order_id,
            )

            return simulated_cancellation

        # Real trading mode
        return await asyncio.to_thread(self._client.cancel, order_id)
