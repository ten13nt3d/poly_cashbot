"""Test helper functions and utilities."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List

from src.models import Market, Order, Position


def assert_decimal_equal(actual: Decimal, expected: Decimal, places: int = 2) -> None:
    """
    Assert two Decimal values are equal within a tolerance.

    Args:
        actual: Actual value
        expected: Expected value
        places: Number of decimal places to compare
    """
    actual_rounded = round(actual, places)
    expected_rounded = round(expected, places)
    assert actual_rounded == expected_rounded, (
        f"Expected {expected_rounded}, got {actual_rounded}"
    )


def create_test_datetime(hours_from_now: float = 1.0) -> datetime:
    """
    Create a datetime for testing.

    Args:
        hours_from_now: Hours to add to current time

    Returns:
        datetime: Future datetime
    """
    return datetime.now() + timedelta(hours=hours_from_now)


def assert_market_valid(market: Market) -> None:
    """
    Assert a Market instance has valid data.

    Args:
        market: Market to validate
    """
    assert market.id is not None
    assert len(market.question) > 0
    assert market.end_date is not None

    if market.yes_price is not None:
        assert Decimal("0") <= market.yes_price <= Decimal("1")

    if market.no_price is not None:
        assert Decimal("0") <= market.no_price <= Decimal("1")

    if market.liquidity is not None:
        assert market.liquidity >= Decimal("0")


def assert_order_valid(order: Order) -> None:
    """
    Assert an Order instance has valid data.

    Args:
        order: Order to validate
    """
    assert order.id is not None
    assert order.market_id is not None
    assert order.side in ("BUY", "SELL", "buy", "sell")
    assert order.size > Decimal("0")
    assert Decimal("0") <= order.price <= Decimal("1")
    assert order.filled_size >= Decimal("0")
    assert order.filled_size <= order.size


def assert_position_valid(position: Position) -> None:
    """
    Assert a Position instance has valid data.

    Args:
        position: Position to validate
    """
    assert position.id is not None
    assert position.market_id is not None
    assert position.side in ("BUY", "SELL", "buy", "sell")
    assert position.size > Decimal("0")
    assert Decimal("0") <= position.entry_price <= Decimal("1")
