"""Trade model for executed trades."""

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class MarketSide(str, Enum):
    """Trading side enumeration."""

    BUY = "buy"
    SELL = "sell"


class StrategyType(str, Enum):
    """Trading strategy enumeration."""

    INTERVAL_15M = "interval_15m"
    WHALE_FRONTRUN = "whale_frontrun"
    MARKET_MAKING = "market_making"


class Trade(Base, TimestampMixin):
    """Represents an executed trade on Polymarket."""

    __tablename__ = "trades"

    # Primary key
    id: Mapped[str] = mapped_column(String(255), primary_key=True, doc="Unique trade ID")

    # Foreign keys
    order_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        doc="Associated order ID",
    )
    market_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("markets.id", ondelete="CASCADE"),
        nullable=False,
        doc="Market where trade was executed",
    )

    # Trade details
    side: Mapped[str] = mapped_column(String(10), nullable=False, doc="BUY or SELL")
    size: Mapped[Decimal] = mapped_column(Numeric(18, 2), nullable=False, doc="Trade size in USDC")
    price: Mapped[Decimal] = mapped_column(
        Numeric(10, 8), nullable=False, doc="Execution price (0.0-1.0)"
    )
    fee: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, default=Decimal("0"), doc="Trading fee in USDC"
    )

    # P&L tracking
    pnl: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2), nullable=True, doc="Realized profit/loss in USDC"
    )

    # Strategy classification
    strategy: Mapped[str] = mapped_column(
        String(50), nullable=False, doc="Strategy that generated this trade"
    )

    # Metadata
    confidence: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 4), nullable=True, doc="Signal confidence (0.0-1.0)"
    )
    sentiment_score: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2), nullable=True, doc="Sentiment score (-100 to +100)"
    )

    # Execution timestamp
    executed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, doc="When trade executed"
    )

    # Indexes
    __table_args__ = (
        Index("idx_trades_market", "market_id"),
        Index("idx_trades_executed", "executed_at"),
        Index("idx_trades_strategy", "strategy"),
    )

    def is_winner(self) -> bool:
        """Check if trade resulted in profit."""
        return self.pnl is not None and self.pnl > Decimal("0")

    def roi_pct(self) -> Optional[Decimal]:
        """Calculate ROI as percentage."""
        if self.pnl is not None and self.size > Decimal("0"):
            return (self.pnl / self.size) * Decimal("100")
        return None
