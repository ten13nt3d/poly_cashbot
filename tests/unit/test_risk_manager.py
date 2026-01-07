"""Unit tests for Risk Manager."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from src.lib.risk.manager import (
    ScalableRiskManager,
    RiskCheck,
    DailyRiskMetrics,
)


class TestRiskManagerInitialization:
    """Test risk manager initialization and tier assignment."""

    def test_micro_tier_assignment(self):
        """Test micro tier assignment for $10-$50 capital."""
        manager = ScalableRiskManager(Decimal("25.00"))

        assert manager.tier == "micro"
        assert manager.total_capital == Decimal("25.00")
        assert manager.params["per_trade_risk"] == 0.10
        assert manager.params["daily_loss_limit"] == 0.20
        assert manager.params["max_positions"] == 2

    def test_small_tier_assignment(self):
        """Test small tier assignment for $50-$200 capital."""
        manager = ScalableRiskManager(Decimal("100.00"))

        assert manager.tier == "small"
        assert manager.params["per_trade_risk"] == 0.05
        assert manager.params["daily_loss_limit"] == 0.15
        assert manager.params["max_positions"] == 3

    def test_medium_tier_assignment(self):
        """Test medium tier assignment for $200-$1000 capital."""
        manager = ScalableRiskManager(Decimal("500.00"))

        assert manager.tier == "medium"
        assert manager.params["per_trade_risk"] == 0.03
        assert manager.params["daily_loss_limit"] == 0.10
        assert manager.params["max_positions"] == 4

    def test_large_tier_assignment(self):
        """Test large tier assignment for $1000+ capital."""
        manager = ScalableRiskManager(Decimal("2000.00"))

        assert manager.tier == "large"
        assert manager.params["per_trade_risk"] == 0.02
        assert manager.params["daily_loss_limit"] == 0.10
        assert manager.params["max_positions"] == 5

    def test_tier_boundary_exactly_50(self):
        """Test tier boundary at exactly $50."""
        manager = ScalableRiskManager(Decimal("50.00"))

        assert manager.tier == "small"  # $50 is start of small tier

    def test_tier_boundary_exactly_200(self):
        """Test tier boundary at exactly $200."""
        manager = ScalableRiskManager(Decimal("200.00"))

        assert manager.tier == "medium"

    def test_initialization_sets_peak_equity(self):
        """Test that peak equity is set to initial capital."""
        manager = ScalableRiskManager(Decimal("100.00"))

        assert manager.peak_equity == Decimal("100.00")

    def test_initialization_creates_empty_positions(self):
        """Test that open positions list is initialized empty."""
        manager = ScalableRiskManager(Decimal("100.00"))

        assert manager.open_positions == []

    def test_initialization_creates_daily_metrics(self):
        """Test that daily metrics are initialized."""
        manager = ScalableRiskManager(Decimal("100.00"))

        assert isinstance(manager.daily_metrics, DailyRiskMetrics)
        assert manager.daily_metrics.total_pnl == Decimal("0")
        assert manager.daily_metrics.total_trades == 0
        assert manager.daily_metrics.winning_trades == 0
        assert manager.daily_metrics.consecutive_losses == 0


class TestPositionSizeCalculation:
    """Test position size calculation with various factors."""

    @pytest.fixture
    def micro_manager(self):
        """Create micro tier manager."""
        return ScalableRiskManager(Decimal("25.00"))

    @pytest.fixture
    def medium_manager(self):
        """Create medium tier manager."""
        return ScalableRiskManager(Decimal("500.00"))

    def test_base_position_size_high_confidence(self, micro_manager):
        """Test position size with high confidence."""
        size = micro_manager.calculate_position_size(
            signal_confidence=0.95,
            market_volatility=0.10
        )

        # Micro tier: 10% of $25 = $2.50 base
        # Confidence multiplier: 0.95 - 0.2 = 0.75
        # Volatility factor: 1.0 - 0.10 = 0.90
        # $2.50 * 0.75 * 0.90 = $1.6875
        # But min position is $5.00 for micro tier
        assert size == Decimal("5.00")

    def test_base_position_size_medium_confidence(self, medium_manager):
        """Test position size with medium confidence."""
        size = medium_manager.calculate_position_size(
            signal_confidence=0.85,
            market_volatility=0.15
        )

        # Medium tier: 3% of $500 = $15.00 base
        # Confidence multiplier: 0.85 - 0.2 = 0.65
        # Volatility factor: 1.0 - 0.15 = 0.85
        # $15.00 * 0.65 * 0.85 = $8.2875
        # But min position is $20.00 for medium tier
        assert size == Decimal("20.00")

    def test_position_size_low_confidence(self, medium_manager):
        """Test position size with low confidence."""
        size = medium_manager.calculate_position_size(
            signal_confidence=0.70,
            market_volatility=0.10
        )

        # Confidence multiplier capped at 0.6 minimum
        # $15 * 0.6 * 0.9 = $8.10, capped at $20 min
        assert size == Decimal("20.00")

    def test_position_size_high_volatility(self, medium_manager):
        """Test position size reduces with high volatility."""
        low_vol_size = medium_manager.calculate_position_size(
            signal_confidence=0.90,
            market_volatility=0.10
        )

        high_vol_size = medium_manager.calculate_position_size(
            signal_confidence=0.90,
            market_volatility=0.50
        )

        # Higher volatility should result in smaller position
        # But both might be at minimum $20
        assert high_vol_size <= low_vol_size

    def test_position_size_respects_max_limit(self, medium_manager):
        """Test position size respects maximum limit."""
        # Use custom high risk percentage to test max cap
        size = medium_manager.calculate_position_size(
            signal_confidence=1.0,
            market_volatility=0.0,
            risk_percentage=1.0  # Try to use 100% of capital
        )

        # Should be capped at max_single_position for medium tier ($100)
        assert size <= medium_manager.params["max_single_position"]

    def test_custom_risk_percentage(self, medium_manager):
        """Test position size with custom risk percentage."""
        size = medium_manager.calculate_position_size(
            signal_confidence=0.90,
            market_volatility=0.10,
            risk_percentage=0.01  # 1% risk instead of default 3%
        )

        # Should use lower custom risk percentage
        # 1% of $500 = $5, adjusted = ~$3-4, capped at $20 min
        assert size == Decimal("20.00")


class TestOrderValidation:
    """Test order validation against risk limits."""

    @pytest.fixture
    def manager(self):
        """Create manager with $5000 capital (large tier)."""
        return ScalableRiskManager(Decimal("5000.00"))

    def test_valid_order(self, manager):
        """Test validation of valid order."""
        # Large tier: 2% of $5000 = $100 max per-trade
        # Min $50, max $500 per position
        # Valid order: $75 (within all limits)
        result = manager.validate_order(Decimal("75.00"))

        assert result.passed is True
        assert result.maximum_size == Decimal("100.00")
        assert result.risk_percentage == 0.02

    def test_order_exceeds_per_trade_limit(self, manager):
        """Test order exceeding per-trade risk limit."""
        # Large tier allows 2% of $5000 = $100, try $150
        result = manager.validate_order(Decimal("150.00"))

        assert result.passed is False
        assert "exceeds" in result.reason.lower()
        assert result.maximum_size == Decimal("100.00")

    def test_order_below_minimum_size(self, manager):
        """Test order below minimum position size."""
        # Large tier minimum is $50.00
        result = manager.validate_order(Decimal("25.00"))

        assert result.passed is False
        assert "below minimum" in result.reason.lower()

    def test_order_exceeds_maximum_single_position(self, manager):
        """Test order exceeding maximum single position limit."""
        # Large tier max single position is $500.00
        # Note: Per-trade limit ($100) triggers first for $600
        result = manager.validate_order(Decimal("600.00"))

        assert result.passed is False
        # Will fail on per-trade limit, not max single position
        assert "exceeds" in result.reason.lower()

    def test_daily_loss_limit_exceeded(self, manager):
        """Test order blocked when daily loss limit exceeded."""
        # Set daily loss to exceed limit (10% of $5000 = $500)
        manager.daily_metrics.total_pnl = Decimal("-600.00")

        result = manager.validate_order(Decimal("75.00"))

        assert result.passed is False
        assert "daily loss" in result.reason.lower()

    def test_max_positions_reached(self, manager):
        """Test order blocked when max positions reached."""
        # Large tier allows 5 positions
        manager.add_position("pos_1", Decimal("75.00"))
        manager.add_position("pos_2", Decimal("75.00"))
        manager.add_position("pos_3", Decimal("75.00"))
        manager.add_position("pos_4", Decimal("75.00"))
        manager.add_position("pos_5", Decimal("75.00"))

        result = manager.validate_order(Decimal("75.00"))

        assert result.passed is False
        assert "maximum" in result.reason.lower()
        assert "positions" in result.reason.lower()

    def test_liquidity_check_passes(self, manager):
        """Test order passes liquidity check."""
        # Order is 10% of liquidity (exactly at limit)
        result = manager.validate_order(
            Decimal("75.00"),
            market_liquidity=Decimal("750.00")
        )

        assert result.passed is True

    def test_liquidity_check_fails(self, manager):
        """Test order fails liquidity check."""
        # Order exceeds 10% of liquidity
        result = manager.validate_order(
            Decimal("75.00"),
            market_liquidity=Decimal("500.00")
        )

        assert result.passed is False
        assert "liquidity" in result.reason.lower()

    def test_win_rate_protection_not_enough_trades(self, manager):
        """Test win rate protection doesn't block with <10 trades."""
        # With < 10 trades, should allow trading
        manager.daily_metrics.total_trades = 5
        manager.daily_metrics.winning_trades = 1  # 20% win rate

        result = manager.validate_order(Decimal("75.00"))

        # Should pass because not enough data
        assert result.passed is True

    def test_win_rate_protection_blocks_low_win_rate(self, manager):
        """Test win rate protection blocks with low win rate."""
        # Large tier requires 70% win rate
        manager.daily_metrics.total_trades = 20
        manager.daily_metrics.winning_trades = 10  # 50% win rate

        result = manager.validate_order(Decimal("75.00"))

        assert result.passed is False
        assert "win rate" in result.reason.lower()

    def test_win_rate_protection_passes_good_win_rate(self, manager):
        """Test win rate protection passes with good win rate."""
        # Large tier requires 70% win rate
        manager.daily_metrics.total_trades = 20
        manager.daily_metrics.winning_trades = 15  # 75% win rate

        result = manager.validate_order(Decimal("75.00"))

        assert result.passed is True


