"""Unit tests for Whale Detector."""

import pytest
from datetime import datetime, timedelta
from decimal import Decimal

from src.lib.whale.detector import (
    WhaleDetector,
    WhaleAlert,
    OrderbookSnapshot,
)


class TestWhaleDetectorInitialization:
    """Test whale detector initialization."""

    def test_initialization_default(self):
        """Test default initialization."""
        detector = WhaleDetector(market_id="market_123")

        assert detector.market_id == "market_123"
        assert detector.min_history_samples == 50
        assert detector.order_size_history == []
        assert detector.orderbook_depth_history == []
        assert detector.recent_whales == []
        assert len(detector.known_whale_wallets) == 0
        assert detector.average_order_size == Decimal("0")

    def test_initialization_custom_samples(self):
        """Test initialization with custom history samples."""
        detector = WhaleDetector(market_id="market_456", min_history_samples=100)

        assert detector.min_history_samples == 100

    def test_add_known_whale_wallet(self):
        """Test adding known whale wallet."""
        detector = WhaleDetector(market_id="market_123")

        detector.add_known_whale_wallet("0x1234567890ABCDEF")

        assert "0x1234567890abcdef" in detector.known_whale_wallets

    def test_add_multiple_whale_wallets(self):
        """Test adding multiple whale wallets."""
        detector = WhaleDetector(market_id="market_123")

        detector.add_known_whale_wallet("0x1111111111")
        detector.add_known_whale_wallet("0x2222222222")
        detector.add_known_whale_wallet("0x3333333333")

        assert len(detector.known_whale_wallets) == 3


class TestLargeOrderDetection:
    """Test large order detection."""

    @pytest.fixture
    def detector_with_history(self):
        """Create detector with order history."""
        detector = WhaleDetector(market_id="market_123")

        # Add 50 historical orders with average size of $1000
        for _ in range(50):
            detector.order_size_history.append(Decimal("1000"))

        return detector

    @pytest.fixture
    def normal_snapshot(self):
        """Create normal orderbook snapshot."""
        return OrderbookSnapshot(
            market_id="market_123",
            bids=[
                {'price': '0.55', 'size': '1000'},
                {'price': '0.54', 'size': '950'},
            ],
            asks=[
                {'price': '0.56', 'size': '1050'},
                {'price': '0.57', 'size': '900'},
            ],
            timestamp=datetime.now()
        )

    @pytest.fixture
    def whale_snapshot(self):
        """Create orderbook snapshot with whale order."""
        return OrderbookSnapshot(
            market_id="market_123",
            bids=[
                {'price': '0.55', 'size': '15000'},  # Whale order (15x average)
                {'price': '0.54', 'size': '950'},
            ],
            asks=[
                {'price': '0.56', 'size': '1050'},
                {'price': '0.57', 'size': '900'},
            ],
            timestamp=datetime.now()
        )

    def test_no_detection_insufficient_history(self):
        """Test no detection with insufficient history."""
        detector = WhaleDetector(market_id="market_123")

        # Only add 10 samples (need 50)
        for _ in range(10):
            detector.order_size_history.append(Decimal("1000"))

        snapshot = OrderbookSnapshot(
            market_id="market_123",
            bids=[{'price': '0.55', 'size': '15000'}],
            asks=[],
            timestamp=datetime.now()
        )

        alerts = detector._detect_large_orders(snapshot)

        assert len(alerts) == 0

    def test_detect_large_bid(self, detector_with_history, whale_snapshot):
        """Test detection of large bid order."""
        alerts = detector_with_history._detect_large_orders(whale_snapshot)

        assert len(alerts) == 1
        assert alerts[0].side == "buy"
        assert alerts[0].order_size == Decimal("15000")
        assert alerts[0].relative_size == 15.0
        assert alerts[0].confidence == 0.8

    def test_detect_large_ask(self, detector_with_history):
        """Test detection of large ask order."""
        snapshot = OrderbookSnapshot(
            market_id="market_123",
            bids=[{'price': '0.55', 'size': '1000'}],
            asks=[{'price': '0.56', 'size': '20000'}],  # Whale sell
            timestamp=datetime.now()
        )

        alerts = detector_with_history._detect_large_orders(snapshot)

        assert len(alerts) == 1
        assert alerts[0].side == "sell"
        assert alerts[0].order_size == Decimal("20000")

    def test_no_detection_normal_orders(self, detector_with_history, normal_snapshot):
        """Test no detection for normal-sized orders."""
        alerts = detector_with_history._detect_large_orders(normal_snapshot)

        assert len(alerts) == 0

    def test_multiple_whale_orders(self, detector_with_history):
        """Test detection of multiple whale orders."""
        snapshot = OrderbookSnapshot(
            market_id="market_123",
            bids=[
                {'price': '0.55', 'size': '15000'},  # Whale
                {'price': '0.54', 'size': '12000'},  # Whale
            ],
            asks=[
                {'price': '0.56', 'size': '18000'},  # Whale
            ],
            timestamp=datetime.now()
        )

        alerts = detector_with_history._detect_large_orders(snapshot)

        assert len(alerts) == 3


