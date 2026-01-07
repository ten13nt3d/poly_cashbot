"""Scalable Risk Management System for $10-$1000+ Capital."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from src.lib.exceptions import RiskLimitExceeded, TradingError
# Simple logger fallback
import logging
def get_logger(name):
    return logging.getLogger(name)

logger = get_logger(__name__)


@dataclass
class RiskCheck:
    """Result of a risk validation check."""
    passed: bool
    reason: Optional[str] = None
    maximum_size: Optional[Decimal] = None
    risk_percentage: Optional[float] = None


@dataclass
class DailyRiskMetrics:
    """Daily risk tracking metrics."""
    date: datetime
    total_pnl: Decimal
    total_trades: int
    winning_trades: int
    max_drawdown: Decimal
    consecutive_losses: int


class ScalableRiskManager:
    """
    Risk management system that adapts to any capital size ($10-$1000+).
    
    Features:
    1. Capital tier system with different risk parameters
    2. Dynamic position sizing based on confidence and capital
    3. Daily loss limits and per-trade risk controls
    4. Win rate protection (pause trading if performing poorly)
    5. Drawdown monitoring and position limits
    6. Real-time risk breach alerts
    
    Capital Tiers:
    - Micro: $10-$50 (higher risk for growth)
    - Small: $50-$200 (moderate risk)
    - Medium: $200-$1000 (conservative risk)
    - Large: $1000+ (institutional risk)
    """

    # Capital tier definitions
    CAPITAL_TIERS = {
        "micro": (Decimal("0"), Decimal("50")),        # $0-$50
        "small": (Decimal("50"), Decimal("200")),      # $50-$200
        "medium": (Decimal("200"), Decimal("1000")),   # $200-$1000
        "large": (Decimal("1000"), Decimal("999999"))  # $1000+
    }

    # Risk parameters by tier
    RISK_PARAMS = {
        "micro": {
            "per_trade_risk": 0.10,  # 10% per trade (needs to grow)
            "daily_loss_limit": 0.20,  # 20% daily loss limit
            "max_positions": 2,  # 2 concurrent positions
            "min_position_size": Decimal("5.00"),  # $5 minimum
            "max_single_position": Decimal("10.00"),  # $10 max
            "win_rate_threshold": 0.60  # 60% minimum (more lenient)
        },
        "small": {
            "per_trade_risk": 0.05,  # 5% per trade
            "daily_loss_limit": 0.15,  # 15% daily loss limit
            "max_positions": 3,
            "min_position_size": Decimal("10.00"),
            "max_single_position": Decimal("25.00"),
            "win_rate_threshold": 0.65
        },
        "medium": {
            "per_trade_risk": 0.03,  # 3% per trade
            "daily_loss_limit": 0.10,  # 10% daily loss limit
            "max_positions": 4,
            "min_position_size": Decimal("20.00"),
            "max_single_position": Decimal("100.00"),
            "win_rate_threshold": 0.65
        },
        "large": {
            "per_trade_risk": 0.02,  # 2% per trade (most conservative)
            "daily_loss_limit": 0.10,  # 10% daily loss limit
            "max_positions": 5,
            "min_position_size": Decimal("50.00"),
            "max_single_position": Decimal("500.00"),
            "win_rate_threshold": 0.70  # Strictest threshold
        }
    }

    def __init__(self, total_capital: Decimal):
        """
        Initialize risk manager with capital.
        
        Args:
            total_capital: Total trading capital
        """
        self.total_capital = total_capital
        self.tier = self._get_tier(total_capital)
        self.params = self.RISK_PARAMS[self.tier]
        
        # Track open positions and daily metrics
        self.open_positions = []
        self.daily_metrics = self._initialize_daily_metrics()
        
        # Track peak equity for drawdown calculation
        self.peak_equity = total_capital
        
        logger.info(
            f"Risk manager initialized - Capital: ${float(total_capital):.2f}, "
            f"Tier: {self.tier}, Per-trade risk: {self.params['per_trade_risk']}, "
            f"Daily limit: {self.params['daily_loss_limit']}"
        )

    def _get_tier(self, capital: Decimal) -> str:
        """Determine capital tier for given capital amount."""
        for tier, (min_cap, max_cap) in self.CAPITAL_TIERS.items():
            if min_cap <= capital < max_cap:
                return tier
        return "large"

    def _initialize_daily_metrics(self) -> DailyRiskMetrics:
        """Initialize daily risk tracking."""
        return DailyRiskMetrics(
            date=datetime.now().date(),
            total_pnl=Decimal("0"),
            total_trades=0,
            winning_trades=0,
            max_drawdown=Decimal("0"),
            consecutive_losses=0
        )

    def validate_order(
        self,
        order_size: Decimal,
        market_liquidity: Optional[Decimal] = None
    ) -> RiskCheck:
        """
        Validate order against risk limits.
        
        Args:
            order_size: Size of order in USD
            market_liquidity: Available market liquidity (optional)
            
        Returns:
            RiskCheck with validation result
        """
        # Check per-trade risk
        max_size = self.total_capital * Decimal(str(self.params["per_trade_risk"]))
        if order_size > max_size:
            return RiskCheck(
                passed=False,
                reason=f"Order size ${order_size:.2f} exceeds {self.tier} tier limit of ${max_size:.2f}",
                maximum_size=max_size,
                risk_percentage=self.params["per_trade_risk"]
            )

        # Check minimum position size
        if order_size < self.params["min_position_size"]:
            return RiskCheck(
                passed=False,
                reason=f"Order size ${order_size:.2f} below minimum of ${self.params['min_position_size']}"
            )

        # Check maximum single position
        if order_size > self.params["max_single_position"]:
            return RiskCheck(
                passed=False,
                reason=f"Order size ${order_size:.2f} exceeds maximum of ${self.params['max_single_position']}"
            )

        # Check daily loss limit
        daily_pnl = self.daily_metrics.total_pnl
        loss_limit = self.total_capital * Decimal(str(self.params["daily_loss_limit"]))
        if daily_pnl < -loss_limit:
            return RiskCheck(
                passed=False,
                reason=f"Daily loss ${abs(daily_pnl):.2f} exceeds limit of ${loss_limit:.2f}"
            )

        # Check maximum concurrent positions
        if len(self.open_positions) >= self.params["max_positions"]:
            return RiskCheck(
                passed=False,
                reason=f"Maximum {self.params['max_positions']} positions for {self.tier} tier"
            )

        # Check market liquidity (if provided)
        if market_liquidity and order_size > market_liquidity * Decimal("0.1"):
            return RiskCheck(
                passed=False,
                reason=f"Order size {order_size:.2f} exceeds 10% of market liquidity {market_liquidity:.2f}"
            )

        # Check win rate protection
        if not self._check_win_rate_protection():
            return RiskCheck(
                passed=False,
                reason=f"Win rate too low, trading paused for {self.tier} tier"
            )

        return RiskCheck(
            passed=True,
            maximum_size=max_size,
            risk_percentage=self.params["per_trade_risk"]
        )

    def calculate_position_size(
        self,
        signal_confidence: float,
        market_volatility: float = 0.15,
        risk_percentage: Optional[float] = None
    ) -> Decimal:
        """
        Calculate optimal position size based on multiple factors.
        
        Args:
            signal_confidence: Signal confidence (0.0 to 1.0)
            market_volatility: Current market volatility (normalized)
            risk_percentage: Override default risk percentage
            
        Returns:
            Recommended position size in USD
        """
        # Use tier-specific risk or override
        if risk_percentage is None:
            risk_pct = self.params["per_trade_risk"]
        else:
            risk_pct = min(risk_percentage, self.params["per_trade_risk"])

        # Base position size
        base_size = self.total_capital * Decimal(str(risk_pct))

        # Confidence scaling (0.8 confidence = 0.6x size, 0.95 confidence = 0.95x size)
        confidence_multiplier = max(signal_confidence - 0.2, 0.6)

        # Volatility adjustment (higher vol = smaller position)
        volatility_factor = max(1.0 - market_volatility, 0.5)

        # Calculate final position size
        adjusted_size = base_size * Decimal(str(confidence_multiplier)) * Decimal(str(volatility_factor))

        # Apply tier-specific bounds
        min_size = self.params["min_position_size"]
        max_size = self.params["max_single_position"]

        return max(min(adjusted_size, max_size), min_size)

    def calculate_dynamic_stop_loss(
        self,
        market_volatility: float,
        position_side: str
    ) -> Decimal:
        """
        Calculate dynamic stop-loss based on market conditions.
        
        Args:
            market_volatility: Current market volatility (0.0 to 1.0)
            position_side: "buy" or "sell"
            
        Returns:
            Stop-loss percentage as Decimal
        """
        # Base stop-loss by tier
        base_stop = {
            "micro": 0.15,   # 15% (wider stops for growth)
            "small": 0.12,   # 12%
            "medium": 0.10,  # 10%
            "large": 0.08    # 8% (tightest for large capital)
        }[self.tier]

        # Adjust for volatility (higher vol = wider stop)
        volatility_adj = market_volatility * 0.5

        stop_loss = Decimal(str(base_stop + volatility_adj))

        # Cap at reasonable limits
        return min(stop_loss, Decimal("0.20"))  # Max 20%

    def add_position(self, position_id: str, size: Decimal):
        """Add a new position to tracking."""
        self.open_positions.append({
            "id": position_id,
            "size": size,
            "opened_at": datetime.now()
        })

    def remove_position(self, position_id: str) -> bool:
        """Remove position from tracking (returns True if found)."""
        for i, pos in enumerate(self.open_positions):
            if pos["id"] == position_id:
                del self.open_positions[i]
                return True
        return False

    def update_daily_metrics(
        self,
        pnl: Decimal,
        is_win: bool,
        current_equity: Optional[Decimal] = None
    ):
        """
        Update daily risk metrics after trade completion.
        
        Args:
            pnl: Profit/loss from trade
            is_win: Whether trade was profitable
            current_equity: Current total equity
        """
        # Reset if new day
        if datetime.now().date() > self.daily_metrics.date:
            self.daily_metrics = self._initialize_daily_metrics()
            logger.info("Daily metrics reset", date=self.daily_metrics.date)

        # Update metrics
        self.daily_metrics.total_pnl += pnl
        self.daily_metrics.total_trades += 1
        if is_win:
            self.daily_metrics.winning_trades += 1
            self.daily_metrics.consecutive_losses = 0
        else:
            self.daily_metrics.consecutive_losses += 1

        # Update peak equity and calculate drawdown
        if current_equity is not None:
            if current_equity > self.peak_equity:
                self.peak_equity = current_equity
            
            current_dd = self.peak_equity - current_equity
            if current_dd > self.daily_metrics.max_drawdown:
                self.daily_metrics.max_drawdown = current_dd

        logger.debug(
            "Daily metrics updated",
            pnl=float(pnl),
            is_win=is_win,
            total_pnl=float(self.daily_metrics.total_pnl),
            win_rate=self.get_daily_win_rate()
        )

    def _check_win_rate_protection(self) -> bool:
        """Check if win rate is above threshold for trading."""
        if self.daily_metrics.total_trades < 10:
            return True  # Not enough data yet

        win_rate = self.get_daily_win_rate()
        threshold = self.params["win_rate_threshold"]

        return win_rate >= threshold

    def get_daily_win_rate(self) -> float:
        """Calculate current daily win rate."""
        if self.daily_metrics.total_trades == 0:
            return 0.0
        return self.daily_metrics.winning_trades / self.daily_metrics.total_trades

    def check_circuit_breaker(self) -> Optional[str]:
        """
        Check if circuit breaker should be triggered.
        
        Returns:
            Reason if circuit breaker should trigger, None otherwise
        """
        # Check daily loss limit
        daily_loss_limit = self.total_capital * Decimal(str(self.params["daily_loss_limit"]))
        if self.daily_metrics.total_pnl < -daily_loss_limit:
            return f"Daily loss limit exceeded: ${abs(self.daily_metrics.total_pnl):.2f}"

        # Check consecutive losses
        if self.daily_metrics.consecutive_losses >= 3:
            return f"Consecutive losses: {self.daily_metrics.consecutive_losses}"

        # Check maximum drawdown
        if self.daily_metrics.max_drawdown > self.total_capital * Decimal("0.25"):
            return f"Maximum drawdown exceeded: ${self.daily_metrics.max_drawdown:.2f}"

        # Check win rate
        if self.daily_metrics.total_trades >= 20 and self.get_daily_win_rate() < self.params["win_rate_threshold"]:
            return f"Win rate too low: {self.get_daily_win_rate():.1%}"

        return None

    def get_risk_summary(self) -> Dict[str, Any]:
        """Get comprehensive risk summary."""
        return {
            "tier": self.tier,
            "total_capital": float(self.total_capital),
            "open_positions": len(self.open_positions),
            "daily_pnl": float(self.daily_metrics.total_pnl),
            "daily_trades": self.daily_metrics.total_trades,
            "daily_win_rate": self.get_daily_win_rate(),
            "max_drawdown": float(self.daily_metrics.max_drawdown),
            "consecutive_losses": self.daily_metrics.consecutive_losses,
            "per_trade_risk_pct": self.params["per_trade_risk"],
            "daily_loss_limit_pct": self.params["daily_loss_limit"],
            "max_positions": self.params["max_positions"],
            "circuit_breaker": self.check_circuit_breaker()
        }

    def get_position_risk_metrics(self) -> List[Dict[str, any]]:
        """Get risk metrics for all open positions."""
        return [
            {
                "position_id": pos["id"],
                "size": float(pos["size"]),
                "age_minutes": (datetime.now() - pos["opened_at"]).total_seconds() / 60
            }
            for pos in self.open_positions
        ]
