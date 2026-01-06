"""Whale detection and front-running system."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Dict, Any

from src.lib.exceptions import WhaleDetectionError, LiquidityInsufficientError
# Simple logger fallback
import logging
def get_logger(name):
    return logging.getLogger(name)

logger = get_logger(__name__)


@dataclass
class WhaleAlert:
    """Alert when a whale is detected."""
    market_id: str
    order_size: Decimal
    side: str  # "buy" or "sell"
    relative_size: float  # Relative to average
    wallet_address: Optional[str] = None
    detected_at: datetime = None
    expected_impact: float = 0.0  # Expected price impact percentage
    confidence: float = 0.0  # Confidence in whale detection


@dataclass
class OrderbookSnapshot:
    """Snapshot of orderbook state."""
    bids: List[Dict[str, Any]]  # List of {price, size}
    asks: List[Dict[str, Any]]
    timestamp: datetime
    market_id: str


class WhaleDetector:
    """
    Detects large orders (whales) and provides front-running opportunities.
    
    Detects whales based on:
    1. Order size relative to historical average
    2. Sudden depth changes in orderbook
    3. Known whale wallet addresses
    4. Rapid accumulation patterns
    
    Strategy:
    1. Monitor orderbook for large orders (>10x average)
    2. Calculate expected market impact
    3. Execute front-run if impact >2%
    4. Position size scales with whale size
    """

    # Detection thresholds
    WHALE_SIZE_MULTIPLIER = 10.0  # Order >10x average size
    MIN_ORDER_VALUE_USD = Decimal("10000")  # Minimum $10k value
    MIN_DEPTH_CHANGE_PCT = 0.20  # 20% depth change trigger
    MIN_LIQUIDITY_USD = Decimal("10000")  # Minimum market liquidity
    
    # Front-running parameters
    MIN_IMPACT_THRESHOLD = 0.02  # 2% minimum expected impact
    FRONT_RUN_CONFIDENCE = 0.85  # High confidence on whale signals
    MAX_POSITION_PCT = 0.05  # Max 5% of capital per front-run
    
    def __init__(self, market_id: str, min_history_samples: int = 50):
        """
        Initialize whale detector.
        
        Args:
            market_id: Market identifier
            min_history_samples: Minimum samples for statistical baseline
        """
        self.market_id = market_id
        self.min_history_samples = min_history_samples
        
        # Historical data for baseline calculations
        self.order_size_history: List[Decimal] = []
        self.orderbook_depth_history: List[Decimal] = []
        self.recent_whales: List[WhaleAlert] = []
        
        # Known whale wallets (would be populated from on-chain data)
        self.known_whale_wallets: set[str] = set()
        
        # Statistics
        self.average_order_size = Decimal("0")
        self.average_depth = Decimal("0")

    def add_known_whale_wallet(self, wallet_address: str):
        """Add a wallet address to known whales list."""
        self.known_whale_wallets.add(wallet_address.lower())
        logger.info("Added whale wallet", wallet=wallet_address[:8] + "...")

    def update_orderbook_snapshot(self, snapshot: OrderbookSnapshot) -> List[WhaleAlert]:
        """
        Analyze new orderbook snapshot for whale activity.
        
        Args:
            snapshot: Current orderbook state
            
        Returns:
            List of whale alerts detected
        """
        alerts = []
        
        try:
            # 1. Check for large orders in current orderbook
            large_order_alerts = self._detect_large_orders(snapshot)
            alerts.extend(large_order_alerts)
            
            # 2. Check for sudden depth changes
            depth_change_alerts = self._detect_depth_changes(snapshot)
            alerts.extend(depth_change_alerts)
            
            # 3. Update historical data
            self._update_historical_data(snapshot)
            
            # 4. Filter and enhance alerts
            filtered_alerts = self._filter_alerts(alerts)
            
            # 5. Store recent whale alerts
            self.recent_whales.extend(filtered_alerts)
            
            # 6. Clean old alerts (keep last 100)
            if len(self.recent_whales) > 100:
                self.recent_whales = self.recent_whales[-100:]
            
            return filtered_alerts
            
        except Exception as e:
            logger.error(f"Error detecting whales: {e}")
            raise WhaleDetectionError(f"Failed to detect whales: {e}")

    def _detect_large_orders(self, snapshot: OrderbookSnapshot) -> List[WhaleAlert]:
        """Detect orders larger than historical average."""
        alerts = []
        
        # Calculate average order size if we have enough history
        if len(self.order_size_history) < self.min_history_samples:
            return alerts  # Not enough data to establish baseline
        
        self.average_order_size = sum(self.order_size_history) / len(self.order_size_history)
        
        # Check bids
        for bid in snapshot.bids:
            order_size = Decimal(str(bid['size']))
            if order_size > self.average_order_size * Decimal(str(self.WHALE_SIZE_MULTIPLIER)):
                relative_size = float(order_size / self.average_order_size)
                
                alert = WhaleAlert(
                    market_id=self.market_id,
                    order_size=order_size,
                    side="buy",
                    relative_size=relative_size,
                    detected_at=snapshot.timestamp,
                    confidence=0.8  # Base confidence
                )
                alerts.append(alert)
        
        # Check asks
        for ask in snapshot.asks:
            order_size = Decimal(str(ask['size']))
            if order_size > self.average_order_size * Decimal(str(self.WHALE_SIZE_MULTIPLIER)):
                relative_size = float(order_size / self.average_order_size)
                
                alert = WhaleAlert(
                    market_id=self.market_id,
                    order_size=order_size,
                    side="sell",
                    relative_size=relative_size,
                    detected_at=snapshot.timestamp,
                    confidence=0.8
                )
                alerts.append(alert)
        
        return alerts

    def _detect_depth_changes(self, snapshot: OrderbookSnapshot) -> List[WhaleAlert]:
        """Detect sudden changes in orderbook depth. """
        alerts = []
        
        if len(self.orderbook_depth_history) < 10:
            return alerts  # Not enough history
        
        # Calculate current depth (sum of sizes on both sides)
        current_depth = self._calculate_orderbook_depth(snapshot)
        recent_depths = self.orderbook_depth_history[-10:]
        avg_recent_depth = sum(recent_depths) / len(recent_depths)
        
        if avg_recent_depth == 0:
            return alerts
        
        # Calculate percentage change
        depth_change_pct = abs(float((current_depth - avg_recent_depth) / avg_recent_depth))
        
        if depth_change_pct > self.MIN_DEPTH_CHANGE_PCT:
            # Create alert for significant depth change
            side = "buy" if current_depth > avg_recent_depth else "sell"
            
            alert = WhaleAlert(
                market_id=self.market_id,
                order_size=current_depth - avg_recent_depth,  # Size of change
                side=side,
                relative_size=depth_change_pct,
                detected_at=snapshot.timestamp,
                confidence=0.75,  # Slightly lower confidence for depth changes
                expected_impact=depth_change_pct * 0.5  # Rough impact estimate
            )
            alerts.append(alert)
        
        return alerts

    def _calculate_orderbook_depth(self, snapshot: OrderbookSnapshot) -> Decimal:
        """Calculate total depth of orderbook."""
        bid_depth = sum(Decimal(str(bid['size'])) for bid in snapshot.bids)
        ask_depth = sum(Decimal(str(ask['size'])) for ask in snapshot.asks)
        return bid_depth + ask_depth

    def _update_historical_data(self, snapshot: OrderbookSnapshot):
        """Update historical data with current snapshot."""
        # Store order sizes from current snapshot
        for bid in snapshot.bids:
            self.order_size_history.append(Decimal(str(bid['size'])))
        for ask in snapshot.asks:
            self.order_size_history.append(Decimal(str(ask['size'])))
        
        # Store orderbook depth
        current_depth = self._calculate_orderbook_depth(snapshot)
        self.orderbook_depth_history.append(current_depth)
        
        # Trim history to last 1000 samples
        if len(self.order_size_history) > 1000:
            self.order_size_history = self.order_size_history[-1000:]
        if len(self.orderbook_depth_history) > 1000:
            self.orderbook_depth_history = self.orderbook_depth_history[-1000:]

    def _filter_alerts(self, alerts: List[WhaleAlert]) -> List[WhaleAlert]:
        """
        Filter and enhance whale alerts.
        
        Filters by:
        1. minimum order value
        2. market liquidity
        3. expected impact
        4. confidence scoring
        """
        filtered = []
        
        for alert in alerts:
            # Check minimum order value
            if alert.order_size < self.MIN_ORDER_VALUE_USD:
                continue
            
            # Calculate expected impact
            alert.expected_impact = self._estimate_price_impact(alert)
            
            # Skip if impact is too small
            if alert.expected_impact < self.MIN_IMPACT_THRESHOLD:
                continue
            
            # Enhance confidence based on multiple factors
            alert.confidence = self._calculate_whale_confidence(alert)
            
            # Only keep high-confidence alerts
            if alert.confidence >= 0.7:
                filtered.append(alert)
        
        return sorted(filtered, key=lambda a: a.confidence, reverse=True)

    def _estimate_price_impact(self, alert: WhaleAlert) -> float:
        """
        Estimate expected price impact of whale order.
        
        Simple model: larger relative size = larger impact
        Scale: 10x relative = ~2% impact
        """
        # Base impact calculation
        if alert.relative_size > 50:  # Very large whale
            return 0.05  # 5% impact
        elif alert.relative_size > 20:  # Large whale
            return 0.03  # 3% impact
        else:
            return 0.02  # 2% impact minimum for whale triggers

    def _calculate_whale_confidence(self, alert: WhaleAlert) -> float:
        """Calculate confidence score for whale detection."""
        confidence = 0.5  # Base confidence
        
        # Size factor (larger = more confident)
        if alert.relative_size > 50:
            confidence += 0.3
        elif alert.relative_size > 20:
            confidence += 0.2
        elif alert.relative_size > 10:
            confidence += 0.1
        
        # Known whale factor
        if alert.wallet_address and alert.wallet_address.lower() in self.known_whale_wallets:
            confidence += 0.2
        
        # Depth change factor
        if alert.expected_impact > 0.03:
            confidence += 0.1
        
        return min(confidence, 0.95)  # Cap at 95%

    def get_recent_whales(self, minutes: int = 60) -> List[WhaleAlert]:
        """
        Get whale alerts from recent time period.
        
        Args:
            minutes: Lookback period in minutes
            
        Returns:
            List of recent whale alerts
        """
        cutoff = datetime.now() - timedelta(minutes=minutes)
        return [w for w in self.recent_whales if w.detected_at >= cutoff]

    def is_liquidity_sufficient(self, snapshot: OrderbookSnapshot) -> bool:
        """
        Check if market has sufficient liquidity for trading.
        
        Args:
            snapshot: Current orderbook snapshot
            
        Returns:
            True if liquidity is sufficient
        """
        total_liquidity = self._calculate_orderbook_depth(snapshot)
        return total_liquidity >= self.MIN_LIQUIDITY_USD

    def calculate_front_run_position_size(
        self,
        whale_alert: WhaleAlert,
        available_capital: Decimal
    ) -> Decimal:
        """
        Calculate position size for front-running a whale.
        
        Args:
            whale_alert: Whale detection alert
            available_capital: Capital available for position
            
        Returns:
            Recommended position size
        """
        # Calculate base position (1-3% of capital based on whale size)
        base_pct = min(whale_alert.relative_size / 30.0, 0.03)  # Max 3%
        base_position = available_capital * Decimal(str(base_pct))
        
        # Adjust by expected impact
        impact_adjustment = whale_alert.expected_impact / 0.02  # Normalize to 2%
        adjusted_position = base_position * Decimal(str(impact_adjustment))
        
        # Apply maximum limit
        max_position = available_capital * Decimal(str(self.MAX_POSITION_PCT))
        
        return min(adjusted_position, max_position)

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get whale detection statistics.
        
        Returns:
            Dictionary with detection stats
        """
        recent_whales = self.get_recent_whales(minutes=60 * 24)  # Last 24 hours
        
        return {
            "average_order_size": float(self.average_order_size),
            "whales_detected_24h": len(recent_whales),
            "avg_confidence_24h": sum(w.confidence for w in recent_whales) / max(len(recent_whales), 1),
            "avg_impact_24h": sum(w.expected_impact for w in recent_whales) / max(len(recent_whales), 1),
            "known_whale_wallets": len(self.known_whale_wallets)
        }