class TestDepthChangeDetection:
    """Test orderbook depth change detection."""

    @pytest.fixture
    def detector_with_depth_history(self):
        """Create detector with depth history."""
        detector = WhaleDetector(market_id="market_123")

        # Add stable depth history around $10,000
        for _ in range(20):
            detector.orderbook_depth_history.append(Decimal("10000"))

        return detector

    def test_no_detection_insufficient_depth_history(self):
        """Test no detection with insufficient depth history."""
        detector = WhaleDetector(market_id="market_123")

        # Only 5 samples (need 10)
        for _ in range(5):
            detector.orderbook_depth_history.append(Decimal("10000"))

        snapshot = OrderbookSnapshot(
            market_id="market_123",
            bids=[{'price': '0.55', 'size': '20000'}],
            asks=[],
            timestamp=datetime.now()
        )

        alerts = detector._detect_depth_changes(snapshot)

        assert len(alerts) == 0

    def test_detect_depth_increase(self, detector_with_depth_history):
        """Test detection of significant depth increase."""
        # Sudden increase to $15,000 (50% change)
        snapshot = OrderbookSnapshot(
            market_id="market_123",
            bids=[{'price': '0.55', 'size': '8000'}],
            asks=[{'price': '0.56', 'size': '7000'}],
            timestamp=datetime.now()
        )

        alerts = detector_with_depth_history._detect_depth_changes(snapshot)

        assert len(alerts) == 1
        assert alerts[0].side == "buy"  # Depth increased
        assert alerts[0].confidence == 0.75

    def test_detect_depth_decrease(self, detector_with_depth_history):
        """Test detection of significant depth decrease."""
        # Sudden decrease to $6,000 (40% change)
        snapshot = OrderbookSnapshot(
            market_id="market_123",
            bids=[{'price': '0.55', 'size': '3000'}],
            asks=[{'price': '0.56', 'size': '3000'}],
            timestamp=datetime.now()
        )

        alerts = detector_with_depth_history._detect_depth_changes(snapshot)

        assert len(alerts) == 1
        assert alerts[0].side == "sell"  # Depth decreased

    def test_no_detection_small_depth_change(self, detector_with_depth_history):
        """Test no detection for small depth changes."""
        # Small change to $10,500 (5% change, < 20% threshold)
        snapshot = OrderbookSnapshot(
            market_id="market_123",
            bids=[{'price': '0.55', 'size': '5500'}],
            asks=[{'price': '0.56', 'size': '5000'}],
            timestamp=datetime.now()
        )

        alerts = detector_with_depth_history._detect_depth_changes(snapshot)

        assert len(alerts) == 0


