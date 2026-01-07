"""Unit tests for Interval Trading Strategy."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal
from unittest.mock import patch

from src.lib.strategy.interval_strategy import (
    IntervalStrategy,
    Position,
    ExitStrategy,
)


class TestStrategyInitialization:
    """Test strategy initialization."""

    def test_initialization_without_history(self):
        """Test initializing strategy without trade history."""
        strategy = IntervalStrategy()

        assert strategy.open_positions == []
        assert strategy.trade_history == []
        assert strategy.recent_trades == []
        assert strategy.total_trades == 0
        assert strategy.winning_trades == 0
        assert strategy.consecutive_losses == 0

    def test_initialization_with_history(self):
        """Test initializing strategy with trade history."""
        history = [
            {'pnl': 10.0, 'roi_pct': 0.10},
            {'pnl': -5.0, 'roi_pct': -0.05},
        ]
        strategy = IntervalStrategy(trade_history=history)

        assert strategy.trade_history == history
        assert len(strategy.trade_history) == 2


class TestShouldTrade:
    """Test trade filtering logic."""

    @pytest.fixture
    def strategy(self):
        """Create strategy for testing."""
        return IntervalStrategy()

    def test_should_trade_all_conditions_met(self, strategy):
        """Test trade allowed when all conditions met with good history."""
        # Add some winning trades to pass performance check
        strategy.trade_history = [
            {'pnl': 10.0}, {'pnl': 15.0}, {'pnl': 20.0}, {'pnl': 5.0}
        ]

        result = strategy.should_trade(
            signal_confidence=0.85,
            sentiment_score=50.0,
            expected_win_rate=0.70,
            market_liquidity=15000.0,
            capital_available=Decimal("100.00")
        )

        assert result is True

    def test_should_trade_no_history_blocks(self, strategy):
        """Test trade blocked when no history (win rate = 0)."""
        result = strategy.should_trade(
            signal_confidence=0.85,
            sentiment_score=50.0,
            expected_win_rate=0.70,
            market_liquidity=15000.0,
            capital_available=Decimal("100.00")
        )

        # With no history, win rate is 0.0 which blocks trading
        assert result is False

    def test_should_trade_low_confidence(self, strategy):
        """Test trade rejected for low confidence."""
        result = strategy.should_trade(
            signal_confidence=0.75,  # < 0.80
            sentiment_score=50.0,
            expected_win_rate=0.70,
            market_liquidity=15000.0,
            capital_available=Decimal("100.00")
        )

        assert result is False

    def test_should_trade_weak_sentiment(self, strategy):
        """Test trade rejected for weak sentiment."""
        result = strategy.should_trade(
            signal_confidence=0.85,
            sentiment_score=30.0,  # < 40
            expected_win_rate=0.70,
            market_liquidity=15000.0,
            capital_available=Decimal("100.00")
        )

        assert result is False

    def test_should_trade_low_expected_win_rate(self, strategy):
        """Test trade rejected for low expected win rate."""
        result = strategy.should_trade(
            signal_confidence=0.85,
            sentiment_score=50.0,
            expected_win_rate=0.60,  # < 0.65
            market_liquidity=15000.0,
            capital_available=Decimal("100.00")
        )

        assert result is False

    def test_should_trade_low_liquidity(self, strategy):
        """Test trade rejected for low market liquidity."""
        result = strategy.should_trade(
            signal_confidence=0.85,
            sentiment_score=50.0,
            expected_win_rate=0.70,
            market_liquidity=5000.0,  # < 10000
            capital_available=Decimal("100.00")
        )

        assert result is False

    def test_should_trade_max_positions_reached(self, strategy):
        """Test trade rejected when max positions reached."""
        # Add 3 positions (MAX_POSITIONS = 3)
        for i in range(3):
            strategy.open_positions.append(Position(
                market_id=f"market_{i}",
                side="buy",
                size=Decimal("10.00"),
                entry_price=Decimal("0.50"),
                entry_sentiment=50.0,
                entry_confidence=0.85,
                opened_at=datetime.now()
            ))

        result = strategy.should_trade(
            signal_confidence=0.85,
            sentiment_score=50.0,
            expected_win_rate=0.70,
            market_liquidity=15000.0,
            capital_available=Decimal("100.00")
        )

        assert result is False


class TestCalculatePositionSize:
    """Test position size calculation."""

    @pytest.fixture
    def strategy(self):
        """Create strategy for testing."""
        return IntervalStrategy()

    def test_position_size_high_confidence(self, strategy):
        """Test position size with high confidence."""
        size = strategy.calculate_position_size(
            confidence=0.95,
            capital_available=Decimal("1000.00"),
            risk_percentage=0.03
        )

        # Base: 3% of $1000 = $30
        # Confidence multiplier: 0.5 + (0.95 * 1.0) = 1.45
        # Adjusted: $30 * 1.45 = $43.50
        # Min for $1000+ capital: 2% = $20
        # Max: 10% = $100
        assert Decimal("20") <= size <= Decimal("100")

    def test_position_size_low_confidence(self, strategy):
        """Test position size with low confidence."""
        size = strategy.calculate_position_size(
            confidence=0.80,
            capital_available=Decimal("1000.00"),
            risk_percentage=0.03
        )

        # Confidence multiplier: 0.5 + 0.80 = 1.30
        # Should be lower than high confidence
        assert Decimal("20") <= size <= Decimal("100")

    def test_position_size_small_capital(self, strategy):
        """Test position size with small capital (<$50)."""
        size = strategy.calculate_position_size(
            confidence=0.90,
            capital_available=Decimal("25.00"),
            risk_percentage=0.10
        )

        # Min position for <$50 is $5.00
        assert size >= Decimal("5.00")

    def test_position_size_medium_capital(self, strategy):
        """Test position size with medium capital ($50-$200)."""
        size = strategy.calculate_position_size(
            confidence=0.90,
            capital_available=Decimal("100.00"),
            risk_percentage=0.05
        )

        # Min position for $50-$200 is $10.00
        assert size >= Decimal("10.00")

    def test_position_size_respects_max_limit(self, strategy):
        """Test position size respects 10% max."""
        size = strategy.calculate_position_size(
            confidence=1.0,
            capital_available=Decimal("1000.00"),
            risk_percentage=0.50  # Try 50%
        )

        # Should be capped at 10% = $100
        assert size <= Decimal("100.00")


class TestCreatePosition:
    """Test position creation."""

    @pytest.fixture
    def strategy(self):
        """Create strategy for testing."""
        return IntervalStrategy()

    def test_create_buy_position(self, strategy):
        """Test creating a buy position."""
        position = strategy.create_position(
            market_id="market_123",
            side="buy",
            size=Decimal("50.00"),
            entry_price=Decimal("0.55"),
            sentiment_score=60.0,
            confidence=0.90
        )

        assert position.market_id == "market_123"
        assert position.side == "buy"
        assert position.size == Decimal("50.00")
        assert position.entry_price == Decimal("0.55")
        assert position.entry_sentiment == 60.0
        assert position.entry_confidence == 0.90
        assert position.status == "open"
        assert len(strategy.open_positions) == 1

    def test_create_sell_position(self, strategy):
        """Test creating a sell position."""
        position = strategy.create_position(
            market_id="market_456",
            side="sell",
            size=Decimal("75.00"),
            entry_price=Decimal("0.45"),
            sentiment_score=-50.0,
            confidence=0.85
        )

        assert position.side == "sell"
        assert position.entry_sentiment == -50.0

    def test_multiple_positions(self, strategy):
        """Test creating multiple positions."""
        strategy.create_position("m1", "buy", Decimal("50"), Decimal("0.55"), 60, 0.90)
        strategy.create_position("m2", "sell", Decimal("40"), Decimal("0.45"), -50, 0.85)

        assert len(strategy.open_positions) == 2


class TestCalculateExitStrategy:
    """Test exit strategy calculation."""

    @pytest.fixture
    def strategy(self):
        """Create strategy for testing."""
        return IntervalStrategy()

    @pytest.fixture
    def buy_position(self):
        """Create a sample buy position."""
        pos = Position(
            market_id="market_123",
            side="buy",
            size=Decimal("50.00"),
            entry_price=Decimal("0.50"),
            entry_sentiment=60.0,
            entry_confidence=0.90,
            opened_at=datetime.now() - timedelta(minutes=10)
        )
        pos.age_minutes = 10.0  # Add property for testing
        return pos

    def test_exit_take_profit(self, strategy, buy_position):
        """Test take profit exit."""
        # Price increased by 15%+
        exit_strategy = strategy.calculate_exit_strategy(
            position=buy_position,
            current_price=Decimal("0.60"),  # 20% profit
            current_sentiment=60.0,
            market_volatility=0.10
        )

        assert exit_strategy.type == "TAKE_PROFIT"
        assert "profit" in exit_strategy.reason.lower()

    def test_exit_sentiment_reversal(self, strategy, buy_position):
        """Test exit on sentiment reversal."""
        exit_strategy = strategy.calculate_exit_strategy(
            position=buy_position,
            current_price=Decimal("0.52"),  # Small profit
            current_sentiment=-30.0,  # Reversed to bearish
            market_volatility=0.10
        )

        assert exit_strategy.type == "EXIT_NOW"
        assert "reversal" in exit_strategy.reason.lower()

    def test_exit_time_based(self, strategy):
        """Test time-based exit."""
        # Position opened 15+ minutes ago
        old_position = Position(
            market_id="market_123",
            side="buy",
            size=Decimal("50.00"),
            entry_price=Decimal("0.50"),
            entry_sentiment=60.0,
            entry_confidence=0.90,
            opened_at=datetime.now() - timedelta(minutes=16)
        )

        # Add age_minutes property for testing
        old_position.age_minutes = 16.0

        exit_strategy = strategy.calculate_exit_strategy(
            position=old_position,
            current_price=Decimal("0.52"),
            current_sentiment=60.0,
            market_volatility=0.10
        )

        assert exit_strategy.type == "EXIT_TIME"

    def test_exit_stop_loss(self, strategy, buy_position):
        """Test stop loss exit."""
        # Price dropped significantly
        exit_strategy = strategy.calculate_exit_strategy(
            position=buy_position,
            current_price=Decimal("0.45"),  # -10% loss
            current_sentiment=60.0,
            market_volatility=0.10
        )

        assert exit_strategy.type == "STOP_LOSS"
        assert "stop loss" in exit_strategy.reason.lower()

    def test_exit_hold_favorable(self, strategy, buy_position):
        """Test hold when sentiment still favorable."""
        exit_strategy = strategy.calculate_exit_strategy(
            position=buy_position,
            current_price=Decimal("0.52"),  # Small profit
            current_sentiment=60.0,  # Still bullish
            market_volatility=0.10
        )

        assert exit_strategy.type == "HOLD"


class TestClosePosition:
    """Test position closing and trade recording."""

    @pytest.fixture
    def strategy(self):
        """Create strategy for testing."""
        return IntervalStrategy()

    @pytest.fixture
    def open_position(self, strategy):
        """Create and add an open position."""
        pos = strategy.create_position(
            market_id="market_123",
            side="buy",
            size=Decimal("50.00"),
            entry_price=Decimal("0.50"),
            sentiment_score=60.0,
            confidence=0.90
        )
        # Add age_minutes property
        pos.age_minutes = (datetime.now() - pos.opened_at).total_seconds() / 60.0
        return pos

    def test_close_position_profit(self, strategy, open_position):
        """Test closing position with profit."""
        trade = strategy.close_position(
            position=open_position,
            exit_price=Decimal("0.60"),
            exit_reason="Take profit"
        )

        assert trade['market_id'] == "market_123"
        assert trade['side'] == "buy"
        assert trade['pnl'] > 0  # Profitable
        assert trade['roi_pct'] > 0
        assert trade['exit_reason'] == "Take profit"
        assert len(strategy.open_positions) == 0
        assert strategy.total_trades == 1
        assert strategy.winning_trades == 1
        assert strategy.consecutive_losses == 0

    def test_close_position_loss(self, strategy, open_position):
        """Test closing position with loss."""
        trade = strategy.close_position(
            position=open_position,
            exit_price=Decimal("0.45"),
            exit_reason="Stop loss"
        )

        assert trade['pnl'] < 0  # Loss
        assert trade['roi_pct'] < 0
        assert strategy.total_trades == 1
        assert strategy.winning_trades == 0
        assert strategy.consecutive_losses == 1

    def test_close_sell_position_profit(self, strategy):
        """Test closing sell position with profit."""
        position = strategy.create_position(
            market_id="market_456",
            side="sell",
            size=Decimal("50.00"),
            entry_price=Decimal("0.50"),
            sentiment_score=-60.0,
            confidence=0.90
        )

        # Sell at 0.50, price drops to 0.40 = profit
        trade = strategy.close_position(
            position=position,
            exit_price=Decimal("0.40"),
            exit_reason="Take profit"
        )

        assert trade['pnl'] > 0  # Profitable for sell
        assert strategy.winning_trades == 1

    def test_multiple_position_closes(self, strategy):
        """Test closing multiple positions."""
        # Open and close 3 positions
        for i in range(3):
            pos = strategy.create_position(
                f"market_{i}", "buy", Decimal("50"), Decimal("0.50"), 60, 0.90
            )
            strategy.close_position(pos, Decimal("0.55"), "Exit")

        assert strategy.total_trades == 3
        assert strategy.winning_trades == 3
        assert len(strategy.trade_history) == 3


class TestPerformanceMetrics:
    """Test performance metrics calculation."""

    @pytest.fixture
    def strategy_with_trades(self):
        """Create strategy with trade history."""
        strategy = IntervalStrategy()

        # Add 3 winning trades
        for i in range(3):
            pos = strategy.create_position(
                f"m{i}", "buy", Decimal("50"), Decimal("0.50"), 60, 0.90
            )
            strategy.close_position(pos, Decimal("0.55"), "Profit")

        # Add 2 losing trades
        for i in range(2):
            pos = strategy.create_position(
                f"m{i+3}", "buy", Decimal("50"), Decimal("0.50"), 60, 0.90
            )
            strategy.close_position(pos, Decimal("0.45"), "Loss")

        return strategy

    def test_get_performance_metrics_with_trades(self, strategy_with_trades):
        """Test performance metrics with trades."""
        metrics = strategy_with_trades.get_performance_metrics()

        assert metrics['total_trades'] == 5
        assert metrics['winning_trades'] == 3
        assert metrics['losing_trades'] == 2
        assert 0.5 < metrics['win_rate'] < 0.7
        assert metrics['total_pnl'] != 0
        assert metrics['avg_win'] > 0
        assert metrics['avg_loss'] > 0
        assert 'profit_factor' in metrics
        assert 'open_positions' in metrics

    def test_get_performance_metrics_empty(self):
        """Test performance metrics with no trades."""
        strategy = IntervalStrategy()
        metrics = strategy.get_performance_metrics()

        assert metrics['total_trades'] == 0
        assert metrics['win_rate'] == 0.0
        assert metrics['total_pnl'] == 0.0
        assert metrics['avg_win'] == 0.0
        assert metrics['avg_loss'] == 0.0

    def test_win_rate_property(self, strategy_with_trades):
        """Test win_rate property."""
        win_rate = strategy_with_trades.win_rate

        assert win_rate == 0.6  # 3 wins out of 5 trades


class TestHelperMethods:
    """Test helper methods."""

    @pytest.fixture
    def strategy(self):
        """Create strategy for testing."""
        return IntervalStrategy()

    def test_is_trending_favorable_buy(self, strategy):
        """Test favorable trend for buy position."""
        assert strategy._is_trending_favorable("buy", 50.0) is True
        assert strategy._is_trending_favorable("buy", 10.0) is False

    def test_is_trending_favorable_sell(self, strategy):
        """Test favorable trend for sell position."""
        assert strategy._is_trending_favorable("sell", -50.0) is True
        assert strategy._is_trending_favorable("sell", -10.0) is False

    def test_sentiment_reversed_bullish_to_bearish(self, strategy):
        """Test sentiment reversal from bullish to bearish."""
        assert strategy._sentiment_reversed(60.0, -30.0) is True

    def test_sentiment_reversed_bearish_to_bullish(self, strategy):
        """Test sentiment reversal from bearish to bullish."""
        assert strategy._sentiment_reversed(-60.0, 30.0) is True

    def test_sentiment_not_reversed(self, strategy):
        """Test no sentiment reversal."""
        assert strategy._sentiment_reversed(60.0, 50.0) is False
        assert strategy._sentiment_reversed(-60.0, -50.0) is False

    def test_calculate_dynamic_stop_loss_low_volatility(self, strategy):
        """Test stop loss with low volatility."""
        stop_loss = strategy._calculate_dynamic_stop_loss(0.10)

        # Base 8% + (10% * 0.5) = 13%
        assert 0.10 < stop_loss < 0.15

    def test_calculate_dynamic_stop_loss_high_volatility(self, strategy):
        """Test stop loss with high volatility."""
        stop_loss = strategy._calculate_dynamic_stop_loss(0.50)

        # Should be wider but capped at 20%
        assert stop_loss <= 0.20

    def test_calculate_dynamic_stop_loss_capped(self, strategy):
        """Test stop loss is capped at 20%."""
        stop_loss = strategy._calculate_dynamic_stop_loss(1.0)

        assert stop_loss == 0.20

    def test_calculate_recent_win_rate_with_trades(self, strategy):
        """Test recent win rate calculation."""
        # Add trade history
        strategy.trade_history = [
            {'pnl': 10.0},
            {'pnl': -5.0},
            {'pnl': 15.0},
            {'pnl': 20.0},
            {'pnl': -8.0},
        ]

        win_rate = strategy._calculate_recent_win_rate()

        assert win_rate == 0.6  # 3 wins out of 5

    def test_calculate_recent_win_rate_empty(self, strategy):
        """Test recent win rate with no trades."""
        win_rate = strategy._calculate_recent_win_rate()

        assert win_rate == 0.0

    def test_check_recent_performance_good(self, strategy):
        """Test performance check with good win rate."""
        strategy.trade_history = [
            {'pnl': 10.0}, {'pnl': 15.0}, {'pnl': 20.0},
            {'pnl': 5.0}, {'pnl': 8.0},
        ]

        assert strategy._check_recent_performance() is True

    def test_check_recent_performance_poor(self, strategy):
        """Test performance check with poor win rate."""
        strategy.trade_history = [
            {'pnl': -10.0}, {'pnl': -15.0}, {'pnl': -20.0},
            {'pnl': -5.0}, {'pnl': -8.0},
        ]

        assert strategy._check_recent_performance() is False


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_position_size_zero_capital(self):
        """Test position size with zero capital."""
        strategy = IntervalStrategy()

        size = strategy.calculate_position_size(
            confidence=0.90,
            capital_available=Decimal("0.00"),
            risk_percentage=0.03
        )

        # Should return minimum based on capital tier
        assert size == Decimal("5.00")

    def test_close_position_zero_size(self):
        """Test closing position with zero size."""
        strategy = IntervalStrategy()

        position = Position(
            market_id="test",
            side="buy",
            size=Decimal("0.00"),
            entry_price=Decimal("0.50"),
            entry_sentiment=60.0,
            entry_confidence=0.90,
            opened_at=datetime.now()
        )

        trade = strategy.close_position(position, Decimal("0.55"), "Test")

        assert trade['roi_pct'] == 0

    def test_performance_metrics_profit_factor_infinity(self):
        """Test profit factor when no losses."""
        strategy = IntervalStrategy()

        # Only winning trades
        pos = strategy.create_position("m1", "buy", Decimal("50"), Decimal("0.50"), 60, 0.90)
        strategy.close_position(pos, Decimal("0.55"), "Profit")

        metrics = strategy.get_performance_metrics()

        assert metrics['profit_factor'] == float('inf')
