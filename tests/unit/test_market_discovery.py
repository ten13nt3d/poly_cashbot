"""
Comprehensive tests for Market Discovery service.

Tests cover:
- Asset detection from market questions
- Time window validation
- Priority sorting (XRP > BTC > ETH)
- Market filtering (asset, liquidity, time)
- Database persistence (upsert pattern)
- Full discovery flow
"""

import pytest
import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

from src.services.market_discovery import MarketDiscoveryService
from src.models import Market


# Disable logging during tests
@pytest.fixture(autouse=True)
def disable_logging():
    """Disable logging during tests."""
    logging.disable(logging.CRITICAL)
    yield
    logging.disable(logging.NOTSET)


# ============================================================================
# FIXTURES - Mocks
# ============================================================================

@pytest.fixture
def mock_polymarket():
    """Mock Polymarket client."""
    client = AsyncMock()
    client.get_markets = AsyncMock(return_value=[])
    client.get_order_book = AsyncMock(return_value={})
    return client


@pytest.fixture
def mock_price_feed():
    """Mock Price Feed service."""
    service = AsyncMock()
    service.get_price = AsyncMock(return_value=Decimal("2.45"))
    return service


@pytest.fixture
def mock_db_manager():
    """Mock Database Manager."""
    db = AsyncMock()
    mock_session = AsyncMock()
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    db.session = MagicMock(return_value=mock_session)
    return db


@pytest.fixture
def discovery_service(mock_polymarket, mock_price_feed, mock_db_manager):
    """Create MarketDiscoveryService instance with mocks."""
    return MarketDiscoveryService(mock_polymarket, mock_price_feed, mock_db_manager)


# ============================================================================
# FIXTURES - Sample Data
# ============================================================================

@pytest.fixture
def sample_xrp_market():
    """Sample XRP market."""
    now = datetime.now(timezone.utc)
    return {
        "id": "xrp_market_1",
        "question": "Will XRP reach $2.50 by EOD?",
        "end_date": (now + timedelta(hours=2)).isoformat(),
        "yes_price": 0.55,
        "no_price": 0.45,
        "volume_24h": 50000,
        "liquidity": 15000,
    }


@pytest.fixture
def sample_btc_market():
    """Sample BTC market."""
    now = datetime.now(timezone.utc)
    return {
        "id": "btc_market_1",
        "question": "Will Bitcoin stay above $45k?",
        "end_date": (now + timedelta(hours=3)).isoformat(),
        "yes_price": 0.72,
        "no_price": 0.28,
        "volume_24h": 120000,
        "liquidity": 35000,
    }


@pytest.fixture
def sample_eth_market():
    """Sample ETH market."""
    now = datetime.now(timezone.utc)
    return {
        "id": "eth_market_1",
        "question": "Will Ethereum reach $3500?",
        "end_date": (now + timedelta(hours=4)).isoformat(),
        "yes_price": 0.60,
        "no_price": 0.40,
        "volume_24h": 80000,
        "liquidity": 25000,
    }


# ============================================================================
# TEST CLASS - Asset Detection
# ============================================================================

class TestAssetDetection:
    """Test crypto asset detection from market questions."""

    def test_detect_xrp(self, discovery_service):
        """Test XRP detection from question."""
        market = {"question": "Will XRP reach $2.50?"}
        asset = discovery_service._detect_asset(market)
        assert asset == "XRP"

    def test_detect_xrp_lowercase(self, discovery_service):
        """Test XRP detection is case-insensitive."""
        market = {"question": "Will xrp moon?"}
        asset = discovery_service._detect_asset(market)
        assert asset == "XRP"

    def test_detect_ripple(self, discovery_service):
        """Test Ripple keyword detection."""
        market = {"question": "Will Ripple win the lawsuit?"}
        asset = discovery_service._detect_asset(market)
        assert asset == "XRP"

    def test_detect_btc(self, discovery_service):
        """Test BTC detection from question."""
        market = {"question": "Will BTC hit $50k?"}
        asset = discovery_service._detect_asset(market)
        assert asset == "BTC"

    def test_detect_bitcoin(self, discovery_service):
        """Test Bitcoin keyword detection."""
        market = {"question": "Will Bitcoin reach new ATH?"}
        asset = discovery_service._detect_asset(market)
        assert asset == "BTC"

    def test_detect_eth(self, discovery_service):
        """Test ETH detection from question."""
        market = {"question": "Will ETH stay above $3k?"}
        asset = discovery_service._detect_asset(market)
        assert asset == "ETH"

    def test_detect_ethereum(self, discovery_service):
        """Test Ethereum keyword detection."""
        market = {"question": "Will Ethereum reach $4000?"}
        asset = discovery_service._detect_asset(market)
        assert asset == "ETH"

    def test_detect_no_asset(self, discovery_service):
        """Test no asset detected for unrelated markets."""
        market = {"question": "Will Trump win election?"}
        asset = discovery_service._detect_asset(market)
        assert asset is None

    def test_detect_priority_xrp_over_btc(self, discovery_service):
        """Test XRP has priority when multiple assets mentioned."""
        market = {"question": "Will XRP outperform BTC this month?"}
        asset = discovery_service._detect_asset(market)
        # XRP should be detected first due to priority order
        assert asset == "XRP"

    def test_detect_priority_btc_over_eth(self, discovery_service):
        """Test BTC has priority over ETH when both mentioned."""
        market = {"question": "Will BTC or ETH reach ATH first?"}
        asset = discovery_service._detect_asset(market)
        # BTC should be detected first due to priority order
        assert asset == "BTC"