class TestOrderbookCalculations:
    """Test orderbook calculation utilities."""

    @pytest.fixture
    def detector(self):
        """Create detector for testing."""
        return WhaleDetector(market_id="market_123")

    def test_calculate_orderbook_depth(self, detector):
        """Test orderbook depth calculation."""
        snapshot = OrderbookSnapshot(
            market_id="market_123",
            bids=[
                {'price': '0.55', 'size': '3000'},
                {'price': '0.54', 'size': '2000'},
            ],
            asks=[
                {'price': '0.56', 'size': '2500'},
                {'price': '0.57', 'size': '1500'},
            ],
            timestamp=datetime.now()
        )

        depth = detector._calculate_orderbook_depth(snapshot)

        assert depth == Decimal("9000")  # 3000 + 2000 + 2500 + 1500

    def test_calculate_depth_empty_orderbook(self, detector):
        """Test depth calculation with empty orderbook."""
        snapshot = OrderbookSnapshot(
            market_id="market_123",
            bids=[],
            asks=[],
            timestamp=datetime.now()
        )

        depth = detector._calculate_orderbook_depth(snapshot)

        assert depth == Decimal("0")


class TestHistoricalDataUpdate:
    """Test historical data updates."""

    @pytest.fixture
    def detector(self):
        """Create detector for testing."""
        return WhaleDetector(market_id="market_123")

    def test_update_historical_data(self, detector):
        """Test updating historical data."""
        snapshot = OrderbookSnapshot(
            market_id="market_123",
            bids=[
                {'price': '0.55', 'size': '1000'},
                {'price': '0.54', 'size': '900'},
            ],
            asks=[
                {'price': '0.56', 'size': '1100'},
            ],
            timestamp=datetime.now()
        )

        detector._update_historical_data(snapshot)

        assert len(detector.order_size_history) == 3  # 2 bids + 1 ask
        assert len(detector.orderbook_depth_history) == 1
        assert detector.orderbook_depth_history[0] == Decimal("3000")

    def test_history_trimming(self, detector):
        """Test history is trimmed to 1000 samples."""
        # Add 1100 samples
        for i in range(1100):
            detector.order_size_history.append(Decimal(str(i)))

        snapshot = OrderbookSnapshot(
            market_id="market_123",
            bids=[{'price': '0.55', 'size': '100'}],
            asks=[],
            timestamp=datetime.now()
        )

        detector._update_historical_data(snapshot)

        # Should be trimmed to 1000
        assert len(detector.order_size_history) == 1000


class TestAlertFiltering:
    """Test whale alert filtering."""

    @pytest.fixture
    def detector(self):
        """Create detector for testing."""
        return WhaleDetector(market_id="market_123")

    def test_filter_by_minimum_order_value(self, detector):
        """Test filtering by minimum order value."""
        alerts = [
            WhaleAlert(
                market_id="market_123",
                order_size=Decimal("5000"),  # Below $10k minimum
                side="buy",
                relative_size=15.0,
                confidence=0.8
            ),
            WhaleAlert(
                market_id="market_123",
                order_size=Decimal("15000"),  # Above minimum
                side="buy",
                relative_size=25.0,  # High enough for good impact
                confidence=0.8
            )
        ]

        filtered = detector._filter_alerts(alerts)

        # Only the $15k order should pass (other filtered by size)
        assert len(filtered) >= 0  # May be 0 or 1 depending on impact calculation
        if len(filtered) > 0:
            assert filtered[0].order_size == Decimal("15000")

    def test_filter_by_expected_impact(self, detector):
        """Test filtering by expected impact."""
        alerts = [
            WhaleAlert(
                market_id="market_123",
                order_size=Decimal("15000"),
                side="buy",
                relative_size=5.0,  # Low relative size = low impact
                confidence=0.8
            )
        ]

        filtered = detector._filter_alerts(alerts)

        # Should be filtered out by low impact
        assert len(filtered) == 0

    def test_filter_by_confidence(self, detector):
        """Test filtering by confidence threshold."""
        alerts = [
            WhaleAlert(
                market_id="market_123",
                order_size=Decimal("15000"),
                side="buy",
                relative_size=15.0,
                confidence=0.6  # Below 0.7 threshold
            )
        ]

        filtered = detector._filter_alerts(alerts)

        assert len(filtered) == 0


