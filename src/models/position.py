"""Position model for tracking open positions."""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin


class Position(Base, TimestampMixin):
    """Represents an open position in a Polymarket market."""

    __tablename__ = "positions"

    # Primary key
    id: Mapped[str] = mapped_column(String(255), primary_key=True, doc="Unique position ID")

    # Foreign keys
    market_id: Mapped[str] = mapped_column(
        String(255),
        ForeignKey("markets.id", ondelete="CASCADE"),
        nullable=False,
        doc="Market where position is held",
    )

    # Position details
    side: Mapped[str] = mapped_column(String(10), nullable=False, doc="BUY or SELL")
    size: Mapped[Decimal] = mapped_column(
        Numeric(18, 2), nullable=False, doc="Position size in USDC"
    )
    entry_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 8), nullable=False, doc="Entry price (0.0-1.0)"
    )

    # Current valuation
    current_price: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 8), nullable=True, doc="Current market price"
    )
    unrealized_pnl: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(18, 2), nullable=True, doc="Unrealized profit/loss in USDC"
    )

    # Timestamps
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, doc="When position opened"
    )
    closed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, doc="When position closed"
    )

    # Status
    is_open: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, doc="Whether position is still open"
    )

    # Strategy metadata
    strategy: Mapped[str] = mapped_column(
        String(50), nullable=False, doc="Strategy that opened this position"
    )
    entry_confidence: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 4), nullable=True, doc="Signal confidence at entry (0.0-1.0)"
    )
    entry_sentiment: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(6, 2), nullable=True, doc="Sentiment score at entry (-100 to +100)"
    )

    # Indexes
    __table_args__ = (
        Index("idx_positions_open", "is_open"),
        Index("idx_positions_market", "market_id"),
        Index("idx_positions_opened", "opened_at"),
    )

    @property
    def age_minutes(self) -> float:
        """Calculate position age in minutes."""
        if self.is_open:
            age_seconds = (datetime.now() - self.opened_at.replace(tzinfo=None)).total_seconds()
            return age_seconds / 60.0
        elif self.closed_at is not None:
            age_seconds = (self.closed_at.replace(tzinfo=None) - self.opened_at.replace(tzinfo=None)).total_seconds()
            return age_seconds / 60.0
        return 0.0

    @property
    def unrealized_pnl_pct(self) -> Optional[Decimal]:
        """Calculate unrealized P&L as percentage."""
        if self.unrealized_pnl is not None and self.size > Decimal("0"):
            return (self.unrealized_pnl / self.size) * Decimal("100")
        return None

    def update_pnl(self, current_price: Decimal) -> None:
        """Update current price and unrealized P&L."""
        self.current_price = current_price
        price_diff = current_price - self.entry_price

        if self.side.upper() == "BUY":
            self.unrealized_pnl = price_diff * self.size
        else:  # sell
            self.unrealized_pnl = -price_diff * self.size
