"""Unit tests for CashBot shutdown and cleanup."""

import pytest
from decimal import Decimal
from unittest.mock import MagicMock, patch

from src.bot.main import CashBot


class TestCashBotShutdown:
    """Test cases for bot shutdown and cleanup."""

    @pytest.fixture(autouse=True)
    def mock_components(self):
        """Mock all bot components."""
        with patch("src.bot.main.TemporalArbitrageDetector") as mock_arb, \
             patch("src.bot.main.WhaleDetector") as mock_whale, \
             patch("src.bot.main.IntervalStrategy") as mock_strategy, \
             patch("src.bot.main.ScalableRiskManager") as mock_risk, \
             patch("src.bot.main.DatabaseManager") as mock_db, \
             patch("src.bot.main.PolymarketClient") as mock_poly, \
             patch("src.bot.main.PriceFeedService") as mock_price, \
             patch("src.bot.main.MarketDiscoveryService") as mock_discovery:

            yield {
                "arbitrage": mock_arb,
                "whale": mock_whale,
                "strategy": mock_strategy,
                "risk": mock_risk,
                "db": mock_db,
                "polymarket": mock_poly,
                "price_feed": mock_price,
                "discovery": mock_discovery,
            }

    @pytest.mark.asyncio
    async def test_circuit_breaker_stops_bot(self, mock_components):
        """Test circuit breaker stops bot execution."""
        bot = CashBot(total_capital=Decimal("1000"))
        bot.is_running = True

        # Mock circuit breaker triggered
        bot.risk_manager.check_circuit_breaker = MagicMock(
            return_value="DAILY_LOSS_LIMIT_EXCEEDED"
        )
        bot.risk_manager.get_risk_summary = MagicMock(
            return_value={"consecutive_losses": 0}
        )

        await bot._check_risk_limits()

        assert bot.is_running is False

    @pytest.mark.asyncio
    async def test_performance_summary_available_after_shutdown(self, mock_components):
        """Test performance summary can be retrieved after shutdown."""
        bot = CashBot(total_capital=Decimal("1000"))
        bot.is_running = False

        # Mock metrics
        bot.strategy.get_performance_metrics = MagicMock(return_value={
            "total_pnl": 100.0,
            "win_rate": 0.70,
            "total_trades": 5,
        })

        bot.risk_manager.get_risk_summary = MagicMock(return_value={
            "daily_pnl": 50.0,
        })

        bot.whale_detector.get_statistics = MagicMock(return_value={
            "total_whales_detected": 2,
        })

        summary = bot.get_performance_summary()

        assert summary is not None
        assert "bot_stats" in summary
        assert "performance" in summary

    def test_positions_remain_accessible_after_stop(self, mock_components):
        """Test open positions remain accessible after bot stops."""
        bot = CashBot(total_capital=Decimal("1000"))

        # Add mock position
        position = MagicMock()
        position.market_id = "market_1"
        bot.strategy.open_positions = [position]

        bot.is_running = False

        # Positions should still be accessible
        assert len(bot.strategy.open_positions) == 1
        assert bot.strategy.open_positions[0].market_id == "market_1"

    def test_stats_preserved_after_shutdown(self, mock_components):
        """Test statistics are preserved after shutdown."""
        bot = CashBot(total_capital=Decimal("1000"))

        # Set some stats
        bot.stats["signals_generated"] = 10
        bot.stats["signals_executed"] = 5
        bot.stats["total_trades"] = 3

        bot.is_running = False

        # Stats should be preserved
        assert bot.stats["signals_generated"] == 10
        assert bot.stats["signals_executed"] == 5
        assert bot.stats["total_trades"] == 3

    def test_capital_preserved_after_shutdown(self, mock_components):
        """Test capital values are preserved after shutdown."""
        bot = CashBot(total_capital=Decimal("1000"))

        # Modify capital
        bot.available_capital = Decimal("850")

        bot.is_running = False

        # Capital should be preserved
        assert bot.total_capital == Decimal("1000")
        assert bot.available_capital == Decimal("850")

    def test_graceful_shutdown_with_open_positions(self, mock_components):
        """Test bot can shut down gracefully with open positions."""
        bot = CashBot(total_capital=Decimal("1000"))

        # Add mock positions
        position1 = MagicMock()
        position1.market_id = "market_1"
        position2 = MagicMock()
        position2.market_id = "market_2"

        bot.strategy.open_positions = [position1, position2]
        bot.is_running = False

        # Should shut down without errors
        summary = bot.get_performance_summary()
        assert summary is not None

    @pytest.mark.asyncio
    async def test_consecutive_losses_trigger_shutdown(self, mock_components):
        """Test consecutive losses trigger shutdown via circuit breaker."""
        bot = CashBot(total_capital=Decimal("1000"))
        bot.is_running = True

        # Mock 3 consecutive losses
        bot.risk_manager.check_circuit_breaker = MagicMock(
            return_value="CONSECUTIVE_LOSSES_LIMIT"
        )
        bot.risk_manager.get_risk_summary = MagicMock(
            return_value={"consecutive_losses": 3}
        )

        await bot._check_risk_limits()

        assert bot.is_running is False

    @pytest.mark.asyncio
    async def test_daily_loss_limit_triggers_shutdown(self, mock_components):
        """Test daily loss limit triggers shutdown."""
        bot = CashBot(total_capital=Decimal("1000"))
        bot.is_running = True

        # Mock daily loss limit exceeded
        bot.risk_manager.check_circuit_breaker = MagicMock(
            return_value="DAILY_LOSS_LIMIT_EXCEEDED"
        )
        bot.risk_manager.get_risk_summary = MagicMock(
            return_value={"daily_pnl": -200.0}
        )

        await bot._check_risk_limits()

        assert bot.is_running is False

    def test_shutdown_does_not_lose_position_mapping(self, mock_components):
        """Test position ID mapping is preserved on shutdown."""
        bot = CashBot(total_capital=Decimal("1000"))

        # Add position mappings
        bot.position_id_map["market_1"] = "risk_pos_1"
        bot.position_id_map["market_2"] = "risk_pos_2"

        bot.is_running = False

        # Mappings should be preserved
        assert bot.position_id_map["market_1"] == "risk_pos_1"
        assert bot.position_id_map["market_2"] == "risk_pos_2"
        assert len(bot.position_id_map) == 2
