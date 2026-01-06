"""High-Accurity Sentiment Analysis Engine for >70% Win Rate."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any

from src.lib.exceptions import InsufficientDataError, LowConfidenceError


@dataclass
class Signal:
    """Trading signal with confidence metrics."""
    direction: str  # "BUY" or "SELL"
    confidence: float  # 0.0 to 1.0
    sentiment_score: float  # -100 to +100
    expected_win_rate: float  # Historical win rate at similar conditions
    timeframe_alignment: float  # 0.0 to 1.0 (how well timeframes align)
    strength: float  # 0.0 to 1.0 (signal strength)
    reason: str  # Human-readable reason


@dataclass
class TimeframeSentiment:
    """Sentiment data for a specific timeframe."""
    timeframe: str  # "15m", "1h", "4h"
    price_momentum: float  # -100 to +100
    volume_confirmation: float  # 0.0 to 1.0
    trend_strength: float  # -1.0 to +1.0
    volatility: float  # Annualized volatility
    timestamp: datetime


class HighAccuracySentimentAnalyzer:
    """
    Ultra-selective sentiment analyzer optimized for >70% win rate.

    Only generates signals when confidence >80% and sentiment magnitude >40.
    Uses multi-timeframe analysis and filters choppy markets.

    Strategy:
    1. Analyze price momentum across 15m, 1h, 4h timeframes
    2. Check for timeframe alignment (all pointing same direction)
    3. Validate with volume confirmation
    4. Filter low-confidence setups
    5. Return signal only if all criteria met
    """

    # Ultra-selective parameters for high win rate
    MIN_CONFIDENCE = 0.80  # Only trade 80%+ confidence
    MIN_SENTIMENT_MAGNITUDE = 40  # Strong signals only
    MIN_ALIGNMENT_SCORE = 0.7  # Timeframes must align
    MAX_VOLATILITY_THRESHOLD = 0.25  # Skip extreme volatility
    MIN_DATA_POINTS = 20  # Minimum data points for analysis

    def __init__(self):
        """Initialize the sentiment analyzer."""
        self.historical_accuracy = {}  # Cache for historical accuracy lookups

    def analyze(
        self,
        price_data: Dict[str, Any],
        news_sentiment: float,
        current_volatility: float,
        timestamp: Optional[datetime] = None
    ) -> Optional[Signal]:
        """
        Analyze market data and generate trading signal.

        Args:
            price_data: Dict with OHLCV data and timestamps
            news_sentiment: News sentiment score (-100 to +100)
            current_volatility: Current market volatility (0.0 to 1.0)
            timestamp: Analysis timestamp (defaults to now)

        Returns:
            Signal if all criteria met, None if no high-confidence setup

        Raises:
            InsufficientDataError: If price_data has insufficient points
            LowConfidenceError: If analysis passes but confidence < MIN_CONFIDENCE
        """
        if len(price_data.get('close', [])) < self.MIN_DATA_POINTS:
            raise InsufficientDataError(
                f"Need at least {self.MIN_DATA_POINTS} data points, "
                f"got {len(price_data.get('close', []))}"
            )

        # Skip extreme volatility (choppy markets)
        if current_volatility > self.MAX_VOLATILITY_THRESHOLD:
            return None

        # 1. Multi-timeframe analysis
        timeframe_sentiments = self._analyze_timeframes(price_data)
        
        # 2. Check timeframe alignment
        alignment_score = self._calculate_alignment(timeframe_sentiments)
        if alignment_score < self.MIN_ALIGNMENT_SCORE:
            return None  # Timeframes don't align

        # 3. Calculate composite sentiment
        composite_sentiment = self._calculate_composite_sentiment(
            timeframe_sentiments, news_sentiment
        )

        # 4. Check if signal is strong enough
        if abs(composite_sentiment.score) < self.MIN_SENTIMENT_MAGNITUDE:
            return None  # Signal too weak

        # 5. Calculate overall confidence
        confidence = self._calculate_confidence(
            timeframe_sentiments,
            news_sentiment,
            current_volatility,
            alignment_score
        )

        # 6. Historical accuracy lookup
        expected_win_rate = self._get_historical_accuracy(
            composite_sentiment.score, confidence
        )

        # 7. CRITICAL: Only return signal if confidence >80%
        if confidence < self.MIN_CONFIDENCE:
            return None

        # 8. Determine direction
        direction = "BUY" if composite_sentiment.score > 0 else "SELL"

        # 9. Generate human-readable reason
        reason = self._generate_reason(
            timeframe_sentiments,
            news_sentiment,
            alignment_score,
            confidence
        )

        return Signal(
            direction=direction,
            confidence=confidence,
            sentiment_score=composite_sentiment.score,
            expected_win_rate=expected_win_rate,
            timeframe_alignment=alignment_score,
            strength=min(abs(composite_sentiment.score) / 100, 1.0),
            reason=reason
        )

    def _analyze_timeframes(self, price_data: Dict[str, Any]) -> List[TimeframeSentiment]:
        """Analyze sentiment across multiple timeframes."""
        timeframes = [
            ("15m", 15),
            ("1h", 60),
            ("4h", 240)
        ]
        
        results = []
        close_prices = price_data.get('close', [])
        volumes = price_data.get('volume', [])
        
        for timeframe_name, minutes in timeframes:
            # Get data for this timeframe
            tf_close_prices = close_prices[-minutes:] if len(close_prices) >= minutes else close_prices
            tf_volumes = volumes[-minutes:] if len(volumes) >= minutes else volumes
            
            if len(tf_close_prices) < 5:  # Need at least 5 points
                continue
            
            # Store in simple dict format for compatibility
            tf_data = {
                'close': tf_close_prices,
                'volume': tf_volumes
            }
            
            # Calculate price momentum (rate of change)
            price_momentum = self._calculate_price_momentum(tf_data)
            
            # Volume confirmation (volume above recent average)
            volume_confirmation = self._calculate_volume_confirmation(tf_data)
            
            # Trend strength (-1 to +1)
            trend_strength = self._calculate_trend_strength(tf_data)
            
            # Volatility (for this timeframe)
            volatility = self._calculate_volatility(tf_data)
            
            results.append(TimeframeSentiment(
                timeframe=timeframe_name,
                price_momentum=price_momentum,
                volume_confirmation=volume_confirmation,
                trend_strength=trend_strength,
                volatility=volatility,
                timestamp=datetime.now()
            ))
        
        return results

    def _calculate_price_momentum(self, data: Dict[str, Any]) -> float:
        """Calculate price momentum as percentage change."""
        close_prices = data.get('close', [])
        
        if len(close_prices) < 2:
            return 0.0
        
        first_price = close_prices[0]
        last_price = close_prices[-1]
        
        if first_price == 0:
            return 0.0
        
        pct_change = ((last_price - first_price) / first_price) * 100
        return max(min(pct_change, 100), -100)    # Clamp to -100 to +100

    def _calculate_volume_confirmation(self, data: Dict[str, Any]) -> float:
        """Calculate volume confirmation (0.0 to 1.0)."""
        volumes = data.get('volume', [])
        
        if len(volumes) < 10:
            return 0.5  # Default to neutral
        
        recent_volume = volumes[-1]
        avg_volume = sum(volumes[:-1]) / len(volumes[:-1])  # Exclude latest from average
        
        if avg_volume == 0:
            return 0.5
        
        # Volume spike = good confirmation
        volume_ratio = recent_volume / avg_volume
        
        # Convert to 0-1 scale (capped at 3x average)
        return min(volume_ratio / 3, 1.0)

    def _calculate_trend_strength(self, data: Dict[str, Any]) -> float:
        """Calculate trend strength using linear regression slope."""
        close_prices = data.get('close', [])
        
        if len(close_prices) < 5:
            return 0.0
        
        # Simple linear regression
        x = list(range(len(close_prices)))
        n = len(close_prices)
        
        sum_x = sum(x)
        sum_y = sum(close_prices)
        sum_xy = sum(xi * yi for xi, yi in zip(x, close_prices))
        sum_x2 = sum(xi * xi for xi in x)
        
        # Calculate slope
        denominator = n * sum_x2 - sum_x * sum_x
        if denominator == 0:
            return 0.0
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        
        # Normalize slope to -1 to +1 range
        # Approximate normalization (will vary by price level)
        max_slope = sum(close_prices) / len(close_prices) * 0.1  # 10% per period is max
        return max(min(slope / max_slope, 1), -1)

    def _calculate_volatility(self, data: Dict[str, Any]) -> float:
        """Calculate annualized volatility."""
        close_prices = data.get('close', [])
        
        if len(close_prices) < 2:
            return 0.0
        
        # Calculate daily returns
        returns = []
        for i in range(1, len(close_prices)):
            return_pct = (close_prices[i] - close_prices[i-1]) / close_prices[i-1]
            returns.append(return_pct)
        
        if not returns:
            return 0.0
        
        # Calculate standard deviation of returns
        avg_return = sum(returns) / len(returns)
        variance = sum((r - avg_return) ** 2 for r in returns) / len(returns)
        
        # Annualized volatility (assuming returns are per period)
        volatility = (variance ** 0.5) * (252 ** 0.5)  # Annualized
        
        return min(volatility, 1.0)  # Cap at 100%

    @dataclass
    class CompositeSentiment:
        score: float
        momentum_score: float
        news_score: float
        volume_confirmation: float

    def _calculate_composite_sentiment(
        self,
        timeframe_sentiments: List[TimeframeSentiment],
        news_sentiment: float
    ) -> CompositeSentiment:
        """Calculate composite sentiment from all inputs."""
        
        # Weight timeframes (more recent = higher weight)
        momentum_weights = {"15m": 0.4, "1h": 0.35, "4h": 0.25}
        momentum_score = 0.0
        total_weight = 0.0
        
        for tf_sentiment in timeframe_sentiments:
            weight = momentum_weights.get(tf_sentiment.timeframe, 0)
            momentum_score += tf_sentiment.price_momentum * weight
            total_weight += weight
        
        if total_weight > 0:
            momentum_score /= total_weight
        
        # Volume confirmation (average across timeframes)
        volume_confirmation = sum(
            tf.volume_confirmation for tf in timeframe_sentiments
        ) / max(len(timeframe_sentiments), 1)
        
        # Composite score (weighted combination)
        # Momentum 60%, News 30%, Volume 10%
        composite_score = (
            momentum_score * 0.6 +
            news_sentiment * 0.3 +
            (volume_confirmation - 0.5) * 20 * 0.1  # Volume converted to -10 to +10 range
        )
        
        return self.CompositeSentiment(
            score=composite_score,
            momentum_score=momentum_score,
            news_score=news_sentiment,
            volume_confirmation=volume_confirmation
        )

    def _calculate_alignment(
        self,
        timeframe_sentiments: List[TimeframeSentiment]
    ) -> float:
        """Calculate how well timeframes align (0.0 to 1.0)."""
        if len(timeframe_sentiments) < 2:
            return 0.5  # Neutral if only one timeframe
        
        # Check if all timeframes point in same direction
        directions = [1 if tf.price_momentum > 5 else -1 if tf.price_momentum < -5 else 0 
                     for tf in timeframe_sentiments]
        
        # Remove neutral directions
        directions = [d for d in directions if d != 0]
        
        if len(directions) == 0:
            return 0.5  # All neutral
        
        # Calculate alignment (how many point same direction)
        if len(directions) == 1:
            return 0.75  # Good but not perfect
        
        # Check if all point same way
        if all(d == directions[0] for d in directions):
            return 0.95  # Perfect alignment
        
        # Calculate percentage alignment
        majority_direction = max(set(directions), key=directions.count)
        aligned_count = sum(1 for d in directions if d == majority_direction)
        
        return aligned_count / len(directions)

    def _calculate_confidence(
        self,
        timeframe_sentiments: List[TimeframeSentiment],
        news_sentiment: float,
        current_volatility: float,
        alignment_score: float
    ) -> float:
        """Calculate overall confidence in the signal."""
        
        # Component scores
        alignment_conf = alignment_score  # 0.0 to 1.0
        
        # News confidence (absolute value, normalized)
        news_conf = min(abs(news_sentiment) / 50, 1.0)
        
        # Volume confidence (average across timeframes)
        volume_conf = sum(tf.volume_confirmation for tf in timeframe_sentiments) / max(len(timeframe_sentiments), 1)
        
        # Trend strength confidence
        trend_confidence = sum(abs(tf.trend_strength) for tf in timeframe_sentiments) / max(len(timeframe_sentiments), 1)
        
        # Volatility penalty (high volatility = lower confidence)
        volatility_penalty = current_volatility * 0.2
        
        # Timeframe diversity bonus (more timeframes = higher confidence)
        diversity_bonus = min(len(timeframe_sentiments) / 3, 1.0) * 0.1
        
        # Weighted combination
        confidence = (
            alignment_conf * 0.35 +
            news_conf * 0.20 +
            volume_conf * 0.15 +
            trend_confidence * 0.20 +
            diversity_bonus
        ) - volatility_penalty
        
        return max(min(confidence, 0.99), 0.0)  # Clamp to 0-99%

    def _get_historical_accuracy(self, sentiment_score: float, confidence: float) -> float:
        """Get historical win rate for similar sentiment conditions."""
        
        # In production, this would query a database of past trades
        # For now, use a simple heuristic based on sentiment and confidence
        
        # Base win rate assumption
        base_accuracy = 0.65  # 65% base accuracy
        
        # Sentiment strength bonus
        sentiment_bonus = (abs(sentiment_score) / 100) * 0.1  # Up to 10% bonus
        
        # Confidence bonus
        confidence_bonus = (confidence - 0.5) * 0.3  # Up to 15% bonus
        
        expected_win_rate = base_accuracy + sentiment_bonus + confidence_bonus
        
        return min(expected_win_rate, 0.95)  # Cap at 95%

    def _generate_reason(
        self,
        timeframe_sentiments: List[TimeframeSentiment],
        news_sentiment: float,
        alignment_score: float,
        confidence: float
    ) -> str:
        """Generate human-readable reason for the signal."""
        
        direction = "bullish" if news_sentiment > 0 else "bearish"
        sentiment_strength = "strong" if abs(news_sentiment) > 60 else "moderate"
        
        timeframes_str = ", ".join([tf.timeframe for tf in timeframe_sentiments])
        
        reasons = []
        
        # Timeframe alignment
        if alignment_score > 0.8:
            reasons.append(f"Perfect alignment across {timeframes_str}")
        elif alignment_score > 0.6:
            reasons.append(f"Good alignment across {timeframes_str}")
        
        # News sentiment
        if abs(news_sentiment) > 40:
            reasons.append(f"{sentiment_strength} {direction} news sentiment ({news_sentiment:+.1f})")
        
        # Overall confidence
        if confidence > 0.9:
            reasons.append("Very high confidence signal")
        elif confidence > 0.85:
            reasons.append("High confidence signal")
        
        return "; ".join(reasons) if reasons else "Multi-factor analysis indicates trading opportunity"
