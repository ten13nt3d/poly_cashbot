"""Temporal Arbitrage Detection Engine for >98% Win Rate."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple, Dict, Any

from src.lib.exceptions import InsufficientDataError, LowConfidenceError


@dataclass
class TemporalArbitrageOpportunity:
    """Temporal arbitrage opportunity between spot and prediction markets."""
    direction: str  # "BUY" or "SELL"
    spot_momentum: float  # -100 to +100 from spot exchanges
    polymarket_lag: float  # Seconds of delay on Polymarket
    implied_probability: float  # Real probability from spot price
    polymarket_price: float  # Current Polymarket price
    certainty_gap: float  # Difference in certainty
    confidence: float  # Confidence in arbitrage opportunity
    expected_win_rate: float  # Expected win rate (should be >95%)
    urgency: str  # "HIGH", "MEDIUM", "LOW" based on lag size


@dataclass
class TimeframeSentiment:
    """Sentiment data for a specific timeframe."""
    timeframe: str  # "15m", "1h", "4h"
    price_momentum: float  # -100 to +100
    volume_confirmation: float  # 0.0 to 1.0
    trend_strength: float  # -1.0 to +1.0
    volatility: float  # Annualized volatility
    timestamp: datetime


class TemporalArbitrageDetector:
    """
    Temporal arbitrage detector focused on price lag between spot and prediction markets.
    
    Key Strategy:
    1. Monitor real-time spot price momentum (Binance + Coinbase + Kraken)
    2. Compare with Polymarket pricing (15-minute markets)
    3. Trade when there's a 30+ second lag with strong momentum
    4. Target: 98% win rate by exploiting mispriced certainty
    
    NOT prediction - this is arbitrage:
    - When spot moves decisively, Polymarket pricing lags
    - Bot trades the lag, not predicting direction
    - Certainty is already >85%, but Polymarket shows 50/50
    """

    # Critical thresholds for 98% win rate
    MIN_SPOT_MOMENTUM = 15.0  # >15% momentum change
    MIN_POLYMARKET_LAG = 30.0  # 30+ seconds delay
    MIN_CERTAINTY_GAP = 30.0  # Certainty difference >30%
    MIN_IMPLIED_PROBABILITY = 75.0  # Real probability >75%
    
    # Risk management
    MAX_POSITION_SIZE_USD = 5000  # Consistent sizing
    TRADE_FREQUENCY = "15m"  # Only 15-minute markets
    ASSETS = ["BTC", "ETH", "SOL"]  # Target assets

    def __init__(self):
        """Initialize the temporal arbitrage detector."""
        self.spot_prices = {}  # Latest spot prices from exchanges
        self.polymarket_prices = {}  # Latest Polymarket prices
        self.last_updated = {}  # Timestamp tracking for lag detection
        self.historical_opportunities = []  # Track successful arbitrage

    def detect_arbitrage_opportunity(
        self,
        spot_data: Dict[str, Any],
        polymarket_data: Dict[str, Any],
        asset: str
    ) -> Optional[TemporalArbitrageOpportunity]:
        """
        Detect temporal arbitrage opportunities between spot and prediction markets.
        
        Args:
            spot_data: Real-time spot price data
            polymarket_data: Polymarket market data
            asset: Asset being analyzed (BTC/ETH/SOL)
            
        Returns:
            Arbitrage opportunity if criteria met, None otherwise
        """
        if asset not in self.ASSETS:
            return None  # Only trade target assets
            
        # Update price tracking
        current_time = datetime.now()
        self.spot_prices[asset] = spot_data
        self.polymarket_prices[asset] = polymarket_data
        
        # Check if we have both data sources
        if not spot_data.get('price') or not polymarket_data.get('price'):
            return None
            
        # Calculate spot momentum (last 5 minutes)
        spot_momentum = self._calculate_spot_momentum(asset)
        
        # Check for sufficient momentum
        if abs(spot_momentum) < self.MIN_SPOT_MOMENTUM:
            return None  # Not enough momentum for arbitrage
            
        # Calculate implied probability from spot
        implied_prob = self._calculate_implied_probability(spot_momentum)
        
        # Get Polymarket price and calculate its implied probability
        poly_price = polymarket_data['price']
        poly_prob = 1.0 / (1.0 + poly_price) if poly_price > 0 else 0.5
        
        # Calculate certainty gap
        certainty_gap = abs(implied_prob - poly_prob) * 100
        
        # Check sufficient certainty gap
        if certainty_gap < self.MIN_CERTAINTY_GAP:
            return None  # Not enough mispricing
            
        # Check implied probability is high enough
        if implied_prob < self.MIN_IMPLIED_PROBABILITY / 100:
            return None  # Not certain enough
            
        # Calculate timing lag
        lag_seconds = self._calculate_lag(asset, current_time)
        
        # Check sufficient lag
        if lag_seconds < self.MIN_POLYMARKET_LAG:
            return None  # Lag too small
            
        # Determine urgency based on lag
        if lag_seconds > 60:
            urgency = "HIGH"
        elif lag_seconds > 45:
            urgency = "MEDIUM"
        else:
            urgency = "LOW"
            
        # Determine trade direction
        direction = "BUY" if implied_prob > 0.5 else "SELL"
        
        # Calculate confidence (very high for temporal arbitrage)
        confidence = min(0.98, 0.90 + (certainty_gap / 100))
        
        # Expected win rate (should be very high)
        expected_win_rate = 0.95 + (confidence - 0.90) * 0.5
        
        # Create opportunity
        opportunity = TemporalArbitrageOpportunity(
            direction=direction,
            spot_momentum=spot_momentum,
            polymarket_lag=lag_seconds,
            implied_probability=implied_prob * 100,
            polymarket_price=poly_price,
            certainty_gap=certainty_gap,
            confidence=confidence,
            expected_win_rate=expected_win_rate,
            urgency=urgency
        )
        
        # Track for learning
        self.historical_opportunities.append({
            'timestamp': current_time,
            'opportunity': opportunity,
            'spot_momentum': spot_momentum,
            'lag_seconds': lag_seconds
        })
        
        return opportunity

    def _calculate_spot_momentum(self, asset: str) -> float:
        """Calculate spot price momentum from real-time data."""
        # Simple momentum calculation (would integrate with real exchanges)
        if asset not in self.spot_prices:
            return 0.0
        spot_data = self.spot_prices[asset]
        prices = spot_data.get('prices', [])
        if len(prices) < 5:
            return 0.0
            
        # 5-minute momentum calculation
        recent_prices = prices[-5:]
        start_price = recent_prices[0]
        end_price = recent_prices[-1]
        
        if start_price == 0:
            return 0.0
            
        momentum = ((end_price - start_price) / start_price) * 100
        return momentum

    def _calculate_implied_probability(self, momentum: float) -> float:
        """Convert momentum to implied probability."""
        # Simple conversion: momentum -> probability
        # If momentum is >20%, probability approaches 100%
        # If momentum is <-20%, probability approaches 0%
        
        # Normalize momentum to 0-1 range
        normalized = max(-20, min(20, momentum)) / 20
        probability = (normalized + 1) / 2
        
        return probability

    def _calculate_lag(self, asset: str, current_time: datetime) -> float:
        """Calculate timing lag between spot and Polymarket."""
        last_spot_time = self.last_updated.get(f'{asset}_spot', current_time)
        last_poly_time = self.last_updated.get(f'{asset}_poly', current_time)
        
        spot_age = (current_time - last_spot_time).total_seconds()
        poly_age = (current_time - last_poly_time).total_seconds()
        
        # Lag is the difference in freshness
        lag = poly_age - spot_age
        
        return max(0, lag)  # Can't be negative

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
