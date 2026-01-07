"""Unit tests for Market model."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from src.models.market import Market


class TestMarketModel:
    """Test cases for the Market model."""

    @pytest.fixture
    def sample_market_data(self):
        """Create sample market data."""
        return {
            "id": "market_123",
            "question": "Will BTC be above $50k on Dec 31?",
            "end_date": datetime.now() + timedelta(hours=12),
            "yes_price": Decimal("0.55"),
            "no_price": Decimal("0.45"),
            "volume_24h": Decimal("50000.00"),
            "liquidity": Decimal("25000.00"),
            "related_asset": "BTC",
        }

    @pytest.fixture
    def active_market(self, sample_market_data):
        """Create an active market."""
        return Market(**sample_market_data)

    @pytest.fixture
    def expired_market(self, sample_market_data):
        """Create an expired market."""
        data = sample_market_data.copy()
        data["end_date"] = datetime.now() - timedelta(hours=1)
        return Market(**data)

    def test_market_creation(self, sample_market_data):
        """Test creating a market with valid data."""
        market = Market(**sample_market_data)

        assert market.id == "market_123"
        assert market.question == "Will BTC be above $50k on Dec 31?"
        assert market.yes_price == Decimal("0.55")
        assert market.no_price == Decimal("0.45")
        assert market.related_asset == "BTC"

    def test_is_active_for_future_market(self):
        """Test is_active returns True for market ending in future."""
        market = Market(
            id="market_1",
            question="Test question?",
            end_date=datetime.now() + timedelta(days=1),
        )

        assert market.is_active() is True

    def test_is_active_for_expired_market(self):
        """Test is_active returns False for expired market."""
        market = Market(
            id="market_2",
            question="Test question?",
            end_date=datetime.now() - timedelta(days=1),
        )

        assert market.is_active() is False

    def test_is_active_for_market_ending_soon(self):
        """Test is_active for market ending very soon."""
        market = Market(
            id="market_3",
            question="Test question?",
            end_date=datetime.now() + timedelta(minutes=5),
        )

        assert market.is_active() is True

    def test_is_active_for_market_just_expired(self):
        """Test is_active for market that just expired."""
        market = Market(
            id="market_4",
            question="Test question?",
            end_date=datetime.now() - timedelta(seconds=1),
        )

        assert market.is_active() is False

    def test_mid_price_calculation(self):
        """Test mid price calculation with both prices."""
        market = Market(
            id="market_5",
            question="Test question?",
            end_date=datetime.now() + timedelta(days=1),
            yes_price=Decimal("0.60"),
            no_price=Decimal("0.40"),
        )

        mid = market.mid_price()
        assert mid == Decimal("0.50")  # (0.60 + 0.40) / 2

    def test_mid_price_with_equal_prices(self):
        """Test mid price when YES and NO prices are equal."""
        market = Market(
            id="market_6",
            question="Test question?",
            end_date=datetime.now() + timedelta(days=1),
            yes_price=Decimal("0.50"),
            no_price=Decimal("0.50"),
        )

        mid = market.mid_price()
        assert mid == Decimal("0.50")

    def test_mid_price_with_extreme_prices(self):
        """Test mid price with extreme values."""
        market = Market(
            id="market_7",
            question="Test question?",
            end_date=datetime.now() + timedelta(days=1),
            yes_price=Decimal("0.95"),
            no_price=Decimal("0.05"),
        )

        mid = market.mid_price()
        assert mid == Decimal("0.50")  # Still 0.50

    def test_mid_price_with_missing_yes_price(self):
        """Test mid price returns None when yes_price is missing."""
        market = Market(
            id="market_8",
            question="Test question?",
            end_date=datetime.now() + timedelta(days=1),
            yes_price=None,
            no_price=Decimal("0.40"),
        )

        mid = market.mid_price()
        assert mid is None

    def test_mid_price_with_missing_no_price(self):
        """Test mid price returns None when no_price is missing."""
        market = Market(
            id="market_9",
            question="Test question?",
            end_date=datetime.now() + timedelta(days=1),
            yes_price=Decimal("0.60"),
            no_price=None,
        )

        mid = market.mid_price()
        assert mid is None

    def test_mid_price_with_both_prices_none(self):
        """Test mid price returns None when both prices are missing."""
        market = Market(
            id="market_10",
            question="Test question?",
            end_date=datetime.now() + timedelta(days=1),
            yes_price=None,
            no_price=None,
        )

        mid = market.mid_price()
        assert mid is None

    def test_has_minimum_liquidity_above_threshold(self):
        """Test has_minimum_liquidity returns True when above threshold."""
        market = Market(
            id="market_11",
            question="Test question?",
            end_date=datetime.now() + timedelta(days=1),
            liquidity=Decimal("15000.00"),
        )

        assert market.has_minimum_liquidity(Decimal("10000")) is True

    def test_has_minimum_liquidity_at_threshold(self):
        """Test has_minimum_liquidity returns True when exactly at threshold."""
        market = Market(
            id="market_12",
            question="Test question?",
            end_date=datetime.now() + timedelta(days=1),
            liquidity=Decimal("10000.00"),
        )

        assert market.has_minimum_liquidity(Decimal("10000")) is True

    def test_has_minimum_liquidity_below_threshold(self):
        """Test has_minimum_liquidity returns False when below threshold."""
        market = Market(
            id="market_13",
            question="Test question?",
            end_date=datetime.now() + timedelta(days=1),
            liquidity=Decimal("5000.00"),
        )

        assert market.has_minimum_liquidity(Decimal("10000")) is False

    def test_has_minimum_liquidity_with_none(self):
        """Test has_minimum_liquidity returns False when liquidity is None."""
        market = Market(
            id="market_14",
            question="Test question?",
            end_date=datetime.now() + timedelta(days=1),
            liquidity=None,
        )

        assert market.has_minimum_liquidity(Decimal("10000")) is False

    def test_has_minimum_liquidity_default_threshold(self):
        """Test has_minimum_liquidity with default threshold."""
        market = Market(
            id="market_15",
            question="Test question?",
            end_date=datetime.now() + timedelta(days=1),
            liquidity=Decimal("20000.00"),
        )

        # Default threshold is 10000
        assert market.has_minimum_liquidity() is True

    def test_has_minimum_liquidity_zero_threshold(self):
        """Test has_minimum_liquidity with zero threshold."""
        market = Market(
            id="market_16",
            question="Test question?",
            end_date=datetime.now() + timedelta(days=1),
            liquidity=Decimal("100.00"),
        )

        assert market.has_minimum_liquidity(Decimal("0")) is True

    def test_market_with_high_volume(self):
        """Test market with high 24h volume."""
        market = Market(
            id="market_17",
            question="Test question?",
            end_date=datetime.now() + timedelta(days=1),
            volume_24h=Decimal("1000000.00"),
        )

        assert market.volume_24h == Decimal("1000000.00")

    def test_market_with_no_volume(self):
        """Test market with no volume data."""
        market = Market(
            id="market_18",
            question="Test question?",
            end_date=datetime.now() + timedelta(days=1),
            volume_24h=None,
        )

        assert market.volume_24h is None

    def test_market_with_multiple_assets(self):
        """Test markets for different assets."""
        btc_market = Market(
            id="market_btc",
            question="BTC question?",
            end_date=datetime.now() + timedelta(days=1),
            related_asset="BTC",
        )

        eth_market = Market(
            id="market_eth",
            question="ETH question?",
            end_date=datetime.now() + timedelta(days=1),
            related_asset="ETH",
        )

        assert btc_market.related_asset == "BTC"
        assert eth_market.related_asset == "ETH"

    def test_market_without_related_asset(self):
        """Test market without related asset."""
        market = Market(
            id="market_19",
            question="General question?",
            end_date=datetime.now() + timedelta(days=1),
            related_asset=None,
        )

        assert market.related_asset is None

    def test_market_price_precision(self):
        """Test market prices maintain decimal precision."""
        market = Market(
            id="market_20",
            question="Test question?",
            end_date=datetime.now() + timedelta(days=1),
            yes_price=Decimal("0.55555555"),
            no_price=Decimal("0.44444444"),
        )

        assert market.yes_price == Decimal("0.55555555")
        assert market.no_price == Decimal("0.44444444")

    def test_market_liquidity_precision(self):
        """Test market liquidity maintains decimal precision."""
        market = Market(
            id="market_21",
            question="Test question?",
            end_date=datetime.now() + timedelta(days=1),
            liquidity=Decimal("12345.67"),
        )

        assert market.liquidity == Decimal("12345.67")

    def test_market_with_long_question(self):
        """Test market with very long question."""
        long_question = "Will " + ("BTC " * 50) + "be above $100k?"
        market = Market(
            id="market_22",
            question=long_question,
            end_date=datetime.now() + timedelta(days=1),
        )

        assert market.question == long_question
        assert len(market.question) > 100
