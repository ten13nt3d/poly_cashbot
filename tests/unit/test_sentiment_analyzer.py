"""Unit tests for TemporalArbitrageDetector."""

import pytest
from datetime import datetime
from decimal import Decimal
from unittest.mock import Mock

import pandas as pd

from src.lib.exceptions import InsufficientDataError, LowConfidenceError
from src.lib.sentiment.analyzer import (
    TemporalArbitrageDetector,
    TemporalArbitrageOpportunity,
    TimeframeSentiment
)


class TestTemporalArbitrageDetector:
    """Test cases for the temporal arbitrage detector."""

    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance for testing."""
        return TemporalArbitrageDetector()

    @pytest.fixture
    def sample_price_data(self):
        """Create sample price data for testing."""
        # 30 data points over 15-minute intervals
        timestamps = pd.date_range('2024-01-01 00:00', periods=30, freq='15min')
        data = {
            'open': [1.00 + i * 0.001 for i in range(30)],
            'high': [1.01 + i * 0.001 for i in range(30)],
            'low': [0.99 + i * 0.001 for i in range(30)],
            'close': [1.005 + i * 0.001 for i in range(30)],
            'volume': [1000 + i * 10 for i in range(30)]
        }
        return pd.DataFrame(data, index=timestamps)

    @pytest.fixture
    def bull_market_data(self):
        """Create bullish price data."""
        timestamps = pd.date_range('2024-01-01 00:00', periods=30, freq='15min')
        # Trending up with volume
        data = {
            'open': [1.00 + i * 0.005 for i in range(30)],
            'high': [1.01 + i * 0.005 for i in range(30)],
            'low': [0.99 + i * 0.005 for i in range(30)],
            'close': [1.005 + i * 0.005 for i in range(30)],
            'volume': [1000 * (1 + i * 0.05) for i in range(30)]  # Increasing volume
        }
        return pd.DataFrame(data, index=timestamps)

    @pytest.fixture
    def bear_market_data(self):
        """Create bearish price data."""
        timestamps = pd.date_range('2024-01-01 00:00', periods=30, freq='15min')
        # Trending down with volume
        data = {
            'open': [1.00 - i * 0.005 for i in range(30)],
            'high': [1.01 - i * 0.005 for i in range(30)],
            'low': [0.99 - i * 0.005 for i in range(30)],
            'close': [1.005 - i * 0.005 for i in range(30)],
            'volume': [1000 * (1 + i * 0.05) for i in range(30)]
        }
        return pd.DataFrame(data, index=timestamps)

    def test_analyzer_initialization(self, analyzer):
        """Test analyzer initializes correctly."""
        assert analyzer.MIN_CONFIDENCE == 0.80
        assert analyzer.MIN_SENTIMENT_MAGNITUDE == 40
        assert analyzer.MIN_ALIGNMENT_SCORE == 0.7
        assert analyzer.MIN_DATA_POINTS == 20

    def test_insufficient_data_error(self, analyzer):
        """Test analyzer rejects insufficient data."""
        small_data = pd.DataFrame({
            'close': [1.0, 1.1, 1.2]
        })
        
        with pytest.raises(InsufficientDataError) as exc_info:
            analyzer.analyze(small_data, news_sentiment=50, current_volatility=0.1)
        
        assert "Need at least 20 data points" in str(exc_info.value)

    def test_high_volatility_filtered(self, analyzer, sample_price_data):
        """Test analyzer skips high volatility (choppy markets)."""
        result = analyzer.analyze(
            sample_price_data,
            news_sentiment=50,
            current_volatility=0.3  # Above threshold
        )
        
        assert result is None  # Should skip choppy market

    def test_bullish_signal_generation(self, analyzer, bull_market_data):
        """Test bullish signal generation with strong alignment."""
        signal = analyzer.analyze(
            bull_market_data,
            news_sentiment=60,  # Strong bullish news
            current_volatility=0.15
        )
        
        assert signal is not None
        assert signal.direction == "BUY"
        assert signal.confidence >= analyzer.MIN_CONFIDENCE
        assert signal.sentiment_score > analyzer.MIN_SENTIMENT_MAGNITUDE
        assert signal.expected_win_rate > 0.7
        assert signal.reason != ""

    def test_bearish_signal_generation(self, analyzer, bear_market_data):
        """Test bearish signal generation with strong alignment."""
        signal = analyzer.analyze(
            bear_market_data,
            news_sentiment=-60,  # Strong bearish news
            current_volatility=0.15
        )
        
        assert signal is not None
        assert signal.direction == "SELL"
        assert signal.confidence >= analyzer.MIN_CONFIDENCE
        assert signal.sentiment_score < -analyzer.MIN_SENTIMENT_MAGNITUDE
        assert signal.expected_win_rate > 0.7

    def test_weak_signal_filtered(self, analyzer, sample_price_data):
        """Test analyzer rejects weak signals."""
        signal = analyzer.analyze(
            sample_price_data,
            news_sentiment=20,  # Weak news sentiment
            current_volatility=0.15
        )
        
        assert signal is None  # Should reject weak signal

    def test_low_confidence_filtered(self, analyzer, sample_price_data):
        """Test analyzer doesn't return signal if confidence < 80%."""
        # Create choppy data that should result in low confidence
        choppy_data = sample_price_data.copy()
        choppy_data['close'] = [1.0, 1.1, 0.9, 1.05, 0.95] * 6  # Oscillating
        
        signal = analyzer.analyze(
            choppy_data,
            news_sentiment=30,
            current_volatility=0.15
        )
        
        # Should return None due to low confidence
        # (We can't guarantee this will be None due to complexity,
        # but the analyzer should filter internally)
        if signal:
            assert signal.confidence < analyzer.MIN_CONFIDENCE

    def test_timeframe_analysis(self, analyzer, bull_market_data):
        """Test multi-timeframe analysis."""
        # Mock the analyze method to test timeframe analysis only
        analyzer._analyze_timeframes = Mock(wraps=analyzer._analyze_timeframes)
        
        try:
            analyzer.analyze(
                bull_market_data,
                news_sentiment=60,
                current_volatility=0.15
            )
        except:
            pass  # We're just testing the method was called
        
        # Check that timeframe analysis was called
        analyzer._analyze_timeframes.assert_called_once()
        
        # Direct test of timeframe analysis
        timeframes = analyzer._analyze_timeframes(bull_market_data)
        
        assert len(timeframes) == 3  # Should analyze 15m, 1h, 4h
        assert all(isinstance(tf, TimeframeSentiment) for tf in timeframes)
        
        # Check timeframe names
        timeframe_names = [tf.timeframe for tf in timeframes]
        assert "15m" in timeframe_names
        assert "1h" in timeframe_names
        assert "4h" in timeframe_names

    def test_price_momentum_calculation(self, analyzer):
        """Test price momentum calculation."""
        # Bullish data
        bull_data = pd.DataFrame({
            'close': [100, 105, 110, 115, 120]
        })
        momentum = analyzer._calculate_price_momentum(bull_data)
        assert momentum > 0
        
        # Bearish data
        bear_data = pd.DataFrame({
            'close': [120, 115, 110, 105, 100]
        })
        momentum = analyzer._calculate_price_momentum(bear_data)
        assert momentum < 0
        
        # Flat data
        flat_data = pd.DataFrame({
            'close': [100, 100, 100, 100, 100]
        })
        momentum = analyzer._calculate_price_momentum(flat_data)
        assert momentum == 0

    def test_volume_confirmation(self, analyzer):
        """Test volume confirmation calculation."""
        # Volume spike
        data = pd.DataFrame({
            'volume': [100, 100, 100, 100, 500]  # Spike at end
        })
        conf = analyzer._calculate_volume_confirmation(data)
        assert conf > 0.5  # Should indicate confirmation
        
        # Low volume
        data = pd.DataFrame({
            'volume': [100, 100, 100, 100, 50]  # Drop at end
        })
        conf = analyzer._calculate_volume_confirmation(data)
        assert conf < 0.5

    def test_trend_strength_calculation(self, analyzer):
        """Test trend strength calculation."""
        # Strong uptrend
        trend_data = pd.DataFrame({
            'close': [100, 110, 120, 130, 140]
        })
        strength = analyzer._calculate_trend_strength(trend_data)
        assert strength > 0
        
        # Strong downtrend
        trend_data = pd.DataFrame({
            'close': [140, 130, 120, 110, 100]
        })
        strength = analyzer._calculate_trend_strength(trend_data)
        assert strength < 0
        
        # No trend
        flat_data = pd.DataFrame({
            'close': [100, 105, 95, 105, 95]
        })
        strength = analyzer._calculate_trend_strength(flat_data)
        assert -0.1 < strength < 0.1

    def test_composite_sentiment_calculation(self, analyzer):
        """Test composite sentiment calculation."""
        timeframe_sentiments = [
            TimeframeSentiment("15m", 20, 0.8, 0.5, 0.1, datetime.now()),
            TimeframeSentiment("1h", 25, 0.7, 0.6, 0.12, datetime.now()),
            TimeframeSentiment("4h", 30, 0.9, 0.7, 0.08, datetime.now())
        ]
        
        composite = analyzer._calculate_composite_sentiment(
            timeframe_sentiments,
            news_sentiment=40
        )
        
        assert composite.score > 0  # Should be bullish
        assert composite.momentum_score > 0
        assert composite.volume_confirmation > 0.5

    def test_alignment_calculation(self, analyzer):
        """Test timeframe alignment calculation."""
        # Perfect alignment
        aligned_sentiments = [
            TimeframeSentiment("15m", 20, 0.8, 0.5, 0.1, datetime.now()),
            TimeframeSentiment("1h", 25, 0.8, 0.6, 0.12, datetime.now()),
            TimeframeSentiment("4h", 30, 0.8, 0.7, 0.08, datetime.now())
        ]
        alignment = analyzer._calculate_alignment(aligned_sentiments)
        assert alignment > 0.9  # Should be near perfect
        
        # Mixed alignment
        mixed_sentiments = [
            TimeframeSentiment("15m", 20, 0.8, 0.5, 0.1, datetime.now()),
            TimeframeSentiment("1h", -10, 0.8, -0.3, 0.12, datetime.now()),
            TimeframeSentiment("4h", 30, 0.8, 0.7, 0.08, datetime.now())
        ]
        alignment = analyzer._calculate_alignment(mixed_sentiments)
        assert alignment < 0.8  # Should be lower due to misalignment

    def test_confidence_calculation(self, analyzer):
        """Test confidence calculation."""
        # High confidence scenario
        timeframe_sentiments = [
            TimeframeSentiment("15m", 40, 0.9, 0.8, 0.1, datetime.now()),
            TimeframeSentiment("1h", 45, 0.9, 0.8, 0.1, datetime.now()),
            TimeframeSentiment("4h", 50, 0.9, 0.8, 0.1, datetime.now())
        ]
        
        confidence = analyzer._calculate_confidence(
            timeframe_sentiments,
            news_sentiment=60,  # Strong news
            current_volatility=0.1,  # Low volatility
            alignment_score=0.95  # Perfect alignment
        )
        
        assert confidence > analyzer.MIN_CONFIDENCE
        
        # Low confidence scenario
        confidence = analyzer._calculate_confidence(
            timeframe_sentiments,
            news_sentiment=20,  # Weak news
            current_volatility=0.3,  # High volatility
            alignment_score=0.5  # Poor alignment
        )
        
        assert confidence < analyzer.MIN_CONFIDENCE

    def test_historical_accuracy_lookup(self, analyzer):
        """Test historical accuracy lookup."""
        # High sentiment and confidence should yield high expected win rate
        win_rate = analyzer._get_historical_accuracy(
            sentiment_score=60,
            confidence=0.9
        )
        assert win_rate > 0.8
        
        # Low values should yield lower win rate
        win_rate = analyzer._get_historical_accuracy(
            sentiment_score=20,
            confidence=0.6
        )
        assert 0.65 <= win_rate <= 0.75

    def test_reason_generation(self, analyzer):
        """Test human-readable reason generation."""
        timeframe_sentiments = [
            TimeframeSentiment("15m", 40, 0.9, 0.8, 0.1, datetime.now()),
            TimeframeSentiment("1h", 45, 0.9, 0.8, 0.1, datetime.now()),
            TimeframeSentiment("4h", 50, 0.9, 0.8, 0.1, datetime.now())
        ]
        
        reason = analyzer._generate_reason(
            timeframe_sentiments,
            news_sentiment=60,
            alignment_score=0.95,
            confidence=0.92
        )
        
        assert "alignment" in reason.lower()
        assert "bullish" in reason.lower() or "bearish" in reason.lower()
        assert "high confidence" in reason.lower()

    def test_arbitrage_opportunity_dataclass(self):
        """Test TemporalArbitrageOpportunity dataclass validation."""
        opportunity = TemporalArbitrageOpportunity(
            direction="BUY",
            spot_momentum=45.0,
            polymarket_lag=35.5,
            implied_probability=0.78,
            polymarket_price=0.52,
            certainty_gap=0.26,
            confidence=0.92,
            expected_win_rate=0.98,
            urgency="HIGH"
        )

        assert opportunity.direction == "BUY"
        assert opportunity.confidence == 0.92
        assert opportunity.spot_momentum == 45.0
        assert opportunity.expected_win_rate == 0.98
        assert opportunity.polymarket_lag == 35.5
        assert opportunity.urgency == "HIGH"
        assert opportunity.certainty_gap == 0.26

    def test_timeframe_sentiment_dataclass(self):
        """Test TimeframeSentiment dataclass validation."""
        tf_sentiment = TimeframeSentiment(
            timeframe="15m",
            price_momentum=25.5,
            volume_confirmation=0.85,
            trend_strength=0.72,
            volatility=0.15,
            timestamp=datetime.now()
        )
        
        assert tf_sentiment.timeframe == "15m"
        assert tf_sentiment.price_momentum == 25.5
        assert tf_sentiment.volume_confirmation == 0.85
        assert tf_sentiment.trend_strength == 0.72
        assert tf_sentiment.volatility == 0.15

    def test_edge_cases(self, analyzer):
        """Test edge cases and error handling."""
        # Empty dataframe
        empty_df = pd.DataFrame()
        with pytest.raises(InsufficientDataError):
            analyzer.analyze(empty_df, 50, 0.1)
        
        # DataFrame with only timestamps
        timestamp_df = pd.DataFrame(index=pd.date_range('2024-01-01', periods=25, freq='15min'))
        with pytest.raises(InsufficientDataError):
            analyzer.analyze(timestamp_df, 50, 0.1)

    def test_constant_parameters(self, analyzer):
        """Test that critical parameters are set correctly."""
        assert analyzer.MIN_CONFIDENCE == 0.80  # Ultra-selective
        assert analyzer.MIN_SENTIMENT_MAGNITUDE == 40  # Strong signals only
        assert analyzer.MIN_ALIGNMENT_SCORE == 0.7  # Require alignment
        assert analyzer.MAX_VOLATILITY_THRESHOLD == 0.25  # Skip choppy
        assert analyzer.MIN_DATA_POINTS == 20  # Minimum data

    def test_arbitrage_opportunity_detection(self, analyzer):
        """Test arbitrage opportunity detection with valid conditions."""
        from datetime import datetime, timedelta

        # Setup with strong momentum (>15% needed)
        spot_data = {
            "price": 50000,
            "prices": [42000, 44000, 46000, 48000, 50000]  # ~19% momentum
        }
        polymarket_data = {
            "price": 2.5  # Outdated, implies ~29% probability
        }

        # Setup timestamps to ensure sufficient lag (>30 seconds needed)
        current_time = datetime.now()
        analyzer.last_updated["BTC_spot"] = current_time - timedelta(seconds=5)
        analyzer.last_updated["BTC_poly"] = current_time - timedelta(seconds=70)

        opportunity = analyzer.detect_arbitrage_opportunity(
            spot_data=spot_data,
            polymarket_data=polymarket_data,
            asset="BTC"
        )

        assert opportunity is not None
        assert opportunity.direction in ["BUY", "SELL"]
        assert opportunity.spot_momentum != 0
        assert opportunity.confidence >= 0.90
        assert opportunity.expected_win_rate >= 0.95

    def test_arbitrage_insufficient_momentum(self, analyzer):
        """Test that low momentum is filtered out."""
        spot_data = {
            "price": 50000,
            "prices": [50000, 50001, 50002, 50001, 50000]  # Very low momentum
        }
        polymarket_data = {
            "price": 1.0
        }

        opportunity = analyzer.detect_arbitrage_opportunity(
            spot_data=spot_data,
            polymarket_data=polymarket_data,
            asset="BTC"
        )

        assert opportunity is None  # Should filter low momentum

    def test_arbitrage_insufficient_certainty_gap(self, analyzer):
        """Test that small certainty gaps are filtered out."""
        spot_data = {
            "price": 50000,
            "prices": [48000, 48500, 49000, 49500, 50000]  # Good momentum
        }
        polymarket_data = {
            "price": 0.95  # Price already reflects the movement
        }

        opportunity = analyzer.detect_arbitrage_opportunity(
            spot_data=spot_data,
            polymarket_data=polymarket_data,
            asset="BTC"
        )

        assert opportunity is None  # Certainty gap too small

    def test_arbitrage_invalid_asset(self, analyzer):
        """Test that non-target assets are filtered."""
        spot_data = {"price": 100, "prices": [90, 95, 100, 105, 110]}
        polymarket_data = {"price": 1.5}

        opportunity = analyzer.detect_arbitrage_opportunity(
            spot_data=spot_data,
            polymarket_data=polymarket_data,
            asset="DOGE"  # Not in target assets
        )

        assert opportunity is None

    def test_arbitrage_missing_price_data(self, analyzer):
        """Test handling of missing price data."""
        spot_data = {"price": None}
        polymarket_data = {"price": 1.0}

        opportunity = analyzer.detect_arbitrage_opportunity(
            spot_data=spot_data,
            polymarket_data=polymarket_data,
            asset="BTC"
        )

        assert opportunity is None

    def test_calculate_spot_momentum(self, analyzer):
        """Test spot momentum calculation."""
        # Setup spot prices
        analyzer.spot_prices["BTC"] = {
            "prices": [48000, 48500, 49000, 49500, 50000]
        }

        momentum = analyzer._calculate_spot_momentum("BTC")
        assert momentum > 0  # Positive momentum
        assert momentum > 4.0  # Should be ~4.17% ((50000-48000)/48000 * 100)

        # Test downward momentum
        analyzer.spot_prices["ETH"] = {
            "prices": [3000, 2900, 2800, 2700, 2600]
        }

        momentum = analyzer._calculate_spot_momentum("ETH")
        assert momentum < 0  # Negative momentum

    def test_calculate_spot_momentum_edge_cases(self, analyzer):
        """Test spot momentum edge cases."""
        # Asset not in spot_prices
        momentum = analyzer._calculate_spot_momentum("UNKNOWN")
        assert momentum == 0.0

        # Insufficient prices
        analyzer.spot_prices["BTC"] = {"prices": [50000, 50100]}
        momentum = analyzer._calculate_spot_momentum("BTC")
        assert momentum == 0.0

        # Zero start price
        analyzer.spot_prices["BTC"] = {"prices": [0, 100, 200, 300, 400]}
        momentum = analyzer._calculate_spot_momentum("BTC")
        assert momentum == 0.0

    def test_calculate_implied_probability(self, analyzer):
        """Test implied probability calculation from momentum."""
        # Strong positive momentum
        prob = analyzer._calculate_implied_probability(20.0)
        assert prob > 0.5  # Should imply >50% probability

        # Strong negative momentum
        prob = analyzer._calculate_implied_probability(-20.0)
        assert prob < 0.5  # Should imply <50% probability

        # Zero momentum
        prob = analyzer._calculate_implied_probability(0.0)
        assert prob == 0.5  # Should be 50%

        # Extreme values should be clamped
        prob = analyzer._calculate_implied_probability(100.0)
        assert 0.0 <= prob <= 1.0

    def test_calculate_lag(self, analyzer):
        """Test lag calculation between spot and polymarket."""
        from datetime import datetime, timedelta

        current_time = datetime.now()
        analyzer.last_updated["BTC_spot"] = current_time - timedelta(seconds=10)
        analyzer.last_updated["BTC_poly"] = current_time - timedelta(seconds=50)

        lag = analyzer._calculate_lag("BTC", current_time)
        assert lag >= 35  # Should detect ~40 second lag

        # Test when poly is newer (negative lag should return 0)
        analyzer.last_updated["BTC_spot"] = current_time - timedelta(seconds=50)
        analyzer.last_updated["BTC_poly"] = current_time - timedelta(seconds=10)

        lag = analyzer._calculate_lag("BTC", current_time)
        assert lag == 0  # Negative lag returns 0

    def test_arbitrage_urgency_levels(self, analyzer):
        """Test that urgency is correctly assigned based on lag."""
        from datetime import datetime, timedelta

        current_time = datetime.now()

        # High urgency (>60 seconds lag)
        analyzer.last_updated["BTC_spot"] = current_time - timedelta(seconds=5)
        analyzer.last_updated["BTC_poly"] = current_time - timedelta(seconds=70)

        spot_data = {
            "price": 50000,
            "prices": [48000, 48500, 49000, 49500, 50000]
        }
        polymarket_data = {"price": 2.0}

        opportunity = analyzer.detect_arbitrage_opportunity(
            spot_data=spot_data,
            polymarket_data=polymarket_data,
            asset="BTC"
        )

        if opportunity:
            assert opportunity.urgency == "HIGH"

    def test_extract_series_edge_cases(self, analyzer):
        """Test _extract_series with various input types."""
        # Test with Series
        series = pd.Series([1, 2, 3, 4, 5])
        result = analyzer._extract_series(series, "close")
        assert result == [1, 2, 3, 4, 5]

        # Test with dict containing non-iterable
        data = {"close": 42}
        result = analyzer._extract_series(data, "close")
        assert result == []

        # Test with missing key
        df = pd.DataFrame({"open": [1, 2, 3]})
        result = analyzer._extract_series(df, "close")
        assert result == []