class TestPositionTracking:
    """Test position tracking functionality."""

    @pytest.fixture
    def manager(self):
        """Create manager for position tests."""
        return ScalableRiskManager(Decimal("100.00"))

    def test_add_position(self, manager):
        """Test adding a position."""
        manager.add_position("pos_123", Decimal("15.00"))

        assert len(manager.open_positions) == 1
        assert manager.open_positions[0]["id"] == "pos_123"
        assert manager.open_positions[0]["size"] == Decimal("15.00")
        assert "opened_at" in manager.open_positions[0]

    def test_add_multiple_positions(self, manager):
        """Test adding multiple positions."""
        manager.add_position("pos_1", Decimal("10.00"))
        manager.add_position("pos_2", Decimal("15.00"))
        manager.add_position("pos_3", Decimal("20.00"))

        assert len(manager.open_positions) == 3

    def test_remove_position_success(self, manager):
        """Test removing existing position."""
        manager.add_position("pos_123", Decimal("15.00"))

        result = manager.remove_position("pos_123")

        assert result is True
        assert len(manager.open_positions) == 0

    def test_remove_position_not_found(self, manager):
        """Test removing non-existent position."""
        result = manager.remove_position("nonexistent")

        assert result is False

    def test_remove_position_from_multiple(self, manager):
        """Test removing specific position from multiple."""
        manager.add_position("pos_1", Decimal("10.00"))
        manager.add_position("pos_2", Decimal("15.00"))
        manager.add_position("pos_3", Decimal("20.00"))

        result = manager.remove_position("pos_2")

        assert result is True
        assert len(manager.open_positions) == 2
        assert all(p["id"] != "pos_2" for p in manager.open_positions)

    def test_get_position_risk_metrics(self, manager):
        """Test getting position risk metrics."""
        manager.add_position("pos_1", Decimal("10.00"))
        manager.add_position("pos_2", Decimal("15.00"))

        metrics = manager.get_position_risk_metrics()

        assert len(metrics) == 2
        assert metrics[0]["position_id"] == "pos_1"
        assert metrics[0]["size"] == 10.00
        assert "age_minutes" in metrics[0]