# ============================================================================
# TEST CLASS - Time Validation
# ============================================================================

class TestTimeValidation:
    """Test market expiration time validation."""

    def test_time_valid_2_hours(self, discovery_service):
        """Test valid market with 2 hours until expiry."""
        now = datetime.now(timezone.utc)
        market = {"end_date": (now + timedelta(hours=2)).isoformat()}

        assert discovery_service._is_time_valid(market) is True

    def test_time_valid_30_minutes(self, discovery_service):
        """Test valid market with 30 minutes until expiry."""
        now = datetime.now(timezone.utc)
        market = {"end_date": (now + timedelta(minutes=30)).isoformat()}

        assert discovery_service._is_time_valid(market) is True

    def test_time_valid_20_hours(self, discovery_service):
        """Test valid market with 20 hours until expiry."""
        now = datetime.now(timezone.utc)
        market = {"end_date": (now + timedelta(hours=20)).isoformat()}

        assert discovery_service._is_time_valid(market) is True

    def test_time_too_soon_10_minutes(self, discovery_service):
        """Test invalid market with only 10 minutes until expiry."""
        now = datetime.now(timezone.utc)
        market = {"end_date": (now + timedelta(minutes=10)).isoformat()}

        assert discovery_service._is_time_valid(market) is False

    def test_time_too_far_30_hours(self, discovery_service):
        """Test invalid market with 30 hours until expiry."""
        now = datetime.now(timezone.utc)
        market = {"end_date": (now + timedelta(hours=30)).isoformat()}

        assert discovery_service._is_time_valid(market) is False

    def test_time_expired(self, discovery_service):
        """Test invalid expired market."""
        now = datetime.now(timezone.utc)
        market = {"end_date": (now - timedelta(hours=1)).isoformat()}

        assert discovery_service._is_time_valid(market) is False

    def test_time_missing_end_date(self, discovery_service):
        """Test invalid market with missing end_date."""
        market = {"question": "Test market"}

        assert discovery_service._is_time_valid(market) is False

    def test_time_invalid_format(self, discovery_service):
        """Test invalid market with malformed date."""
        market = {"end_date": "invalid-date-format"}

        assert discovery_service._is_time_valid(market) is False


# ============================================================================
# TEST CLASS - Priority Sorting
# ============================================================================

class TestPrioritySorting:
    """Test market priority sorting by asset."""

    def test_sort_xrp_first(self, discovery_service):
        """Test XRP markets sorted to front."""
        markets = [
            {"related_asset": "ETH"},
            {"related_asset": "XRP"},
            {"related_asset": "BTC"},
        ]

        sorted_markets = discovery_service._sort_by_priority(markets)

        assert sorted_markets[0]["related_asset"] == "XRP"
        assert sorted_markets[1]["related_asset"] == "BTC"
        assert sorted_markets[2]["related_asset"] == "ETH"

    def test_sort_btc_over_eth(self, discovery_service):
        """Test BTC sorted before ETH."""
        markets = [
            {"related_asset": "ETH"},
            {"related_asset": "BTC"},
        ]

        sorted_markets = discovery_service._sort_by_priority(markets)

        assert sorted_markets[0]["related_asset"] == "BTC"
        assert sorted_markets[1]["related_asset"] == "ETH"

    def test_sort_none_asset_last(self, discovery_service):
        """Test markets without asset sorted to end."""
        markets = [
            {"related_asset": None},
            {"related_asset": "XRP"},
        ]

        sorted_markets = discovery_service._sort_by_priority(markets)

        assert sorted_markets[0]["related_asset"] == "XRP"
        assert sorted_markets[1]["related_asset"] is None

    def test_sort_multiple_same_asset(self, discovery_service):
        """Test multiple markets with same asset maintain order."""
        markets = [
            {"id": "xrp1", "related_asset": "XRP"},
            {"id": "xrp2", "related_asset": "XRP"},
        ]

        sorted_markets = discovery_service._sort_by_priority(markets)

        assert len(sorted_markets) == 2
        assert all(m["related_asset"] == "XRP" for m in sorted_markets)