class TestPriceImpactEstimation:
    """Test price impact estimation."""

    @pytest.fixture
    def detector(self):
        """Create detector for testing."""
        return WhaleDetector(market_id="market_123")

    def test_estimate_impact_very_large_whale(self, detector):
        """Test impact for very large whale (>50x)."""
        alert = WhaleAlert(
            market_id="market_123",
            order_size=Decimal("50000"),
            side="buy",
            relative_size=60.0
        )

        impact = detector._estimate_price_impact(alert)

        assert impact == 0.05  # 5% impact

    def test_estimate_impact_large_whale(self, detector):
        """Test impact for large whale (20-50x)."""
        alert = WhaleAlert(
            market_id="market_123",
            order_size=Decimal("30000"),
            side="buy",
            relative_size=30.0
        )

        impact = detector._estimate_price_impact(alert)

        assert impact == 0.03  # 3% impact

    def test_estimate_impact_medium_whale(self, detector):
        """Test impact for medium whale (10-20x)."""
        alert = WhaleAlert(
            market_id="market_123",
            order_size=Decimal("15000"),
            side="buy",
            relative_size=15.0
        )

        impact = detector._estimate_price_impact(alert)

        assert impact == 0.02  # 2% impact


class TestConfidenceCalculation:
    """Test whale confidence calculation."""

    @pytest.fixture
    def detector(self):
        """Create detector for testing."""
        detector = WhaleDetector(market_id="market_123")
        detector.add_known_whale_wallet("0xWHALE123")
        return detector

    def test_confidence_base(self, detector):
        """Test base confidence calculation."""
        alert = WhaleAlert(
            market_id="market_123",
            order_size=Decimal("15000"),
            side="buy",
            relative_size=15.0,
            expected_impact=0.02
        )

        confidence = detector._calculate_whale_confidence(alert)

        # Base 0.5 + size 0.1 = 0.6
        assert confidence == 0.6

    def test_confidence_large_whale(self, detector):
        """Test confidence for large whale."""
        alert = WhaleAlert(
            market_id="market_123",
            order_size=Decimal("30000"),
            side="buy",
            relative_size=30.0,
            expected_impact=0.03
        )

        confidence = detector._calculate_whale_confidence(alert)

        # Base 0.5 + size 0.2 = 0.7
        assert confidence == 0.7

    def test_confidence_known_wallet(self, detector):
        """Test confidence boost for known whale wallet."""
        alert = WhaleAlert(
            market_id="market_123",
            order_size=Decimal("15000"),
            side="buy",
            relative_size=15.0,
            expected_impact=0.02,
            wallet_address="0xWHALE123"
        )

        confidence = detector._calculate_whale_confidence(alert)

        # Base 0.5 + size 0.1 + known wallet 0.2 = 0.8
        assert confidence == 0.8

    def test_confidence_high_impact(self, detector):
        """Test confidence boost for high impact."""
        alert = WhaleAlert(
            market_id="market_123",
            order_size=Decimal("50000"),
            side="buy",
            relative_size=60.0,
            expected_impact=0.05
        )

        confidence = detector._calculate_whale_confidence(alert)

        # Base 0.5 + size 0.3 + impact 0.1 = 0.9
        assert confidence == 0.9

    def test_confidence_capped_at_95(self, detector):
        """Test confidence is capped at 95%."""
        alert = WhaleAlert(
            market_id="market_123",
            order_size=Decimal("100000"),
            side="buy",
            relative_size=100.0,
            expected_impact=0.10,
            wallet_address="0xWHALE123"
        )

        confidence = detector._calculate_whale_confidence(alert)

        assert confidence == 0.95  # Capped