class TestDailyMetrics:
    """Test daily metrics tracking and calculations."""

    @pytest.fixture
    def manager(self):
        """Create manager for metrics tests."""
        return ScalableRiskManager(Decimal("100.00"))

    def test_update_metrics_winning_trade(self, manager):
        """Test updating metrics for winning trade."""
        manager.update_daily_metrics(
            pnl=Decimal("5.00"),
            is_win=True,
            current_equity=Decimal("105.00")
        )

        assert manager.daily_metrics.total_pnl == Decimal("5.00")
        assert manager.daily_metrics.total_trades == 1
        assert manager.daily_metrics.winning_trades == 1
        assert manager.daily_metrics.consecutive_losses == 0

    def test_update_metrics_losing_trade(self, manager):
        """Test updating metrics for losing trade."""
        manager.update_daily_metrics(
            pnl=Decimal("-3.00"),
            is_win=False,
            current_equity=Decimal("97.00")
        )

        assert manager.daily_metrics.total_pnl == Decimal("-3.00")
        assert manager.daily_metrics.total_trades == 1
        assert manager.daily_metrics.winning_trades == 0
        assert manager.daily_metrics.consecutive_losses == 1

    def test_consecutive_losses_tracking(self, manager):
        """Test consecutive losses counter."""
        # First loss
        manager.update_daily_metrics(Decimal("-2.00"), False)
        assert manager.daily_metrics.consecutive_losses == 1

        # Second loss
        manager.update_daily_metrics(Decimal("-3.00"), False)
        assert manager.daily_metrics.consecutive_losses == 2

        # Win resets counter
        manager.update_daily_metrics(Decimal("5.00"), True)
        assert manager.daily_metrics.consecutive_losses == 0

    def test_peak_equity_tracking(self, manager):
        """Test peak equity tracking."""
        # Initial peak is $100
        assert manager.peak_equity == Decimal("100.00")

        # Update with higher equity
        manager.update_daily_metrics(
            pnl=Decimal("10.00"),
            is_win=True,
            current_equity=Decimal("110.00")
        )
        assert manager.peak_equity == Decimal("110.00")

        # Update with lower equity (peak shouldn't change)
        manager.update_daily_metrics(
            pnl=Decimal("-5.00"),
            is_win=False,
            current_equity=Decimal("105.00")
        )
        assert manager.peak_equity == Decimal("110.00")

    def test_max_drawdown_calculation(self, manager):
        """Test maximum drawdown calculation."""
        # Start at $100, go to $110 (new peak)
        manager.update_daily_metrics(
            pnl=Decimal("10.00"),
            is_win=True,
            current_equity=Decimal("110.00")
        )

        # Drop to $95 (drawdown of $15 from peak)
        manager.update_daily_metrics(
            pnl=Decimal("-15.00"),
            is_win=False,
            current_equity=Decimal("95.00")
        )

        assert manager.daily_metrics.max_drawdown == Decimal("15.00")

    def test_get_daily_win_rate(self, manager):
        """Test daily win rate calculation."""
        # No trades
        assert manager.get_daily_win_rate() == 0.0

        # 3 wins out of 5 trades
        manager.daily_metrics.total_trades = 5
        manager.daily_metrics.winning_trades = 3

        assert manager.get_daily_win_rate() == 0.6