# ============================================================================
# TEST CLASS - Market Filtering
# ============================================================================

class TestMarketFiltering:
    """Test comprehensive market filtering."""

    def test_filter_by_asset_valid(self, discovery_service, sample_xrp_market):
        """Test markets with valid asset pass filter."""
        with patch("src.services.market_discovery.settings") as mock_settings:
            mock_settings.min_market_liquidity = Decimal("10000")

            filtered = discovery_service._filter_markets([sample_xrp_market])

            assert len(filtered) == 1
            assert filtered[0]["related_asset"] == "XRP"

    def test_filter_by_asset_invalid(self, discovery_service):
        """Test markets without crypto asset filtered out."""
        now = datetime.now(timezone.utc)
        market = {
            "id": "politics_1",
            "question": "Will Trump win?",
            "end_date": (now + timedelta(hours=2)).isoformat(),
            "liquidity": 50000,
        }

        with patch("src.services.market_discovery.settings") as mock_settings:
            mock_settings.min_market_liquidity = Decimal("10000")

            filtered = discovery_service._filter_markets([market])

            assert len(filtered) == 0

    def test_filter_by_liquidity_pass(self, discovery_service, sample_xrp_market):
        """Test market with sufficient liquidity passes."""
        with patch("src.services.market_discovery.settings") as mock_settings:
            mock_settings.min_market_liquidity = Decimal("10000")

            filtered = discovery_service._filter_markets([sample_xrp_market])

            assert len(filtered) == 1

    def test_filter_by_liquidity_fail(self, discovery_service):
        """Test market with insufficient liquidity filtered out."""
        now = datetime.now(timezone.utc)
        market = {
            "id": "low_liq",
            "question": "Will XRP moon?",
            "end_date": (now + timedelta(hours=2)).isoformat(),
            "liquidity": 5000,  # Below threshold
        }

        with patch("src.services.market_discovery.settings") as mock_settings:
            mock_settings.min_market_liquidity = Decimal("10000")

            filtered = discovery_service._filter_markets([market])

            assert len(filtered) == 0

    def test_filter_by_time_window(self, discovery_service):
        """Test time window filtering."""
        now = datetime.now(timezone.utc)

        markets = [
            {
                "id": "valid",
                "question": "Will XRP reach $3?",
                "end_date": (now + timedelta(hours=2)).isoformat(),
                "liquidity": 15000,
            },
            {
                "id": "too_soon",
                "question": "Will XRP reach $3?",
                "end_date": (now + timedelta(minutes=10)).isoformat(),
                "liquidity": 15000,
            },
            {
                "id": "too_far",
                "question": "Will XRP reach $3?",
                "end_date": (now + timedelta(hours=30)).isoformat(),
                "liquidity": 15000,
            },
        ]

        with patch("src.services.market_discovery.settings") as mock_settings:
            mock_settings.min_market_liquidity = Decimal("10000")

            filtered = discovery_service._filter_markets(markets)

            # Only the valid one should pass
            assert len(filtered) == 1
            assert filtered[0]["id"] == "valid"

    def test_filter_sorts_by_priority(self, discovery_service, sample_xrp_market, sample_btc_market, sample_eth_market):
        """Test filtered markets sorted by asset priority."""
        with patch("src.services.market_discovery.settings") as mock_settings:
            mock_settings.min_market_liquidity = Decimal("10000")

            # Pass in reverse priority order
            markets = [sample_eth_market, sample_btc_market, sample_xrp_market]
            filtered = discovery_service._filter_markets(markets)

            # Should be sorted: XRP, BTC, ETH
            assert len(filtered) == 3
            assert filtered[0]["id"] == "xrp_market_1"
            assert filtered[1]["id"] == "btc_market_1"
            assert filtered[2]["id"] == "eth_market_1"


