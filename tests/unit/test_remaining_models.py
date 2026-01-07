"""Unit tests for Order, Sentiment, Trade, and Whale Alert models."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from src.models.order import Order
from src.models.sentiment import SentimentScore
from src.models.trade import Trade
from src.models.whale_alert import WhaleAlert


class TestOrderModel:
    """Test cases for Order model."""

    def test_is_active_pending(self):
        """Test is_active returns True for pending order."""
        order = Order(
            id="order_1",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            price=Decimal("0.55"),
            status="pending",
            created_at=datetime.now(),
        )
        assert order.is_active() is True

    def test_is_active_open(self):
        """Test is_active returns True for open order."""
        order = Order(
            id="order_2",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            price=Decimal("0.55"),
            status="open",
            created_at=datetime.now(),
        )
        assert order.is_active() is True

    def test_is_active_partially_filled(self):
        """Test is_active returns True for partially filled order."""
        order = Order(
            id="order_3",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            price=Decimal("0.55"),
            status="partially_filled",
            created_at=datetime.now(),
        )
        assert order.is_active() is True

    def test_is_active_filled(self):
        """Test is_active returns False for filled order."""
        order = Order(
            id="order_4",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            price=Decimal("0.55"),
            status="filled",
            created_at=datetime.now(),
        )
        assert order.is_active() is False

    def test_is_filled_true(self):
        """Test is_filled returns True for filled order."""
        order = Order(
            id="order_5",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            price=Decimal("0.55"),
            status="filled",
            created_at=datetime.now(),
        )
        assert order.is_filled() is True

    def test_is_filled_false(self):
        """Test is_filled returns False for non-filled order."""
        order = Order(
            id="order_6",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            price=Decimal("0.55"),
            status="open",
            created_at=datetime.now(),
        )
        assert order.is_filled() is False

    def test_fill_percentage_full(self):
        """Test fill_percentage for fully filled order."""
        order = Order(
            id="order_7",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            filled_size=Decimal("100.00"),
            price=Decimal("0.55"),
            status="filled",
            created_at=datetime.now(),
        )
        assert order.fill_percentage() == Decimal("100")

    def test_fill_percentage_partial(self):
        """Test fill_percentage for partially filled order."""
        order = Order(
            id="order_8",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            filled_size=Decimal("50.00"),
            price=Decimal("0.55"),
            status="partially_filled",
            created_at=datetime.now(),
        )
        assert order.fill_percentage() == Decimal("50")

    def test_fill_percentage_zero_size(self):
        """Test fill_percentage with zero size."""
        order = Order(
            id="order_9",
            market_id="market_1",
            side="BUY",
            size=Decimal("0.00"),
            filled_size=Decimal("0.00"),
            price=Decimal("0.55"),
            status="pending",
            created_at=datetime.now(),
        )
        assert order.fill_percentage() == Decimal("0")


class TestSentimentModel:
    """Test cases for SentimentScore model."""

    def test_is_bullish_true(self):
        """Test is_bullish returns True for positive score above threshold."""
        sentiment = SentimentScore(
            timestamp=datetime.now(),
            asset="BTC",
            score=Decimal("50.0"),
            timeframe="15m",
        )
        assert sentiment.is_bullish() is True  # 50 > 40 (default threshold)

    def test_is_bullish_false(self):
        """Test is_bullish returns False for score below threshold."""
        sentiment = SentimentScore(
            timestamp=datetime.now(),
            asset="BTC",
            score=Decimal("30.0"),
            timeframe="15m",
        )
        assert sentiment.is_bullish() is False  # 30 < 40

    def test_is_bearish_true(self):
        """Test is_bearish returns True for negative score below threshold."""
        sentiment = SentimentScore(
            timestamp=datetime.now(),
            asset="BTC",
            score=Decimal("-50.0"),
            timeframe="15m",
        )
        assert sentiment.is_bearish() is True  # -50 < -40 (default threshold)

    def test_is_bearish_false(self):
        """Test is_bearish returns False for score above threshold."""
        sentiment = SentimentScore(
            timestamp=datetime.now(),
            asset="BTC",
            score=Decimal("-30.0"),
            timeframe="15m",
        )
        assert sentiment.is_bearish() is False  # -30 > -40

    def test_is_neutral_true(self):
        """Test is_neutral returns True for score between thresholds."""
        sentiment = SentimentScore(
            timestamp=datetime.now(),
            asset="BTC",
            score=Decimal("20.0"),
            timeframe="15m",
        )
        assert sentiment.is_neutral() is True  # -40 <= 20 <= 40

    def test_is_neutral_false_high(self):
        """Test is_neutral returns False for high score."""
        sentiment = SentimentScore(
            timestamp=datetime.now(),
            asset="BTC",
            score=Decimal("60.0"),
            timeframe="15m",
        )
        assert sentiment.is_neutral() is False

    def test_magnitude_positive(self):
        """Test magnitude returns absolute value for positive score."""
        sentiment = SentimentScore(
            timestamp=datetime.now(),
            asset="BTC",
            score=Decimal("45.5"),
            timeframe="15m",
        )
        assert sentiment.magnitude() == Decimal("45.5")

    def test_magnitude_negative(self):
        """Test magnitude returns absolute value for negative score."""
        sentiment = SentimentScore(
            timestamp=datetime.now(),
            asset="BTC",
            score=Decimal("-55.25"),
            timeframe="15m",
        )
        assert sentiment.magnitude() == Decimal("55.25")


class TestTradeModel:
    """Test cases for Trade model."""

    def test_is_winner_true(self):
        """Test is_winner returns True for positive P&L."""
        trade = Trade(
            id="trade_1",
            order_id="order_1",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            price=Decimal("0.60"),
            pnl=Decimal("10.00"),
            strategy="interval_15m",
            executed_at=datetime.now(),
        )
        assert trade.is_winner() is True

    def test_is_winner_false(self):
        """Test is_winner returns False for negative P&L."""
        trade = Trade(
            id="trade_2",
            order_id="order_2",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            price=Decimal("0.50"),
            pnl=Decimal("-10.00"),
            strategy="interval_15m",
            executed_at=datetime.now(),
        )
        assert trade.is_winner() is False

    def test_is_winner_none_pnl(self):
        """Test is_winner returns False when pnl is None."""
        trade = Trade(
            id="trade_3",
            order_id="order_3",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            price=Decimal("0.50"),
            pnl=None,
            strategy="interval_15m",
            executed_at=datetime.now(),
        )
        assert trade.is_winner() is False

    def test_roi_pct_profit(self):
        """Test roi_pct for profitable trade."""
        trade = Trade(
            id="trade_4",
            order_id="order_4",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            price=Decimal("0.60"),
            pnl=Decimal("10.00"),
            strategy="interval_15m",
            executed_at=datetime.now(),
        )
        # 10 / 100 * 100 = 10%
        assert trade.roi_pct() == Decimal("10.00")

    def test_roi_pct_loss(self):
        """Test roi_pct for losing trade."""
        trade = Trade(
            id="trade_5",
            order_id="order_5",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            price=Decimal("0.50"),
            pnl=Decimal("-20.00"),
            strategy="interval_15m",
            executed_at=datetime.now(),
        )
        assert trade.roi_pct() == Decimal("-20.00")

    def test_roi_pct_none_pnl(self):
        """Test roi_pct returns None when pnl is None."""
        trade = Trade(
            id="trade_6",
            order_id="order_6",
            market_id="market_1",
            side="BUY",
            size=Decimal("100.00"),
            price=Decimal("0.50"),
            pnl=None,
            strategy="interval_15m",
            executed_at=datetime.now(),
        )
        assert trade.roi_pct() is None

    def test_roi_pct_zero_size(self):
        """Test roi_pct returns None with zero size."""
        trade = Trade(
            id="trade_7",
            order_id="order_7",
            market_id="market_1",
            side="BUY",
            size=Decimal("0.00"),
            price=Decimal("0.50"),
            pnl=Decimal("10.00"),
            strategy="interval_15m",
            executed_at=datetime.now(),
        )
        assert trade.roi_pct() is None


class TestWhaleAlertModel:
    """Test cases for WhaleAlert model."""

    def test_is_significant_true(self):
        """Test is_significant returns True when above threshold."""
        alert = WhaleAlert(
            market_id="market_1",
            wallet_address="0x1234567890",
            order_size=Decimal("100000.00"),
            side="BUY",
            relative_size=Decimal("15.0"),
        )
        # 15.0 >= 10.0 (default threshold)
        assert alert.is_significant() is True

    def test_is_significant_false(self):
        """Test is_significant returns False when below threshold."""
        alert = WhaleAlert(
            market_id="market_1",
            wallet_address="0x1234567890",
            order_size=Decimal("5000.00"),
            side="BUY",
            relative_size=Decimal("5.0"),
        )
        assert alert.is_significant() is False

    def test_is_significant_at_threshold(self):
        """Test is_significant at exact threshold."""
        alert = WhaleAlert(
            market_id="market_1",
            wallet_address="0x1234567890",
            order_size=Decimal("50000.00"),
            side="BUY",
            relative_size=Decimal("10.0"),
        )
        assert alert.is_significant() is True

    def test_is_significant_none_relative_size(self):
        """Test is_significant returns False when relative_size is None."""
        alert = WhaleAlert(
            market_id="market_1",
            wallet_address="0x1234567890",
            order_size=Decimal("50000.00"),
            side="BUY",
            relative_size=None,
        )
        assert alert.is_significant() is False

    def test_is_significant_custom_threshold(self):
        """Test is_significant with custom threshold."""
        alert = WhaleAlert(
            market_id="market_1",
            wallet_address="0x1234567890",
            order_size=Decimal("50000.00"),
            side="BUY",
            relative_size=Decimal("7.0"),
        )
        # Custom threshold
        assert alert.is_significant(threshold=Decimal("5.0")) is True
        assert alert.is_significant(threshold=Decimal("10.0")) is False

    def test_was_frontrun_true(self):
        """Test was_frontrun returns True when frontrun executed."""
        alert = WhaleAlert(
            market_id="market_1",
            wallet_address="0x1234567890",
            order_size=Decimal("100000.00"),
            side="BUY",
            action_taken="frontrun",
            frontrun_order_id="order_123",
        )
        assert alert.was_frontrun() is True

    def test_was_frontrun_false_no_action(self):
        """Test was_frontrun returns False when no frontrun action."""
        alert = WhaleAlert(
            market_id="market_1",
            wallet_address="0x1234567890",
            order_size=Decimal("100000.00"),
            side="BUY",
            action_taken="ignored",
            frontrun_order_id=None,
        )
        assert alert.was_frontrun() is False

    def test_was_frontrun_false_no_order_id(self):
        """Test was_frontrun returns False when frontrun but no order_id."""
        alert = WhaleAlert(
            market_id="market_1",
            wallet_address="0x1234567890",
            order_size=Decimal("100000.00"),
            side="BUY",
            action_taken="frontrun",
            frontrun_order_id=None,
        )
        assert alert.was_frontrun() is False