class TestCircuitBreaker:
    """Test circuit breaker triggers."""

    @pytest.fixture
    def manager(self):
        """Create manager for circuit breaker tests."""
        return ScalableRiskManager(Decimal("5000.00"))

    def test_no_circuit_breaker_normal_conditions(self, manager):
        """Test circuit breaker doesn't trigger under normal conditions."""
        manager.daily_metrics.total_pnl = Decimal("100.00")
        manager.daily_metrics.total_trades = 10
        manager.daily_metrics.winning_trades = 8

        reason = manager.check_circuit_breaker()

        assert reason is None

    def test_circuit_breaker_daily_loss_limit(self, manager):
        """Test circuit breaker triggers on daily loss limit."""
        # Large tier: 10% of $5000 = $500 loss limit
        manager.daily_metrics.total_pnl = Decimal("-600.00")

        reason = manager.check_circuit_breaker()

        assert reason is not None
        assert "daily loss" in reason.lower()

    def test_circuit_breaker_consecutive_losses(self, manager):
        """Test circuit breaker triggers on 3 consecutive losses."""
        manager.daily_metrics.consecutive_losses = 3

        reason = manager.check_circuit_breaker()

        assert reason is not None
        assert "consecutive" in reason.lower()

    def test_circuit_breaker_max_drawdown(self, manager):
        """Test circuit breaker triggers on excessive drawdown."""
        # Max drawdown threshold is 25% of capital
        manager.daily_metrics.max_drawdown = Decimal("1500.00")  # 30% of $5000

        reason = manager.check_circuit_breaker()

        assert reason is not None
        assert "drawdown" in reason.lower()

    def test_circuit_breaker_low_win_rate(self, manager):
        """Test circuit breaker triggers on low win rate."""
        # Large tier requires 70% win rate
        manager.daily_metrics.total_trades = 20
        manager.daily_metrics.winning_trades = 10  # 50% win rate

        reason = manager.check_circuit_breaker()

        assert reason is not None
        assert "win rate" in reason.lower()

    def test_circuit_breaker_win_rate_needs_min_trades(self, manager):
        """Test circuit breaker requires 20+ trades for win rate check."""
        # Only 15 trades, even with bad win rate
        manager.daily_metrics.total_trades = 15
        manager.daily_metrics.winning_trades = 5  # 33% win rate

        reason = manager.check_circuit_breaker()

        # Should not trigger on win rate with <20 trades
        assert reason is None


