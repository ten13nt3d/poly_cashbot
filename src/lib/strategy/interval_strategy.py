"""15-Minute Interval Trading Strategy with >70% Win Rate Target."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any

from src.lib.exceptions import StrategyError, TradingError
# Simple logger fallback
import logging
def get_logger(name):
    return logging.getLogger(name)

logger = get_logger(__name__)


@dataclass
class Position:
    """Open trading position."""
    market_id: str
    side: str  # "buy" or "sell"
    size: Decimal
    entry_price: Decimal
    entry_sentiment: float
    entry_confidence: float
    opened_at: datetime
    unrealized_pnl: Decimal = Decimal("0")
    status: str = "open"  # "open", "closed", "stopped"

    @property
    def age_minutes(self) -> float:
        """Calculate position age in minutes."""
        age_seconds = (datetime.now() - self.opened_at).total_seconds()
        return age_seconds / 60.0


@dataclass
class ExitStrategy:
    """Strategy for exiting a position."""
    type: str  # "TAKE_PROFIT", "STOP_LOSS", "EXIT_TIME", "EXIT_NOW", "HOLD"
    reason: str
    target_price: Optional[Decimal] = None
    hold_until: Optional[datetime] = None
    stop_loss_pct: Optional[float] = None


class IntervalStrategy:
    """
    High win rate 15-minute interval trading strategy.
    
    Optimized for >70% win rate through:
    1. Ultra-selective signal filtering (only >80% confidence)
    2. Strong signal requirements (sentiment magnitude >40)
    3. Multi-confirmation system
    4. Dynamic exit optimization (not fixed 15min)
    5. Quick profit taking (10-15% ROI target)
    6. Fast stop losses
    
    Capital Agnostic:
    - Works with $10 to $1000+
    - Position sizes scale with capital
    - Risk limits adapt to capital tier
    """

    # Ultra-selective thresholds
    MIN_CONFIDENCE = 0.80  # Only trade 80%+ confidence
    MIN_SENTIMENT_MAGNITUDE = 40  # Strong signals only
    TARGET_WIN_RATE = 0.70  # Target win rate
    MIN_LIQUIDITY_USD = Decimal("10000")  # Minimum market liquidity

    # Position management
    TARGET_PROFIT_PCT = 0.15  # 15% ROI target
    MIN_HOLD_MINUTES = 3  # Hold at least 3 minutes
    MAX_HOLD_MINUTES = 25  # Hold max 25 minutes
    DEFAULT_HOLD_MINUTES = 15  # Default 15-minute window

    # Risk management
    MAX_CONSECUTIVE_LOSSES = 3  # Stop trading after 3 losses
    MIN_WIN_RATE_PCT = 0.65  # Minimum win rate threshold
    MAX_POSITIONS = 3  # Maximum concurrent positions

    def __init__(self, trade_history: Optional[List[Dict]] = None):
        """Initialize interval strategy."""
        self.open_positions: List[Position] = []
        self.trade_history = trade_history or []
        self.recent_trades = []  # Last 20 trades
        self.total_trades = 0
        self.winning_trades = 0
        self.consecutive_losses = 0

    def should_trade(
        self,
        signal_confidence: float,
        sentiment_score: float,
        expected_win_rate: float,
        market_liquidity: float,
        capital_available: Decimal
    ) -> bool:
        """
        Ultra-selective trade filter.
        
        Returns True if trade meets all criteria for high win rate.
        """
        # 1. Confidence check
        if signal_confidence < self.MIN_CONFIDENCE:
            logger.debug(
                "Reject trade: low confidence",
                confidence=signal_confidence,
                required=self.MIN_CONFIDENCE
            )
            return False

        # 2. Sentiment strength check
        if abs(sentiment_score) < self.MIN_SENTIMENT_MAGNITUDE:
            logger.debug(
                "Reject trade: weak sentiment",
                sentiment=sentiment_score,
                required=self.MIN_SENTIMENT_MAGNITUDE
            )
            return False

        # 3. Expected win rate check
        if expected_win_rate < 0.65:
            logger.debug(
                "Reject trade: low expected win rate",
                win_rate=expected_win_rate
            )
            return False

        # 4. Market liquidity check
        if market_liquidity < self.MIN_LIQUIDITY_USD:
            logger.debug(
                "Reject trade: insufficient liquidity",
                liquidity=float(market_liquidity),
                required=float(self.MIN_LIQUIDITY_USD)
            )
            return False

        # 5. Position count check
        if len(self.open_positions) >= self.MAX_POSITIONS:
            logger.debug(
                "Reject trade: too many positions",
                current=len(self.open_positions),
                max=self.MAX_POSITIONS
            )
            return False

        # 6. Recent performance check (stop if performing poorly)
        if not self._check_recent_performance():
            logger.info(
                "Pause trading: poor recent performance",
                win_rate=self._calculate_recent_win_rate()
            )
            return False

        return True

    def calculate_position_size(
        self,
        confidence: float,
        capital_available: Decimal,
        risk_percentage: float = 0.03
    ) -> Decimal:
        """
        Calculate position size based on confidence and capital.
        
        Args:
            confidence: Signal confidence (0.0 to 1.0)
            capital_available: Total capital available
            risk_percentage: Risk per trade percentage
            
        Returns:
            Position size in USD
        """
        # Base position size
        base_size = capital_available * Decimal(str(risk_percentage))

        # Confidence multiplier (scale 0.8 to 1.5)
        confidence_multiplier = 0.5 + (confidence * 1.0)
        adjusted_size = base_size * Decimal(str(confidence_multiplier))

        # Ensure minimum position based on capital
        if capital_available < Decimal("50"):
            min_position = Decimal("5.00")
        elif capital_available < Decimal("200"):
            min_position = Decimal("10.00")
        else:
            min_position = capital_available * Decimal("0.02")

        # Ensure maximum position (10% of capital)
        max_position = capital_available * Decimal("0.10")

        return max(min(adjusted_size, max_position), min_position)

    def create_position(
        self,
        market_id: str,
        side: str,
        size: Decimal,
        entry_price: Decimal,
        sentiment_score: float,
        confidence: float
    ) -> Position:
        """Create a new trading position."""
        position = Position(
            market_id=market_id,
            side=side,
            size=size,
            entry_price=entry_price,
            entry_sentiment=sentiment_score,
            entry_confidence=confidence,
            opened_at=datetime.now()
        )
        
        self.open_positions.append(position)
        logger.info(
            "Position opened",
            market_id=market_id,
            side=side,
            size=float(size),
            price=float(entry_price)
        )
        
        return position

    def calculate_exit_strategy(
        self,
        position: Position,
        current_price: Decimal,
        current_sentiment: float,
        market_volatility: float
    ) -> ExitStrategy:
        """
        Dynamic exit strategy based on multiple factors.
        
        Args:
            position: Current position
            current_price: Current market price
            current_sentiment: Current sentiment score
            market_volatility: Current market volatility
            
        Returns:
            Exit strategy for the position
        """
        # Calculate current P&L
        if position.side == "buy":
            pnl_pct = float((current_price - position.entry_price) / position.entry_price)
        else:  # sell
            pnl_pct = float((position.entry_price - current_price) / position.entry_price)
        
        position.unrealized_pnl = Decimal(str(pnl_pct)) * position.size

        # 1. Take profit if target reached
        if pnl_pct >= self.TARGET_PROFIT_PCT:
            return ExitStrategy(
                type="TAKE_PROFIT",
                reason=f"Target profit reached: {pnl_pct:.1%}"
            )

        # 2. Check if position is continuing to favor
        if self._is_trending_favorable(position.side, current_sentiment):
            # Extend hold time from 15 to 25 minutes
            if position.age_minutes < self.MIN_HOLD_MINUTES:
                target_hold = self.DEFAULT_HOLD_MINUTES
            else:
                target_hold = self.MAX_HOLD_MINUTES

            return ExitStrategy(
                type="HOLD",
                reason=f"Trend still favorable, holding until {target_hold} minutes",
                hold_until=position.opened_at + timedelta(minutes=target_hold)
            )

        # 3. Early exit if sentiment reverses
        if self._sentiment_reversed(position.entry_sentiment, current_sentiment):
            return ExitStrategy(
                type="EXIT_NOW",
                reason="Sentiment reversal detected"
            )

        # 4. Time-based exit
        if position.age_minutes >= self.DEFAULT_HOLD_MINUTES:
            return ExitStrategy(
                type="EXIT_TIME",
                reason="15-minute window closed"
            )

        # 5. Dynamic stop-loss based on volatility
        stop_loss_pct = self._calculate_dynamic_stop_loss(market_volatility)
        if pnl_pct <= -stop_loss_pct:
            return ExitStrategy(
                type="STOP_LOSS",
                reason=f"Stop loss at {stop_loss_pct:.1%}",
                stop_loss_pct=stop_loss_pct
            )

        # 6. Default: hold
        return ExitStrategy(
            type="HOLD",
            reason="Position within parameters, continuing to hold"
        )

    @property
    def age_minutes(self) -> float:
        """Calculate position age in minutes."""
        return (datetime.now() - self.opened_at).total_seconds() / 60.0

    def _is_trending_favorable(self, side: str, current_sentiment: float) -> bool:
        """Check if sentiment continues to favor the position."""
        if side == "buy":
            return current_sentiment > 20  # Still bullish
        else:  # sell
            return current_sentiment < -20  # Still bearish

    def _sentiment_reversed(self, entry_sentiment: float, current_sentiment: float) -> bool:
        """Check if sentiment has reversed direction."""
        # If both were bullish and now bearish (or vice versa)
        if entry_sentiment > 40 and current_sentiment < -20:
            return True
        if entry_sentiment < -40 and current_sentiment > 20:
            return True
        return False

    def _calculate_dynamic_stop_loss(self, volatility: float) -> float:
        """Calculate dynamic stop loss based on market volatility."""
        # Base stop loss
        base_stop = 0.08  # 8%
        
        # Adjust for volatility (higher vol = wider stop)
        volatility_adj = volatility * 0.5
        
        stop_loss = base_stop + volatility_adj
        
        # Cap at 20%
        return min(stop_loss, 0.20)

    def _check_recent_performance(self) -> bool:
        """Check if recent performance meets minimum criteria."""
        win_rate = self._calculate_recent_win_rate()
        
        if win_rate < self.MIN_WIN_RATE_PCT:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0
        
        # Pause after 3 consecutive losses or very low win rate
        if self.consecutive_losses >= 3 or win_rate < 0.5:
            return False
        
        return True

    def _calculate_recent_win_rate(self, trades_window: int = 20) -> float:
        """Calculate win rate for recent trades."""
        recent_trades = self.trade_history[-trades_window:] if len(self.trade_history) >= trades_window else self.trade_history
        
        if not recent_trades:
            return 0.0
        
        wins = sum(1 for trade in recent_trades if trade.get('pnl', 0) > 0)
        return wins / len(recent_trades)

    def close_position(
        self,
        position: Position,
        exit_price: Decimal,
        exit_reason: str
    ) -> Dict[str, Any]:
        """
        Close a position and record the trade.
        
        Returns:
            Trade record with all details
        """
        # Calculate P&L
        if position.side == "buy":
            pnl = (exit_price - position.entry_price) * position.size
        else:  # sell
            pnl = (position.entry_price - exit_price) * position.size
        
        # Calculate ROI percentage
        roi_pct = float(pnl / position.size) if position.size > 0 else 0
        
        # Update position
        position.status = "closed"
        
        # Create trade record
        trade = {
            'market_id': position.market_id,
            'side': position.side,
            'size': float(position.size),
            'entry_price': float(position.entry_price),
            'exit_price': float(exit_price),
            'entry_sentiment': position.entry_sentiment,
            'entry_confidence': position.entry_confidence,
            'opened_at': position.opened_at,
            'closed_at': datetime.now(),
            'pnl': float(pnl),
            'roi_pct': roi_pct,
            'exit_reason': exit_reason,
            'hold_minutes': position.age_minutes
        }
        
        # Update history
        self.trade_history.append(trade)
        self.recent_trades = self.trade_history[-20:]  # Keep last 20
        
        # Update statistics
        self.total_trades += 1
        if pnl > 0:
            self.winning_trades += 1
            self.consecutive_losses = 0
        else:
            self.consecutive_losses += 1
        
        # Remove from open positions
        if position in self.open_positions:
            self.open_positions.remove(position)
        
        logger.info(
            "Position closed",
            market_id=position.market_id,
            side=position.side,
            pnl=float(pnl),
            roi_pct=roi_pct,
            reason=exit_reason
        )
        
        return trade

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get comprehensive performance metrics."""
        if not self.trade_history:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'total_pnl': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0,
                'profit_factor': 0.0,
                'consecutive_losses': 0,
                'open_positions': len(self.open_positions)
            }
        
        winning_trades = [t for t in self.trade_history if t['pnl'] > 0]
        losing_trades = [t for t in self.trade_history if t['pnl'] < 0]
        
        total_pnl = sum(t['pnl'] for t in self.trade_history)
        
        avg_win = sum(t['pnl'] for t in winning_trades) / len(winning_trades) if winning_trades else 0
        avg_loss = sum(abs(t['pnl']) for t in losing_trades) / len(losing_trades) if losing_trades else 0
        
        gross_profit = sum(t['pnl'] for t in winning_trades)
        gross_loss = sum(abs(t['pnl']) for t in losing_trades)
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Expected value per trade
        ev_per_trade = (self.win_rate * avg_win) - ((1 - self.win_rate) * avg_loss)
        
        return {
            'total_trades': self.total_trades,
            'winning_trades': len(winning_trades),
            'losing_trades': len(losing_trades),
            'win_rate': self.winning_trades / self.total_trades if self.total_trades > 0 else 0,
            'total_pnl': total_pnl,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'ev_per_trade': ev_per_trade,
            'profit_factor': profit_factor,
            'consecutive_losses': self.consecutive_losses,
            'open_positions': len(self.open_positions),
            'avg_hold_minutes': sum(t['hold_minutes'] for t in self.trade_history) / len(self.trade_history) if self.trade_history else 0
        }

    @property
    def win_rate(self) -> float:
        """Current win rate."""
        if self.total_trades == 0:
            return 0.0
        return self.winning_trades / self.total_trades