# ============================================================================
# TEST CLASS - Database Operations
# ============================================================================

class TestDatabaseOperations:
    """Test database persistence operations."""

    @pytest.mark.asyncio
    async def test_save_markets_success(self, discovery_service, sample_xrp_market):
        """Test markets saved to database successfully."""
        # Add related_asset to market
        sample_xrp_market["related_asset"] = "XRP"

        # Mock database session
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()

        # Mock Market retrieval
        mock_result = MagicMock()
        mock_market = Market(
            id="xrp_market_1",
            question=sample_xrp_market["question"],
            end_date=datetime.now(timezone.utc) + timedelta(hours=2),
            yes_price=Decimal("0.55"),
            no_price=Decimal("0.45"),
            volume_24h=Decimal("50000"),
            liquidity=Decimal("15000"),
            related_asset="XRP",
        )
        mock_result.scalar_one_or_none.return_value = mock_market

        mock_session.execute.return_value = mock_result

        discovery_service.db.session.return_value.__aenter__.return_value = mock_session

        saved = await discovery_service._save_markets([sample_xrp_market])

        assert len(saved) == 1
        assert saved[0].id == "xrp_market_1"
        mock_session.commit.assert_called_once()


# ============================================================================
# TEST CLASS - Discovery Flow
# ============================================================================

class TestDiscoveryFlow:
    """Test full market discovery flow."""

    @pytest.mark.asyncio
    async def test_discover_markets_full_flow(self, discovery_service, sample_xrp_market, sample_btc_market):
        """Test complete discovery flow with filtering and saving."""
        # Configure mock API response
        discovery_service.polymarket.get_markets.return_value = [
            sample_xrp_market,
            sample_btc_market,
        ]

        # Mock settings
        with patch("src.services.market_discovery.settings") as mock_settings:
            mock_settings.min_market_liquidity = Decimal("10000")

            # Mock database operations
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_session.commit = AsyncMock()

            # Create Market instances for return
            xrp_market = Market(
                id="xrp_market_1",
                question=sample_xrp_market["question"],
                end_date=datetime.now(timezone.utc) + timedelta(hours=2),
                yes_price=Decimal("0.55"),
                no_price=Decimal("0.45"),
                volume_24h=Decimal("50000"),
                liquidity=Decimal("15000"),
                related_asset="XRP",
            )

            btc_market = Market(
                id="btc_market_1",
                question=sample_btc_market["question"],
                end_date=datetime.now(timezone.utc) + timedelta(hours=3),
                yes_price=Decimal("0.72"),
                no_price=Decimal("0.28"),
                volume_24h=Decimal("120000"),
                liquidity=Decimal("35000"),
                related_asset="BTC",
            )

            # Mock execute to return markets
            call_count = 0

            def mock_execute(*args, **kwargs):
                nonlocal call_count
                call_count += 1
                mock_result = MagicMock()
                if call_count == 1 or call_count == 2:
                    # First two calls are upserts (no return)
                    mock_result.scalar_one_or_none.return_value = None
                elif call_count == 3:
                    mock_result.scalar_one_or_none.return_value = xrp_market
                elif call_count == 4:
                    mock_result.scalar_one_or_none.return_value = btc_market
                return mock_result

            mock_session.execute.side_effect = mock_execute

            discovery_service.db.session.return_value.__aenter__.return_value = mock_session

            markets = await discovery_service.discover_markets()

            # Should return 2 filtered markets
            assert len(markets) == 2
            # XRP should be first (priority)
            assert markets[0].related_asset == "XRP"
            assert markets[1].related_asset == "BTC"

    @pytest.mark.asyncio
    async def test_discover_markets_no_results(self, discovery_service):
        """Test discovery with no markets passing filters."""
        # Return markets that will be filtered out
        now = datetime.now(timezone.utc)
        bad_market = {
            "id": "bad",
            "question": "Will Trump win?",  # No crypto asset
            "end_date": (now + timedelta(hours=2)).isoformat(),
            "liquidity": 50000,
        }

        discovery_service.polymarket.get_markets.return_value = [bad_market]

        with patch("src.services.market_discovery.settings") as mock_settings:
            mock_settings.min_market_liquidity = Decimal("10000")

            # Mock empty database save
            mock_session = AsyncMock()
            mock_session.commit = AsyncMock()
            discovery_service.db.session.return_value.__aenter__.return_value = mock_session

            markets = await discovery_service.discover_markets()

            assert len(markets) == 0