class TestStopLossCalculation:
    """Test dynamic stop-loss calculation."""

    @pytest.fixture
    def micro_manager(self):
        """Create micro tier manager."""
        return ScalableRiskManager(Decimal("25.00"))

    @pytest.fixture
    def large_manager(self):
        """Create large tier manager."""
        return ScalableRiskManager(Decimal("2000.00"))

    def test_stop_loss_micro_tier_low_volatility(self, micro_manager):
        """Test stop-loss for micro tier with low volatility."""
        stop = micro_manager.calculate_dynamic_stop_loss(
            market_volatility=0.10,
            position_side="buy"
        )

        # Base: 15%, volatility adj: 0.10 * 0.5 = 0.05
        # Total: 20%
        assert stop == Decimal("0.20")

    def test_stop_loss_large_tier_low_volatility(self, large_manager):
        """Test stop-loss for large tier with low volatility."""
        stop = large_manager.calculate_dynamic_stop_loss(
            market_volatility=0.10,
            position_side="buy"
        )

        # Base: 8%, volatility adj: 0.10 * 0.5 = 0.05
        # Total: 13%
        assert stop == Decimal("0.13")

    def test_stop_loss_high_volatility(self, micro_manager):
        """Test stop-loss widens with high volatility."""
        low_vol_stop = micro_manager.calculate_dynamic_stop_loss(
            market_volatility=0.10,
            position_side="buy"
        )

        high_vol_stop = micro_manager.calculate_dynamic_stop_loss(
            market_volatility=0.50,
            position_side="buy"
        )

        # Higher volatility should result in wider stop
        assert high_vol_stop >= low_vol_stop

    def test_stop_loss_capped_at_20_percent(self, micro_manager):
        """Test stop-loss is capped at 20%."""
        stop = micro_manager.calculate_dynamic_stop_loss(
            market_volatility=1.0,  # Very high volatility
            position_side="buy"
        )

        # Should be capped at 20%
        assert stop == Decimal("0.20")