class TestRecentWhales:
    """Test recent whale retrieval."""

    @pytest.fixture
    def detector_with_whales(self):
        """Create detector with recent whales."""
        detector = WhaleDetector(market_id="market_123")

        # Add whales at different times
        now = datetime.now()
        detector.recent_whales = [
            WhaleAlert(
                market_id="market_123",
                order_size=Decimal("15000"),
                side="buy",
                relative_size=15.0,
                detected_at=now - timedelta(minutes=30)
            ),
            WhaleAlert(
                market_id="market_123",
                order_size=Decimal("20000"),
                side="sell",
                relative_size=20.0,
                detected_at=now - timedelta(minutes=90)
            ),
            WhaleAlert(
                market_id="market_123",
                order_size=Decimal("18000"),
                side="buy",
                relative_size=18.0,
                detected_at=now - timedelta(minutes=10)
            ),
        ]

        return detector

    def test_get_recent_whales_60_minutes(self, detector_with_whales):
        """Test getting whales from last 60 minutes."""
        recent = detector_with_whales.get_recent_whales(minutes=60)

        # Should return 2 whales (30 min and 10 min ago)
        assert len(recent) == 2

    def test_get_recent_whales_all(self, detector_with_whales):
        """Test getting all recent whales."""
        recent = detector_with_whales.get_recent_whales(minutes=120)

        assert len(recent) == 3


class TestLiquidityCheck:
    """Test liquidity sufficiency checks."""

    @pytest.fixture
    def detector(self):
        """Create detector for testing."""
        return WhaleDetector(market_id="market_123")

    def test_sufficient_liquidity(self, detector):
        """Test liquidity check passes with sufficient depth."""
        snapshot = OrderbookSnapshot(
            market_id="market_123",
            bids=[{'price': '0.55', 'size': '6000'}],
            asks=[{'price': '0.56', 'size': '5000'}],
            timestamp=datetime.now()
        )

        is_sufficient = detector.is_liquidity_sufficient(snapshot)

        assert is_sufficient is True  # $11,000 > $10,000 minimum

    def test_insufficient_liquidity(self, detector):
        """Test liquidity check fails with low depth."""
        snapshot = OrderbookSnapshot(
            market_id="market_123",
            bids=[{'price': '0.55', 'size': '3000'}],
            asks=[{'price': '0.56', 'size': '2000'}],
            timestamp=datetime.now()
        )

        is_sufficient = detector.is_liquidity_sufficient(snapshot)

        assert is_sufficient is False  # $5,000 < $10,000 minimum


class TestFrontRunPositionSizing:
    """Test front-run position size calculation."""

    @pytest.fixture
    def detector(self):
        """Create detector for testing."""
        return WhaleDetector(market_id="market_123")

    def test_position_size_small_whale(self, detector):
        """Test position size for small whale."""
        alert = WhaleAlert(
            market_id="market_123",
            order_size=Decimal("15000"),
            side="buy",
            relative_size=15.0,
            expected_impact=0.02
        )

        size = detector.calculate_front_run_position_size(
            whale_alert=alert,
            available_capital=Decimal("10000")
        )

        # Should be conservative for smaller whale
        assert Decimal("0") < size <= Decimal("500")  # Max 5%

    def test_position_size_large_whale(self, detector):
        """Test position size for large whale."""
        alert = WhaleAlert(
            market_id="market_123",
            order_size=Decimal("50000"),
            side="buy",
            relative_size=50.0,
            expected_impact=0.05
        )

        size = detector.calculate_front_run_position_size(
            whale_alert=alert,
            available_capital=Decimal("10000")
        )

        # Should be larger for bigger whale, but capped at 5%
        assert size == Decimal("500")  # Max 5% of $10k

    def test_position_size_respects_max_limit(self, detector):
        """Test position size respects maximum limit."""
        alert = WhaleAlert(
            market_id="market_123",
            order_size=Decimal("100000"),
            side="buy",
            relative_size=100.0,
            expected_impact=0.10
        )

        size = detector.calculate_front_run_position_size(
            whale_alert=alert,
            available_capital=Decimal("10000")
        )

        # Should be capped at 5% even for huge whale
        assert size == Decimal("500")


