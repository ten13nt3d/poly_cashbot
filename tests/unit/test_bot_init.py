"""Unit tests for CashBot initialization."""

import pytest
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from src.bot.main import CashBot


class TestCashBotInitialization:
    """Test cases for bot initialization."""

    @pytest.fixture(autouse=True)
    def mock_components(self):
        """Mock all bot components to avoid real initialization."""
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

    def test_bot_initialization_default_capital(self, mock_components):
        """Test bot initialization with default capital."""
        bot = CashBot(total_capital=Decimal("1000"))

        assert bot.total_capital == Decimal("1000")
        assert bot.available_capital == Decimal("1000")
        assert bot.is_running is False
        assert bot.stats == {
            "start_time": None,
            "signals_generated": 0,
            "signals_executed": 0,
            "total_trades": 0,
        }

    def test_bot_initialization_small_capital(self, mock_components):
        """Test bot initialization with small capital ($10)."""
        bot = CashBot(total_capital=Decimal("10"))

        assert bot.total_capital == Decimal("10")
        assert bot.available_capital == Decimal("10")

    def test_bot_initialization_large_capital(self, mock_components):
        """Test bot initialization with large capital ($10,000)."""
        bot = CashBot(total_capital=Decimal("10000"))

        assert bot.total_capital == Decimal("10000")
        assert bot.available_capital == Decimal("10000")

    def test_bot_initialization_paper_trading_default(self, mock_components):
        """Test bot defaults to paper trading mode."""
        bot = CashBot(total_capital=Decimal("1000"))

        # Verify PolymarketClient was initialized with paper_trading=True
        mock_components["polymarket"].assert_called_once_with(paper_trading=True)

    def test_bot_initialization_live_trading(self, mock_components):
        """Test bot initialization with live trading mode."""
        bot = CashBot(total_capital=Decimal("1000"), paper_trading=False)

        # Verify PolymarketClient was initialized with paper_trading=False
        mock_components["polymarket"].assert_called_once_with(paper_trading=False)

    def test_arbitrage_detector_initialization(self, mock_components):
        """Test temporal arbitrage detector is initialized."""
        bot = CashBot(total_capital=Decimal("1000"))

        mock_components["arbitrage"].assert_called_once()
        assert bot.arbitrage_detector is not None

    def test_whale_detector_initialization(self, mock_components):
        """Test whale detector is initialized with correct filter."""
        bot = CashBot(total_capital=Decimal("1000"))

        mock_components["whale"].assert_called_once_with("XRP_markets")
        assert bot.whale_detector is not None

    def test_interval_strategy_initialization(self, mock_components):
        """Test interval strategy is initialized."""
        bot = CashBot(total_capital=Decimal("1000"))

        mock_components["strategy"].assert_called_once()
        assert bot.strategy is not None

    def test_risk_manager_initialization(self, mock_components):
        """Test risk manager is initialized with total capital."""
        capital = Decimal("5000")
        bot = CashBot(total_capital=capital)

        mock_components["risk"].assert_called_once_with(capital)
        assert bot.risk_manager is not None

    def test_database_manager_initialization(self, mock_components):
        """Test database manager is initialized."""
        bot = CashBot(total_capital=Decimal("1000"))

        mock_components["db"].assert_called_once()
        assert bot.db_manager is not None

    def test_price_feed_service_initialization(self, mock_components):
        """Test price feed service is initialized."""
        bot = CashBot(total_capital=Decimal("1000"))

        mock_components["price_feed"].assert_called_once()
        assert bot.price_feed is not None

    def test_market_discovery_initialization(self, mock_components):
        """Test market discovery service is initialized with polymarket client."""
        bot = CashBot(total_capital=Decimal("1000"))

        # Should be called with the polymarket client instance
        mock_components["discovery"].assert_called_once()
        assert bot.market_discovery is not None

    def test_position_id_map_initialized_empty(self, mock_components):
        """Test position ID mapping dictionary starts empty."""
        bot = CashBot(total_capital=Decimal("1000"))

        assert bot.position_id_map == {}
        assert isinstance(bot.position_id_map, dict)

    def test_all_components_initialized_together(self, mock_components):
        """Test all 8 components are initialized in one bot."""
        bot = CashBot(total_capital=Decimal("1000"))

        # Verify all components were initialized
        assert mock_components["arbitrage"].called
        assert mock_components["whale"].called
        assert mock_components["strategy"].called
        assert mock_components["risk"].called
        assert mock_components["db"].called
        assert mock_components["polymarket"].called
        assert mock_components["price_feed"].called
        assert mock_components["discovery"].called

    def test_initial_state_not_running(self, mock_components):
        """Test bot starts in not-running state."""
        bot = CashBot(total_capital=Decimal("1000"))

        assert bot.is_running is False

    def test_stats_initialized_to_zero(self, mock_components):
        """Test statistics are initialized to zero."""
        bot = CashBot(total_capital=Decimal("1000"))

        assert bot.stats["start_time"] is None
        assert bot.stats["signals_generated"] == 0
        assert bot.stats["signals_executed"] == 0
        assert bot.stats["total_trades"] == 0

    def test_available_capital_equals_total_initially(self, mock_components):
        """Test available capital equals total capital on initialization."""
        capital = Decimal("2500.50")
        bot = CashBot(total_capital=capital)

        assert bot.available_capital == bot.total_capital
        assert bot.available_capital == capital

    def test_initialization_with_decimal_string(self, mock_components):
        """Test initialization with Decimal from string."""
        bot = CashBot(total_capital=Decimal("1234.56"))

        assert bot.total_capital == Decimal("1234.56")
        assert bot.available_capital == Decimal("1234.56")

    def test_bot_attributes_exist(self, mock_components):
        """Test all expected attributes exist after initialization."""
        bot = CashBot(total_capital=Decimal("1000"))

        # Check all key attributes
        assert hasattr(bot, "total_capital")
        assert hasattr(bot, "available_capital")
        assert hasattr(bot, "is_running")
        assert hasattr(bot, "stats")
        assert hasattr(bot, "arbitrage_detector")
        assert hasattr(bot, "whale_detector")
        assert hasattr(bot, "strategy")
        assert hasattr(bot, "risk_manager")
        assert hasattr(bot, "db_manager")
        assert hasattr(bot, "polymarket")
        assert hasattr(bot, "price_feed")
        assert hasattr(bot, "market_discovery")
        assert hasattr(bot, "position_id_map")