class TestRiskSummary:
    """Test risk summary generation."""

    @pytest.fixture
    def manager(self):
        """Create manager with some activity."""
        mgr = ScalableRiskManager(Decimal("5000.00"))
        mgr.add_position("pos_1", Decimal("75.00"))
        mgr.update_daily_metrics(Decimal("50.00"), True, Decimal("5050.00"))
        return mgr

    def test_get_risk_summary_structure(self, manager):
        """Test risk summary has all required fields."""
        summary = manager.get_risk_summary()

        assert "tier" in summary
        assert "total_capital" in summary
        assert "open_positions" in summary
        assert "daily_pnl" in summary
        assert "daily_trades" in summary
        assert "daily_win_rate" in summary
        assert "max_drawdown" in summary
        assert "consecutive_losses" in summary
        assert "per_trade_risk_pct" in summary
        assert "daily_loss_limit_pct" in summary
        assert "max_positions" in summary
        assert "circuit_breaker" in summary

    def test_get_risk_summary_values(self, manager):
        """Test risk summary contains correct values."""
        summary = manager.get_risk_summary()

        assert summary["tier"] == "large"
        assert summary["total_capital"] == 5000.00
        assert summary["open_positions"] == 1
        assert summary["daily_pnl"] == 50.00
        assert summary["daily_trades"] == 1
        assert summary["daily_win_rate"] == 1.0
        assert summary["per_trade_risk_pct"] == 0.02
        assert summary["circuit_breaker"] is None


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_very_small_capital(self):
        """Test with very small capital amount."""
        manager = ScalableRiskManager(Decimal("10.00"))

        assert manager.tier == "micro"
        assert manager.total_capital == Decimal("10.00")

    def test_position_size_with_zero_volatility(self):
        """Test position size calculation with zero volatility."""
        manager = ScalableRiskManager(Decimal("100.00"))

        size = manager.calculate_position_size(
            signal_confidence=0.90,
            market_volatility=0.0
        )

        # Should not crash, should return valid size
        assert size >= manager.params["min_position_size"]

    def test_position_size_with_max_volatility(self):
        """Test position size with maximum volatility."""
        manager = ScalableRiskManager(Decimal("100.00"))

        size = manager.calculate_position_size(
            signal_confidence=0.90,
            market_volatility=1.0
        )

        # Volatility factor capped at 0.5 minimum
        assert size >= manager.params["min_position_size"]

    def test_validate_order_zero_size(self):
        """Test validating order with zero size."""
        manager = ScalableRiskManager(Decimal("100.00"))

        result = manager.validate_order(Decimal("0.00"))

        assert result.passed is False

    def test_remove_all_positions_sequentially(self):
        """Test removing all positions one by one."""
        manager = ScalableRiskManager(Decimal("100.00"))

        manager.add_position("pos_1", Decimal("10.00"))
        manager.add_position("pos_2", Decimal("15.00"))
        manager.add_position("pos_3", Decimal("20.00"))

        assert len(manager.open_positions) == 3

        manager.remove_position("pos_1")
        assert len(manager.open_positions) == 2

        manager.remove_position("pos_2")
        assert len(manager.open_positions) == 1

        manager.remove_position("pos_3")
        assert len(manager.open_positions) == 0
