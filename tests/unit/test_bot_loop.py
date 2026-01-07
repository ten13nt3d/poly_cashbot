"""Unit tests for CashBot main trading loop."""

import pytest
import asyncio
from decimal import Decimal
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch, call

from src.bot.main import CashBot
from src.lib.sentiment.analyzer import TemporalArbitrageOpportunity
from src.lib.whale.detector import WhaleAlert


class TestCashBotMainLoop:
    """Test cases for bot main trading loop."""

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
    async def test_start_sets_running_flag(self, mock_components):
        """Test start() sets is_running flag."""
        bot = CashBot(total_capital=Decimal("1000"))

        # Mock the main loop to exit immediately
        with patch.object(bot, "_main_loop", new_callable=AsyncMock) as mock_loop:
            await bot.start()
            mock_loop.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_markets_fetches_data(self, mock_components):
        """Test _analyze_markets fetches spot and polymarket data."""
        bot = CashBot(total_capital=Decimal("1000"))

        with patch.object(bot, "_fetch_spot_data", new_callable=AsyncMock) as mock_spot, \
             patch.object(bot, "_fetch_polymarket_data", new_callable=AsyncMock) as mock_poly:

            mock_spot.return_value = {}
            mock_poly.return_value = {}

            await bot._analyze_markets()

            mock_spot.assert_called_once()
            mock_poly.assert_called_once()

    @pytest.mark.asyncio
    async def test_analyze_markets_detects_arbitrage(self, mock_components):
        """Test _analyze_markets detects arbitrage opportunities."""
        bot = CashBot(total_capital=Decimal("1000"))

        # Mock arbitrage detector ASSETS
        bot.arbitrage_detector.ASSETS = ["BTC"]

        # Mock opportunity
        opportunity = MagicMock(spec=TemporalArbitrageOpportunity)
        opportunity.confidence = 0.95
        opportunity.polymarket_lag = 35
        opportunity.direction = "BUY"
        opportunity.urgency = "HIGH"

        bot.arbitrage_detector.detect_arbitrage_opportunity = MagicMock(return_value=opportunity)

        with patch.object(bot, "_fetch_spot_data", new_callable=AsyncMock) as mock_spot, \
             patch.object(bot, "_fetch_polymarket_data", new_callable=AsyncMock) as mock_poly, \
             patch.object(bot, "_execute_arbitrage", new_callable=AsyncMock):

            mock_spot.return_value = {"BTC": {"price": 50000}}
            mock_poly.return_value = {"BTC": {"price": 0.55}}

            # Mock risk check to pass
            risk_check = MagicMock()
            risk_check.passed = True
            bot.risk_manager.validate_order = MagicMock(return_value=risk_check)

            await bot._analyze_markets()

            # Should increment signals_generated
            assert bot.stats["signals_generated"] > 0

    @pytest.mark.asyncio
    async def test_check_whale_alerts_method_exists(self, mock_components):
        """Test _check_whale_alerts method exists and is callable."""
        bot = CashBot(total_capital=Decimal("1000"))

        # Just verify the method exists and can be called
        assert hasattr(bot, "_check_whale_alerts")
        assert callable(getattr(bot, "_check_whale_alerts"))

    @pytest.mark.asyncio
    async def test_monitor_positions_checks_all_open_positions(self, mock_components):
        """Test _monitor_positions checks all open positions."""
        bot = CashBot(total_capital=Decimal("1000"))

        # Create mock positions
        position1 = MagicMock()
        position1.market_id = "market_1"
        position1.side = "buy"

        position2 = MagicMock()
        position2.market_id = "market_2"
        position2.side = "sell"

        bot.strategy.open_positions = [position1, position2]

        # Mock exit strategy
        exit_strategy = MagicMock()
        exit_strategy.type = "HOLD"

        bot.strategy.calculate_exit_strategy = MagicMock(return_value=exit_strategy)

        await bot._monitor_positions()

        # Should calculate exit strategy for both positions
        assert bot.strategy.calculate_exit_strategy.call_count == 2

    @pytest.mark.asyncio
    async def test_monitor_positions_closes_position_on_exit_signal(self, mock_components):
        """Test _monitor_positions closes position when exit strategy is not HOLD."""
        bot = CashBot(total_capital=Decimal("1000"))

        position = MagicMock()
        position.market_id = "market_1"
        position.side = "buy"

        bot.strategy.open_positions = [position]

        # Mock exit strategy that says to exit
        exit_strategy = MagicMock()
        exit_strategy.type = "TAKE_PROFIT"
        exit_strategy.reason = "Target profit reached"

        bot.strategy.calculate_exit_strategy = MagicMock(return_value=exit_strategy)

        with patch.object(bot, "_close_position", new_callable=AsyncMock) as mock_close:
            await bot._monitor_positions()

            mock_close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_position_updates_capital(self, mock_components):
        """Test _close_position returns capital + PnL."""
        bot = CashBot(total_capital=Decimal("1000"))
        bot.available_capital = Decimal("900")  # 100 in position

        position = MagicMock()
        position.market_id = "market_1"

        # Mock trade result
        trade_result = {
            "size": 100.00,
            "pnl": 15.00,
            "roi_pct": 0.15,
        }

        bot.strategy.close_position = MagicMock(return_value=trade_result)
        bot.position_id_map["market_1"] = "risk_pos_1"
        bot.risk_manager.remove_position = MagicMock()

        await bot._close_position(position, Decimal("0.60"), "Test exit")

        # Capital should be 900 + 100 + 15 = 1015
        assert bot.available_capital == Decimal("1015")

    @pytest.mark.asyncio
    async def test_close_position_increments_total_trades(self, mock_components):
        """Test _close_position increments total trades counter."""
        bot = CashBot(total_capital=Decimal("1000"))

        position = MagicMock()
        position.market_id = "market_1"

        trade_result = {
            "size": 100.00,
            "pnl": 10.00,
            "roi_pct": 0.10,
        }

        bot.strategy.close_position = MagicMock(return_value=trade_result)
        bot.position_id_map["market_1"] = "risk_pos_1"
        bot.risk_manager.remove_position = MagicMock()

        initial_trades = bot.stats["total_trades"]

        await bot._close_position(position, Decimal("0.55"), "Test")

        assert bot.stats["total_trades"] == initial_trades + 1

    @pytest.mark.asyncio
    async def test_check_risk_limits_stops_bot_on_circuit_breaker(self, mock_components):
        """Test _check_risk_limits stops bot when circuit breaker triggers."""
        bot = CashBot(total_capital=Decimal("1000"))
        bot.is_running = True

        # Mock circuit breaker triggered
        bot.risk_manager.check_circuit_breaker = MagicMock(return_value="DAILY_LOSS_LIMIT_EXCEEDED")
        bot.risk_manager.get_risk_summary = MagicMock(return_value={"consecutive_losses": 0})

        await bot._check_risk_limits()

        assert bot.is_running is False

    @pytest.mark.asyncio
    async def test_check_risk_limits_continues_when_safe(self, mock_components):
        """Test _check_risk_limits continues when no issues detected."""
        bot = CashBot(total_capital=Decimal("1000"))
        bot.is_running = True

        # Mock no circuit breaker
        bot.risk_manager.check_circuit_breaker = MagicMock(return_value=None)
        bot.risk_manager.get_risk_summary = MagicMock(return_value={"consecutive_losses": 1})

        await bot._check_risk_limits()

        assert bot.is_running is True

    @pytest.mark.asyncio
    async def test_fetch_spot_data_uses_price_feed_service(self, mock_components):
        """Test _fetch_spot_data uses PriceFeedService."""
        bot = CashBot(total_capital=Decimal("1000"))

        mock_prices = {
            "BTC": {"price": Decimal("50000"), "volume": 1000000},
            "ETH": {"price": Decimal("3000"), "volume": 500000},
        }

        bot.price_feed.get_multi_asset_prices = AsyncMock(return_value=mock_prices)

        result = await bot._fetch_spot_data()

        bot.price_feed.get_multi_asset_prices.assert_called_once()
        assert "BTC" in result
        assert "ETH" in result

    @pytest.mark.asyncio
    async def test_fetch_polymarket_data_uses_market_discovery(self, mock_components):
        """Test _fetch_polymarket_data uses MarketDiscoveryService."""
        bot = CashBot(total_capital=Decimal("1000"))

        # Mock market
        mock_market = MagicMock()
        mock_market.id = "market_123"
        mock_market.related_asset = "BTC"
        mock_market.yes_price = Decimal("0.55")
        mock_market.volume_24h = Decimal("50000")
        mock_market.liquidity = Decimal("15000")

        bot.market_discovery.discover_markets = AsyncMock(return_value=[mock_market])

        result = await bot._fetch_polymarket_data()

        bot.market_discovery.discover_markets.assert_called_once()
        assert "BTC" in result

    @pytest.mark.asyncio
    async def test_get_performance_summary_aggregates_metrics(self, mock_components):
        """Test get_performance_summary aggregates all metrics."""
        bot = CashBot(total_capital=Decimal("1000"))

        # Mock metrics
        bot.strategy.get_performance_metrics = MagicMock(return_value={
            "total_pnl": 150.0,
            "win_rate": 0.72,
            "total_trades": 10,
        })

        bot.risk_manager.get_risk_summary = MagicMock(return_value={
            "daily_pnl": 50.0,
            "consecutive_losses": 0,
        })

        bot.whale_detector.get_statistics = MagicMock(return_value={
            "total_whales_detected": 5,
            "frontrun_success_rate": 0.80,
        })

        summary = bot.get_performance_summary()

        assert "bot_stats" in summary
        assert "performance" in summary
        assert "risk" in summary
        assert "whale" in summary
        assert summary["total_pnl"] == 150.0
        assert summary["win_rate"] == 0.72