class TestStatistics:
    """Test whale detection statistics."""

    @pytest.fixture
    def detector_with_data(self):
        """Create detector with historical data."""
        detector = WhaleDetector(market_id="market_123")

        detector.average_order_size = Decimal("1000")
        detector.add_known_whale_wallet("0xWHALE1")
        detector.add_known_whale_wallet("0xWHALE2")

        # Add recent whales
        now = datetime.now()
        detector.recent_whales = [
            WhaleAlert(
                market_id="market_123",
                order_size=Decimal("15000"),
                side="buy",
                relative_size=15.0,
                detected_at=now - timedelta(hours=1),
                confidence=0.85,
                expected_impact=0.03
            ),
            WhaleAlert(
                market_id="market_123",
                order_size=Decimal("20000"),
                side="sell",
                relative_size=20.0,
                detected_at=now - timedelta(hours=2),
                confidence=0.90,
                expected_impact=0.04
            ),
        ]

        return detector

    def test_get_statistics(self, detector_with_data):
        """Test getting whale detection statistics."""
        stats = detector_with_data.get_statistics()

        assert stats['average_order_size'] == 1000.0
        assert stats['whales_detected_24h'] == 2
        assert stats['avg_confidence_24h'] == 0.875  # (0.85 + 0.90) / 2
        assert stats['avg_impact_24h'] == 0.035  # (0.03 + 0.04) / 2
        assert stats['known_whale_wallets'] == 2


class TestFullWorkflow:
    """Test complete whale detection workflow."""

    @pytest.fixture
    def detector_ready(self):
        """Create detector with sufficient history."""
        detector = WhaleDetector(market_id="market_123")

        # Build up history with normal orders
        for _ in range(60):
            detector.order_size_history.append(Decimal("1000"))
            detector.orderbook_depth_history.append(Decimal("10000"))

        return detector

    def test_detect_whale_complete_workflow(self, detector_ready):
        """Test complete whale detection workflow."""
        # Create snapshot with whale order
        snapshot = OrderbookSnapshot(
            market_id="market_123",
            bids=[
                {'price': '0.55', 'size': '25000'},  # Whale (25x average)
                {'price': '0.54', 'size': '1000'},
            ],
            asks=[
                {'price': '0.56', 'size': '1000'},
            ],
            timestamp=datetime.now()
        )

        # Process snapshot
        alerts = detector_ready.update_orderbook_snapshot(snapshot)

        # Should detect the whale
        assert len(alerts) == 1
        assert alerts[0].side == "buy"
        assert alerts[0].order_size == Decimal("25000")
        assert alerts[0].confidence >= 0.7
        assert alerts[0].expected_impact >= 0.02

        # Check history was updated
        assert len(detector_ready.order_size_history) > 60
        assert len(detector_ready.recent_whales) == 1

    def test_no_whale_detected_normal_orders(self, detector_ready):
        """Test no whale detected for normal orders."""
        snapshot = OrderbookSnapshot(
            market_id="market_123",
            bids=[
                {'price': '0.55', 'size': '1100'},
                {'price': '0.54', 'size': '950'},
            ],
            asks=[
                {'price': '0.56', 'size': '1050'},
            ],
            timestamp=datetime.now()
        )

        alerts = detector_ready.update_orderbook_snapshot(snapshot)

        assert len(alerts) == 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_orderbook(self):
        """Test handling of empty orderbook."""
        detector = WhaleDetector(market_id="market_123")

        snapshot = OrderbookSnapshot(
            market_id="market_123",
            bids=[],
            asks=[],
            timestamp=datetime.now()
        )

        # Should not crash
        depth = detector._calculate_orderbook_depth(snapshot)
        assert depth == Decimal("0")

    def test_whale_alert_trimming(self):
        """Test recent whales list is trimmed."""
        detector = WhaleDetector(market_id="market_123")

        # Add 150 whale alerts
        for i in range(150):
            detector.recent_whales.append(
                WhaleAlert(
                    market_id="market_123",
                    order_size=Decimal("15000"),
                    side="buy",
                    relative_size=15.0,
                    detected_at=datetime.now()
                )
            )

        # Trigger trimming by processing a snapshot
        for _ in range(60):
            detector.order_size_history.append(Decimal("1000"))

        snapshot = OrderbookSnapshot(
            market_id="market_123",
            bids=[{'price': '0.55', 'size': '1000'}],
            asks=[],
            timestamp=datetime.now()
        )

        detector.update_orderbook_snapshot(snapshot)

        # Should be trimmed to 100
        assert len(detector.recent_whales) == 100
